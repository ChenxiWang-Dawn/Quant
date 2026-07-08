# Indicator Studio 设计说明

`Indicator Studio` 是 `ai-quant-lab` 下的第一个静态量化研究工具，用于选择股票行情、添加技术指标、调节参数并即时重绘。

## 当前版本

- 运行方式：直接打开 `index.html`。
- 数据来源：内置示例行情，或导入 CSV。
- 真实数据：可连接本地 Python 服务，通过 AkShare、Yahoo Finance、RQData、Tushare 拉取行情。
- CSV 字段：`date,open,high,low,close,volume`。
- 图表能力：K 线、成交量、十字光标、滚轮缩放。
- 主图指标：MA、EMA、BOLL。
- 副图指标：MACD、RSI、KDJ、ATR。
- 成交量指标：VOLMA。
- 快捷模板：趋势、动量、波动三类指标组合。
- 信号视图：基于 MA、MACD、RSI、BOLL、成交量的规则信号标注。
- 策略摘要：用规则信号做简化满仓买卖模拟，展示收益、回撤、交易数和胜率。
- 对比视图：多只股票归一化到 100 起点，比较区间表现。
- 优化视图：扫描 MA 快慢线参数组合，展示收益、回撤、交易次数、评分和热力图。
- 策略视图：Strategy Lab，可调策略、快慢均线、目标仓位、初始资金、手续费、滑点、最低佣金，并展示完整绩效指标和交易流水。
- 回测核心：本地 Python 服务调用项目根目录的 `quant_lab` 可复用回测包；浏览器轻量回测保留为服务不可用时的 fallback。
- RQAlpha Plus：策略视图可选择完整 RQAlpha Plus 数据包回测，后端调用 `rqalpha.run_func`，解析 `sys_analyser` 的 `summary`、`trades`、`portfolio` 和持仓数据。
- 参数优化：浏览器轻量扫描和本地 Python `/api/optimize` 专业扫描均可用，后者与 notebook 共用同一套回测逻辑。
- 模板市场：内置趋势跟随、动量反转、波动风险三类指标组合，可继续扩展。
- AI 视图：基于当前指标、信号、专业回测和参数扫描结果生成解释与 RQAlpha 策略草稿。
- 项目视图：使用 localStorage 管理本地研究项目、实验历史、策略参数、回测引擎和版本对比。
- 研究摘要：自动汇总趋势结构、动量状态、波动风险和最近信号。
- 配置能力：保存到浏览器 localStorage、加载、删除、导入/导出 JSON、生成分享链接。
- 数据导出：可下载当前 K 线数据为 CSV。

## 本地真实数据服务

静态页面部署到 GitHub Pages 后仍可使用示例数据。若需要真实行情和本地策略回测，在本机启动：

```text
/opt/miniconda3/envs/quant/bin/python backend/quant_lab_server.py
```

默认服务地址为：

```text
http://127.0.0.1:8766
```

数据源说明：

- AkShare：当前 `quant` 环境已安装。
- Yahoo Finance：当前 `quant` 环境已安装 `yfinance`。
- RQData：当前 `quant` 环境已安装 `rqdatac`，需要本机 RQData 授权可用。
- Tushare：需要安装 `tushare` 并设置环境变量 `TUSHARE_TOKEN`。

## 可复用回测核心

项目根目录新增 `quant_lab/` 包，用于在 notebook、脚本和网站后端之间复用：

- `data.py`：行情数据标准化、CSV 读取、RQData 拉取。
- `strategies.py`：策略基类和 `MACrossStrategy`。
- `backtester.py`：信号收盘确认、下一交易日开盘成交、现金和持仓模拟。
- `metrics.py`：收益、年化、波动、最大回撤、Sharpe、Sortino、Calmar、胜率、盈亏比、Profit Factor、成本等指标。
- `optimize.py`：参数网格扫描。
- `plotting.py`：notebook 可视化辅助。
- `rqalpha_runner.py`：完整 RQAlpha Plus MA 双均线回测入口与结果解析。

第一版策略执行假设：

- 信号在当日收盘后确认。
- 默认下一交易日开盘成交。
- A 股默认按 100 股一手取整。
- 默认不允许做空。
- 已计入手续费、滑点和最低佣金。
- 暂不模拟涨跌停、流动性冲击和部分成交，后续可扩展。

RQAlpha Plus 高级引擎说明：

- 入口使用官方 `rqalpha.run_func`。
- 配置使用 `base.accounts`、`base.data_bundle_path`、`mod.sys_simulation`、`mod.sys_transaction_cost` 和 `mod.sys_analyser`。
- 数据来自本机 `~/.rqalpha-plus/bundle` 数据包；如果数据包不覆盖当前标的或日期，后端会返回明确错误或回退到 `quant_lab` 引擎。
- 当前接入 MA 双均线策略，后续新增策略时需要补对应的 RQAlpha 约定函数。

## 界面结构

- 顶部栏：应用名、CSV 导入、配置管理。
- 数据栏：股票、日期、周期、复权、加载、重置。
- 左侧栏：指标添加、显示隐藏、参数、颜色、排序、删除。
- 右侧图表：主图、成交量、副图。
- 研究视图：图表、信号、对比、优化、策略、模板、AI、项目、研究多个模式。
- 底部状态栏：加载状态和鼠标所在 K 线信息。

## 已实现扩展

- 接入 RQData 获取真实行情。
- 增加买卖信号标注；信号视图显示规则信号，策略视图同时显示专业回测实际成交点。
- 增加指标组合模板市场，并联动策略参数。
- 将完整 RQAlpha Plus 数据包回测作为可选高级引擎接入。
- 增加 AI 指标解释和 RQAlpha 策略草稿生成。
- 增加本地研究项目管理、实验历史、策略参数保存和版本对比。
- 将 rqalpha 从轻量入口扩展为完整数据包回测和交易明细解析。

## 后续可深化

- 为更多策略补 RQAlpha Plus 高级引擎实现。
- 增加涨跌停、停牌、成交量限制和调仓失败原因在前端的明细展示。
- 将 localStorage 项目实验升级为本地文件或 SQLite 存储。
