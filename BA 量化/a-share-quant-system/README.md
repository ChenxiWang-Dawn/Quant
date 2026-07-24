# A Share Quant System

独立、组合原生的 A 股量化研究、回测与影子运行系统。代码、配置、数据契约、账本、任务和产物全部位于本项目中，不依赖工作区内其他量化项目。

系统实现了：

- 时间点正确的行情、财务数据和公司行动契约；
- A 股上市时间、价格、流动性、风险警示、退市、停牌过滤；
- 质量、估值、中期动量、盈利改善、量价突破与风险惩罚；
- 缩尾、缺失值处理、行业及市值中性化；
- 规则 Alpha、市场状态、Top-K 与约束优化组合；
- 单股、行业、流动性、回撤和总仓位风控；
- 次日成交、T+1、涨跌停、一字板、停牌、整手、费用、滑点、冲击与部分成交；
- 现金、持仓、分红送转、净值、绩效、行业归因与研究 Gate；
- 消融、成本压力、Purged Walk-Forward 和 Ridge 排序 Challenger；
- 可复现实验、SQLite 元数据、Parquet/JSON 产物、异步任务、取消与幂等；
- 每日影子运行、人工审核状态、只读订单预览、告警、CLI 与 FastAPI。

系统不会连接真实券商或自动提交订单。所有订单预览都标记为 `PENDING_HUMAN_REVIEW` 和 `broker_submission=disabled`。

## 安装

```bash
conda run -n quant python -m pip install -e ".[dev]"
```

## 五分钟验证

```bash
conda run -n quant a-share-quant generate-demo \
  --output storage/demo \
  --securities 80 \
  --days 520

conda run -n quant a-share-quant validate-data storage/demo

conda run -n quant a-share-quant backtest storage/demo \
  --start 2024-07-01 \
  --end 2025-12-31

conda run -n quant a-share-quant daily storage/demo \
  --as-of 2025-12-31
```

合成数据只用于验证软件行为，不能用于证明策略有效。

## 使用 RQData

系统的正式 A 股数据源为 RQData。先在本机完成 RQData 客户端授权配置，
凭据不会写入项目文件。同步默认使用中证 500 历史成分股并以中证 500 为基准：

```bash
conda run -n quant a-share-quant sync-rqdata \
  --start 2019-01-01 \
  --end 2026-06-30 \
  --output storage/rqdata

conda run -n quant a-share-quant validate-data storage/rqdata

conda run -n quant a-share-quant backtest storage/rqdata \
  --start 2020-01-01 \
  --end 2026-06-30
```

同步内容包括未复权成交价、前复权信号价、涨跌停、停牌、ST、总股本与
流通股本、点时可用财务因子、历史行业分类、基准和公司行动。重复同步默认
按主键增量合并；使用 `--replace` 可覆盖已有区间。开发时可通过
`--securities 600519.XSHG,000858.XSHE` 做小样本校验。

## 测试与质量检查

```bash
conda run -n quant pytest -q
conda run -n quant python -m ruff check src tests
```

## API

```bash
conda run -n quant a-share-quant serve --host 127.0.0.1 --port 8788
```

OpenAPI 文档位于 `http://127.0.0.1:8788/docs`。主要资源包括 capabilities、数据快照、股票池、回测任务、实验、影子运行、订单预览、监控和告警。

## 项目入口

- [完整规格](SPEC.md)
- [跨电脑 Codex 接续说明](HANDOFF.md)
- [运行手册](docs/RUNBOOK.md)
- [数据接入契约](docs/DATA_CONTRACT.md)
- [RQData 数据契约](docs/DATA_CONTRACT.md)
- `configs/`：版本化策略、股票池、执行和 Gate 配置
- `src/a_share_quant/`：独立 Python 包
- `tests/`：单元、制度场景、契约与端到端测试
- `artifacts/`：实验和影子运行产物，默认不入库
- `storage/`：本地数据和 SQLite 元数据，默认不入库

真实研究上线前，必须使用已授权的 RQData 数据，并完成样本外、成本压力、
容量和模拟盘 Gate。当前基线策略在真实中证 500 历史样本上未通过超额收益
Gate，详见 [接续说明](HANDOFF.md)；不要把它当成可实盘策略。
