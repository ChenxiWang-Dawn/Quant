from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from a_share_quant.contracts.models import AlphaConfig, ExecutionProfile


@dataclass(slots=True, frozen=True)
class PurgedWalkForwardSplit:
    train_size: int
    test_size: int
    purge_size: int = 20
    step_size: int | None = None

    def split(self, sample_count: int):
        step = self.step_size or self.test_size
        test_start = self.train_size + self.purge_size
        while test_start < sample_count:
            train_end = test_start - self.purge_size
            train_start = max(0, train_end - self.train_size)
            test_end = min(test_start + self.test_size, sample_count)
            yield (
                np.arange(train_start, train_end, dtype=int),
                np.arange(test_start, test_end, dtype=int),
            )
            test_start += step


def execution_stress_profiles(base: ExecutionProfile) -> dict[str, ExecutionProfile]:
    return {
        "base": base,
        "cost_1_5x": base.model_copy(update={
            "commission_rate": base.commission_rate * 1.5,
            "slippage_rate": base.slippage_rate * 1.5,
            "impact_coefficient": base.impact_coefficient * 1.5,
        }),
        "cost_2x": base.model_copy(update={
            "commission_rate": base.commission_rate * 2.0,
            "slippage_rate": base.slippage_rate * 2.0,
            "impact_coefficient": base.impact_coefficient * 2.0,
        }),
    }


def ablation_alpha_configs(base: AlphaConfig) -> dict[str, AlphaConfig]:
    fields = [
        "quality_weight", "value_weight", "momentum_weight",
        "earnings_event_weight", "breakout_weight",
    ]
    result = {"full": base}
    raw = base.model_dump()
    for removed in fields:
        update = {field: float(raw[field]) for field in fields}
        update[removed] = 0.0
        total = sum(update.values())
        update = {field: value / total for field, value in update.items()}
        update["penalty_weight"] = base.penalty_weight
        result[f"without_{removed.removesuffix('_weight')}"] = AlphaConfig(**update)
    return result
