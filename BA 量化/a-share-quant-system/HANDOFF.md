# 跨电脑 Codex 接续说明

本文档是另一台电脑上的 Codex 的唯一接续入口。项目是独立的 A 股量化研究、
回测与影子运行系统，正式数据源仅为 RQData，不依赖聚宽或工作区中的其他系统。

## 1. 当前状态

- Python 版本：3.11 或更高；
- 包入口：`a-share-quant`；
- 正式数据源：RQData；
- 默认股票池与基准：中证 500，代码 `000905.XSHG`；
- 数据按历史成分股并集同步，避免当前成分股幸存者偏差；
- 成交使用未复权价格，信号使用前复权价格；
- 已接入历史停牌、ST、涨跌停、股本、市值、点时因子、行业和公司行动；
- 回测模拟次日成交、T+1、整手、费用、滑点、冲击、涨跌停与部分成交；
- 技术指标按全区间一次性向量化预计算，横截面因子批量中性化；
- 系统不会连接券商，订单只进入人工审核预览。

## 2. 新机器首次启动

在仓库根目录执行：

```bash
cd "BA 量化/a-share-quant-system"

conda create -n quant python=3.11 -y
conda run -n quant python -m pip install -e ".[dev]"

conda run -n quant python -m ruff check src tests
conda run -n quant python -m pytest -q
```

随后在新机器按 RQData 官方方式配置客户端认证。不要把用户名、密码、令牌或
本机认证配置提交到 Git。

## 3. 重建真实数据

数据和实验产物被 `.gitignore` 排除，必须在新机器重新生成：

```bash
conda run -n quant a-share-quant sync-rqdata \
  --start 2018-01-01 \
  --end 2026-07-23 \
  --output storage/rqdata-csi500 \
  --universe-index 000905.XSHG \
  --benchmark 000905.XSHG \
  --replace

conda run -n quant a-share-quant validate-data storage/rqdata-csi500
```

预期数据量会随 RQData 修订略有变化。本机验证快照包含约 1,179 只历史证券和
约 223 万条日线；健康检查要求无重复行情、缺失价格率低于 1%、无未来交易日，
并存在基本面可用时点字段。

## 4. 复现基线

```bash
conda run -n quant a-share-quant backtest storage/rqdata-csi500 \
  --start 2019-01-01 \
  --end 2026-07-23 \
  --initial-cash 1000000
```

本机最后一次真实基线结果如下：

| 指标 | 结果 |
|---|---:|
| 累计收益 | 51.97% |
| 年化收益 | 5.70% |
| 中证 500 年化收益 | 8.65% |
| 年化超额 | -2.96% |
| 最大回撤 | 17.26% |
| 信息比率 | -0.33 |
| 显式交易费用 | 123,185.87 元 |
| 滑点与冲击成本 | 83,430.07 元 |

对应运行 ID 为 `run_9d18c977eb7e469394410a87179bc38c`，但本地 artifact
不会上传。该基线没有通过 Gate，失败项为年化超额和信息比率。不要将它描述为
有效策略，更不要据此实盘。

## 5. 已知问题与下一阶段优先级

当前平均有效仓位约 64.5%，平均单周单边换手约 16.3%。策略在 2019、2020
和 2025 年明显落后中证 500；2021、2022、2023 年有正超额。下一阶段应按以下
顺序研究：

1. 先建立年度、市场状态、行业和因子分组归因，解释超额来源；
2. 将组合目标从绝对收益 Top-K 改为相对中证 500 的主动权重框架；
3. 将换手约束真正纳入 Top-K 构建，不只作为诊断字段；
4. 对月度调仓、持仓缓冲区和更低换手进行独立样本外测试；
5. 分离市场择时与选股贡献，避免现金仓位让牛市相对收益结构性落后；
6. 用滚动训练/验证/测试区间选择参数，禁止在 2019 至 2026 全样本上追最优；
7. 在通过基础 Gate 后再运行成本 1.5 倍、2 倍、容量和行业拥挤压力测试。

不要直接大规模网格搜索后报告最好结果。每个实验必须保留请求、数据指纹、
配置版本、净值、成交、持仓、信号、排除原因、归因和 Gate。

## 6. 给另一台电脑 Codex 的建议首条指令

可直接粘贴以下内容：

> 阅读 `BA 量化/a-share-quant-system/HANDOFF.md`、`SPEC.md`、
> `docs/DATA_CONTRACT.md` 和 `docs/RUNBOOK.md`。先运行测试并通过 RQData
> 重建数据，复现基线。不要接入聚宽或券商。然后先完成基线归因与换手约束修复，
> 使用严格的滚动样本外验证优化策略；所有实验保留数据指纹和 Gate，不允许只挑
> 最优回测结果。

## 7. 关键文件

- `src/a_share_quant/data/rqdata_adapter.py`：RQData 同步与字段映射；
- `src/a_share_quant/data/dataset.py`：数据契约、校验和日期索引；
- `src/a_share_quant/features/engine.py`：滚动特征、批量中性化；
- `src/a_share_quant/backtest/engine.py`：回测主循环；
- `configs/strategies/a_share_regime_multifactor_v1.yaml`：当前基线配置；
- `docs/DATA_CONTRACT.md`：点时数据约束；
- `SPEC.md`：完整系统规格。
