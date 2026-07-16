import tempfile
import unittest
from pathlib import Path

import numpy as np

import app
from research_platform import AIPlatform, ResearchStore


class ResearchPlatformTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.platform = AIPlatform(ResearchStore(Path(self.tempdir.name) / "research.db"), True)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_rl_environment_cost_is_monotonic(self):
        result = self.platform.rl_validate({"prices": [100, 104, 101, 106, 108, 105], "actions": [0, 1, .2, 1, 0]})
        self.assertEqual(result["status"], "passed")
        check = next(item for item in result["checks"] if item["name"] == "成本单调性")
        self.assertEqual(check["status"], "passed")

    def test_copilot_returns_real_platform_citations_without_external_calls(self):
        trace = self.platform.copilot({"mode": "review", "role": "experiment_reviewer", "question": "如何检查时间切分和成本？"})
        self.assertGreaterEqual(len(trace["citations"]), 1)
        self.assertEqual(trace["usage"]["externalCalls"], 0)
        self.assertIn("不执行交易", trace["boundary"])

    def test_model_cannot_bypass_gate(self):
        result = {"id": "ai_test", "status": "completed", "engine": "test", "configHash": "c", "dataFingerprint": "d", "split": {"trainEnd": "2020-01-01"}, "metrics": {"totalReturn": -.1, "benchmarkReturn": .1, "rebalances": 1}, "model": {"name": "test", "card": {}}, "dataset": {"featureNames": []}}
        self.platform.record_experiment(result, {})
        model = self.platform.register_model({"experimentId": "ai_test"})
        with self.assertRaises(ValueError):
            self.platform.promote_model(model["id"], {"status": "validated", "reason": "should fail"})

    def test_training_features_are_past_only(self):
        rows = [{"date": f"2020-01-{day:02d}", "open": 100 + day, "high": 101 + day, "low": 99 + day, "close": 100 + day, "volume": 1000 + day * 10} for day in range(1, 29)]
        original = app.ai_feature_frame(rows, "000001.XSHE", "测试", 5)
        changed_rows = [dict(row) for row in rows]
        for row in changed_rows[20:]:
            row["close"] *= 10
            row["volume"] *= 10
        changed = app.ai_feature_frame(changed_rows, "000001.XSHE", "测试", 5)
        columns = app.AI_FEATURES
        np.testing.assert_allclose(original.loc[:19, columns].fillna(0), changed.loc[:19, columns].fillna(0))


if __name__ == "__main__":
    unittest.main()
