from fastapi.testclient import TestClient

from a_share_quant.api import create_app
from a_share_quant.storage.metadata import MetadataStore


def test_api_health_and_metadata_idempotency(tmp_path) -> None:
    database = tmp_path / "system.db"
    store = MetadataStore(database)
    first = store.create_job("backtest", {"x": 1}, "same-key")
    second = store.create_job("backtest", {"x": 2}, "same-key")
    assert first.id == second.id
    client = TestClient(create_app(tmp_path / "artifacts", database))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["broker_submission"] == "disabled"
