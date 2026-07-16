import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "./lib/api";
import type { AIExperimentRequest, AIExperimentResult } from "./types";

const defaultUniverse = ["000001.XSHE", "600519.XSHG", "000333.XSHE", "002594.XSHE", "600036.XSHG", "601318.XSHG", "600900.XSHG", "000858.XSHE", "600276.XSHG", "300750.XSHE"].join(", ");
const featureNames: Record<string, string> = { momentum_5: "5 日动量", momentum_20: "20 日动量", volatility_20: "20 日波动率", volume_zscore_20: "成交量异常度" };
const fmtPct = (value: number) => `${(value * 100).toFixed(2)}%`;
const fmtNumber = (value: number) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);

function EquityChart({ result }: { result: AIExperimentResult }) {
  const points = useMemo(() => {
    const width = 720; const height = 260; const padding = 20;
    const values = result.equity.flatMap((item) => [item.equity, item.benchmark]);
    const min = Math.min(...values) * 0.985; const max = Math.max(...values) * 1.015; const spread = Math.max(max - min, 0.01);
    const path = (field: "equity" | "benchmark") => result.equity.map((item, index) => {
      const x = padding + index / Math.max(result.equity.length - 1, 1) * (width - padding * 2);
      const y = height - padding - (item[field] - min) / spread * (height - padding * 2);
      return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return { width, height, padding, min, max, model: path("equity"), benchmark: path("benchmark") };
  }, [result]);
  return <div className="ai-equity-chart" role="img" aria-label="策略与等权基准的测试期净值曲线">
    <div className="ai-chart-legend"><span><i className="ai-line model" />Top-K 模型组合</span><span><i className="ai-line benchmark" />等权基准</span></div>
    <svg viewBox={`0 0 ${points.width} ${points.height}`} preserveAspectRatio="none">
      {[0.2, 0.5, 0.8].map((ratio) => <line key={ratio} x1={points.padding} x2={points.width - points.padding} y1={points.padding + ratio * (points.height - points.padding * 2)} y2={points.padding + ratio * (points.height - points.padding * 2)} className="ai-grid" />)}
      <path d={points.benchmark} className="ai-path benchmark" />
      <path d={points.model} className="ai-path model" />
    </svg>
    <div className="ai-chart-axis"><span>{result.equity[0]?.date}</span><span>净值区间 {points.min.toFixed(2)} — {points.max.toFixed(2)}</span><span>{result.equity[result.equity.length - 1]?.date}</span></div>
  </div>;
}

export default function AIResearchLab() {
  const [universe, setUniverse] = useState(defaultUniverse);
  const [start, setStart] = useState("2020-01-01");
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));
  const [horizon, setHorizon] = useState(10);
  const [topK, setTopK] = useState(5);
  const [cost, setCost] = useState(0.001);
  const [model, setModel] = useState<AIExperimentRequest["model"]>("ridge");
  const [splitMode, setSplitMode] = useState<AIExperimentRequest["splitMode"]>("forward");
  const [result, setResult] = useState<AIExperimentResult | null>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const symbols = useMemo(() => universe.split(/[，,\n\s]+/).map((item) => item.trim()).filter(Boolean), [universe]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(""); setResult(null); setRunning(true);
    const payload: AIExperimentRequest = { universe: symbols, start, end, horizon, topK, transactionCost: cost, source: "auto", task: "ranking", model, splitMode, walkForwardFolds: splitMode === "walk_forward" ? 3 : 1 };
    try { setResult(await api.aiExperiment(payload)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "实验运行失败，请稍后重试。"); }
    finally { setRunning(false); }
  };

  return <div className="ai-research-page">
    <section className="ai-hero wrap">
      <div><p className="eyebrow">AI RESEARCH LAB / PHASE 1</p><h1>从可复现的基线，<br /><em>开始 AI 量化研究。</em></h1><p>先把数据、时间切分、成本和基准说清楚。这个工作台会用历史价格与成交量，构建一个透明的横截面选股基线。</p></div>
      <aside className="ai-guardrail"><span>研究边界</span><b>先验证，再扩展</b><p>传统模型可在线研究；深度学习仅在本地受控环境训练；强化学习只做历史仿真；助手只输出带引用的研究材料。</p></aside>
    </section>

    <section className="wrap ai-workbench">
      <form className="ai-config-panel" onSubmit={submit}>
        <div className="ai-panel-heading"><div><p className="eyebrow">01 / CONFIGURE</p><h2>配置一次实验</h2></div><span className="ai-stage">可运行</span></div>
        <label>标的池 <small>至少 4 个，用逗号、空格或换行分隔</small><textarea value={universe} onChange={(event) => setUniverse(event.target.value)} rows={4} spellCheck="false" /></label>
        <p className="ai-symbol-count">已识别 {symbols.length} 个标的 · 将自动显示证券名称并剔除无效数据</p>
        <div className="ai-form-grid"><label>开始日期<input type="date" value={start} onChange={(event) => setStart(event.target.value)} required /></label><label>结束日期<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} required /></label><label>持有期<select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}><option value={5}>5 个交易日</option><option value={10}>10 个交易日</option><option value={20}>20 个交易日</option></select></label><label>Top-K<select value={topK} onChange={(event) => setTopK(Number(event.target.value))}>{[2, 3, 4, 5, 6, 8].map((item) => <option key={item} value={item}>{item} 只股票</option>)}</select></label><label>候选模型<select value={model} onChange={(event) => setModel(event.target.value as AIExperimentRequest["model"])}><option value="ridge">Ridge 线性基线</option><option value="linear">线性回归</option><option value="elastic_net">Elastic Net</option><option value="random_forest">随机森林</option><option value="gradient_boosting">梯度提升树</option></select><small>始终与 Ridge 和等权基准比较</small></label><label>验证方式<select value={splitMode} onChange={(event) => setSplitMode(event.target.value as AIExperimentRequest["splitMode"])}><option value="forward">单次前向切分</option><option value="walk_forward">3 折 Walk-Forward</option></select><small>时间顺序不可随机打乱</small></label><label>单边交易成本<input type="number" value={cost} min="0" max="0.02" step="0.0001" onChange={(event) => setCost(Number(event.target.value))} /><small>0.001 = 10 个基点</small></label></div>
        <div className="ai-method-note"><b>本次方法</b><span>日频 OHLCV → 历史特征 → 60/20/20 时间切分 → 验证集检查 → 测试集 Top-K 等权组合</span></div>
        <button className="button ai-run" type="submit" disabled={running || symbols.length < 4}>{running ? "正在拉取数据并运行实验…" : "运行 AI 选股实验 →"}</button>
        <p className="disclaimer">RQData 仅在本地服务可用；在线部署会自动使用 AkShare 或 yfinance。历史结果不构成投资建议。</p>
      </form>
      <aside className="ai-learning-panel"><p className="eyebrow">FOR BEGINNERS</p><h2>这不是“预测涨跌”按钮</h2><ol><li><b>特征</b><span>只从当时已经发生的价格、成交量中提取信息。</span></li><li><b>切分</b><span>训练、验证、测试按时间顺序隔开，避免把未来带回过去。</span></li><li><b>组合</b><span>每个持有期选择预测排名靠前的股票，并扣减换手成本。</span></li></ol><Link to="/methodology" className="text-link">阅读研究方法与风险提示 <span>→</span></Link></aside>
    </section>

    {error && <section className="wrap"><div className="ai-error"><b>本次实验未完成</b><span>{error}</span><small>请确认 API 服务已部署、日期区间足够长，且标的池包含可获取的 A 股代码。</small></div></section>}
    {result && <section className="wrap ai-results">
      <div className="ai-result-top"><div><p className="eyebrow">02 / REVIEW</p><h2>测试集结果</h2><p>实验 {result.id} · {result.dataset.symbols.length} 个可用标的 · {result.dataset.sampleCount.toLocaleString()} 条样本 · {result.dataset.dataSources.join(" / ")}</p></div><span className="ai-stage completed">已完成</span></div>
      <div className="ai-metric-grid"><Metric label="模型组合收益" value={fmtPct(result.metrics.totalReturn)} tone={result.metrics.totalReturn >= 0 ? "up" : "down"} note={`基准 ${fmtPct(result.metrics.benchmarkReturn)}`} /><Metric label="最大回撤" value={fmtPct(result.metrics.maxDrawdown)} tone="down" note="测试期净值回撤" /><Metric label="夏普比率" value={fmtNumber(result.metrics.sharpe)} note="按持有期年化" /><Metric label="测试集 Rank IC" value={fmtNumber(result.metrics.rankIc)} note={`验证集 ${fmtNumber(result.metrics.validationRankIc)}`} /><Metric label="平均换手率" value={fmtPct(result.metrics.turnover)} note={`${result.metrics.rebalances} 次再平衡`} /></div>
      <div className="ai-result-grid"><article className="ai-card ai-chart-card"><div className="ai-card-heading"><div><p className="eyebrow">OUT-OF-SAMPLE</p><h3>成本后净值</h3></div><span>测试开始：{result.split.testStart}</span></div><EquityChart result={result} /><p className="ai-card-foot">模型组合：{fmtPct(result.metrics.totalReturn)} · {result.baseline.name}：{fmtPct(result.baseline.totalReturn)}</p></article>
        <article className="ai-card"><div className="ai-card-heading"><div><p className="eyebrow">TIME INTEGRITY</p><h3>时间切分与 embargo</h3></div><span>{result.split.embargoDays} 日</span></div><div className="ai-timeline"><div className="train"><b>训练</b><span>截至 {result.split.trainEnd}</span><small>{result.split.trainSamples} 样本</small></div><div className="gap">隔离</div><div className="validation"><b>验证</b><span>{result.split.validationStart} — {result.split.validationEnd}</span><small>{result.split.validationSamples} 样本</small></div><div className="gap">隔离</div><div className="test"><b>测试</b><span>{result.split.testStart} — {result.split.testEnd}</span><small>{result.split.testSamples} 样本</small></div></div><p className="ai-card-foot">隔离期长度等于持有期，降低标签重叠和未来信息泄漏风险。</p></article></div>
      <div className="ai-result-grid"><article className="ai-card"><div className="ai-card-heading"><div><p className="eyebrow">MODEL CARD</p><h3>{result.model.name}</h3></div><span>{result.model.card.status}</span></div><p>{result.model.card.purpose}</p><div className="ai-coefficients">{result.model.featureCoefficients.map((item) => <div key={item.feature}><span>{featureNames[item.feature] || item.feature}</span><b className={item.coefficient >= 0 ? "up" : "down"}>{item.coefficient >= 0 ? "+" : ""}{item.coefficient.toFixed(4)}</b></div>)}</div><ul>{result.model.card.limitations.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article className="ai-card"><div className="ai-card-heading"><div><p className="eyebrow">PORTFOLIO LOG</p><h3>最近一次候选组合</h3></div><span>{result.holdings[result.holdings.length - 1]?.date}</span></div>{result.holdings.slice(-1).map((holding) => <div className="ai-holdings" key={holding.date}>{holding.symbols.map((symbol, index) => <div key={symbol}><span>{index + 1}</span><b>{holding.names[index] || symbol}</b><small>{symbol} · 分数 {holding.scores[index].toFixed(4)}</small></div>)}</div>)}<p className="ai-card-foot">这是一份历史测试期的组合记录，不是当前推荐或实盘交易指令。</p></article></div>
      <div className="ai-warnings"><b>研究记录与限制</b>{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}<small>配置哈希：{result.configHash} · 数据指纹：{result.dataFingerprint}</small></div>
    </section>}

    <section className="wrap ai-roadmap"><p className="eyebrow">RESEARCH CAPABILITIES</p><h2>受控扩展能力</h2><div><article><span>本地训练</span><h3>深度学习</h3><p>MLP 多种子、早停与梯度裁剪已可用；TCN、GRU/LSTM、Transformer 必须先通过基线 Gate。</p><Link to="/ai/deep-learning">打开深度学习基线 →</Link></article><article><span>仿真限定</span><h3>强化学习</h3><p>环境先做未来数据与成本单调性测试，再运行多种子受约束配置仿真。</p><Link to="/ai/rl">打开 RL 实验室 →</Link></article><article><span>证据优先</span><h3>研究助手</h3><p>四个专业角色、可核验引用、工具轨迹和最小权限；不具备交易或外部写入权限。</p><Link to="/ai/copilot">打开研究助手 →</Link></article></div></section>
  </div>;
}

function Metric({ label, value, note, tone }: { label: string; value: string; note: string; tone?: "up" | "down" }) {
  return <article className="ai-metric"><span>{label}</span><b className={tone || ""}>{value}</b><small>{note}</small></article>;
}
