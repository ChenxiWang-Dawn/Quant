from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class RidgeRankChallenger:
    regularization: float = 10.0
    feature_names: tuple[str, ...] = ()
    coefficients: np.ndarray | None = None
    means: np.ndarray | None = None
    scales: np.ndarray | None = None

    def fit(
        self,
        frame: pd.DataFrame,
        label: str = "forward_excess_return",
        feature_names: list[str] | None = None,
    ) -> RidgeRankChallenger:
        feature_names = feature_names or [
            column for column in frame.columns if column.endswith("_z")
        ]
        clean = frame.dropna(subset=[label, *feature_names])
        if len(clean) <= len(feature_names):
            raise ValueError("insufficient clean samples for challenger training")
        matrix = clean[feature_names].to_numpy(dtype=float)
        target = clean[label].to_numpy(dtype=float)
        means = matrix.mean(axis=0)
        scales = matrix.std(axis=0)
        scales[scales <= 1e-12] = 1.0
        standardized = (matrix - means) / scales
        design = np.column_stack([np.ones(len(standardized)), standardized])
        penalty = np.eye(design.shape[1]) * self.regularization
        penalty[0, 0] = 0.0
        coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ target)
        self.feature_names = tuple(feature_names)
        self.coefficients = coefficients
        self.means = means
        self.scales = scales
        return self

    def predict(self, frame: pd.DataFrame) -> pd.Series:
        if self.coefficients is None or self.means is None or self.scales is None:
            raise RuntimeError("challenger has not been fitted")
        matrix = frame[list(self.feature_names)].fillna(0.0).to_numpy(dtype=float)
        standardized = (matrix - self.means) / self.scales
        design = np.column_stack([np.ones(len(standardized)), standardized])
        return pd.Series(design @ self.coefficients, index=frame.index, name="ml_score")

    def explain(self) -> pd.DataFrame:
        if self.coefficients is None:
            raise RuntimeError("challenger has not been fitted")
        return pd.DataFrame({
            "feature": self.feature_names,
            "coefficient": self.coefficients[1:],
            "absolute_importance": np.abs(self.coefficients[1:]),
        }).sort_values("absolute_importance", ascending=False)
