from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Board(StrEnum):
    MAIN = "main"
    CHINEXT = "chinext"
    STAR = "star"


class JobStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYABLE_FAILED = "retryable_failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class UniverseConfig(FrozenModel):
    version: str = "cn_a_share_liquid_v1.0.0"
    min_listing_days: int = Field(default=250, ge=0)
    min_price_cny: float = Field(default=3.0, ge=0)
    min_adv20_cny: float = Field(default=50_000_000, ge=0)
    min_valid_days_20: int = Field(default=15, ge=1, le=20)
    exclude_risk_warning: bool = True
    exclude_delisting: bool = True
    exclude_suspended: bool = True
    allowed_boards: tuple[Board, ...] = (Board.MAIN, Board.CHINEXT, Board.STAR)


class FeatureConfig(FrozenModel):
    winsor_lower: float = Field(default=0.01, ge=0, lt=0.5)
    winsor_upper: float = Field(default=0.99, gt=0.5, le=1)
    neutralize_industry: bool = True
    neutralize_log_market_cap: bool = True

    @model_validator(mode="after")
    def validate_quantiles(self) -> FeatureConfig:
        if self.winsor_lower >= self.winsor_upper:
            raise ValueError("winsor_lower must be smaller than winsor_upper")
        return self


class AlphaConfig(FrozenModel):
    quality_weight: float = 0.25
    value_weight: float = 0.20
    momentum_weight: float = 0.25
    earnings_event_weight: float = 0.15
    breakout_weight: float = 0.15
    penalty_weight: float = 1.0

    @model_validator(mode="after")
    def validate_weights(self) -> AlphaConfig:
        positive = (
            self.quality_weight
            + self.value_weight
            + self.momentum_weight
            + self.earnings_event_weight
            + self.breakout_weight
        )
        if abs(positive - 1.0) > 1e-9:
            raise ValueError("positive alpha weights must sum to 1")
        if max(
            self.quality_weight,
            self.value_weight,
            self.momentum_weight,
            self.earnings_event_weight,
            self.breakout_weight,
        ) > 0.35:
            raise ValueError("single alpha sleeve weight cannot exceed 35%")
        return self


class RegimeConfig(FrozenModel):
    fast_window: int = Field(default=60, ge=5)
    slow_window: int = Field(default=120, ge=20)
    volatility_window: int = Field(default=20, ge=5)
    high_volatility: float = Field(default=0.035, gt=0)
    risk_on_exposure: float = Field(default=0.95, ge=0, le=1)
    neutral_exposure: float = Field(default=0.75, ge=0, le=1)
    risk_off_exposure: float = Field(default=0.50, ge=0, le=1)

    @model_validator(mode="after")
    def validate_windows(self) -> RegimeConfig:
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        if not self.risk_off_exposure <= self.neutral_exposure <= self.risk_on_exposure:
            raise ValueError("regime exposures must be ordered")
        return self


class PortfolioConfig(FrozenModel):
    builder: Literal["topk", "optimized"] = "topk"
    target_holdings: int = Field(default=40, ge=1)
    exit_rank: int = Field(default=70, ge=1)
    max_stock_weight: float = Field(default=0.03, gt=0, le=1)
    max_sector_weight: float = Field(default=0.20, gt=0, le=1)
    max_weekly_one_way_turnover: float = Field(default=0.25, gt=0, le=2)
    max_adv_participation: float = Field(default=0.05, gt=0, le=1)

    @model_validator(mode="after")
    def validate_portfolio(self) -> PortfolioConfig:
        if self.exit_rank < self.target_holdings:
            raise ValueError("exit_rank must be at least target_holdings")
        return self


class ExecutionProfile(FrozenModel):
    id: str = "cn_a_share_base_2026"
    trade_price: Literal["open", "vwap_proxy"] = "vwap_proxy"
    commission_rate: float = Field(default=0.0003, ge=0)
    minimum_commission: float = Field(default=5.0, ge=0)
    sell_stamp_tax_rate: float = Field(default=0.0005, ge=0)
    transfer_fee_rate: float = Field(default=0.00001, ge=0)
    slippage_rate: float = Field(default=0.0005, ge=0)
    impact_coefficient: float = Field(default=0.001, ge=0)
    lot_size: int = Field(default=100, ge=1)
    max_adv_participation: float = Field(default=0.05, gt=0, le=1)
    simulate_t_plus_one: bool = True
    simulate_price_limits: bool = True


class GateConfig(FrozenModel):
    id: str = "gate_research_v1"
    min_annualized_excess_return: float = 0.0
    min_information_ratio: float = 0.6
    max_drawdown: float = Field(default=0.25, gt=0, le=1)
    require_adverse_cost_positive_excess: bool = True
    max_single_year_contribution: float = Field(default=0.35, gt=0, le=1)
    max_single_industry_contribution: float = Field(default=0.35, gt=0, le=1)


class StrategyConfig(FrozenModel):
    id: str = "a_share_regime_multifactor_v1"
    version: str = "1.0.0"
    rebalance_weekday: int = Field(default=4, ge=0, le=4)
    target_holdings: int = Field(default=40, ge=1)
    feature: FeatureConfig = Field(default_factory=FeatureConfig)
    alpha: AlphaConfig = Field(default_factory=AlphaConfig)
    regime: RegimeConfig = Field(default_factory=RegimeConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)


class BacktestRequest(FrozenModel):
    dataset: str
    start: date | None = None
    end: date | None = None
    initial_cash: float = Field(default=1_000_000, gt=0)
    strategy_config: StrategyConfig = Field(default_factory=StrategyConfig)
    universe_config: UniverseConfig = Field(default_factory=UniverseConfig)
    execution_profile: ExecutionProfile = Field(default_factory=ExecutionProfile)
    gate_config: GateConfig = Field(default_factory=GateConfig)
    idempotency_key: str | None = None


class JobRecord(BaseModel):
    id: str
    kind: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    progress: float = Field(default=0, ge=0, le=1)
    request_json: dict[str, Any]
    result_ref: str | None = None
    error_code: str | None = None
    error_message: str | None = None
