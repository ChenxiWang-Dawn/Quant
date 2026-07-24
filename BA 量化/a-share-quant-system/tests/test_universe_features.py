from pathlib import Path

import pandas as pd

from a_share_quant.alpha import AlphaEngine
from a_share_quant.config import load_strategy, load_universe
from a_share_quant.data import DatasetBundle
from a_share_quant.features import FeatureEngine
from a_share_quant.universe import UniverseEngine

ROOT = Path(__file__).resolve().parents[1]


def test_universe_feature_alpha_pipeline(demo_dataset) -> None:
    bundle = DatasetBundle.load(demo_dataset)
    as_of = bundle.trade_dates[-1]
    universe = UniverseEngine(
        load_universe(ROOT / "configs/universes/cn_a_share_liquid_v1.yaml")
    ).build(bundle, as_of)
    strategy = load_strategy(ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml")
    features = FeatureEngine(strategy.feature).compute(bundle, universe.members, as_of)
    scores = AlphaEngine(strategy.alpha).score(features)
    assert len(universe.members) == 48
    assert len(scores) == 48
    assert scores["alpha_rank"].is_unique
    assert scores.iloc[0]["alpha_rank"] == 1


def test_prepared_features_match_on_demand_features(demo_dataset) -> None:
    bundle = DatasetBundle.load(demo_dataset)
    as_of = bundle.trade_dates[-1]
    universe = UniverseEngine(
        load_universe(ROOT / "configs/universes/cn_a_share_liquid_v1.yaml")
    ).build(bundle, as_of)
    config = load_strategy(
        ROOT / "configs/strategies/a_share_regime_multifactor_v1.yaml"
    ).feature
    on_demand = FeatureEngine(config).compute(
        bundle, universe.members, as_of
    )
    prepared_engine = FeatureEngine(config)
    prepared_engine.prepare(bundle, {as_of})
    prepared = prepared_engine.compute(bundle, universe.members, as_of)
    columns = [
        "security_id",
        "mom20",
        "mom60",
        "mom120_20",
        "vol20",
        "breakout60",
        "ma20_distance",
        "ma60_distance",
        "quality_z",
        "value_z",
        "momentum_z",
        "earnings_z",
        "breakout_z",
        "risk_penalty_z",
    ]
    pd.testing.assert_frame_equal(
        on_demand[columns].sort_values("security_id").reset_index(drop=True),
        prepared[columns].sort_values("security_id").reset_index(drop=True),
        check_exact=False,
        rtol=1e-10,
        atol=1e-10,
    )
