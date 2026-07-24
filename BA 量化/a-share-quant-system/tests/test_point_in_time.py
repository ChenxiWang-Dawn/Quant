import pandas as pd

from a_share_quant.data import DatasetBundle


def test_future_fundamental_revision_is_not_visible(demo_dataset) -> None:
    bundle = DatasetBundle.load(demo_dataset)
    security_id = bundle.fundamentals.iloc[0]["security_id"]
    original = bundle.fundamentals[bundle.fundamentals["security_id"] == security_id].iloc[0]
    future = original.copy()
    future["available_time"] = pd.Timestamp("2030-01-01")
    future["revision_time"] = pd.Timestamp("2030-01-01")
    future["roe_ttm"] = 999.0
    bundle.fundamentals = pd.concat(
        [bundle.fundamentals, pd.DataFrame([future])], ignore_index=True
    )
    latest = bundle.latest_fundamentals(pd.Timestamp("2025-12-31"))
    assert float(latest.loc[security_id, "roe_ttm"]) != 999.0
