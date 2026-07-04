# Cline 项目级系统提示

你正在参与一个使用 Ricequant SDK 的量化研究项目。本项目提供了 Ricequant SDK 官方文档索引文件，用于准确查找和使用 API。在编写任何与 Ricequant SDK 相关的代码之前，必须严格遵守以下规则：

1. 编写 Ricequant 相关代码前，必须查阅 `docs/document_index.md`。
2. API 的定位和使用必须遵循 `docs/index_guide.md`。
3. 不允许根据经验或常识推断未明确说明的 API 行为。
4. 若文档无法直接读取，使用 `curl -L <官方文档 URL>` 获取官方文档，不得使用泛化 web search。
5. 若索引中缺失或描述不清，必须先向用户确认。
6. 需要金融数据时，优先使用 `rqdatac`，并在 conda 环境 `quant` 中通过最小命令验证 API，例如 `conda run -n quant python -c "import rqdatac; rqdatac.init(); help(rqdatac.get_price)"`。

当文档与通用认知冲突时，以文档为准。
