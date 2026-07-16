# 4090 本地研究服务

本地服务承担模型训练、私有文档检索和模型密钥；GitHub Pages 只访问 API 并展示已审核研究资产。

## 前提

- NVIDIA 驱动与 NVIDIA Container Toolkit 已可用。
- Docker Compose 已支持 GPU reservation。
- 首次启动后，在本机拉取本地模型，例如：

```bash
docker compose -f docker-compose.gpu.yml exec ollama ollama pull qwen2.5:14b-instruct
```

## 启动

```bash
docker compose -f docker-compose.gpu.yml up --build
```

前端设置中的 API 地址指向本机服务；不要把本地服务、私有文档目录或 RQData 凭据暴露到 GitHub Pages。

## 安全边界

- GPU Worker 只在本地运行。
- 私有文档、模型权重和审计库只写入 Docker volume。
- LLM Gateway 只允许本地 OpenAI 兼容端点；不配置地址时退化为带平台引用的证据回答。
- 没有下单、券商连接或外部写入工具。
