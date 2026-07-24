from __future__ import annotations

import pandas as pd

from a_share_quant.contracts.models import AlphaConfig


class AlphaEngine:
    def __init__(self, config: AlphaConfig) -> None:
        self.config = config

    def score(self, features: pd.DataFrame) -> pd.DataFrame:
        if features.empty:
            return features.copy()
        scored = features.copy()
        scored["alpha_score"] = (
            self.config.quality_weight * scored["quality_z"]
            + self.config.value_weight * scored["value_z"]
            + self.config.momentum_weight * scored["momentum_z"]
            + self.config.earnings_event_weight * scored["earnings_z"]
            + self.config.breakout_weight * scored["breakout_z"]
            - self.config.penalty_weight * scored["risk_penalty_z"]
        )
        scored["alpha_rank"] = scored["alpha_score"].rank(
            method="first", ascending=False
        ).astype(int)
        return scored.sort_values(["alpha_rank", "security_id"]).reset_index(drop=True)
