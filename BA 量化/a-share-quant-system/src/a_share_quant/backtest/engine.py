from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from a_share_quant.accounting import Ledger
from a_share_quant.alpha import AlphaEngine
from a_share_quant.attribution import industry_return_attribution
from a_share_quant.contracts.models import BacktestRequest
from a_share_quant.data import DatasetBundle
from a_share_quant.evaluation import GateDecision, evaluate_gates
from a_share_quant.execution import ExecutionSimulator
from a_share_quant.features import FeatureEngine
from a_share_quant.metrics import evaluate_performance
from a_share_quant.portfolio import PortfolioBuilder
from a_share_quant.regime import RegimeEngine
from a_share_quant.risk import RiskEngine
from a_share_quant.universe import UniverseEngine


@dataclass(slots=True)
class BacktestResult:
    nav: pd.DataFrame
    fills: pd.DataFrame
    positions: pd.DataFrame
    signals: pd.DataFrame
    exclusions: pd.DataFrame
    attribution: pd.DataFrame
    metrics: dict[str, float | int]
    gate: GateDecision
    metadata: dict[str, str | int | float]


class BacktestEngine:
    def __init__(self, request: BacktestRequest) -> None:
        self.request = request
        self.universe = UniverseEngine(request.universe_config)
        self.features = FeatureEngine(request.strategy_config.feature)
        self.alpha = AlphaEngine(request.strategy_config.alpha)
        self.regime = RegimeEngine(request.strategy_config.regime)
        self.portfolio = PortfolioBuilder(request.strategy_config.portfolio)
        self.risk = RiskEngine(request.strategy_config.portfolio)
        self.execution = ExecutionSimulator(request.execution_profile)

    def run(
        self,
        bundle: DatasetBundle,
        progress: Callable[[float], None] | None = None,
    ) -> BacktestResult:
        dates = self._date_range(bundle)
        if not dates:
            raise ValueError("backtest date range has no trading days")
        rebalance_dates = self._rebalance_dates(dates)
        self.features.prepare(bundle, rebalance_dates)
        ledger = Ledger(self.request.initial_cash)
        pending_targets: pd.DataFrame | None = None
        pending_attempts = 0
        nav_rows: list[dict[str, object]] = []
        position_rows: list[pd.DataFrame] = []
        signal_rows: list[dict[str, object]] = []
        exclusion_rows: list[pd.DataFrame] = []
        actions_by_date = (
            {
                pd.Timestamp(date): frame
                for date, frame in bundle.corporate_actions.groupby("ex_date")
            }
            if not bundle.corporate_actions.empty
            else {}
        )

        for index, trade_date in enumerate(dates):
            ledger.start_day()
            actions = actions_by_date.get(trade_date)
            if actions is not None:
                ledger.apply_corporate_actions(actions)
            day_bars = bundle.bars_on(trade_date)
            if pending_targets is not None and not pending_targets.empty:
                fills = self.execution.execute_targets(
                    trade_date, pending_targets, day_bars, ledger
                )
                pending_attempts += 1
                requested = [fill for fill in fills if fill.requested_quantity > 0]
                complete = bool(requested) and all(
                    fill.status == "FILLED" for fill in requested
                )
                if complete or pending_attempts >= 3:
                    pending_targets = None
                    pending_attempts = 0
            close_prices = dict(
                zip(day_bars["security_id"].astype(str), day_bars["close_raw"].astype(float))
            )
            ledger.mark(close_prices)
            nav_rows.append({
                "trade_date": trade_date,
                "nav": ledger.nav,
                "cash": ledger.cash,
                "gross_exposure": sum(position.market_value for position in ledger.positions.values())
                / max(ledger.nav, 1e-12),
                "positions": len(ledger.positions),
            })
            day_positions = ledger.positions_frame()
            if not day_positions.empty:
                day_positions["trade_date"] = trade_date
                position_rows.append(day_positions)

            if trade_date in rebalance_dates:
                universe = self.universe.build(bundle, trade_date)
                if not universe.exclusions.empty:
                    exclusions = universe.exclusions.copy()
                    exclusions["as_of"] = trade_date
                    exclusion_rows.append(exclusions)
                feature_frame = self.features.compute(bundle, universe.members, trade_date)
                scored = self.alpha.score(feature_frame)
                regime = self.regime.classify(bundle, trade_date)
                peak_nav = max(float(row["nav"]) for row in nav_rows)
                drawdown = max(0.0, 1.0 - ledger.nav / max(peak_nav, 1e-12))
                effective_exposure = (
                    regime.target_exposure
                    * self.risk.drawdown_exposure_multiplier(drawdown)
                )
                portfolio = self.portfolio.build(
                    scored, effective_exposure, ledger.weights()
                )
                risk_report = self.risk.validate(portfolio.target_weights, ledger.nav)
                if not risk_report.passed:
                    raise RuntimeError(
                        "risk validation failed: " + ", ".join(risk_report.violations)
                    )
                pending_targets = portfolio.target_weights.copy()
                pending_attempts = 0
                signal_rows.append({
                    "as_of": trade_date,
                    "regime": regime.state,
                    "target_exposure": regime.target_exposure,
                    "effective_exposure": effective_exposure,
                    "portfolio_drawdown": drawdown,
                    "breadth": regime.breadth,
                    "benchmark_volatility": regime.volatility,
                    "universe_size": len(universe.members),
                    "target_holdings": len(portfolio.target_weights),
                    "one_way_turnover": portfolio.diagnostics.get("one_way_turnover", 0.0),
                    "top_security": (
                        str(scored.iloc[0]["security_id"]) if not scored.empty else ""
                    ),
                    "top_score": (
                        float(scored.iloc[0]["alpha_score"]) if not scored.empty else np.nan
                    ),
                })
            if progress:
                progress((index + 1) / len(dates))

        nav = pd.DataFrame(nav_rows)
        metrics = evaluate_performance(nav, self.request.initial_cash)
        metrics.update(self._benchmark_metrics(bundle, nav))
        gate = evaluate_gates(
            metrics, self.request.gate_config,
            enforce_benchmark_checks=not bundle.benchmark.empty,
        )
        fills = pd.DataFrame([asdict(fill) for fill in ledger.fills])
        if not fills.empty:
            metrics["transaction_cost"] = float(
                fills[["commission", "stamp_tax", "transfer_fee"]].sum().sum()
            )
            metrics["slippage_and_impact_cost"] = float(
                fills[["slippage_cost", "impact_cost"]].sum().sum()
            )
            metrics["rejected_orders"] = int((fills["status"] == "REJECTED").sum())
        positions = (
            pd.concat(position_rows, ignore_index=True)
            if position_rows else ledger.positions_frame()
        )
        signals = pd.DataFrame(signal_rows)
        exclusions = (
            pd.concat(exclusion_rows, ignore_index=True)
            if exclusion_rows else pd.DataFrame()
        )
        attribution = industry_return_attribution(
            positions,
            nav,
            bundle.bars,
            bundle.securities,
            bundle.industry_history,
        )
        return BacktestResult(
            nav, fills, positions, signals, exclusions, attribution, metrics, gate,
            {
                "dataset_fingerprint": bundle.fingerprint,
                "strategy_id": self.request.strategy_config.id,
                "strategy_version": self.request.strategy_config.version,
                "execution_profile": self.request.execution_profile.id,
                "start": str(dates[0].date()),
                "end": str(dates[-1].date()),
                "trading_days": len(dates),
            },
        )

    def _date_range(self, bundle: DatasetBundle) -> list[pd.Timestamp]:
        dates = list(bundle.trade_dates)
        if self.request.start:
            dates = [item for item in dates if item >= pd.Timestamp(self.request.start)]
        if self.request.end:
            dates = [item for item in dates if item <= pd.Timestamp(self.request.end)]
        return dates

    def _rebalance_dates(self, dates: list[pd.Timestamp]) -> set[pd.Timestamp]:
        frame = pd.DataFrame({"trade_date": dates})
        calendar = frame["trade_date"].dt.isocalendar()
        frame["year"] = calendar.year
        frame["week"] = calendar.week
        preferred = frame[
            frame["trade_date"].dt.weekday == self.request.strategy_config.rebalance_weekday
        ]
        selected: list[pd.Timestamp] = list(preferred["trade_date"])
        covered = set(zip(preferred["year"], preferred["week"]))
        for key, group in frame.groupby(["year", "week"]):
            if key not in covered:
                selected.append(group["trade_date"].max())
        return set(selected)

    @staticmethod
    def _benchmark_metrics(
        bundle: DatasetBundle, nav: pd.DataFrame
    ) -> dict[str, float]:
        if bundle.benchmark.empty or nav.empty:
            return {}
        benchmark = bundle.benchmark.copy()
        price_column = "close" if "close" in benchmark else "close_raw"
        joined = nav[["trade_date", "nav"]].merge(
            benchmark[["trade_date", price_column]], on="trade_date", how="inner"
        )
        if len(joined) < 2:
            return {}
        strategy_return = joined["nav"].pct_change()
        benchmark_return = joined[price_column].pct_change()
        active = (strategy_return - benchmark_return).dropna()
        days = max((joined["trade_date"].iloc[-1] - joined["trade_date"].iloc[0]).days, 1)
        benchmark_annualized = float(
            (joined[price_column].iloc[-1] / joined[price_column].iloc[0])
            ** (365.25 / days) - 1
        )
        strategy_annualized = float(
            (joined["nav"].iloc[-1] / joined["nav"].iloc[0]) ** (365.25 / days) - 1
        )
        tracking_error = float(active.std(ddof=0) * np.sqrt(252))
        return {
            "benchmark_annualized_return": benchmark_annualized,
            "annualized_excess_return": strategy_annualized - benchmark_annualized,
            "tracking_error": tracking_error,
            "information_ratio": (
                float(active.mean() * 252 / tracking_error) if tracking_error > 0 else 0.0
            ),
        }
