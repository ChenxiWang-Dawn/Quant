# Ricequant RQSDK Agent 指南

本项目用于 Ricequant SDK（RQSDK）量化研究与本地开发。所有 Agent 在编写或修改与 `rqsdk`、`rqdatac`、`rqalpha`、`rqfactor`、`rqoptimizer`、`rqpattr` 相关的代码前，必须先查阅本项目的 Ricequant 官方文档索引，并以索引指向的官方文档为准。

## 文档入口

- 主索引：`ricequant-doc-index.md`
- Claude Code 索引：`.claude/commands/ricequant-doc-index.md`
- Cline/Trae 索引：`docs/document_index.md`
- 官方索引源：`https://www.ricequant.com/doc/document-index.txt`
- RQSDK AI 工具配置文档：`https://www.ricequant.com/doc/sources/rqsdk/manual-rqsdk.md#rqsdk-ai-tools`

## 本地环境

- 本项目的 RQSDK 环境为 conda 环境 `quant`。
- Python 解释器路径：`/opt/miniconda3/envs/quant/bin/python`。
- 在终端验证或运行 Ricequant 相关代码时，优先使用 `conda run -n quant python ...`。
- 已确认 `quant` 环境中可导入 `rqdatac`、`rqsdk`、`rqalpha`、`rqfactor`、`rqoptimizer`。

## 工作规则

1. 需要 API、参数、示例、回测配置或数据字段说明时，先在文档索引中定位 Ricequant 官方 URL。
2. 只读取与当前任务相关的文档页面和章节；不要用泛化 web search 代替官方文档。
3. 当前工具不能直接访问 URL 时，使用终端获取官方文档，例如 `curl -L <官方文档 URL>`。
4. 如果官方文档与经验记忆冲突，以官方文档为准；如果索引或文档缺失关键信息，先向用户确认。
5. 需要金融数据时，优先使用 RQData，即 `import rqdatac` 并在可用环境中调用 `rqdatac.init()`。
6. 查看文档后仍不确定 API 行为时，可在 `quant` 环境中做最小验证，例如 `conda run -n quant python -c "import rqdatac; rqdatac.init(); help(rqdatac.get_trading_dates)"`。
7. 不要把 Ricequant 账号、license、token、数据目录凭据或私有研究数据写入代码、日志、文档或提交信息。

## RQSDK 组件

- RQData / `rqdatac`：金融数据 API，是其他组件的数据基础。
- RQAlpha Plus / `rqalpha`：本地策略回测引擎，常见策略函数包括 `init`、`before_trading`、`handle_bar`、`after_trading`。
- RQFactor：因子编写、计算和检验工具。
- RQOptimizer：选股和组合优化工具。
- RQPAttr：绩效归因工具。

## 量化开发要求

- 明确研究假设、调仓频率、交易日历、标的范围、复权方式、手续费、滑点和基准。
- 避免未来函数和幸存者偏差；下单或生成信号时只能使用决策时点可获得的数据。
- 对数据拉取、因子计算、组合构建和回测执行分别保持清晰边界，便于排查。
- 生成策略代码时，优先写可运行的最小版本，再逐步加入风控、交易成本、日志和参数化配置。
- 修改代码后，尽量运行语法检查或最小 smoke test；如果本机缺少 RQSDK、license 或数据环境，要在结果中说明。

## 输出约定

- 与用户交流优先使用中文。
- Python 代码默认兼容 Ricequant 官方文档要求；没有项目额外约束时，使用 Python 3.6+ 可理解的写法。
- 回答中出现重要数学公式时，使用 Markdown/LaTeX 块级公式，不使用行内公式。
