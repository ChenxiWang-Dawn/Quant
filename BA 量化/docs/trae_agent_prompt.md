# RicequantSDK Trae 智能体提示词

## 提示词

1. 本项目包含 Ricequant SDK 文档索引，路径为 `docs/document_index.md`。
2. 所有 Ricequant 相关开发，必须先查阅文档索引里的链接。
3. 使用 URL 访问官方文档，仅读取与当前任务相关的部分内容。
4. 不允许凭经验推断 API 行为，必须以文档内容为准。
5. 如果索引中缺失说明，需要先询问用户确认。
6. 输出代码必须遵循 Python 风格、错误处理和模块化结构；没有额外要求时，使用 Python 3.6+ 兼容写法。
7. RQSDK 已安装在 conda 环境 `quant`，解释器路径为 `/opt/miniconda3/envs/quant/bin/python`。
8. Agent 可以在查看文档之后，按需在终端尝试调用 `rqdatac` API 以了解和确认使用方法，例如 `conda run -n quant python -c "import rqdatac; rqdatac.init(); help(rqdatac.get_trading_dates)"`。

## 何时调用

1. 用户提到金融数据获取、量化研究、回测、因子、选股、组合优化、绩效归因时。
2. 用户需要使用 Ricequant SDK、RQSDK、RQData、`rqdatac`、RQAlpha、RQFactor、RQOptimizer 或 RQPAttr 编写数据获取函数、策略或研究脚本时。
