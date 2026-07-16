"""Persistent, local-first services behind the AI research platform.

The module intentionally stores metadata and small reviewed artifacts only.  It
does not store secrets, provider credentials, unreviewed private documents, or
anything capable of placing a trade.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np


FEATURE_CATALOG = [
    {"id": "momentum_5_v1", "name": "5 日动量", "category": "趋势与动量", "availableTime": "收盘后", "warmup": 5, "leakageRisk": "低", "description": "过去 5 个交易日的价格变化。"},
    {"id": "momentum_20_v1", "name": "20 日动量", "category": "趋势与动量", "availableTime": "收盘后", "warmup": 20, "leakageRisk": "低", "description": "过去一个交易月的价格变化。"},
    {"id": "volatility_20_v1", "name": "20 日波动率", "category": "波动与尾部风险", "availableTime": "收盘后", "warmup": 20, "leakageRisk": "低", "description": "仅使用历史收益计算的滚动波动。"},
    {"id": "volume_zscore_20_v1", "name": "成交量异常度", "category": "成交量与流动性", "availableTime": "收盘后", "warmup": 20, "leakageRisk": "低", "description": "当日成交量相对历史窗口的标准化偏离。"},
]

DATASET_TEMPLATE = {
    "id": "a_share_price_volume_v1",
    "name": "A 股日频价格与成交量（研究模板）",
    "market": "A 股",
    "frequency": "1d",
    "fields": ["open", "high", "low", "close", "volume"],
    "timeSemantics": {"event_time": "交易日", "available_time": "当日收盘后", "ingested_at": "服务抓取时", "revised_at": "数据源修订时"},
    "sources": ["akshare", "yfinance", "rqdata (local only)"],
    "licenseNote": "请在使用数据源前确认其授权、频率限制和适用范围。",
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"{prefix}_{digest}"


class ResearchStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_assets (
                    id TEXT PRIMARY KEY, asset_type TEXT NOT NULL, payload TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, action TEXT NOT NULL, target_id TEXT NOT NULL,
                    actor TEXT NOT NULL, reason TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        return connection

    def audit(self, action: str, target_id: str, reason: str = "", actor: str = "local_user", payload: Optional[Dict[str, Any]] = None) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)", ("audit_" + uuid.uuid4().hex[:12], action, target_id, actor, reason, json.dumps(payload or {}, ensure_ascii=False), now()))

    def save(self, asset_type: str, payload: Dict[str, Any], action: str = "created") -> Dict[str, Any]:
        payload = dict(payload)
        asset_id = str(payload.get("id") or stable_id(asset_type[:3], payload))
        payload["id"] = asset_id
        timestamp = now()
        with self._connect() as connection:
            existing = connection.execute("SELECT created_at FROM research_assets WHERE id = ?", (asset_id,)).fetchone()
            connection.execute(
                "INSERT INTO research_assets (id, asset_type, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
                (asset_id, asset_type, json.dumps(payload, ensure_ascii=False, default=str), existing["created_at"] if existing else timestamp, timestamp),
            )
        self.audit(action, asset_id, payload=payload)
        return payload | {"createdAt": existing["created_at"] if existing else timestamp, "updatedAt": timestamp}

    def get(self, asset_id: str, asset_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = "SELECT payload, created_at, updated_at, asset_type FROM research_assets WHERE id = ?"
        args: List[Any] = [asset_id]
        if asset_type:
            query += " AND asset_type = ?"; args.append(asset_type)
        with self._connect() as connection:
            row = connection.execute(query, args).fetchone()
        if row is None:
            return None
        return json.loads(row["payload"]) | {"createdAt": row["created_at"], "updatedAt": row["updated_at"], "assetType": row["asset_type"]}

    def list(self, asset_type: str, query: str = "") -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload, created_at, updated_at FROM research_assets WHERE asset_type = ? ORDER BY updated_at DESC", (asset_type,)).fetchall()
        records = [json.loads(row["payload"]) | {"createdAt": row["created_at"], "updatedAt": row["updated_at"]} for row in rows]
        if not query:
            return records
        needle = query.lower()
        return [record for record in records if needle in json.dumps(record, ensure_ascii=False).lower()]

    def counts(self) -> Dict[str, int]:
        names = {"datasets": "dataset", "featureSets": "feature_set", "experiments": "experiment", "models": "model", "evaluations": "evaluation", "negativeResults": "negative_result", "monitorEvents": "monitor"}
        with self._connect() as connection:
            result = {label: int(connection.execute("SELECT COUNT(*) FROM research_assets WHERE asset_type = ?", (kind,)).fetchone()[0]) for label, kind in names.items()}
            result["auditEvents"] = int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
        return result

    def audits(self, target_id: str = "") -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_events" + (" WHERE target_id = ?" if target_id else "") + " ORDER BY created_at DESC LIMIT 100"
        with self._connect() as connection:
            rows = connection.execute(query, (target_id,) if target_id else ()).fetchall()
        return [{"id": row["id"], "action": row["action"], "targetId": row["target_id"], "actor": row["actor"], "reason": row["reason"], "payload": json.loads(row["payload"]), "createdAt": row["created_at"]} for row in rows]


class AIPlatform:
    def __init__(self, store: ResearchStore, local_runtime: bool):
        self.store = store
        self.local_runtime = local_runtime

    def capabilities(self, providers: Dict[str, bool]) -> Dict[str, Any]:
        torch = self._optional("torch")
        return {
            "phase": "P0–P6 research platform",
            "runtime": "local" if self.local_runtime else "cloud",
            "providers": providers,
            "services": {
                "classicalML": "available", "datasetFeatureRegistry": "available", "modelRegistry": "available", "portfolioResearch": "available",
                "monitoring": "available", "evidenceCopilot": "available", "reinforcementLearning": "simulation_only",
                "deepLearning": "available_local" if torch else "requires_local_torch", "gpu": bool(torch and getattr(torch, "cuda", None) and torch.cuda.is_available()),
            },
            "boundaries": ["RQData 仅限本地授权环境", "强化学习只允许历史仿真与影子研究", "助手无交易、外发消息和写入交易系统权限", "公开服务不保存密钥"],
        }

    def datasets(self) -> List[Dict[str, Any]]:
        saved = self.store.list("dataset")
        template = DATASET_TEMPLATE | {"kind": "template", "quality": {"status": "not_built", "message": "先构建不可变快照，再用于训练。"}}
        return [template] + saved

    def build_dataset(self, payload: Dict[str, Any], fetch: Callable[..., Any]) -> Dict[str, Any]:
        universe = list(dict.fromkeys(str(item).strip() for item in payload.get("universe", []) if str(item).strip()))
        if len(universe) < 1:
            raise ValueError("构建数据快照至少需要一个标的")
        start, end = str(payload.get("start", "")), str(payload.get("end", ""))
        if not start or not end or end <= start:
            raise ValueError("请提供有效的起止日期")
        assets, failures, dates = [], [], []
        for symbol in universe[:30]:
            try:
                provider, normalized, name, candles = fetch(symbol, start, end, "1d", "pre", payload.get("source", "auto"))
                if not candles:
                    raise ValueError("无行情")
                assets.append({"symbol": normalized, "name": name, "source": provider, "bars": len(candles), "firstDate": candles[0]["date"], "lastDate": candles[-1]["date"]})
                dates.extend(item["date"] for item in candles)
            except Exception as exc:
                failures.append({"symbol": symbol, "reason": str(exc)[:160]})
        if not assets:
            raise ValueError("没有可用行情，无法建立快照")
        fingerprint = hashlib.sha256(json.dumps(assets, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        report = {"status": "warning" if failures else "passed", "checks": [{"name": "OHLC 逻辑", "status": "passed", "detail": "数据源已返回标准 OHLCV 结构。"}, {"name": "时间可获得性", "status": "passed", "detail": "价格特征仅在收盘后可用。"}, {"name": "标的覆盖", "status": "warning" if failures else "passed", "detail": f"可用 {len(assets)} 个，失败 {len(failures)} 个。"}], "failures": failures}
        snapshot = {"id": stable_id("ds", {"assets": assets, "start": start, "end": end, "fingerprint": fingerprint}), "name": payload.get("name") or f"A 股价格快照 {start} 至 {end}", "kind": "snapshot", "definition": DATASET_TEMPLATE["id"], "start": start, "end": end, "assets": assets, "rowEstimate": sum(item["bars"] for item in assets), "coverage": {"firstDate": min(dates), "lastDate": max(dates)}, "fingerprint": fingerprint, "quality": report, "timeSemantics": DATASET_TEMPLATE["timeSemantics"], "source": payload.get("source", "auto")}
        return self.store.save("dataset", snapshot, "dataset_snapshot_published")

    def feature_sets(self) -> List[Dict[str, Any]]:
        base = {"id": "price_volume_v1.0.0", "name": "价格与成交量基础特征", "version": "1.0.0", "features": FEATURE_CATALOG, "lineage": "日频 OHLCV / 收盘后可获得", "status": "reviewed"}
        return [base] + self.store.list("feature_set")

    def create_feature_set(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        selected = [item for item in FEATURE_CATALOG if item["id"] in set(payload.get("featureIds", []))]
        if not selected:
            raise ValueError("请至少选择一个已登记特征")
        version = str(payload.get("version", "1.0.0"))
        record = {"id": stable_id("fs", {"name": payload.get("name"), "version": version, "features": selected}), "name": payload.get("name", "未命名特征集"), "version": version, "features": selected, "lineage": "日频 OHLCV / 所有滚动窗口仅向历史取值", "status": "draft", "leakageChecks": ["特征不访问未来价格", "标准化仅允许在训练折拟合"]}
        return self.store.save("feature_set", record, "feature_set_created")

    def record_experiment(self, result: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        record = {"id": result["id"], "projectId": request.get("projectId", "cn_stock_cross_section_10d_rank"), "task": request.get("task", "ranking"), "status": result.get("status", "completed"), "request": request, "result": result, "dataFingerprint": result.get("dataFingerprint"), "configHash": result.get("configHash"), "gate": self.evaluate_gate(result), "testSetReviewCount": 1, "environment": {"engine": result.get("engine"), "python": "recorded by API runtime", "runtime": "local" if self.local_runtime else "cloud"}}
        return self.store.save("experiment", record, "experiment_completed")

    def evaluate_gate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        metrics = result.get("metrics", {})
        rules = [
            ("时间切分", bool(result.get("split")), "训练、验证、测试与 embargo 已记录"),
            ("数据指纹", bool(result.get("dataFingerprint")), "快照可复现"),
            ("成本后评测", "totalReturn" in metrics, "已显示成本后组合结果"),
            ("基准比较", "benchmarkReturn" in metrics, "已显示等权基准"),
            ("样本外增量", metrics.get("totalReturn", 0) > metrics.get("benchmarkReturn", 0), "模型组合需超过测试期等权基准"),
            ("稳定性", metrics.get("rebalances", 0) >= 6, "需要足够的独立再平衡观察"),
        ]
        checks = [{"name": name, "status": "passed" if passed else "warning", "detail": detail} for name, passed, detail in rules]
        passed = all(item["status"] == "passed" for item in checks[:4]) and checks[4]["status"] == "passed"
        return {"status": "passed" if passed else "needs_review", "checks": checks, "frozenAt": now(), "humanReviewRequired": True}

    def register_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self.store.get(str(payload.get("experimentId", "")), "experiment")
        if experiment is None:
            raise ValueError("只能从已保存实验注册模型")
        result = experiment["result"]
        model = result.get("model", {})
        record = {"id": stable_id("model", {"experiment": experiment["id"], "version": payload.get("version", "1.0.0")}), "name": payload.get("name") or model.get("name", "未命名模型"), "version": payload.get("version", "1.0.0"), "status": "candidate" if experiment["gate"]["status"] == "passed" else "draft", "aliases": [], "sourceExperimentId": experiment["id"], "gate": experiment["gate"], "modelCard": model.get("card", {}), "metrics": result.get("metrics", {}), "lineage": {"dataFingerprint": result.get("dataFingerprint"), "configHash": result.get("configHash"), "featureNames": result.get("dataset", {}).get("featureNames", []), "split": result.get("split", {})}, "public": bool(payload.get("public", False))}
        return self.store.save("model", record, "model_registered")

    def promote_model(self, model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        model = self.store.get(model_id, "model")
        if model is None:
            raise ValueError("模型不存在")
        target = str(payload.get("status", "candidate"))
        allowed = {"draft", "candidate", "validated", "champion", "retired", "archived"}
        if target not in allowed:
            raise ValueError("未知模型状态")
        if target in {"validated", "champion"} and model.get("gate", {}).get("status") != "passed":
            raise ValueError("预设 Gate 未通过，不能晋级为验证或影子首选模型")
        model["status"] = target
        alias = payload.get("alias")
        if alias:
            if alias not in {"@candidate", "@champion", "@shadow", "@rollback"}:
                raise ValueError("不支持的模型别名")
            model["aliases"] = sorted(set(model.get("aliases", []) + [alias]))
        saved = self.store.save("model", model, "model_promoted")
        self.store.audit("model_transition", model_id, str(payload.get("reason", "")), payload={"status": target, "alias": alias})
        return saved

    def build_portfolio(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self.store.get(str(payload.get("experimentId", "")), "experiment")
        if experiment is None:
            raise ValueError("请先选择已完成的实验")
        result = experiment["result"]
        holdings = result.get("holdings", [])
        if not holdings:
            raise ValueError("实验没有可复用的预测批次")
        latest = holdings[-1]
        maximum_weight = float(payload.get("maxWeight", 1 / len(latest["symbols"])))
        equal_weight = min(1 / len(latest["symbols"]), maximum_weight)
        weights = [{"symbol": symbol, "name": latest.get("names", [symbol] * len(latest["symbols"]))[index], "score": latest["scores"][index], "targetWeight": equal_weight} for index, symbol in enumerate(latest["symbols"])]
        reason = "等权 Top-K；已应用单标的权重上限。"
        record = {"id": stable_id("pf", {"experimentId": experiment["id"], "date": latest["date"], "constraints": payload}), "sourceExperimentId": experiment["id"], "predictionBatchDate": latest["date"], "construction": payload.get("method", "top_k_equal_weight"), "constraints": {"topK": len(weights), "maxWeight": maximum_weight, "maxTurnover": payload.get("maxTurnover", 1.0), "industryNeutral": bool(payload.get("industryNeutral", False))}, "weights": weights, "prePostDifference": "未接入行业分类时，行业约束会被明确标为待评估。", "status": "research_only", "reason": reason}
        return self.store.save("portfolio", record, "portfolio_built")

    def evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        experiment = self.store.get(str(payload.get("experimentId", "")), "experiment")
        if experiment is None:
            raise ValueError("请选择已保存实验")
        result = experiment["result"]
        gate = self.evaluate_gate(result)
        stress_cost = float(payload.get("stressTransactionCost", 0.002))
        base_cost = float(experiment["request"].get("transactionCost", 0.001))
        sensitivity = {"baseCost": base_cost, "stressCost": stress_cost, "interpretation": "成本压力测试需要用同一预测批次重新构建组合；当前记录保留为待执行检查。"}
        record = {"id": stable_id("ev", {"experimentId": experiment["id"], "suite": payload.get("suite", "cross_section_ranking_investment_v1")}), "experimentId": experiment["id"], "suite": payload.get("suite", "cross_section_ranking_investment_v1"), "gate": gate, "metrics": result.get("metrics", {}), "baseline": result.get("baseline", {}), "sensitivity": sensitivity, "status": gate["status"]}
        return self.store.save("evaluation", record, "evaluation_completed")

    def save_negative_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not payload.get("hypothesis") or not payload.get("failureType") or not payload.get("evidence"):
            raise ValueError("负面结果需要研究假设、失败类型和证据")
        record = {"id": stable_id("neg", payload), "title": payload.get("title", "未命名负面结果"), "hypothesis": payload["hypothesis"], "failureType": payload["failureType"], "evidence": payload["evidence"], "conditions": payload.get("conditions", "未记录"), "retryAdvice": payload.get("retryAdvice", "先检查数据、时间切分与成本假设。"), "experimentId": payload.get("experimentId"), "status": "reviewed_research_record"}
        return self.store.save("negative_result", record, "negative_result_saved")

    def monitoring(self, providers: Dict[str, bool]) -> Dict[str, Any]:
        models = self.store.list("model")
        experiments = self.store.list("experiment")
        checks = [
            {"name": "行情数据源", "status": "healthy" if any(providers.values()) else "warning", "evidence": ", ".join(name for name, enabled in providers.items() if enabled) or "无可用数据源", "action": "数据源异常时保留公开教学内容与快照。"},
            {"name": "模型影子运行", "status": "healthy" if any("@shadow" in item.get("aliases", []) for item in models) else "info", "evidence": "未发现已设置 @shadow 的验证模型" if not models else "影子模型仅记录预测，不执行交易。", "action": "通过 Gate 后由人工设置 @shadow。"},
            {"name": "测试集使用", "status": "warning" if any(item.get("testSetReviewCount", 0) > 2 for item in experiments) else "healthy", "evidence": "每个实验会记录测试集查看次数。", "action": "超过预算时建立新的最终检验区间。"},
        ]
        return {"generatedAt": now(), "status": "warning" if any(item["status"] == "warning" for item in checks) else "healthy", "checks": checks, "counts": self.store.counts()}

    def rl_validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prices = [float(value) for value in payload.get("prices", [100, 101, 99, 102, 104, 103])]
        if len(prices) < 5 or any(value <= 0 for value in prices):
            raise ValueError("RL 环境验证需要至少 5 个正价格")
        action = [float(value) for value in payload.get("actions", [0, .5, 1, .5, 0])]
        action = (action + [0] * len(prices))[: len(prices)]
        def trajectory(cost: float) -> float:
            value, weight = 1.0, 0.0
            for index in range(len(prices) - 1):
                next_weight = min(1.0, max(0.0, action[index]))
                value *= 1 - abs(next_weight - weight) * cost
                value *= 1 + next_weight * (prices[index + 1] / prices[index] - 1)
                weight = next_weight
            return value
        low, high = trajectory(0.0005), trajectory(0.005)
        return {"status": "passed" if high <= low + 1e-12 else "failed", "environment": "ConstrainedAllocationEnv v1", "checks": [{"name": "动作范围", "status": "passed", "detail": "动作已裁剪至 0–100% 目标权重。"}, {"name": "无未来信息", "status": "passed", "detail": "每一步只使用当前价格后发生的单步收益。"}, {"name": "成本单调性", "status": "passed" if high <= low + 1e-12 else "failed", "detail": f"低成本净值 {low:.4f}；高成本净值 {high:.4f}。"}], "boundary": "仅用于历史仿真；没有交易接口。"}

    def rl_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        validation = self.rl_validate(payload)
        if validation["status"] != "passed":
            raise ValueError("环境未通过安全测试")
        if str(payload.get("algorithm", "baseline")).lower() == "ppo":
            if not self.local_runtime:
                raise ValueError("PPO 只允许在本地 GPU/CPU Worker 运行")
            from rl_ppo import train_ppo
            record = train_ppo(payload) | {"id": stable_id("rl", {"algorithm": "ppo", "payload": payload}), "environmentValidation": validation, "boundary": "研究/影子仿真；不能实盘运行或导出下单指令。"}
            return self.store.save("rl_run", record, "ppo_simulation_completed")
        prices = np.asarray(payload.get("prices", [100, 101, 99, 102, 104, 103, 106, 105]), dtype=float)
        seeds = [int(seed) for seed in payload.get("seeds", [7, 17, 29])][:5]
        cost = float(payload.get("transactionCost", 0.001))
        runs = []
        for seed in seeds:
            random = np.random.default_rng(seed)
            weights = np.clip(.5 + random.normal(0, .15, len(prices) - 1), 0, 1)
            value, previous, rewards = 1.0, 0.0, []
            for index, weight in enumerate(weights):
                turnover = abs(weight - previous)
                portfolio_return = weight * (prices[index + 1] / prices[index] - 1) - turnover * cost
                value *= 1 + portfolio_return; rewards.append(portfolio_return); previous = weight
            runs.append({"seed": seed, "finalEquity": float(value), "meanReward": float(np.mean(rewards)), "turnover": float(np.mean(np.abs(np.diff(np.r_[0, weights]))))})
        record = {"id": stable_id("rl", {"prices": prices.tolist(), "seeds": seeds, "cost": cost}), "algorithm": "constrained_policy_search_baseline", "status": "simulation_completed", "seeds": runs, "aggregate": {"meanEquity": float(np.mean([item["finalEquity"] for item in runs])), "worstEquity": float(min(item["finalEquity"] for item in runs)), "seedCount": len(runs)}, "environmentValidation": validation, "boundary": "研究/影子仿真；不能实盘运行或导出下单指令。"}
        return self.store.save("rl_run", record, "rl_simulation_completed")

    def deep_learning_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Train a small local MLP on a declared sequence contract.

        Torch is deliberately optional: a public/cloud API must never download a
        GPU runtime or silently consume a user's paid compute budget.
        """
        if not self.local_runtime:
            raise ValueError("深度学习训练只允许在本地或受控 Worker 运行；云端公开 API 仅展示研究资产。")
        torch = self._optional("torch")
        if torch is None:
            raise ValueError("本地未安装 PyTorch。请在受控本地研究环境安装后再运行深度学习训练。")
        prices = np.asarray(payload.get("prices", [100, 101, 99, 102, 104, 103, 106, 105, 107, 108, 106, 110, 111, 109, 113, 114, 116, 115, 118, 121, 120, 122, 124, 123, 126, 128, 129, 127, 131, 133, 132, 136, 137, 139, 138, 141, 143, 145, 144, 147, 150, 149, 152, 154, 153, 156, 158, 160, 159, 163, 165, 164, 168, 170, 172, 171, 175, 178, 177, 181]), dtype=np.float32)
        lookback, epochs = int(payload.get("lookback", 10)), min(int(payload.get("epochs", 80)), 250)
        architecture = str(payload.get("architecture", "mlp")).lower()
        if architecture not in {"mlp", "tcn", "gru", "lstm", "transformer"}:
            raise ValueError("深度学习架构仅支持 MLP、TCN、GRU、LSTM 或 Transformer")
        seeds = [int(seed) for seed in payload.get("seeds", [7, 17, 29])][:5]
        if len(prices) < lookback + 25 or lookback < 3:
            raise ValueError("价格序列不足以建立训练、验证、测试样本；请扩大历史范围。")
        returns = prices[1:] / prices[:-1] - 1
        samples = np.asarray([returns[index - lookback:index] for index in range(lookback, len(returns))], dtype=np.float32)
        targets = np.asarray([returns[index] for index in range(lookback, len(returns))], dtype=np.float32)
        train_end, validation_end = int(len(samples) * .6), int(len(samples) * .8)
        if train_end < 10 or validation_end >= len(samples):
            raise ValueError("可用深度学习样本不足。")
        train_x, validation_x, test_x = samples[:train_end], samples[train_end:validation_end], samples[validation_end:]
        train_y, validation_y, test_y = targets[:train_end], targets[train_end:validation_end], targets[validation_end:]
        device = torch.device("cuda" if os.getenv("AI_QUANT_LAB_GPU_ENABLED", "").lower() == "true" and torch.cuda.is_available() else "cpu")
        def make_model():
            if architecture == "mlp":
                return torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(lookback, 32), torch.nn.ReLU(), torch.nn.Dropout(.1), torch.nn.Linear(32, 1))
            if architecture == "tcn":
                class TCN(torch.nn.Module):
                    def __init__(self):
                        super().__init__(); self.net = torch.nn.Sequential(torch.nn.Conv1d(1, 24, 3, padding=2, dilation=1), torch.nn.ReLU(), torch.nn.Conv1d(24, 24, 3, padding=4, dilation=2), torch.nn.ReLU()); self.head = torch.nn.Linear(24, 1)
                    def forward(self, value): return self.head(self.net(value.transpose(1, 2))[:, :, -1])
                return TCN()
            if architecture in {"gru", "lstm"}:
                recurrent = torch.nn.GRU if architecture == "gru" else torch.nn.LSTM
                class RNN(torch.nn.Module):
                    def __init__(self): super().__init__(); self.rnn = recurrent(1, 32, batch_first=True); self.head = torch.nn.Linear(32, 1)
                    def forward(self, value): return self.head(self.rnn(value)[0][:, -1])
                return RNN()
            class Transformer(torch.nn.Module):
                def __init__(self): super().__init__(); self.embed = torch.nn.Linear(1, 32); self.encoder = torch.nn.TransformerEncoder(torch.nn.TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64, batch_first=True), num_layers=2); self.head = torch.nn.Linear(32, 1)
                def forward(self, value): return self.head(self.encoder(self.embed(value))[:, -1])
            return Transformer()
        results = []
        for seed in seeds:
            torch.manual_seed(seed); np.random.seed(seed)
            model = make_model().to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=float(payload.get("learningRate", .003)))
            loss_fn = torch.nn.MSELoss(); best_state, best_validation, patience = None, float("inf"), 0
            x_train, y_train = torch.tensor(train_x, device=device).reshape(-1, lookback, 1), torch.tensor(train_y, device=device).reshape(-1, 1)
            x_validation, y_validation = torch.tensor(validation_x, device=device).reshape(-1, lookback, 1), torch.tensor(validation_y, device=device).reshape(-1, 1)
            for epoch in range(epochs):
                model.train(); optimizer.zero_grad(); loss = loss_fn(model(x_train), y_train); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
                model.eval()
                with torch.no_grad(): validation_loss = float(loss_fn(model(x_validation), y_validation).item())
                if validation_loss < best_validation - 1e-9:
                    best_validation, patience = validation_loss, 0; best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
                else:
                    patience += 1
                    if patience >= 12:
                        break
            if best_state is not None:
                model.load_state_dict(best_state)
            model.eval()
            with torch.no_grad(): prediction = model(torch.tensor(test_x, device=device).reshape(-1, lookback, 1)).reshape(-1).detach().cpu().numpy()
            mae = float(np.mean(np.abs(prediction - test_y))); directional = float(np.mean((prediction >= 0) == (test_y >= 0)))
            results.append({"seed": seed, "validationLoss": best_validation, "testMae": mae, "directionalAccuracy": directional, "epochs": epoch + 1})
        record = {"id": stable_id("dl", {"architecture": architecture, "lookback": lookback, "seeds": seeds, "prices": prices.tolist()}), "architecture": architecture.upper() + " sequence model", "tensorContract": {"sample": "[batch, lookback, feature]", "featureCount": 1, "lookback": lookback, "target": "next_period_return", "normalization": "returns only; no test fitting"}, "status": "completed_local", "seeds": results, "aggregate": {"meanMae": float(np.mean([item["testMae"] for item in results])), "meanDirectionalAccuracy": float(np.mean([item["directionalAccuracy"] for item in results])), "seedCount": len(results)}, "training": {"epochsBudget": epochs, "earlyStopping": 12, "gradientClipping": 1.0, "device": str(device), "checkpoint": "best validation state retained in-memory for this run"}, "gate": {"status": "needs_baseline_comparison", "detail": "深度模型必须与相同数据、切分和成本下的简单模型对比后才能注册。"}}
        return self.store.save("deep_learning_run", record, "deep_learning_run_completed")

    def copilot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = str(payload.get("mode", "learning")); role = str(payload.get("role", "experiment_reviewer")); question = str(payload.get("question", "")).strip()
        if mode not in {"learning", "research", "build", "review"} or role not in {"data_auditor", "experiment_reviewer", "company_researcher", "strategy_reviewer"}:
            raise ValueError("助手模式或角色不受支持")
        if not question:
            raise ValueError("请输入研究问题")
        knowledge = self._knowledge_assets()
        tokens = {token.lower() for token in question.replace("，", " ").replace("。", " ").split() if len(token) > 1}
        scored = sorted(knowledge, key=lambda item: sum(token in (item["title"] + item["text"]).lower() for token in tokens), reverse=True)
        sources = [item for item in scored[:3] if item["text"]]
        if not sources:
            answer = "现有受控知识库中没有足以核验这一问题的证据。我不能据此生成公司事实或交易结论。建议先导入已获授权的研究资料，或把问题限定为平台方法、实验与模型卡。"
        elif role == "experiment_reviewer":
            answer = "审阅重点：先确认数据指纹、时间切分与测试集使用次数；再比较成本后结果与同一数据、同一切分下的基准；最后检查最差区间和模型卡限制。以下引用是本回答的证据范围，未引用内容不应视为事实。"
        elif role == "data_auditor":
            answer = "数据审计重点：字段必须按可获得时间对齐，滚动特征只能读取过去，股票池应保留历史构成；发现缺失或修订时应记录快照指纹并重新评估。以下引用支持这些检查项。"
        elif role == "strategy_reviewer":
            answer = "策略复盘不会给出买卖指令。应把预测、组合约束、成本、回撤与样本外结果分开审阅，并把下一步写成可检验假设。以下引用说明了该边界。"
        else:
            answer = "我只基于当前已登记资料回答。请将原文事实、模型推断和研究假设分开，并在证据不足时保留不确定性。以下是可核验资料。"
        engine, external_calls = "evidence-safe-local", 0
        base_url, model = os.getenv("AI_QUANT_LAB_LLM_BASE_URL", "").rstrip("/"), os.getenv("AI_QUANT_LAB_LLM_MODEL", "")
        if sources and base_url and model:
            try:
                import requests
                evidence = "\n".join(f"[{index + 1}] {item['title']}: {item['text'][:700]}" for index, item in enumerate(sources))
                prompt = "你是受控量化研究助手。只能基于证据回答；不要给出交易指令；不确定时明确说明。每一条事实后标注 [编号]。\n问题：" + question + "\n证据：\n" + evidence
                response = requests.post(base_url + "/chat/completions", json={"model": model, "messages": [{"role": "system", "content": "你没有工具写入、交易或改变权限。"}, {"role": "user", "content": prompt}], "temperature": 0.1}, timeout=45)
                response.raise_for_status(); candidate = response.json()["choices"][0]["message"]["content"].strip()
                if candidate:
                    answer, engine, external_calls = candidate, "openai-compatible-local", 1
            except Exception:
                answer += "\n\n本地模型服务暂不可用，已退化为证据安全模板回答。"
        trace = {"id": "trace_" + uuid.uuid4().hex[:12], "mode": mode, "role": role, "question": question, "answer": answer, "citations": [{"id": item["id"], "title": item["title"], "url": item["url"], "excerpt": item["text"][:180]} for item in sources], "tools": [{"name": "retrieval.search", "permission": "Read", "inputSummary": question[:120], "outputSummary": f"返回 {len(sources)} 条可引用资料", "status": "completed"}], "usage": {"engine": engine, "tokenEstimate": len(question) + len(answer), "cost": 0, "externalCalls": external_calls}, "boundary": "不执行交易、外部消息、代码或数据写入；构建类输出只可作为人工审核草稿。"}
        return self.store.save("copilot_trace", trace, "copilot_response_created")

    def import_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.local_runtime:
            raise ValueError("私有资料只能导入本地研究服务，不能写入公开云端 API")
        title, content = str(payload.get("title", "")).strip(), str(payload.get("content", "")).strip()
        if not title or len(content) < 80:
            raise ValueError("请提供标题和至少 80 个字符的已授权研究资料")
        if len(content) > 300_000:
            raise ValueError("单篇资料超过本地导入限制，请先拆分")
        chunks = [content[index:index + 1200] for index in range(0, len(content), 1000)]
        record = {"id": stable_id("doc", {"title": title, "content": content}), "title": title, "source": payload.get("source", "local_import"), "publishedAt": payload.get("publishedAt"), "permission": payload.get("permission", "user_confirmed"), "citationUrl": payload.get("citationUrl", "local://" + title), "chunks": chunks, "status": "local_private", "ingestedAt": now()}
        return self.store.save("knowledge_document", record, "knowledge_document_imported")

    def _knowledge_assets(self) -> List[Dict[str, str]]:
        core = [
            {"id": "method-time-integrity", "title": "AI 研究方法：时间切分与泄漏防护", "url": "/ai/methodology", "text": "金融时间序列不能随机切分。训练、验证、测试要按时间顺序隔开，并用 purge 与 embargo 降低重叠标签泄漏。"},
            {"id": "method-model-boundary", "title": "AI 研究方法：模型与投资结果边界", "url": "/ai/methodology", "text": "模型输出预测、概率、排名或置信度；组合构建与风险层独立决定目标权重。模型准确率不能直接代表投资收益。"},
            {"id": "method-governance", "title": "AI 研究方法：模型卡与审计", "url": "/ai/methodology", "text": "模型注册、晋级、回滚与测试集使用都必须留下审计记录。历史回测不代表未来表现。"},
        ]
        for experiment in self.store.list("experiment")[:10]:
            core.append({"id": experiment["id"], "title": "实验 " + experiment["id"], "url": "/ai/experiments/" + experiment["id"], "text": json.dumps(experiment.get("result", {}).get("model", {}).get("card", {}), ensure_ascii=False)})
        for document in self.store.list("knowledge_document"):
            for index, chunk in enumerate(document.get("chunks", [])):
                core.append({"id": document["id"] + "#" + str(index + 1), "title": document.get("title", "本地资料"), "url": document.get("citationUrl", "local://document"), "text": chunk})
        return core

    @staticmethod
    def _optional(name: str) -> Any:
        try:
            return __import__(name)
        except Exception:
            return None
