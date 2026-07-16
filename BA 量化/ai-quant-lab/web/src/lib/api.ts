import type { AIExperimentRequest, AIExperimentResult, BacktestResult, Candle, Quote, Strategy } from "../types";

const LOCAL_DEFAULT = "http://127.0.0.1:8787";
const configuredBase = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "");

export const getApiBase = () => localStorage.getItem("aiQuantLab.apiBase") || configuredBase || LOCAL_DEFAULT;
export const setApiBase = (value: string) => localStorage.setItem("aiQuantLab.apiBase", value.replace(/\/$/, ""));

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || payload?.detail?.error?.message || payload?.detail || "服务请求失败");
  return payload as T;
}

export const api = {
  health: () => request<{ ok: boolean; providers: Record<string, boolean> }>("/api/v1/health"),
  strategies: () => request<{ strategies: Strategy[] }>("/api/v1/strategies"),
  quote: (symbol: string) => request<Quote>(`/api/v1/market-data/quote?symbol=${encodeURIComponent(symbol)}`),
  bars: (symbol: string, start: string, end: string, source = "auto") =>
    request<{ symbol: string; name: string; source: string; candles: Candle[] }>(
      `/api/v1/market-data/bars?symbol=${encodeURIComponent(symbol)}&start=${start}&end=${end}&source=${source}`,
    ),
  backtest: (payload: Record<string, unknown>) => request<BacktestResult>("/api/v1/backtests", { method: "POST", body: JSON.stringify(payload) }),
  aiCapabilities: () => request<{ phase: string; available: string[]; planned: string[]; rqdataLocalOnly: boolean }>("/api/v1/ai/capabilities"),
  aiExperiment: (payload: AIExperimentRequest) => request<AIExperimentResult>("/api/v1/ai/experiments", { method: "POST", body: JSON.stringify(payload) }),
  aiDatasets: () => request<{ datasets: Record<string, unknown>[] }>("/api/v1/ai/datasets"),
  aiBuildDataset: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/datasets/build", { method: "POST", body: JSON.stringify(payload) }),
  aiFeatures: () => request<{ featureSets: Record<string, unknown>[] }>("/api/v1/ai/features"),
  aiFeatureSet: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/feature-sets", { method: "POST", body: JSON.stringify(payload) }),
  aiExperiments: () => request<{ experiments: Record<string, unknown>[] }>("/api/v1/ai/experiments"),
  aiExperimentDetail: (id: string) => request<Record<string, unknown>>(`/api/v1/ai/experiments/${encodeURIComponent(id)}`),
  aiCompareExperiments: (experimentIds: string[]) => request<{ comparable: boolean; warning?: string; experiments: Record<string, unknown>[] }>("/api/v1/ai/experiments/compare", { method: "POST", body: JSON.stringify({ experimentIds }) }),
  aiModels: () => request<{ models: Record<string, unknown>[]; audits: Record<string, unknown>[] }>("/api/v1/ai/models"),
  aiRegisterModel: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/models/register", { method: "POST", body: JSON.stringify(payload) }),
  aiPromoteModel: (id: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/v1/ai/models/${encodeURIComponent(id)}/promote`, { method: "POST", body: JSON.stringify(payload) }),
  aiPortfolios: () => request<{ portfolios: Record<string, unknown>[] }>("/api/v1/ai/portfolios"),
  aiBuildPortfolio: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/portfolios/build", { method: "POST", body: JSON.stringify(payload) }),
  aiEvaluations: () => request<{ evaluations: Record<string, unknown>[] }>("/api/v1/ai/evaluations"),
  aiEvaluation: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/evaluations", { method: "POST", body: JSON.stringify(payload) }),
  aiRlValidate: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/rl/environments/validate", { method: "POST", body: JSON.stringify(payload) }),
  aiRlRun: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/rl/runs", { method: "POST", body: JSON.stringify(payload) }),
  aiRlRuns: () => request<{ runs: Record<string, unknown>[] }>("/api/v1/ai/rl/runs"),
  aiDeepLearningRun: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/deep-learning/runs", { method: "POST", body: JSON.stringify(payload) }),
  aiDeepLearningRuns: () => request<{ runs: Record<string, unknown>[] }>("/api/v1/ai/deep-learning/runs"),
  aiCopilot: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/copilot/responses", { method: "POST", body: JSON.stringify(payload) }),
  aiNegativeResults: () => request<{ negativeResults: Record<string, unknown>[] }>("/api/v1/ai/negative-results"),
  aiSaveNegativeResult: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/ai/negative-results", { method: "POST", body: JSON.stringify(payload) }),
  aiMonitoring: () => request<Record<string, unknown>>("/api/v1/ai/monitoring"),
};

export const loadSnapshot = async (): Promise<{ updatedAt?: string; quotes?: Quote[] }> => {
  const response = await fetch(`${import.meta.env.BASE_URL}snapshots/market-summary.json`);
  if (!response.ok) throw new Error("快照不可用");
  return response.json();
};
