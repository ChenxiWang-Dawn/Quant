# Ricequant 文档索引使用指南

本项目提供 Ricequant SDK 官方文档索引，路径为 `docs/document_index.md`。AI 在回答问题、生成代码、解释 API 或排查 RQSDK 问题时，必须优先以该索引中的官方 URL 为信息来源。

## 使用规则

1. 需要 API、示例、参数说明、字段说明或配置说明时，先在 `docs/document_index.md` 中定位对应模块。
2. 仅访问索引中提供的 Ricequant 官方 URL，不凭经验推断 API 行为。
3. 只读取与当前任务相关的文档片段。
4. 若文档无法直接读取，可使用 `curl -L <官方文档 URL>` 获取页面内容。
5. 索引信息不足或文档缺失时，先询问用户。
6. 本机默认环境为 macOS / zsh，可使用 `rg`、`sed`、`curl`、`python` 或 `python3`。
7. RQSDK 已安装在 conda 环境 `quant`；运行或验证 Ricequant 代码时，优先使用 `conda run -n quant python ...`。

## 输出要求

- 代码语言默认 Python。
- 没有额外项目约束时，保持 Python 3.6+ 兼容。
- 输出内容必须与 Ricequant 官方文档一致。
- 重要数学公式必须使用块级 Markdown/LaTeX。
