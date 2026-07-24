import numpy as np
import pandas as pd

from a_share_quant.contracts.models import AlphaConfig, ExecutionProfile
from a_share_quant.ml import RidgeRankChallenger
from a_share_quant.research import (
    PurgedWalkForwardSplit,
    ablation_alpha_configs,
    execution_stress_profiles,
)


def test_purged_split_and_robustness_configs() -> None:
    splits = list(PurgedWalkForwardSplit(100, 20, 10).split(180))
    assert splits
    for train, test in splits:
        assert train.max() + 10 < test.min()
    assert len(ablation_alpha_configs(AlphaConfig())) == 6
    assert execution_stress_profiles(ExecutionProfile())["cost_2x"].slippage_rate == 0.001


def test_ridge_challenger_fit_predict_explain() -> None:
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({
        "quality_z": rng.normal(size=100),
        "momentum_z": rng.normal(size=100),
    })
    frame["forward_excess_return"] = (
        0.02 * frame["quality_z"] + 0.01 * frame["momentum_z"]
    )
    model = RidgeRankChallenger(regularization=0.1).fit(frame)
    prediction = model.predict(frame)
    assert prediction.corr(frame["forward_excess_return"]) > 0.99
    assert set(model.explain()["feature"]) == {"quality_z", "momentum_z"}
