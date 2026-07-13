import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, getApiBase, loadSnapshot, setApiBase } from "./lib/api";
import { strategies, strategyById } from "./data/strategies";
import { indicatorGuides, type IndicatorCategory, type IndicatorGuide } from "./indicator-library";
import type { BacktestResult, Candle, Experiment, Quote, Strategy } from "./types";

const fmtPct = (value?: number) => (value === undefined || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(2)}%`);
const fmtNum = (value?: number) => (value === undefined || Number.isNaN(value) ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value));
const today = new Date().toISOString().slice(0, 10);
const yearAgo = `${new Date().getFullYear() - 3}-01-01`;

function App() {
  return (
    <div className="app">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/strategies" element={<StrategyCatalog />} />
          <Route path="/strategies/:strategyId" element={<StrategyDetail />} />
          <Route path="/strategies/:strategyId/lab" element={<StrategyLab />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/guide" element={<BeginnerGuide />} />
          <Route path="/indicators" element={<IndicatorLibrary />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

function Header() {
  const [online, setOnline] = useState<boolean | null>(null);
  useEffect(() => {
    api.health().then(() => setOnline(true)).catch(() => setOnline(false));
  }, []);
  return (
    <header className="site-header">
      <Link className="brand" to="/" aria-label="AI Quant Lab 首页"><span className="brand-mark">AQ</span><span>AI Quant Lab<small>RESEARCH PLATFORM</small></span></Link>
      <nav aria-label="主导航">
        <NavLink to="/" end>首页</NavLink>
        <NavLink to="/strategies">策略库</NavLink>
        <NavLink to="/strategies/ma_cross/lab">行情研究</NavLink>
        <NavLink to="/experiments">实验</NavLink>
        <NavLink to="/guide">新手指南</NavLink>
        <NavLink to="/indicators">指标百科</NavLink>
        <NavLink to="/methodology">研究方法</NavLink>
      </nav>
      <div className="header-actions">
        <span className={`service-pill ${online ? "online" : online === false ? "offline" : ""}`} title={online ? "已连接云端或本地数据服务" : "可在设置中配置数据服务"}><i />{online ? "数据服务已连接" : online === false ? "离线快照" : "正在连接"}</span>
        <Link className="button button-small button-quiet" to="/settings">设置</Link>
      </div>
    </header>
  );
}

function HomePage() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [source, setSource] = useState("正在连接实时数据服务");
  useEffect(() => {
    Promise.all(["000001.XSHE", "600519.XSHG", "AAPL"].map((symbol) => api.quote(symbol))).then((data) => {
      setQuotes(data); setSource("实时行情 · 由云端数据服务获取");
    }).catch(() => loadSnapshot().then((snapshot) => { setQuotes(snapshot.quotes || []); setSource(snapshot.updatedAt ? `最近快照 · ${snapshot.updatedAt}` : "尚未生成云端快照"); }).catch(() => setSource("数据服务未连接")));
  }, []);
  return <>
    <WelcomePanel />
    <section className="hero wrap">
      <div className="hero-copy">
        <p className="eyebrow">AI QUANT LAB / RESEARCH FIRST</p>
        <h1>把每一个策略，<br /><em>变成可验证的研究。</em></h1>
        <p className="lead">一个为长期策略积累而设计的量化研究平台。理解假设，固定交易规则，审视成本与回撤，再谈收益。</p>
        <div className="hero-actions"><Link className="button" to="/strategies">浏览策略库</Link><Link className="text-link" to="/strategies/ma_cross/lab">开始一次验证 <span>→</span></Link></div>
        <p className="disclaimer">历史回测不代表未来表现；本平台不构成投资建议。</p>
      </div>
      <div className="hero-terminal" aria-label="实时市场摘要">
        <div className="terminal-top"><span>MARKET PULSE</span><span className="live-dot">LIVE</span></div>
        <div className="quote-list">
          {quotes.length ? quotes.map((quote) => <div className="quote-row" key={quote.symbol}><div><b>{quote.name || quote.symbol}</b><small>{quote.symbol}</small></div><div className="quote-value"><b>{fmtNum(quote.price)}</b><span className={quote.changePercent >= 0 ? "up" : "down"}>{quote.changePercent >= 0 ? "+" : ""}{fmtPct(quote.changePercent)}</span></div></div>) : <div className="quote-empty">{source}<br /><small>部署 API 后，页面会自动读取 AkShare / yfinance 行情。</small></div>}
        </div>
        <div className="terminal-footer"><span>{source}</span><Link to="/settings">数据设置 →</Link></div>
      </div>
    </section>
    <section className="wrap metrics" aria-label="平台概览"><Metric value={`${strategies.length}`} label="已收录策略" /><Metric value="2" label="已验证核心逻辑" /><Metric value="A 股 / ETF / 美股" label="覆盖市场" /><Metric value="收盘确认" label="信号纪律" /></section>
    <section className="wrap start-path"><div className="section-heading"><div><p className="eyebrow">START HERE</p><h2>第一次研究，从这三步开始</h2></div><Link className="text-link" to="/guide">查看完整指南 <span>→</span></Link></div><div className="start-steps"><StartStep number="1" title="选一个熟悉的标的" body="从平安银行、贵州茅台或你熟悉的股票开始，不必一开始就寻找“最好”的标的。" link="打开行情研究" to="/strategies/ma_cross/lab" /><StartStep number="2" title="先看图，再看信号" body="加载 K 线后观察 MA、BOLL、MACD 等指标，让策略规则与价格行为对应起来。" link="查看策略库" to="/strategies" /><StartStep number="3" title="运行并保存一次实验" body="每次回测都会固定区间、成本与参数；保存实验，才有真正可比较的研究记录。" link="学习如何解读结果" to="/guide" /></div></section>
    <section className="wrap section"><div className="section-heading"><div><p className="eyebrow">STRATEGY LIBRARY</p><h2>从清晰的规则开始</h2></div><Link className="text-link" to="/strategies">查看全部策略 <span>→</span></Link></div><div className="strategy-grid">{strategies.map((strategy) => <StrategyCard key={strategy.id} strategy={strategy} />)}</div></section>
    <section className="method-section"><div className="wrap"><p className="eyebrow">RESEARCH DISCIPLINE</p><h2>研究不是寻找最优参数，<br />而是寻找能经受检验的规则。</h2><div className="method-grid"><Method number="01" title="提出假设" body="说明为何预期某种市场行为会持续存在。" /><Method number="02" title="固定规则" body="明确入场、退出、仓位、成本和交易时点。" /><Method number="03" title="历史验证" body="同时查看收益、回撤、交易质量与基准。" /><Method number="04" title="稳健性检查" body="通过参数邻域、分段与成本敏感性检验。" /></div></div></section>
  </>;
}

function Metric({ value, label }: { value: string; label: string }) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div>; }
function Method({ number, title, body }: { number: string; title: string; body: string }) { return <article className="method"><span>{number}</span><h3>{title}</h3><p>{body}</p></article>; }
function StartStep({ number, title, body, link, to }: { number: string; title: string; body: string; link: string; to: string }) { return <article className="start-step"><span>{number}</span><h3>{title}</h3><p>{body}</p><Link to={to}>{link} <b>→</b></Link></article>; }
function WelcomePanel() { const [dismissed, setDismissed] = useState(() => localStorage.getItem("aiQuantLab.welcomeDismissed") === "1"); if (dismissed) return null; const dismiss = () => { localStorage.setItem("aiQuantLab.welcomeDismissed", "1"); setDismissed(true); }; return <section className="wrap welcome-panel" aria-label="新手提示"><div className="welcome-icon">✦</div><div><strong>欢迎来到 AI Quant Lab</strong><p>不需要金融工程背景。先从一张 K 线图和一次可复现的回测开始。</p></div><div className="welcome-actions"><Link className="button button-small" to="/guide">3 分钟入门</Link><button className="text-button" onClick={dismiss}>暂时跳过</button></div></section>; }

function StrategyCard({ strategy }: { strategy: Strategy }) {
  return <article className="strategy-card"><div className="card-top"><span className="tag">{strategy.category}</span><span className="status">已验证</span></div><h3>{strategy.name}</h3><p>{strategy.summary}</p><div className="card-meta"><span>{strategy.holdingPeriod}</span><span>风险 {strategy.riskLevel}</span></div><Link className="card-link" to={`/strategies/${strategy.id}`}>查看策略 <span>→</span></Link></article>;
}

function StrategyCatalog() {
  const [query, setQuery] = useState(""); const [category, setCategory] = useState("全部");
  const items = strategies.filter((strategy) => (category === "全部" || strategy.category === category) && `${strategy.name}${strategy.summary}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="wrap page"><p className="eyebrow">STRATEGY LIBRARY</p><h1>策略库</h1><p className="page-intro">每个策略都应有明确的假设、规则、成本假设和失效场景。</p><div className="catalog-tools"><input aria-label="搜索策略" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索策略" /><div className="filter-row">{["全部", ...new Set(strategies.map((strategy) => strategy.category))].map((item) => <button className={category === item ? "filter active" : "filter"} onClick={() => setCategory(item)} key={item}>{item}</button>)}</div></div><div className="strategy-grid catalog">{items.map((strategy) => <StrategyCard key={strategy.id} strategy={strategy} />)}</div></section>;
}

function StrategyDetail() {
  const { strategyId } = useParams(); const strategy = strategyById(strategyId); const navigate = useNavigate();
  if (!strategy) return <NotFound />;
  return <section className="wrap page strategy-detail"><div className="breadcrumb"><Link to="/strategies">策略库</Link><span>/</span>{strategy.name}</div><div className="detail-hero"><div><p className="eyebrow">{strategy.category.toUpperCase()} / V{strategy.version}</p><h1>{strategy.name}</h1><p className="page-intro">{strategy.summary}</p><button className="button" onClick={() => navigate(`/strategies/${strategy.id}/lab`)}>在工作台中验证</button></div><div className="facts"><Fact label="研究状态" value="已验证" /><Fact label="适用市场" value={strategy.markets.join(" · ")} /><Fact label="主要周期" value={strategy.holdingPeriod} /><Fact label="风险等级" value={strategy.riskLevel} /></div></div><div className="detail-grid"><article className="content-card"><p className="eyebrow">RESEARCH HYPOTHESIS</p><h2>研究假设</h2><p>{strategy.hypothesis}</p><hr /><p className="eyebrow">RULES</p><h2>规则与执行</h2><p>信号均在当日收盘后确认；默认以次一交易日开盘价成交。仓位、交易成本、最小佣金和整手规则可在研究工作台中明确配置。</p></article><aside className="content-card"><p className="eyebrow">DEFAULT PARAMETERS</p><h2>默认参数</h2><dl>{strategy.params.map((param) => <div key={param.key}><dt>{param.label}</dt><dd>{param.default}</dd></div>)}</dl></aside></div><section className="detail-grid"><article className="content-card"><p className="eyebrow">ROBUSTNESS</p><h2>应如何检验</h2><ul><li>在相邻参数区域内检验，不只选择单一最优值。</li><li>按年度或滚动区间观察收益、回撤和交易次数。</li><li>上调手续费与滑点，评估成本敏感性。</li></ul></article><article className="content-card risk-card"><p className="eyebrow">LIMITATIONS</p><h2>局限与风险</h2><ul>{strategy.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul></article></section></section>;
}

function Fact({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }

function StrategyLab() {
  const { strategyId } = useParams(); const strategy = strategyById(strategyId); const [symbol, setSymbol] = useState("000001.XSHE"); const [securityName, setSecurityName] = useState(""); const [start, setStart] = useState(yearAgo); const [end, setEnd] = useState(today); const [source, setSource] = useState("auto");
  const [params, setParams] = useState<Record<string, number>>(() => Object.fromEntries(strategy?.params.map((param) => [param.key, param.default]) || []));
  const [bars, setBars] = useState<Candle[]>([]); const [result, setResult] = useState<BacktestResult | null>(null); const [notice, setNotice] = useState("输入标的后先加载 K 线；云端使用 AkShare 或 yfinance，本地服务可选 RQData。"); const [busy, setBusy] = useState(false);
  const [indicators, setIndicators] = useState<ChartIndicators>({ ma5: true, ma20: true, ema12: false, boll: true, macd: true, rsi: false });
  if (!strategy) return <NotFound />;
  const updateParam = (key: string, value: number) => setParams((current) => ({ ...current, [key]: value }));
  const toggleIndicator = (key: keyof ChartIndicators) => setIndicators((current) => ({ ...current, [key]: !current[key] }));
  const requestBars = async () => {
    const data = await api.bars(symbol, start, end, source);
    setBars(data.candles);
    setSecurityName(data.name || data.symbol);
    return data;
  };
  const loadMarketData = async () => {
    setBusy(true); setNotice("正在加载标的名称、K 线与技术指标…");
    try { const data = await requestBars(); setNotice(`已加载 ${data.name || data.symbol} · ${data.candles.length} 根 K 线 · 行情源：${data.source}`); } catch (error) { setNotice(`加载失败：${error instanceof Error ? error.message : "未知错误"}`); } finally { setBusy(false); }
  };
  const run = async () => {
    setBusy(true); setNotice("正在加载行情并执行回测…");
    try { const data = await requestBars(); const backtest = await api.backtest({ strategy: { id: strategy.id, version: strategy.version }, params, universe: [symbol], period: { start, end, frequency: "1d" }, data: { source, adjustType: "pre" }, execution: { engine: "quant_lab", initialCash: 100000, tradePrice: "next_open", commissionRate: 0.0008, slippageRate: 0.0002, minCommission: 5, lotSize: 100 }, candles: data.candles }); setResult(backtest); setSecurityName(backtest.security?.name || data.name || data.symbol); setNotice(`回测完成 · ${backtest.security?.name || data.name || data.symbol} · 行情源：${data.source} · 引擎：${backtest.engine}`); } catch (error) { setNotice(`运行失败：${error instanceof Error ? error.message : "未知错误"}`); } finally { setBusy(false); }
  };
  const saveExperiment = () => { if (!result) return; const experiments: Experiment[] = JSON.parse(localStorage.getItem("aiQuantLab.experiments") || "[]"); const item: Experiment = { id: crypto.randomUUID(), name: `${strategy.name} · ${securityName || symbol}`, strategyId: strategy.id, strategyName: strategy.name, symbol, securityName, period: `${start} 至 ${end}`, createdAt: new Date().toLocaleString("zh-CN"), engine: result.engine, summary: result.summary, config: { params, source, start, end } }; localStorage.setItem("aiQuantLab.experiments", JSON.stringify([item, ...experiments].slice(0, 100))); setNotice("实验已保存到当前浏览器。未来连接 SQLite 服务后可同步保存。"); };
  return <section className="lab-page"><div className="wrap"><div className="breadcrumb"><Link to={`/strategies/${strategy.id}`}>{strategy.name}</Link><span>/</span>研究工作台</div><div className="lab-title"><div><p className="eyebrow">STRATEGY LAB</p><h1>{strategy.name}</h1></div><div className="lab-actions"><button className="button button-quiet" disabled={busy} onClick={loadMarketData}>{busy ? "加载中…" : "加载行情"}</button><button className="button" disabled={busy} onClick={run}>{busy ? "运行中…" : "运行回测"}</button></div></div><p className="notice">{notice}</p><div className="lab-layout"><aside className="lab-controls"><h2>研究配置</h2><label>标的代码<input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="000001.XSHE / AAPL" /></label>{securityName && <div className="security-name">{securityName}<span>{symbol}</span></div>}<div className="two-fields"><label>开始<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>结束<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label></div><label>数据源<select value={source} onChange={(event) => setSource(event.target.value)}><option value="auto">自动选择</option><option value="akshare">AkShare（A 股）</option><option value="yfinance">yfinance（全球市场）</option><option value="rqdata">RQData（仅本地服务）</option></select></label><div className="indicator-picker"><span>技术指标</span>{([['ma5', 'MA 5'], ['ma20', 'MA 20'], ['ema12', 'EMA 12'], ['boll', 'BOLL 20'], ['macd', 'MACD'], ['rsi', 'RSI 14']] as Array<[keyof ChartIndicators, string]>).map(([key, label]) => <button key={key} type="button" className={indicators[key] ? "indicator-chip active" : "indicator-chip"} onClick={() => toggleIndicator(key)}>{label}</button>)}</div><hr /><h2>策略参数</h2>{strategy.params.map((param) => <label key={param.key}>{param.label}<input type="number" min={param.minimum} max={param.maximum} step={param.step} value={params[param.key]} onChange={(event) => updateParam(param.key, Number(event.target.value))} /><small>{param.minimum} — {param.maximum}</small></label>)}<div className="execution-note">默认：收盘确认，下一交易日开盘成交；初始资金 100,000；手续费 8bp；滑点 2bp。</div></aside><section className="lab-results"><div className="chart-card"><div className="chart-head"><div><p className="eyebrow">CANDLESTICK & INDICATORS</p><h2>{securityName || "待查询标的"} {securityName && <small>{symbol}</small>}</h2></div><span>{bars.length ? `${bars.length} 根日线` : "点击加载行情"}</span></div><MarketChart bars={bars} indicators={indicators} trades={result?.trades || []} /></div><IndicatorPanels bars={bars} indicators={indicators} />{result ? <><div className="result-grid"><ResultCard label="累计收益" value={fmtPct(result.summary.totalReturn)} trend={result.summary.totalReturn} /><ResultCard label="最大回撤" value={fmtPct(result.summary.maxDrawdown)} trend={result.summary.maxDrawdown} inverse /><ResultCard label="Sharpe" value={fmtNum(result.summary.sharpe)} /><ResultCard label="交易次数" value={fmtNum(result.summary.tradeCount)} /></div><div className="chart-card"><div className="chart-head"><div><p className="eyebrow">EQUITY CURVE</p><h2>净值与回撤</h2></div><button className="button button-small button-quiet" onClick={saveExperiment}>保存实验</button></div><EquityPlot result={result} /><div className="warning-list">{[...result.notes, ...result.warnings].map((note) => <p key={note}>• {note}</p>)}</div></div><TradeTable result={result} /></> : <div className="empty-results"><strong>加载 K 线后即可查看指标</strong><p>运行回测后将在这里展示收益、回撤、实际买卖成交与交易流水。</p></div>}</section></div></div></section>;
}

type ChartIndicators = { ma5: boolean; ma20: boolean; ema12: boolean; boll: boolean; macd: boolean; rsi: boolean };
const finite = (value: number | null): value is number => value !== null && Number.isFinite(value);
function sma(values: number[], period: number): Array<number | null> { return values.map((_, index) => index + 1 < period ? null : values.slice(index - period + 1, index + 1).reduce((sum, value) => sum + value, 0) / period); }
function ema(values: number[], period: number): Array<number | null> { const out: Array<number | null> = []; const alpha = 2 / (period + 1); let previous: number | null = null; values.forEach((value, index) => { previous = index === 0 ? value : value * alpha + (previous as number) * (1 - alpha); out.push(previous); }); return out; }
function bollinger(values: number[], period = 20) { const mid = sma(values, period); return { mid, upper: values.map((_, index) => { if (!finite(mid[index])) return null; const slice = values.slice(index - period + 1, index + 1); const deviation = Math.sqrt(slice.reduce((sum, value) => sum + (value - (mid[index] as number)) ** 2, 0) / period); return (mid[index] as number) + 2 * deviation; }), lower: values.map((_, index) => { if (!finite(mid[index])) return null; const slice = values.slice(index - period + 1, index + 1); const deviation = Math.sqrt(slice.reduce((sum, value) => sum + (value - (mid[index] as number)) ** 2, 0) / period); return (mid[index] as number) - 2 * deviation; }) }; }
function linePath(values: Array<number | null>, min: number, max: number, width = 1000, height = 360) { const range = Math.max(max - min, 0.0001); let started = false; return values.map((value, index) => { if (!finite(value)) { started = false; return ""; } const x = (index / Math.max(values.length - 1, 1)) * width; const y = height - 24 - ((value - min) / range) * (height - 48); const command = started ? "L" : "M"; started = true; return `${command}${x.toFixed(2)},${y.toFixed(2)}`; }).join(" "); }
function MarketChart({ bars, indicators, trades }: { bars: Candle[]; indicators: ChartIndicators; trades: BacktestResult["trades"] }) { const visible = bars.slice(-160); if (!visible.length) return <div className="market-chart empty-plot">等待加载 K 线</div>; const closes = visible.map((bar) => bar.close); const ma5 = sma(closes, 5); const ma20 = sma(closes, 20); const ema12 = ema(closes, 12); const boll = bollinger(closes); const overlays = [indicators.ma5 ? ma5 : [], indicators.ma20 ? ma20 : [], indicators.ema12 ? ema12 : [], indicators.boll ? boll.upper : [], indicators.boll ? boll.lower : []].flat().filter(finite); const low = Math.min(...visible.map((bar) => bar.low), ...overlays); const high = Math.max(...visible.map((bar) => bar.high), ...overlays); const range = Math.max(high - low, 0.01); const width = 1000; const height = 360; const slot = width / visible.length; const priceY = (value: number) => height - 24 - ((value - low) / range) * (height - 48); const tradeByDate = new Map(trades.map((trade) => [trade.date, trade])); return <div className="market-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="K 线与技术指标图"><g className="chart-grid"><line x1="0" y1="84" x2={width} y2="84" /><line x1="0" y1="180" x2={width} y2="180" /><line x1="0" y1="276" x2={width} y2="276" /></g>{visible.map((bar, index) => { const x = index * slot + slot / 2; const rising = bar.close >= bar.open; const bodyTop = priceY(Math.max(bar.open, bar.close)); const bodyHeight = Math.max(Math.abs(priceY(bar.open) - priceY(bar.close)), 1); const trade = tradeByDate.get(bar.date); return <g key={bar.date}><line x1={x} y1={priceY(bar.high)} x2={x} y2={priceY(bar.low)} className={rising ? "candle up-candle" : "candle down-candle"} /><rect x={x - Math.max(slot * .28, 1)} y={bodyTop} width={Math.max(slot * .56, 2)} height={bodyHeight} className={rising ? "up-candle" : "down-candle"} />{trade && <text x={x} y={priceY(trade.price) - 8} className={trade.side.toLowerCase() === "buy" ? "buy-marker" : "sell-marker"}>{trade.side.toLowerCase() === "buy" ? "B" : "S"}</text>}</g>; })}{indicators.ma5 && <path d={linePath(ma5, low, high, width, height)} className="overlay ma5" />}{indicators.ma20 && <path d={linePath(ma20, low, high, width, height)} className="overlay ma20" />}{indicators.ema12 && <path d={linePath(ema12, low, high, width, height)} className="overlay ema12" />}{indicators.boll && <><path d={linePath(boll.upper, low, high, width, height)} className="overlay boll" /><path d={linePath(boll.mid, low, high, width, height)} className="overlay boll-mid" /><path d={linePath(boll.lower, low, high, width, height)} className="overlay boll" /></>}</svg><div className="plot-scale"><span>{fmtNum(high)}</span><span>{fmtNum(low)}</span></div><div className="chart-legend">{indicators.ma5 && <span className="legend-ma5">MA 5</span>}{indicators.ma20 && <span className="legend-ma20">MA 20</span>}{indicators.ema12 && <span className="legend-ema">EMA 12</span>}{indicators.boll && <span className="legend-boll">BOLL 20</span>}</div></div>; }
function IndicatorPanels({ bars, indicators }: { bars: Candle[]; indicators: ChartIndicators }) { const values = bars.slice(-160).map((bar) => bar.close); if (!values.length || (!indicators.macd && !indicators.rsi)) return null; const fast = ema(values, 12).map((value) => value ?? 0); const slow = ema(values, 26).map((value) => value ?? 0); const dif = fast.map((value, index) => value - slow[index]); const dea = ema(dif, 9).map((value) => value ?? 0); const histogram = dif.map((value, index) => (value - dea[index]) * 2); const rsi = values.map((_, index) => { if (index < 14) return null; const changes = values.slice(index - 14, index + 1).map((value, position, array) => position === 0 ? 0 : value - array[position - 1]).slice(1); const gain = changes.filter((value) => value > 0).reduce((sum, value) => sum + value, 0) / 14; const loss = Math.abs(changes.filter((value) => value < 0).reduce((sum, value) => sum + value, 0)) / 14; return loss === 0 ? 100 : 100 - 100 / (1 + gain / loss); }); return <div className="indicator-panels">{indicators.macd && <MiniIndicator title="MACD (12,26,9)" values={[dif, dea, histogram]} colors={["#315efb", "#dd7a18", "#91a0b3"]} />}{indicators.rsi && <MiniIndicator title="RSI (14)" values={[rsi]} colors={["#7446dc"]} fixedRange={[0, 100]} />}</div>; }
function MiniIndicator({ title, values, colors, fixedRange }: { title: string; values: Array<Array<number | null>>; colors: string[]; fixedRange?: [number, number] }) { const all = values.flat().filter(finite); const min = fixedRange ? fixedRange[0] : Math.min(...all, 0); const max = fixedRange ? fixedRange[1] : Math.max(...all, 0); return <div className="mini-indicator"><span>{title}</span><svg viewBox="0 0 1000 110" preserveAspectRatio="none">{fixedRange && <><line x1="0" y1="33" x2="1000" y2="33" className="threshold" /><line x1="0" y1="77" x2="1000" y2="77" className="threshold" /></>}{values.map((series, index) => <path key={index} d={linePath(series, min, max, 1000, 110)} stroke={colors[index]} className="mini-line" />)}</svg></div>; }
function EquityPlot({ result }: { result: BacktestResult }) { const values = result.equity.map((item) => item.equity); if (!values.length) return <div className="plot empty-plot">本次回测未返回净值序列</div>; const min = Math.min(...values); const max = Math.max(...values); const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${92 - ((value - min) / Math.max(max - min, 0.01)) * 75}`).join(" "); return <div className="plot equity"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg><div className="plot-scale"><span>{fmtNum(max)}</span><span>{fmtNum(min)}</span></div></div>; }
function ResultCard({ label, value, trend, inverse }: { label: string; value: string; trend?: number; inverse?: boolean }) { const positive = inverse ? (trend || 0) >= 0 : (trend || 0) >= 0; return <div className="result-card"><span>{label}</span><strong className={trend === undefined ? "" : positive ? "up" : "down"}>{value}</strong></div>; }
function TradeTable({ result }: { result: BacktestResult }) { return <div className="trade-card"><div className="chart-head"><div><p className="eyebrow">TRADE LEDGER</p><h2>交易流水</h2></div><span>{result.trades.length} 笔</span></div><div className="table-wrap"><table><thead><tr><th>日期</th><th>方向</th><th>价格</th><th>数量</th><th>原因</th></tr></thead><tbody>{result.trades.slice(0, 20).map((trade, index) => { const isBuy = trade.side.toLowerCase() === "buy"; return <tr key={`${trade.date}-${index}`}><td>{trade.date}</td><td className={isBuy ? "up" : "down"}>{isBuy ? "买入" : "卖出"}</td><td>{fmtNum(trade.price)}</td><td>{fmtNum(trade.shares)}</td><td>{trade.reason || "—"}</td></tr>; })}</tbody></table></div></div>; }

function Experiments() { const [experiments, setExperiments] = useState<Experiment[]>(() => JSON.parse(localStorage.getItem("aiQuantLab.experiments") || "[]")); const clear = () => { localStorage.removeItem("aiQuantLab.experiments"); setExperiments([]); }; return <section className="wrap page"><p className="eyebrow">EXPERIMENT LIBRARY</p><h1>实验库</h1><p className="page-intro">保存配置、数据区间、引擎与成本假设，才有可能复现一次研究。</p>{experiments.length ? <><div className="section-heading minor"><h2>本地已保存实验</h2><button className="text-button" onClick={clear}>清空本地记录</button></div><div className="experiment-list">{experiments.map((item) => <article key={item.id}><div><span className="tag">{item.strategyName}</span><h3>{item.name}</h3><p>{item.period} · {item.engine} · {item.createdAt}</p></div><div className="experiment-metrics"><span>收益 <b className="up">{fmtPct(item.summary.totalReturn)}</b></span><span>回撤 <b>{fmtPct(item.summary.maxDrawdown)}</b></span></div></article>)}</div></> : <div className="empty-results"><strong>尚无保存的实验</strong><p>进入任意策略工作台并运行回测后，即可保存一份配置快照。</p><Link className="button button-small" to="/strategies">选择策略</Link></div>}</section>; }

function BeginnerGuide() { return <section className="wrap page guide-page"><p className="eyebrow">BEGINNER GUIDE</p><h1>从“看图”到“做研究”</h1><p className="page-intro">量化研究不是预测明天涨跌，而是把想法写成规则，再确认它在不同阶段是否依然可靠。</p><div className="guide-hero-card"><div><span className="tag">推荐起点</span><h2>用 MA 双均线做第一次完整研究</h2><p>它的规则清晰、参数很少，适合理解信号、交易成本、回撤和实验保存分别意味着什么。</p></div><Link className="button" to="/strategies/ma_cross/lab">开始示例研究</Link></div><div className="guide-grid"><GuideCard index="01" title="认识一张图" body="输入标的并加载行情。先看价格趋势，再开启 MA、BOLL、MACD 或 RSI；每个指标都是观察市场的角度，不是预测工具。" action="进入行情研究" to="/strategies/ma_cross/lab" /><GuideCard index="02" title="设置一条规则" body="从默认参数开始。先不要追逐最优参数，理解快线、慢线和目标仓位各自改变了什么。" action="查看双均线策略" to="/strategies/ma_cross" /><GuideCard index="03" title="读懂一份结果" body="收益必须与最大回撤、交易次数、成本和样本区间一起看。没有风险上下文的收益数字没有结论价值。" action="学习结果解读" to="/methodology" /></div><section className="glossary"><div><p className="eyebrow">GLOSSARY</p><h2>第一次会遇到的词</h2></div><div className="glossary-grid"><Glossary term="K 线" text="把一个周期内的开盘、最高、最低和收盘价格放在同一根柱中。" /><Glossary term="回测" text="用历史数据模拟一套明确规则的执行过程，不是对未来收益的承诺。" /><Glossary term="最大回撤" text="净值从历史高点到之后低点的最大跌幅，用于观察策略的压力时刻。" /><Glossary term="滑点与手续费" text="模拟成交时的摩擦成本；忽略它们，回测通常会显得过于乐观。" /></div></section></section>; }
function GuideCard({ index, title, body, action, to }: { index: string; title: string; body: string; action: string; to: string }) { return <article className="guide-card"><span>{index}</span><h2>{title}</h2><p>{body}</p><Link to={to}>{action} <b>→</b></Link></article>; }
function Glossary({ term, text }: { term: string; text: string }) { return <article><strong>{term}</strong><p>{text}</p></article>; }

function IndicatorLibrary() {
  const categories: Array<"全部" | IndicatorCategory> = ["全部", "趋势", "动量", "波动与风险", "成交量"];
  const [category, setCategory] = useState<"全部" | IndicatorCategory>("全部");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(indicatorGuides[0].id);
  const [tab, setTab] = useState<"principle" | "calculation" | "meaning" | "playbook" | "decisionGuide">("principle");
  const visible = useMemo(() => indicatorGuides.filter((item) => (category === "全部" || item.category === category) && `${item.name}${item.english}${item.summary}`.toLowerCase().includes(query.toLowerCase())), [category, query]);
  const selected = indicatorGuides.find((item) => item.id === selectedId) || indicatorGuides[0];
  const openIndicator = (item: IndicatorGuide) => { setSelectedId(item.id); setTab("principle"); window.setTimeout(() => document.getElementById("indicator-detail")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0); };
  const tabs: Array<[typeof tab, string]> = [["principle", "原理"], ["calculation", "计算过程"], ["meaning", "含义"], ["playbook", "指标战法"], ["decisionGuide", "投资提示"]];
  const tabContent = tab === "principle" ? [selected.principle] : selected[tab];
  return <section className="wrap page indicator-page"><p className="eyebrow">INDICATOR LIBRARY</p><h1>指标百科</h1><p className="page-intro">把技术指标当作观察市场的语言。先理解它在计算什么、适合什么环境，再决定是否把它写入一条可验证的规则。</p><div className="indicator-intro"><div><strong>{indicatorGuides.length} 个已支持指标</strong><span>趋势、动量、波动风险与成交量</span></div><Link className="button button-small" to="/strategies/ma_cross/lab">在行情图中使用指标</Link></div><div className="indicator-tools"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 MA、MACD、波动或成交量" aria-label="搜索指标" /><div className="filter-row">{categories.map((item) => <button key={item} className={category === item ? "filter active" : "filter"} onClick={() => setCategory(item)}>{item}</button>)}</div></div><div className="indicator-card-grid">{visible.map((item) => <article className={selected.id === item.id ? "indicator-card selected" : "indicator-card"} key={item.id}><div><span className="tag">{item.category}</span><span className="indicator-code">{item.english}</span></div><h2>{item.name}</h2><p>{item.summary}</p><button className="button button-small button-quiet" onClick={() => openIndicator(item)}>查看指标详情</button></article>)}</div><section id="indicator-detail" className="indicator-detail"><div className="indicator-detail-head"><div><p className="eyebrow">{selected.category.toUpperCase()}</p><h2>{selected.name} <span>{selected.english}</span></h2><p>{selected.summary}</p></div><Link className="text-link" to="/strategies/ma_cross/lab">去行情研究中使用 <span>→</span></Link></div><div className="indicator-tabs" role="tablist" aria-label="指标内容切换">{tabs.map(([key, label]) => <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>)}</div><div className="indicator-content"><ol>{tabContent.map((item) => <li key={item}>{item}</li>)}</ol>{tab === "decisionGuide" && <aside><strong>使用边界</strong><ul>{selected.cautions.map((item) => <li key={item}>{item}</li>)}</ul></aside>}</div></section><div className="indicator-disclaimer"><strong>重要提醒</strong><p>指标用于研究与复盘，不构成个性化投资建议。任何战法都应在明确标的、样本区间、交易成本和风险约束后进行回测验证。</p></div></section>;
}

function Methodology() { return <section className="wrap page prose"><p className="eyebrow">METHODOLOGY</p><h1>研究方法</h1><p className="page-intro">平台把可解释性、可复现性和风险暴露放在收益展示之前。</p><h2>交易时点</h2><p>策略在当日收盘后的可得信息上生成信号，默认以次一交易日开盘价成交。此约定避免将收盘后的信息提前用于交易决策。</p><h2>成本与执行</h2><p>每次验证固定初始资金、手续费、滑点、最低佣金、整手规则与是否允许做空。结果页面会同时显示这些假设与使用的回测引擎。</p><h2>稳健性</h2><p>不把单点最优参数当作结论。应检查相邻参数、不同市场阶段、样本外区间以及更高交易成本下的表现。</p><h2>数据来源</h2><p>GitHub 部署环境只使用 AkShare、yfinance 等开源或免费数据源；RQData 只在本地、已授权的研究服务中开放。公开页面的离线快照会标明更新时间，不能替代实时查询。</p></section>; }

function Settings() { const [url, setUrl] = useState(getApiBase()); const [message, setMessage] = useState(""); const save = async () => { setApiBase(url); try { await api.health(); setMessage("数据服务已连接。首页与工作台会优先使用该实时 API。"); } catch { setMessage("地址已保存，但当前无法连接。GitHub Pages 会继续尝试读取已发布快照。"); } }; return <section className="wrap page settings"><p className="eyebrow">SETTINGS</p><h1>数据服务设置</h1><p className="page-intro">GitHub Pages 负责界面；实时行情由部署在云端或本机的 Python API 提供。</p><div className="content-card"><label>API 地址<input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://your-api.example.com" /></label><button className="button" onClick={save}>保存并检查</button>{message && <p className="notice">{message}</p>}<hr /><h2>部署说明</h2><p>将 `api/` 目录部署为 Python Web Service，并在其环境变量中设置允许的 GitHub Pages 域名。页面将优先请求该 API；若它暂时不可用，则回退到 GitHub Actions 定时生成的市场快照。</p></div></section>; }
function NotFound() { return <section className="wrap page"><h1>页面不存在</h1><p className="page-intro">你访问的页面可能还没有被发布。</p><Link className="button" to="/">返回首页</Link></section>; }
function Footer() { return <footer><div className="wrap"><span>AI Quant Lab · Research First</span><span>历史回测不代表未来表现 · 不构成投资建议</span></div></footer>; }

export default App;
