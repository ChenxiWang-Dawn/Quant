# 运行手册

## 1. 安全边界

本系统只运行研究回测、影子组合和只读订单预览。没有券商适配器、交易凭证字段或自动报单端点。任何准备进入实盘的工作都必须作为独立变更重新评审。

## 2. 日常流程

1. 在本机配置 RQData 客户端认证，认证信息不得放入仓库。
2. 运行 `sync-rqdata` 更新指定区间的数据快照。
3. 运行 `validate-data`。失败时不得继续。
4. 运行 `daily` 生成股票池、分数、目标权重和人工审核状态。
5. 检查 `artifacts/experiments/<daily-run-id>/daily_summary.json`。
6. 检查 SQLite 中未确认告警。
7. 由人工决定是否将预览转录到外部流程；本系统不会代为提交。

## 3. 回测流程

1. 固定数据目录和配置文件。
2. 使用明确的开始、结束日期运行 `backtest`。
3. 检查 manifest 中的数据哈希、策略版本、执行配置和 Gate。
4. 不得仅凭单次收益曲线晋级。继续执行成本 1.5 倍、2 倍压力，子信号消融和 Purged Walk-Forward。
5. Gate 失败的结果仍会保存，以防止只保留成功实验。

## 4. API 作业

向 `POST /v1/backtests` 提交 `BacktestRequest` 后，通过 `GET /v1/jobs/{id}` 轮询。状态顺序为 queued、validating、running、evaluating、completed；失败会保留错误类型和消息。相同 idempotency key 返回原作业。

`POST /v1/jobs/{id}/cancel` 会取消尚未开始的作业，或向运行中作业发送协作式取消信号。

## 5. 产物

每个实验目录至少包括：

- request.json；
- nav、fills、positions、signals、exclusions、attribution Parquet；
- summary.json；
- gate.json；
- manifest.json。

manifest 是结果索引；大表不嵌入 API JSON。

## 6. 故障处理

- 数据健康失败：停止运行，修复缺列、重复、OHLC、复权因子或可用时点。
- 无可投资股票：检查历史长度、停牌状态和流动性阈值，不得静默放宽规则。
- 风险检查失败：结果阻断，不生成可审核组合。
- 优化器失败：组合模块回退到受约束 Top-K，并在诊断中标记。
- API 作业失败：读取作业错误和审计记录；用新 idempotency key 重跑修复后的请求。
- 元数据数据库损坏：停止写入，从备份恢复；不要删除实验产物。

## 7. 发布检查

- `pytest -q` 全部通过；
- `ruff check src tests` 全部通过；
- 演示数据的两次回测结果一致；
- 数据泄漏、T+1、涨跌停和公司行动测试通过；
- 配置与代码版本冻结；
- 明确记录真实数据许可、基准、容量与成本假设。

## 8. 新机器恢复

完整步骤、已知基线和下一阶段研究边界见项目根目录
`HANDOFF.md`。`storage/` 与 `artifacts/` 不进入 Git；新机器必须从 RQData
重新同步数据并重新生成实验产物。
