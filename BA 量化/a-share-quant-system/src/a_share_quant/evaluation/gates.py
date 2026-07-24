from __future__ import annotations

from dataclasses import dataclass

from a_share_quant.contracts.models import GateConfig


@dataclass(slots=True)
class GateDecision:
    passed: bool
    checks: dict[str, bool]
    reasons: list[str]


def evaluate_gates(
    metrics: dict[str, float | int],
    gate: GateConfig,
    *,
    enforce_benchmark_checks: bool = False,
) -> GateDecision:
    checks = {
        "maximum_drawdown": float(metrics.get("maximum_drawdown", 1.0)) <= gate.max_drawdown,
        "annualized_excess_return": (
            float(metrics.get("annualized_excess_return", 0.0))
            >= gate.min_annualized_excess_return
            if enforce_benchmark_checks else True
        ),
        "information_ratio": (
            float(metrics.get("information_ratio", 0.0)) >= gate.min_information_ratio
            if enforce_benchmark_checks else True
        ),
    }
    reasons = [name for name, passed in checks.items() if not passed]
    return GateDecision(not reasons, checks, reasons)
