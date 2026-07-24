from pathlib import Path

from a_share_quant.backtest import BacktestEngine
from a_share_quant.config import load_execution, load_gate, load_strategy, load_universe
from a_share_quant.contracts.models import BacktestRequest
from a_share_quant.data import DatasetBundle

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end_backtest_is_deterministic(demo_dataset) -> None:
    request = BacktestRequest(
        dataset=str(demo_dataset),
        initial_cash=1_000_000,
        universe_config=load_universe(ROOT / "configs/universes/cn_a_share_liquid_v1.yaml"),
        strategy_config=load_strategy(ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml"),
        execution_profile=load_execution(ROOT / "configs/execution/cn_a_share_base_2026.yaml"),
        gate_config=load_gate(ROOT / "configs/gates/research_v1.yaml"),
    )
    bundle = DatasetBundle.load(demo_dataset)
    first = BacktestEngine(request).run(bundle)
    second = BacktestEngine(request).run(bundle)
    assert len(first.nav) == 300
    assert first.metrics["end_nav"] == second.metrics["end_nav"]
    assert len(first.signals) > 0
    assert set(first.fills["side"]) <= {"BUY", "SELL"}
