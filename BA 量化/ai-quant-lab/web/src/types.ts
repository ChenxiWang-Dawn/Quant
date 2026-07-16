export type ParamDefinition = {
  key: string;
  label: string;
  type: "integer" | "number";
  default: number;
  minimum: number;
  maximum: number;
  step: number;
};

export type Strategy = {
  id: string;
  version: string;
  name: string;
  category: string;
  status: "draft" | "researching" | "validated" | "archived";
  markets: string[];
  frequencies: string[];
  summary: string;
  hypothesis: string;
  riskLevel: string;
  holdingPeriod: string;
  params: ParamDefinition[];
  constraints: string[];
  capabilities: Record<string, boolean>;
  risks: string[];
  updatedAt: string;
};

export type Candle = { date: string; open: number; high: number; low: number; close: number; volume: number };

export type Quote = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  asOf: string;
  source: string;
  delayed?: boolean;
};

export type BacktestSummary = {
  totalReturn?: number;
  annualizedReturn?: number;
  maxDrawdown?: number;
  sharpe?: number;
  sortino?: number;
  calmar?: number;
  tradeCount?: number;
  winRate?: number;
  profitFactor?: number;
};

export type BacktestResult = {
  engine: string;
  security?: { symbol: string; name: string };
  summary: BacktestSummary;
  metrics: BacktestSummary;
  equity: Array<{ date: string; equity: number; drawdown?: number }>;
  trades: Array<{ date: string; side: string; price: number; shares: number; reason?: string }>;
  notes: string[];
  configHash: string;
  dataFingerprint: string;
  warnings: string[];
};

export type Experiment = {
  id: string;
  name: string;
  strategyId: string;
  strategyName: string;
  symbol: string;
  securityName?: string;
  period: string;
  createdAt: string;
  engine: string;
  summary: BacktestSummary;
  config: Record<string, unknown>;
};

export type AIExperimentRequest = {
  universe: string[];
  start: string;
  end: string;
  horizon: number;
  topK: number;
  transactionCost: number;
  source?: "auto" | "akshare" | "yfinance" | "rqdata";
};

export type AIExperimentResult = {
  id: string;
  status: "completed";
  engine: string;
  configHash: string;
  dataFingerprint: string;
  dataset: {
    symbols: Array<{ symbol: string; name: string; source: string; bars: number; firstDate: string; lastDate: string }>;
    featureNames: string[];
    sampleCount: number;
    dataSources: string[];
  };
  split: { trainEnd: string; validationStart: string; validationEnd: string; testStart: string; testEnd: string; embargoDays: number; trainSamples: number; validationSamples: number; testSamples: number };
  model: {
    name: string;
    type: string;
    alpha: number;
    featureCoefficients: Array<{ feature: string; coefficient: number; scale: number }>;
    card: { purpose: string; status: string; limitations: string[] };
  };
  metrics: { rankIc: number; validationRankIc: number; totalReturn: number; benchmarkReturn: number; maxDrawdown: number; sharpe: number; turnover: number; rebalances: number };
  baseline: { name: string; totalReturn: number; maxDrawdown: number; sharpe: number };
  equity: Array<{ date: string; equity: number; benchmark: number; drawdown: number }>;
  holdings: Array<{ date: string; symbols: string[]; names: string[]; scores: number[] }>;
  warnings: string[];
};
