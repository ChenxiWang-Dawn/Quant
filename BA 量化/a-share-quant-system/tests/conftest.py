from __future__ import annotations

from pathlib import Path

import pytest

from a_share_quant.demo import generate_demo_dataset


@pytest.fixture(scope="session")
def demo_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("dataset")
    generate_demo_dataset(root, securities_count=48, trading_days=300, seed=7)
    return root
