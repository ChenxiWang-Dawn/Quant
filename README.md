# 我的量化学习记录

## 📚 资料来源

本仓库的学习笔记和代码基于以下开源课程整理：

- **[Datawhale - Quant-For-Beginners](https://github.com/datawhalechina/Quant-For-Beginners)** — 面向初学者的量化投资入门教程，包含系统的量化金融知识体系和实战案例。

感谢 Datawhale 社区和课程作者的贡献。

## 学习目标

* 掌握量化投资

## 目录

- `learning-log/`：学习日志
- `notes/`：知识笔记
- `notebooks/`：实验代码
- `src/`：可复用代码
- `strategies/`：策略研究
- `mistakes/`：错误和踩坑记录
- `resources/`：资料索引
- `BA 量化/ai-quant-lab/`：量化工程学习辅助应用

## AI Quant Lab

`BA 量化/ai-quant-lab/indicator-studio/` 是一个本地静态量化研究工具，用于选择股票样例数据、导入 CSV、计算技术指标、调节参数、标注规则信号、查看简易策略表现，并对比多只股票的区间表现。

打开方式：

```text
BA 量化/ai-quant-lab/indicator-studio/index.html
```

当前支持 MA、EMA、BOLL、MACD、RSI、KDJ、ATR、成交量均线、信号视图、对比视图、参数优化视图、研究摘要、配置保存、配置导入导出、分享链接和 CSV 下载。

在线访问：

```text
https://chenxiwang-dawn.github.io/Quant/
```

部署说明：本仓库包含 GitHub Pages 自动部署配置。相关改动合并到 `main` 后，GitHub Actions 会把 `BA 量化/ai-quant-lab/indicator-studio/` 发布为站点根目录。如果首次部署时 Pages 尚未启用，需要在仓库 Settings -> Pages 中选择 GitHub Actions 作为发布源。
