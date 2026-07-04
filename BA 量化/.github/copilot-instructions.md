# RQSDK 开发指导

本项目使用 Ricequant SDK（RQSDK）进行量化开发。GitHub Copilot 在生成或解释代码时，应遵循项目根目录的 `AGENTS.md` 和 `CLAUDE.md`。

## 主要组件

- RQData：金融数据 API，Python 包通常为 `rqdatac`。
- RQAlpha Plus：本地策略回测引擎，常见策略函数包括 `init`、`before_trading`、`handle_bar`、`after_trading`。
- RQFactor：因子编写、计算和检验工具。
- RQOptimizer：选股和组合优化工具。
- RQPAttr：绩效归因工具。

## 文档参考

- 官方文档索引：`https://www.ricequant.com/doc/document-index.txt`
- 本地索引：`ricequant-doc-index.md`
- Cline/Trae 索引副本：`docs/document_index.md`

## 本地环境

- RQSDK 已安装在 conda 环境 `quant`。
- Python 解释器路径：`/opt/miniconda3/envs/quant/bin/python`。
- 终端运行验证命令时，优先使用 `conda run -n quant python ...`。

## 代码要求

- 需要 API、参数或示例时，先查本地索引，再访问索引中的官方 URL。
- 没有 URL 工具时，使用 `curl -L <官方文档 URL>`。
- 需要金融数据时，优先使用 `import rqdatac` 和 `rqdatac.init()`。
- 生成 RQAlpha 策略时，使用清晰的 `context` 状态、明确的标的池、交易成本、调仓频率和风控假设。
- 避免未来函数、幸存者偏差和未经说明的复权方式。
