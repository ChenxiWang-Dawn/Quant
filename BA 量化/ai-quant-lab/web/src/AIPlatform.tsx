import { FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "./lib/api";

type Asset = Record<string, unknown>;
const nav = [
  ["/ai/getting-started", "入门路径"], ["/ai/datasets", "数据与快照"], ["/ai/features", "特征库"], ["/ai/experiments", "实验库"], ["/ai/models", "模型注册表"], ["/ai/portfolios", "组合研究"], ["/ai/evaluations", "评测中心"], ["/ai/deep-learning", "深度学习基线"], ["/ai/rl", "强化学习实验室"], ["/ai/copilot", "研究助手"], ["/ai/monitoring", "监控中心"], ["/ai/negative-results", "负面结果库"], ["/ai/methodology", "研究方法"],
];
const asArray = (value: unknown) => Array.isArray(value) ? value : [];
const text = (value: unknown, fallback = "—") => typeof value === "string" || typeof value === "number" ? String(value) : fallback;

function Shell({ children, title, subtitle, action }: { children: ReactNode; title: string; subtitle: string; action?: ReactNode }) {
  const { pathname } = useLocation();
  return <div className="ai-platform wrap"><aside className="ai-side-nav"><Link to="/ai" className="ai-side-brand">AI 研究工作台<small>可信、可复现、可审计</small></Link>{nav.map(([to, label]) => <Link key={to} to={to} className={pathname === to || (to !== "/ai/getting-started" && pathname.startsWith(`${to}/`)) ? "active" : ""}>{label}</Link>)}</aside><section className="ai-platform-content"><div className="ai-page-heading"><div><p className="eyebrow">AI QUANT LAB / RESEARCH OS</p><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>{children}</section></div>;
}

export default function AIPlatformPage() {
  const { pathname } = useLocation();
  if (pathname === "/ai/getting-started") return <GettingStarted />;
  if (pathname.startsWith("/ai/datasets")) return <Datasets />;
  if (pathname.startsWith("/ai/features")) return <Features />;
  if (pathname.startsWith("/ai/experiments")) return <Experiments />;
  if (pathname.startsWith("/ai/models")) return <Models />;
  if (pathname.startsWith("/ai/portfolios")) return <Portfolios />;
  if (pathname.startsWith("/ai/evaluations")) return <Evaluations />;
  if (pathname.startsWith("/ai/deep-learning")) return <DeepLearningLab />;
  if (pathname.startsWith("/ai/rl")) return <ReinforcementLab />;
  if (pathname.startsWith("/ai/copilot")) return <Copilot />;
  if (pathname.startsWith("/ai/monitoring")) return <Monitoring />;
  if (pathname.startsWith("/ai/negative-results")) return <NegativeResults />;
  return <Methodology />;
}

function GettingStarted() {
  return <Shell title="从第一个可信实验开始" subtitle="不需要先懂机器学习。按这条路径完成一次横截面选股研究，再逐步进入深度学习、强化学习和证据助手。" action={<Link to="/ai/experiments/new" className="button">创建第一个实验 →</Link>}><div className="ai-learning-path">{[["01", "建立数据快照", "固定股票池、时间范围、来源与数据质量报告。", "/ai/datasets"], ["02", "选择可解释特征", "理解每个特征何时可获得、需要多少预热期以及潜在泄漏。", "/ai/features"], ["03", "运行样本外实验", "先和无技能、线性和等权基准比较，再解释成本后的差异。", "/ai/experiments/new"], ["04", "审阅、登记与影子观察", "通过 Gate 后再注册候选模型；影子运行只记录预测，不执行交易。", "/ai/models"]].map(([number, title, body, to]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{body}</p><Link to={to}>进入这一步 →</Link></article>)}</div><div className="ai-callout"><b>初学者的关键原则</b><p>模型只输出排序或预测；仓位、成本和风险约束由独立组合层处理。任何历史结果都不等同于未来收益承诺。</p></div></Shell>;
}

function Datasets() {
  const [datasets, setDatasets] = useState<Asset[]>([]); const [status, setStatus] = useState(""); const [busy, setBusy] = useState(false);
  const refresh = () => api.aiDatasets().then((data) => setDatasets(data.datasets)).catch((error: Error) => setStatus(error.message));
  useEffect(() => { void refresh(); }, []);
  const build = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); setStatus(""); try { const record = await api.aiBuildDataset({ name: form.get("name"), universe: String(form.get("universe")).split(/[，,\s]+/).filter(Boolean), start: form.get("start"), end: form.get("end"), source: "auto" }); setStatus(`已建立快照：${text(record.id)}`); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "构建失败"); } finally { setBusy(false); } };
  return <Shell title="数据集与不可变快照" subtitle="训练只能引用已记录的数据范围、来源、指纹和质量检查。公开网页不保存私有行情凭据。"><div className="ai-page-grid"><form className="ai-card ai-compact-form" onSubmit={build}><h2>构建 A 股数据快照</h2><label>名称<input name="name" placeholder="例如：沪深十股研究快照" /></label><label>标的池<textarea name="universe" defaultValue="000001.XSHE, 600519.XSHG, 000333.XSHE, 002594.XSHE" /></label><div className="ai-two-fields"><label>开始日期<input name="start" type="date" defaultValue="2020-01-01" required /></label><label>结束日期<input name="end" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label></div><button className="button" disabled={busy}>{busy ? "正在建立…" : "建立快照"}</button><small>{status}</small></form><div className="ai-card"><h2>数据时间语义</h2><dl className="ai-definition-list"><dt>事件时间</dt><dd>交易或事件实际发生的时点。</dd><dt>可获得时间</dt><dd>研究者在当时最早能使用的时点；特征按此对齐。</dd><dt>快照指纹</dt><dd>固定覆盖范围、来源和字段，避免重复实验时悄悄换数据。</dd></dl></div></div><AssetTable items={datasets} empty="还没有可用数据集。" columns={["name", "kind", "start", "end", "fingerprint"]} /></Shell>;
}

function Features() {
  const [sets, setSets] = useState<Asset[]>([]); useEffect(() => { api.aiFeatures().then((data) => setSets(data.featureSets)).catch(() => setSets([])); }, []);
  return <Shell title="特征库" subtitle="每个特征都记录经济直觉、可获得时间、预热期和泄漏风险；它们不是自动有效的买卖信号。"><div className="ai-feature-cards">{sets.flatMap((set) => asArray(set.features).map((feature) => ({ set, feature: feature as Asset }))).map(({ set, feature }) => <article key={text(feature.id)}><span>{text(feature.category)}</span><h2>{text(feature.name)}</h2><p>{text(feature.description)}</p><dl><dt>可获得时间</dt><dd>{text(feature.availableTime)}</dd><dt>预热期</dt><dd>{text(feature.warmup)} 个交易日</dd><dt>泄漏风险</dt><dd>{text(feature.leakageRisk)}</dd></dl><small>特征集：{text(set.name)} · {text(set.version)}</small></article>)}</div></Shell>;
}

function Experiments() {
  const { pathname } = useLocation(); const [items, setItems] = useState<Asset[]>([]); const [compare, setCompare] = useState<Asset[] | null>(null); const [error, setError] = useState("");
  useEffect(() => { api.aiExperiments().then((data) => setItems(data.experiments)).catch((caught: Error) => setError(caught.message)); }, []);
  if (pathname.endsWith("/new")) return <ExperimentWizard />;
  const compareRuns = async () => { if (items.length < 2) return setError("至少完成两次实验后才能比较。"); try { const data = await api.aiCompareExperiments(items.slice(0, 2).map((item) => text(item.id))); setCompare(data.experiments); setError(data.warning || "这两次实验使用同一数据和切分，可以比较。"); } catch (caught) { setError(caught instanceof Error ? caught.message : "比较失败"); } };
  return <Shell title="AI 实验库" subtitle="每一次运行保留不可变配置、数据指纹、时间切分、成本后结果与 Gate。不同数据或切分不会被强行判定胜负。" action={<Link className="button" to="/ai/experiments/new">新建实验 →</Link>}><div className="ai-toolbar"><button className="button button-quiet" onClick={compareRuns}>比较最近两次</button><span>{error}</span></div>{compare && <AssetTable items={compare} columns={["id", "model", "gate"]} empty="" />}<AssetTable items={items} columns={["id", "task", "status", "dataFingerprint", "configHash"]} empty="运行一次实验后，结果会在这里成为可检索的研究资产。" detailPrefix="/ai/experiments/" /></Shell>;
}

function ExperimentWizard() {
  return <Shell title="统一 AI 实验向导" subtitle="八步流程会先冻结问题、数据、标签、特征、切分、模型、评测和资源预算。当前可运行模板是 A 股横截面排序；深度学习模板会在本地 Torch 能力可用时开放。"><div className="ai-wizard-steps">{["定义问题", "选择数据", "定义标签", "选择特征", "时间切分", "选择模型", "定义评测", "审核并运行"].map((item, index) => <div key={item}><b>{index + 1}</b><span>{item}</span></div>)}</div><div className="ai-callout"><b>可运行模板：A 股横截面 Top-K 排序</b><p>系统默认使用收盘后可得的价格与成交量特征、按时间隔离的训练/验证/测试、成本后组合和等权基准。</p><Link to="/ai" className="button">打开实验配置器 →</Link></div><div className="ai-card"><h2>高级模板的准入条件</h2><p>深度学习必须先证明相对简单模型的样本外增量；强化学习只在独立的历史仿真环境中运行；研究助手只能读取证据和生成草稿，不能下单或扩大权限。</p></div></Shell>;
}

function Models() {
  const [models, setModels] = useState<Asset[]>([]); const [experiments, setExperiments] = useState<Asset[]>([]); const [status, setStatus] = useState("");
  const refresh = () => { api.aiModels().then((data) => setModels(data.models)).catch(() => setModels([])); api.aiExperiments().then((data) => setExperiments(data.experiments)).catch(() => setExperiments([])); };
  useEffect(refresh, []);
  const register = async () => { const experimentId = text(experiments[0]?.id, ""); if (!experimentId) return setStatus("请先运行实验。"); try { const record = await api.aiRegisterModel({ experimentId, version: "1.0.0" }); setStatus(`已注册：${text(record.id)}`); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "注册失败"); } };
  const promote = async (id: string) => { try { await api.aiPromoteModel(id, { status: "validated", alias: "@candidate", reason: "人工审阅后晋级" }); setStatus("模型状态已更新并写入审计记录。"); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "晋级失败"); } };
  return <Shell title="模型注册表" subtitle="实验产物与注册模型分离。模型必须通过预设 Gate 和人工审阅，才可成为验证模型或影子研究候选。" action={<button className="button" onClick={register}>从最近实验注册</button>}><div className="ai-toolbar"><span>{status}</span></div><div className="ai-model-list">{models.map((model) => <article key={text(model.id)}><div><span className="ai-status">{text(model.status)}</span><h2>{text(model.name)}</h2><p>{text(model.id)} · {text(model.version)}</p></div><div><p>Gate：{text((model.gate as Asset)?.status)}</p><p>别名：{asArray(model.aliases).join("、") || "未设置"}</p><button className="button button-small button-quiet" onClick={() => promote(text(model.id))}>申请验证晋级</button></div></article>)}</div>{!models.length && <Empty text="还没有注册模型。先从一次完成的实验创建候选模型。" />}</Shell>;
}

function Portfolios() {
  const [items, setItems] = useState<Asset[]>([]); const [experiments, setExperiments] = useState<Asset[]>([]); const [status, setStatus] = useState("");
  const refresh = () => { api.aiPortfolios().then((data) => setItems(data.portfolios)).catch(() => setItems([])); api.aiExperiments().then((data) => setExperiments(data.experiments)).catch(() => setExperiments([])); };
  useEffect(refresh, []);
  const build = async () => { if (!experiments[0]) return setStatus("请先完成一个实验。"); try { const result = await api.aiBuildPortfolio({ experimentId: experiments[0].id, method: "top_k_equal_weight", maxWeight: .25, maxTurnover: 1 }); setStatus(`已从固定预测批次构建组合：${text(result.id)}`); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "构建失败"); } };
  return <Shell title="组合研究" subtitle="模型预测不等于交易指令。组合层单独记录权重、换手、集中度等约束，以及约束前后的变化。" action={<button className="button" onClick={build}>从最近实验构建</button>}><div className="ai-toolbar"><span>{status}</span></div><AssetTable items={items} columns={["id", "predictionBatchDate", "construction", "status"]} empty="还没有组合构建记录。" /></Shell>;
}

function Evaluations() {
  const [items, setItems] = useState<Asset[]>([]); const [experiments, setExperiments] = useState<Asset[]>([]); const [status, setStatus] = useState("");
  const refresh = () => { api.aiEvaluations().then((data) => setItems(data.evaluations)).catch(() => setItems([])); api.aiExperiments().then((data) => setExperiments(data.experiments)).catch(() => setExperiments([])); };
  useEffect(refresh, []);
  const run = async () => { if (!experiments[0]) return setStatus("请先运行实验。"); try { const evaluation = await api.aiEvaluation({ experimentId: experiments[0].id, suite: "cross_section_ranking_investment_v1", stressTransactionCost: .002 }); setStatus(`评测已完成：${text(evaluation.id)}`); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "评测失败"); } };
  return <Shell title="统一评测中心" subtitle="同一研究同时检查统计排序、成本后组合、基准、稳定性、时间完整性和预设 Gate。" action={<button className="button" onClick={run}>评测最近实验</button>}><div className="ai-toolbar"><span>{status}</span></div><AssetTable items={items} columns={["id", "experimentId", "suite", "status"]} empty="暂无评测。评测会在模型注册和晋级前固定研究门槛。" /></Shell>;
}

function ReinforcementLab() {
  const [result, setResult] = useState<Asset | null>(null); const [runs, setRuns] = useState<Asset[]>([]); const [status, setStatus] = useState("");
  const refresh = () => api.aiRlRuns().then((data) => setRuns(data.runs)).catch(() => setRuns([])); useEffect(() => { void refresh(); }, []);
  const validate = async () => { try { setResult(await api.aiRlValidate({})); setStatus("环境检查完成。任何失败都会阻止训练。 "); } catch (error) { setStatus(error instanceof Error ? error.message : "检查失败"); } };
  const run = async (algorithm = "baseline") => { try { const item = await api.aiRlRun({ algorithm, seeds: [7, 17, 29], transactionCost: .001, trainingSteps: 20000 }); setResult(item); setStatus(algorithm === "ppo" ? "PPO 多种子仿真已完成；结果只用于研究和影子观察。" : "规则基准仿真已完成；结果只用于研究和影子观察。"); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "仿真失败"); } };
  return <Shell title="强化学习实验室" subtitle="先验证环境，再评估受约束的序列决策。当前只提供历史仿真和影子研究，系统没有任何实盘或下单能力。" action={<div className="ai-action-pair"><button className="button button-quiet" onClick={validate}>验证环境</button><button className="button button-quiet" onClick={() => run("baseline")}>运行规则基准</button><button className="button" onClick={() => run("ppo")}>运行本地 PPO</button></div>}><div className="ai-toolbar"><span>{status}</span></div>{result && <JsonCard title="最近环境/仿真结果" value={result} />}<AssetTable items={runs} columns={["id", "algorithm", "status", "boundary"]} empty="尚未运行 RL 仿真。" /></Shell>;
}

function DeepLearningLab() {
  const [items, setItems] = useState<Asset[]>([]); const [result, setResult] = useState<Asset | null>(null); const [status, setStatus] = useState(""); const [architecture, setArchitecture] = useState("mlp");
  const refresh = () => api.aiDeepLearningRuns().then((data) => setItems(data.runs)).catch(() => setItems([])); useEffect(() => { void refresh(); }, []);
  const run = async () => { try { const item = await api.aiDeepLearningRun({ architecture, lookback: 10, epochs: 80, seeds: [7, 17, 29] }); setResult(item); setStatus(`${architecture.toUpperCase()} 多种子训练已完成；仍需与相同数据和切分下的简单模型比较，才能注册。`); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "训练不可用"); } };
  return <Shell title="深度学习研究基线" subtitle="训练只在本地/受控 Worker 执行，并固定种子、早停、梯度裁剪和张量契约。模型通过简单基线 Gate 前不能晋级。" action={<div className="ai-action-pair"><select value={architecture} onChange={(event) => setArchitecture(event.target.value)}><option value="mlp">MLP</option><option value="tcn">TCN</option><option value="gru">GRU</option><option value="lstm">LSTM</option><option value="transformer">Transformer</option></select><button className="button" onClick={run}>运行本地训练</button></div>}><div className="ai-toolbar"><span>{status}</span></div><div className="ai-page-grid"><div className="ai-card"><h2>准入门槛</h2><p>必须先有简单模型基准、严格时间切分和足够样本。每个随机种子独立记录；只选最优种子不构成有效结论。</p><dl className="ai-definition-list"><dt>模型目录</dt><dd>MLP、TCN、GRU、LSTM 与序列 Transformer。</dd><dt>已实现训练纪律</dt><dd>固定种子、验证早停、最佳验证检查点、梯度裁剪。</dd><dt>运行位置</dt><dd>本地 CUDA Worker；公开云端不训练。</dd></dl></div>{result && <JsonCard title="最近训练结果" value={result} />}</div><AssetTable items={items} columns={["id", "architecture", "status"]} empty="本地尚未训练深度学习基线。" /></Shell>;
}

function Copilot() {
  const [mode, setMode] = useState("review"); const [role, setRole] = useState("experiment_reviewer"); const [question, setQuestion] = useState("请审阅这个平台的时间切分、测试集使用和成本后评测应如何检查？"); const [trace, setTrace] = useState<Asset | null>(null); const [error, setError] = useState("");
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); try { setTrace(await api.aiCopilot({ mode, role, question })); } catch (caught) { setError(caught instanceof Error ? caught.message : "助手暂不可用"); } };
  return <Shell title="量化研究助手" subtitle="它是受控的证据助手：回答带引用、区分事实和推断、记录轨迹；无交易、外发消息、代码执行或权限提升能力。"><form className="ai-card ai-copilot-form" onSubmit={submit}><div className="ai-two-fields"><label>模式<select value={mode} onChange={(event) => setMode(event.target.value)}><option value="learning">学习模式</option><option value="research">研究模式</option><option value="build">构建模式（仅草稿）</option><option value="review">审阅模式</option></select></label><label>专业角色<select value={role} onChange={(event) => setRole(event.target.value)}><option value="data_auditor">数据审计助手</option><option value="experiment_reviewer">实验审阅助手</option><option value="company_researcher">公司研究助手</option><option value="strategy_reviewer">策略复盘助手</option></select></label></div><label>研究问题<textarea value={question} onChange={(event) => setQuestion(event.target.value)} /></label><button className="button">生成带证据的研究回答</button><small>{error}</small></form>{trace && <article className="ai-copilot-answer"><p className="ai-status">{text(trace.role)} · {text((trace.usage as Asset)?.engine)}</p><h2>受控回答</h2><p>{text(trace.answer)}</p><h3>可核验引用</h3>{asArray(trace.citations).map((citation) => <a key={text((citation as Asset).id)} href={text((citation as Asset).url)}>{text((citation as Asset).title)}<small>{text((citation as Asset).excerpt)}</small></a>)}<p className="ai-boundary">{text(trace.boundary)}</p></article>}</Shell>;
}

function Monitoring() {
  const [data, setData] = useState<Asset | null>(null); useEffect(() => { api.aiMonitoring().then(setData).catch(() => setData(null)); }, []);
  return <Shell title="监控与影子运行" subtitle="监控说明影响、证据和建议动作。漂移不会自动触发交易，也不会自动把模型升级为有效。">{data ? <><div className="ai-count-grid">{Object.entries((data.counts as Asset) || {}).map(([label, value]) => <article key={label}><span>{label}</span><b>{text(value)}</b></article>)}</div><div className="ai-monitor-list">{asArray(data.checks).map((check) => <article key={text((check as Asset).name)}><span className={`ai-status ${text((check as Asset).status)}`}>{text((check as Asset).status)}</span><h2>{text((check as Asset).name)}</h2><p>{text((check as Asset).evidence)}</p><small>建议动作：{text((check as Asset).action)}</small></article>)}</div></> : <Empty text="监控服务暂不可用。公开教学与模型卡仍可浏览。" />}</Shell>;
}

function NegativeResults() {
  const [items, setItems] = useState<Asset[]>([]); const [status, setStatus] = useState(""); const refresh = () => api.aiNegativeResults().then((data) => setItems(data.negativeResults)).catch(() => setItems([])); useEffect(() => { void refresh(); }, []);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api.aiSaveNegativeResult({ title: form.get("title"), hypothesis: form.get("hypothesis"), failureType: form.get("failureType"), evidence: form.get("evidence"), retryAdvice: form.get("retryAdvice") }); setStatus("已保存为可检索的负面研究资产。"); event.currentTarget.reset(); refresh(); } catch (error) { setStatus(error instanceof Error ? error.message : "保存失败"); } };
  return <Shell title="负面结果库" subtitle="没有增量、成本后失效和只在单一阶段有效的结论同样值得保存；这能避免重复试错和选择性汇报。"><div className="ai-page-grid"><form className="ai-card ai-compact-form" onSubmit={submit}><h2>保存失败研究</h2><label>标题<input name="title" required /></label><label>研究假设<textarea name="hypothesis" required /></label><label>失败类型<select name="failureType"><option>未超过简单基准</option><option>成本后失效</option><option>时间段不稳定</option><option>潜在泄漏或测试集过用</option></select></label><label>证据<textarea name="evidence" required /></label><label>是否值得重试<input name="retryAdvice" placeholder="例如：扩大股票池后重新验证" /></label><button className="button">保存负面结果</button><small>{status}</small></form><AssetTable items={items} columns={["title", "failureType", "status"]} empty="还没有负面结果。" /></div></Shell>;
}

function Methodology() {
  return <Shell title="AI 研究方法与治理" subtitle="复杂模型不是研究质量的替代品。平台把数据时间语义、样本外验证、成本、可解释性和人工审阅置于模型复杂度之前。"><div className="ai-methodology-grid">{[["数据层", "每条信息按可获得时间对齐；快照、字段、质量和指纹固定。"], ["验证层", "禁止随机切分；使用训练、验证、测试、purge 与 embargo 管理未来信息泄漏。"], ["模型层", "从基线到复杂模型；模型输出预测或排序，不直接输出买卖。"], ["组合与风险层", "独立记录 Top-K、权重、换手、集中度、成本与约束变化。"], ["治理层", "实验、模型、评测、晋级和回滚全部留下审计记录。"], ["助手边界", "引用不足时拒答；工具仅限读取和受控计算；没有实盘权限。"]].map(([title, body]) => <article key={title}><h2>{title}</h2><p>{body}</p></article>)}</div></Shell>;
}

function AssetTable({ items, columns, empty, detailPrefix }: { items: Asset[]; columns: string[]; empty: string; detailPrefix?: string }) { if (!items.length) return <Empty text={empty} />; return <div className="ai-asset-table"><div className="ai-table-row ai-table-head">{columns.map((column) => <span key={column}>{column}</span>)}</div>{items.map((item) => <div className="ai-table-row" key={text(item.id)}>{columns.map((column, index) => <span key={column}>{index === 0 && detailPrefix ? <Link to={`${detailPrefix}${text(item.id)}`}>{text(item[column])}</Link> : typeof item[column] === "object" ? text((item[column] as Asset)?.status, "已记录") : text(item[column])}</span>)}</div>)}</div>; }
function Empty({ text: message }: { text: string }) { return <div className="ai-empty-state">{message}</div>; }
function JsonCard({ title, value }: { title: string; value: Asset }) { return <article className="ai-card ai-json-card"><h2>{title}</h2><pre>{JSON.stringify(value, null, 2)}</pre></article>; }
