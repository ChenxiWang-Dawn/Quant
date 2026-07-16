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
};

export const loadSnapshot = async (): Promise<{ updatedAt?: string; quotes?: Quote[] }> => {
  const response = await fetch(`${import.meta.env.BASE_URL}snapshots/market-summary.json`);
  if (!response.ok) throw new Error("快照不可用");
  return response.json();
};
