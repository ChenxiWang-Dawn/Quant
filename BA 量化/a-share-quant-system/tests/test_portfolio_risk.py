import numpy as np
import pandas as pd

from a_share_quant.contracts.models import PortfolioConfig
from a_share_quant.portfolio import PortfolioBuilder
from a_share_quant.risk import RiskEngine


def test_portfolio_caps_and_exposure() -> None:
    frame = pd.DataFrame({
        "security_id": [f"S{i}" for i in range(40)],
        "alpha_score": np.linspace(2, -2, 40),
        "alpha_rank": np.arange(1, 41),
        "industry": [f"I{i % 8}" for i in range(40)],
        "adv20": 100_000_000,
        "vol20": 0.25,
    })
    config = PortfolioConfig()
    result = PortfolioBuilder(config).build(frame, 0.75)
    report = RiskEngine(config).validate(result.target_weights, 1_000_000)
    assert report.passed
    assert abs(result.target_weights["target_weight"].sum() - 0.75) < 1e-9
    assert result.target_weights["target_weight"].max() <= 0.03
