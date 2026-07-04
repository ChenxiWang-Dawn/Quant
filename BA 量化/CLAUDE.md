# RQSDK 开发指导

本项目使用 Ricequant SDK（RQSDK）进行量化研究与本地开发。Claude Code、Cursor 或其他 Agent 进入项目后，请先阅读 `AGENTS.md`，并按其中的官方文档优先规则工作。

## 文档索引

- 项目主索引：`ricequant-doc-index.md`
- Claude Code 命令索引：`.claude/commands/ricequant-doc-index.md`
- Cline/Trae 索引：`docs/document_index.md`
- 官方索引源：`https://www.ricequant.com/doc/document-index.txt`

## 本地环境

- RQSDK 已安装在 conda 环境 `quant`。
- Python 解释器路径：`/opt/miniconda3/envs/quant/bin/python`。
- 运行或验证 Ricequant 代码时，优先使用 `conda run -n quant python ...`。

## 使用要求

1. 编写 RQSDK、RQData、RQAlpha Plus、RQFactor、RQOptimizer 或 RQPAttr 相关代码前，先在索引中定位官方文档 URL。
2. 没有内置 URL 读取工具时，使用 `curl -L <官方文档 URL>` 获取文档。
3. 不使用泛化 web search 替代 Ricequant 官方文档。
4. 需要金融数据时优先使用 RQData：`import rqdatac`，并在可用环境中调用 `rqdatac.init()`。
5. API 行为不确定时，可在查看文档后用最小命令验证，例如 `conda run -n quant python -c "import rqdatac; rqdatac.init(); help(rqdatac.get_price)"`。
6. 不写入或泄露账号、license、token、私有数据路径和研究数据。

## 常见开发方向

- 数据获取：优先查 RQData 文档。
- 回测策略：优先查 RQAlpha Plus 的参数配置、入口函数、约定函数、交易接口、数据查询接口。
- 因子研究：优先查 RQFactor 的内置因子、算子、自定义算子、因子计算和因子检验。
- 组合优化：优先查 RQOptimizer 的选股 API 和优化器 API。
- 绩效归因：优先查 RQPAttr 文档。
