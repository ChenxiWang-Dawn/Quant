from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from .contracts.models import ExecutionProfile, GateConfig, StrategyConfig, UniverseConfig

T = TypeVar("T", bound=BaseModel)


def load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"configuration must be a mapping: {path}")
    return payload


def load_model(path: str | Path, model_type: type[T]) -> T:
    return model_type.model_validate(load_yaml(path))


def load_strategy(path: str | Path) -> StrategyConfig:
    return load_model(path, StrategyConfig)


def load_universe(path: str | Path) -> UniverseConfig:
    return load_model(path, UniverseConfig)


def load_execution(path: str | Path) -> ExecutionProfile:
    return load_model(path, ExecutionProfile)


def load_gate(path: str | Path) -> GateConfig:
    return load_model(path, GateConfig)
