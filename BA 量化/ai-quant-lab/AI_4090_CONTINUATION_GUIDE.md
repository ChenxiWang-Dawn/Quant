# AI Quant Lab：4090 本地续建指南

本指南用于在配备 NVIDIA RTX 4090 的电脑上继续完成 AI Quant Lab。当前分支已经提供研究平台、GPU 容器、基础深度学习、PPO 仿真、本地模型 Gateway 与私有资料检索的可运行骨架；所有训练、模型权重、私有文档、RQData 凭据和审计数据都只应留在本机。

## 1. 分支与当前状态

克隆后切换到：

```bash
git checkout codex/ai-research-mvp
```

已完成：

- `/ai` 研究工作台、数据快照、特征库、实验、模型注册、组合、评测、监控、负面结果与方法页。
- A 股横截面选股：时间切分、embargo、Ridge/线性/Elastic Net/随机森林/梯度提升、Walk-Forward、成本后 Top-K 评测。
- 本地 SQLite 审计存储、模型 Gate、模型晋级限制与公开/本地边界。
- 受控研究助手：专业角色、引用、工具轨迹、最小权限和无交易边界。
- 深度学习目录：MLP、TCN、GRU、LSTM、Transformer 的本地多种子训练入口。
- RL：环境验证、规则基准与本地 PPO 历史仿真入口。
- CUDA Docker Compose、Ollama 本地 OpenAI 兼容 Gateway 和私有资料 API。

尚需在 4090 上完成真实运行和扩展的部分：

- 将深度模型接到真实 A 股多资产时间序列/横截面数据，而不是当前教学序列输入。
- 为深度学习与 PPO 增加异步 GPU 队列、可恢复检查点和独立 Worker。
- 将 PPO 扩展为多资产 ETF/股票池环境，并增加买入持有、等权、监督学习策略对照。
- 接入本地嵌入模型、向量索引、PDF/Markdown 文件上传与文档删除后的索引清理。
- 启用真实影子预测调度、标签成熟回填和漂移阈值告警。
- 添加完整的 Walk-Forward、成本敏感性、行业/风格约束、容量和多市场状态评测。

这些项目不应以页面占位或模拟结果标记为完成；每项必须通过本指南的验收顺序。

## 2. 本机前提

- NVIDIA 驱动和 NVIDIA Container Toolkit。
- Docker Desktop 或 Docker Engine，支持 Compose GPU reservation。
- Git、Node.js 20+。
- 可选：本机 RQData 授权；它绝不进入容器镜像、Git 或 GitHub Actions。

验证 GPU：

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## 3. 启动本地研究服务

在 `ai-quant-lab` 目录执行：

```bash
docker compose -f docker-compose.gpu.yml up --build
```

首次启动后下载本地模型：

```bash
docker compose -f docker-compose.gpu.yml exec ollama ollama pull qwen2.5:14b-instruct
```

浏览器前端的 API 地址设置为本机服务地址。GitHub Pages 只能托管静态前端，不能训练模型或保存密钥；如果要从外网访问本机 API，请使用具备鉴权和 HTTPS 的受控反向代理，不要直接公开 8787 端口。

## 4. 验收顺序

按以下顺序继续，不要跳过前置 Gate：

1. 数据和泄漏：建立 A 股历史快照，确认可获得时间、缺失、停牌、复权与股票池历史成分。
2. 机器学习：在同一快照与切分上运行 Ridge、树模型和 Walk-Forward；记录成本后结果与等权/Ridge 基准。
3. 组合：复用固定预测批次，测试 Top-K、权重上限、换手约束和成本压力。
4. 注册与影子：只有 Gate 通过且人工审阅后才登记 `@candidate` 或 `@shadow`；影子预测绝不下单。
5. 深度学习：先 MLP，再 TCN/GRU/LSTM，最后 Transformer；每种模型至少三个随机种子，并对比简单模型。
6. 强化学习：先通过随机动作、固定动作、全现金与成本单调性测试；再执行 PPO 的训练/验证/测试隔离评估。
7. 研究助手：导入有授权的资料，检查引用真实性、无证据拒答、提示注入和工具权限测试。
8. 发布公开快照：仅发布已审核的模型卡、方法文档和非私有实验摘要。

## 5. 代码位置

| 位置 | 作用 |
| --- | --- |
| `api/app.py` | FastAPI 路由与公开/本地数据边界 |
| `api/research_platform.py` | 研究资产、Gate、评测、深度模型与受控助手 |
| `api/rl_ppo.py` | 本地 PPO 历史仿真环境 |
| `api/requirements-gpu.txt` | 4090 本地 GPU Python 依赖 |
| `api/Dockerfile.gpu` | CUDA 运行镜像 |
| `docker-compose.gpu.yml` | API 与 Ollama 本地服务 |
| `web/src/AIPlatform.tsx` | AI 多页面控制台 |

## 6. 开发与测试

前端：

```bash
cd web
npm ci
npm run build
```

后端：

```bash
cd api
python -m unittest discover -s tests -v
```

在引入真实 GPU Worker、文档索引或数据源后，必须补充对应的黄金测试、泄漏测试和复现测试；不允许只依赖单次收益展示。

## 7. 严格安全边界

- 不实现自动下单、券商连接、资金操作或外部消息发送。
- 不在网页、日志、数据快照或模型卡中保存密钥。
- RQData 只允许本地环境，云端和 GitHub Pages 只能使用免费/开源数据源。
- 未经人工确认的 LLM 抽取不得进入高影响标签或训练数据。
- 模型晋级必须保留 Gate、数据指纹、配置哈希、人工审阅原因和审计日志。
