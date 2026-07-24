from pathlib import Path

from a_share_quant.config import load_execution, load_strategy, load_universe

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_configs_load() -> None:
    strategy = load_strategy(ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml")
    universe = load_universe(ROOT / "configs/universes/cn_a_share_liquid_v1.yaml")
    execution = load_execution(ROOT / "configs/execution/cn_a_share_base_2026.yaml")
    assert strategy.portfolio.target_holdings == 40
    assert universe.exclude_risk_warning is True
    assert execution.simulate_t_plus_one is True
