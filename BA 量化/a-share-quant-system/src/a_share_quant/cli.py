from __future__ import annotations

import json
from pathlib import Path

import typer

from a_share_quant.api import create_app
from a_share_quant.config import load_execution, load_gate, load_strategy, load_universe
from a_share_quant.contracts.models import BacktestRequest
from a_share_quant.daily import DailyPipeline
from a_share_quant.data import DatasetBundle, RQDataAdapter, RQDataSyncConfig
from a_share_quant.demo import generate_demo_dataset
from a_share_quant.monitoring import data_health
from a_share_quant.services import RunService

app = typer.Typer(no_args_is_help=True, help="独立 A 股量化研究、回测与影子运行系统。")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _paths() -> tuple[Path, Path, Path, Path]:
    return (
        PROJECT_ROOT / "configs/universes/cn_a_share_liquid_v1.yaml",
        PROJECT_ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml",
        PROJECT_ROOT / "configs/execution/cn_a_share_base_2026.yaml",
        PROJECT_ROOT / "configs/gates/research_v1.yaml",
    )


@app.command("generate-demo")
def generate_demo(
    output: Path = typer.Option(PROJECT_ROOT / "storage/demo", help="输出数据目录"),
    securities: int = typer.Option(80, min=10),
    days: int = typer.Option(760, min=260),
) -> None:
    bundle = generate_demo_dataset(output, securities_count=securities, trading_days=days)
    typer.echo(json.dumps({
        "dataset": str(output),
        "fingerprint": bundle.fingerprint,
        "securities": len(bundle.securities),
        "bars": len(bundle.bars),
    }, ensure_ascii=False, indent=2))


@app.command("validate-data")
def validate_data(dataset: Path) -> None:
    bundle = DatasetBundle.load(dataset)
    typer.echo(json.dumps(data_health(bundle), ensure_ascii=False, indent=2))


@app.command("sync-rqdata")
def sync_rqdata(
    start: str = typer.Option(..., help="开始日期，YYYY-MM-DD"),
    end: str = typer.Option(..., help="结束日期，YYYY-MM-DD"),
    output: Path = typer.Option(
        PROJECT_ROOT / "storage/rqdata", help="输出数据目录"
    ),
    universe_index: str = typer.Option(
        "000905.XSHG", help="历史成分股指数；all 表示全部 A 股"
    ),
    benchmark: str = typer.Option("000905.XSHG", help="业绩基准"),
    securities: str = typer.Option(
        "", help="可选，逗号分隔证券代码；设置后覆盖指数股票池"
    ),
    chunk_size: int = typer.Option(300, min=1, max=1000),
    replace: bool = typer.Option(False, help="覆盖式同步，不合并已有数据"),
) -> None:
    security_ids = tuple(
        item.strip() for item in securities.split(",") if item.strip()
    )

    def progress(stage: str, ratio: float) -> None:
        typer.echo(f"[{ratio:6.1%}] {stage}")

    bundle = RQDataAdapter().sync(
        output,
        RQDataSyncConfig(
            start=start,
            end=end,
            universe_index=universe_index,
            benchmark_id=benchmark,
            security_ids=security_ids,
            chunk_size=chunk_size,
            incremental=not replace,
        ),
        progress=progress,
    )
    typer.echo(json.dumps({
        "dataset": str(output),
        "source": bundle.source,
        "fingerprint": bundle.fingerprint,
        "securities": len(bundle.securities),
        "bars": len(bundle.bars),
        "fundamentals": len(bundle.fundamentals),
        "industry_history": len(bundle.industry_history),
        "corporate_actions": len(bundle.corporate_actions),
    }, ensure_ascii=False, indent=2))


@app.command("backtest")
def backtest(
    dataset: Path,
    start: str | None = typer.Option(None),
    end: str | None = typer.Option(None),
    initial_cash: float = typer.Option(1_000_000, min=1),
) -> None:
    universe_path, strategy_path, execution_path, gate_path = _paths()
    request = BacktestRequest(
        dataset=str(dataset),
        start=start,
        end=end,
        initial_cash=initial_cash,
        universe_config=load_universe(universe_path),
        strategy_config=load_strategy(strategy_path),
        execution_profile=load_execution(execution_path),
        gate_config=load_gate(gate_path),
    )
    service = RunService(PROJECT_ROOT / "artifacts", PROJECT_ROOT / "storage/metadata/system.db")
    run_id, result, refs = service.run_backtest(request)
    typer.echo(json.dumps({
        "run_id": run_id,
        "metrics": result.metrics,
        "gate": {
            "passed": result.gate.passed,
            "checks": result.gate.checks,
            "reasons": result.gate.reasons,
        },
        "manifest": refs["manifest"],
    }, ensure_ascii=False, indent=2))


@app.command("daily")
def daily(dataset: Path, as_of: str | None = typer.Option(None)) -> None:
    universe_path, strategy_path, execution_path, _ = _paths()
    pipeline = DailyPipeline(
        load_universe(universe_path),
        load_strategy(strategy_path),
        load_execution(execution_path),
        PROJECT_ROOT / "artifacts",
        PROJECT_ROOT / "storage/metadata/system.db",
    )
    result = pipeline.run(dataset, as_of)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))


@app.command("experiments")
def experiments() -> None:
    service = RunService(PROJECT_ROOT / "artifacts", PROJECT_ROOT / "storage/metadata/system.db")
    typer.echo(json.dumps(service.metadata.list_experiments(), ensure_ascii=False, indent=2))


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8788, min=1, max=65535),
) -> None:
    import uvicorn

    uvicorn.run(create_app(
        PROJECT_ROOT / "artifacts",
        PROJECT_ROOT / "storage/metadata/system.db",
    ), host=host, port=port)


if __name__ == "__main__":
    app()
