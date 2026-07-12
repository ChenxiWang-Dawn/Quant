# AI Quant Lab 2.0

AI Quant Lab 是一个可持续扩展的个人量化策略研究平台。网站前端部署在 GitHub Pages；行情、回测和数据源逻辑由独立 Python API 处理。

## 两层部署架构

```text
浏览器（GitHub Pages）
        │
        ├── 优先：AI Quant Lab API（AkShare / yfinance / 可选 RQData）
        └── 回退：GitHub Actions 定时生成的公开行情快照
```

GitHub Pages 只托管 HTML、CSS 和 JavaScript，不能运行 Python。因此，按请求获取的实时/准实时行情必须经过独立 API；定时快照只作为 API 暂时不可用时的显示回退，不能替代实时服务。

## 本地运行

在一个终端启动 API：

```bash
conda run -n quant pip install -r "ai-quant-lab/api/requirements.txt"
conda run -n quant uvicorn app:app --app-dir "ai-quant-lab/api" --reload --port 8787
```

在另一个终端启动网站：

```bash
cd "ai-quant-lab/web"
npm install
npm run dev
```

网站默认连接 `http://127.0.0.1:8787`。也可以在“设置”页填写云端 API 地址。

## 云端 API

使用仓库根目录的 `render.yaml` 可创建一个 Render Web Service。部署时至少设置：

```text
APP_ALLOWED_ORIGINS=https://chenxiwang-dawn.github.io
```

如果需要 RQData，请仅在自有、受控的服务环境中配置授权；不要将账号、license、token 或本地数据路径写入前端、GitHub Actions 日志、公开快照或仓库。

本地 API 默认允许使用 RQData；云端服务通过 `AI_QUANT_LAB_RUNTIME=cloud` 明确禁用 RQData，只使用 AkShare 与 yfinance 等开源或免费数据源。

## GitHub Pages

1. 在 GitHub 仓库 Settings → Pages 中选择 `GitHub Actions`。
2. 在仓库 Settings → Secrets and variables → Actions → Variables 中设置 `AI_QUANT_LAB_API_URL` 为已部署 API 的 HTTPS 地址。
3. 推送到 `main` 后，`.github/workflows/deploy-ai-quant-lab.yml` 会构建并发布网站。
4. `.github/workflows/refresh-market-snapshot.yml` 可手动或定时生成快照；它随后也会重新发布 Pages。

GitHub Actions 的定时任务会受平台调度影响，不适合承担严格的实时数据职责。浏览器按请求调用云端 API 才是主数据路径。

Render 的免费 Web Service 在空闲后会休眠，首次请求可能有明显冷启动；如果需要连续、低延迟的实时数据，应选择常驻实例或部署到自有服务器。

## 策略接入

策略注册表位于 `shared/strategy_catalog.json`。前端策略库与 API 共用该清单；新增策略时应同时增加 Python 策略实现、参数校验、固定行情测试和研究说明，避免在通用页面中增加 `if strategy === ...` 分支。
