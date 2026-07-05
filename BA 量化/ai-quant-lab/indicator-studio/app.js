(function () {
  "use strict";

  const STOCKS = {
    "000001.XSHE": { name: "平安银行", base: 10.8, drift: 0.00025, vol: 0.017 },
    "600519.XSHG": { name: "贵州茅台", base: 1560, drift: 0.00018, vol: 0.014 },
    "300750.XSHE": { name: "宁德时代", base: 205, drift: 0.00034, vol: 0.022 },
    "002050.XSHE": { name: "三花智控", base: 24, drift: 0.00038, vol: 0.02 },
  };

  const DEFAULT_INDICATORS = [
    {
      id: "ma-1",
      type: "MA",
      visible: true,
      params: { periods: "5,10,20" },
      colors: ["#1f6feb", "#d97706", "#7c3aed"],
    },
    {
      id: "boll-1",
      type: "BOLL",
      visible: true,
      params: { period: 20, multiplier: 2 },
      colors: ["#475569", "#d94a38", "#1f9d72"],
    },
    {
      id: "macd-1",
      type: "MACD",
      visible: true,
      params: { fast: 12, slow: 26, signal: 9 },
      colors: ["#1f6feb", "#d97706", "#94a3b8"],
    },
    {
      id: "rsi-1",
      type: "RSI",
      visible: false,
      params: { period: 14 },
      colors: ["#7c3aed"],
    },
    {
      id: "volma-1",
      type: "VOLMA",
      visible: true,
      params: { periods: "5,20" },
      colors: ["#1f6feb", "#d97706"],
    },
  ];

  const INDICATOR_LABELS = {
    MA: "MA 均线",
    EMA: "EMA 指数均线",
    BOLL: "BOLL 布林带",
    MACD: "MACD",
    RSI: "RSI",
    KDJ: "KDJ",
    ATR: "ATR",
    VOLMA: "成交量均线",
  };

  const INDICATOR_TEMPLATES = {
    trend: [
      {
        id: "ma-trend",
        type: "MA",
        visible: true,
        params: { periods: "5,20,60" },
        colors: ["#1f6feb", "#d97706", "#334155"],
      },
      {
        id: "ema-trend",
        type: "EMA",
        visible: true,
        params: { periods: "12,26" },
        colors: ["#2563eb", "#dc2626"],
      },
      {
        id: "macd-trend",
        type: "MACD",
        visible: true,
        params: { fast: 12, slow: 26, signal: 9 },
        colors: ["#1f6feb", "#d97706", "#94a3b8"],
      },
      {
        id: "vol-trend",
        type: "VOLMA",
        visible: true,
        params: { periods: "5,20" },
        colors: ["#1f6feb", "#d97706"],
      },
    ],
    momentum: [
      {
        id: "boll-momentum",
        type: "BOLL",
        visible: true,
        params: { period: 20, multiplier: 2 },
        colors: ["#475569", "#d94a38", "#1f9d72"],
      },
      {
        id: "rsi-momentum",
        type: "RSI",
        visible: true,
        params: { period: 14 },
        colors: ["#7c3aed"],
      },
      {
        id: "kdj-momentum",
        type: "KDJ",
        visible: true,
        params: { period: 9, m1: 3, m2: 3 },
        colors: ["#1f6feb", "#d97706", "#7c3aed"],
      },
      {
        id: "vol-momentum",
        type: "VOLMA",
        visible: true,
        params: { periods: "5,20" },
        colors: ["#1f6feb", "#d97706"],
      },
    ],
    risk: [
      {
        id: "boll-risk",
        type: "BOLL",
        visible: true,
        params: { period: 20, multiplier: 2 },
        colors: ["#475569", "#d94a38", "#1f9d72"],
      },
      {
        id: "atr-risk",
        type: "ATR",
        visible: true,
        params: { period: 14 },
        colors: ["#d97706"],
      },
      {
        id: "ma-risk",
        type: "MA",
        visible: true,
        params: { periods: "20,60" },
        colors: ["#1f6feb", "#334155"],
      },
    ],
  };

  const STORAGE_KEY = "aiQuantLab.indicatorStudio.presets";
  const PROJECT_KEY = "aiQuantLab.indicatorStudio.projects";

  const MARKET_TEMPLATES = [
    {
      id: "trend",
      name: "趋势跟随",
      tag: "低频观察",
      desc: "MA、EMA、MACD 与成交量均线，适合判断趋势延续和中期结构。",
    },
    {
      id: "momentum",
      name: "动量反转",
      tag: "短线节奏",
      desc: "BOLL、RSI、KDJ 与成交量，适合观察超买超卖和波动边界。",
    },
    {
      id: "risk",
      name: "波动风险",
      tag: "风控优先",
      desc: "BOLL、ATR 与中期均线，适合观察波动扩张、回撤和仓位风险。",
    },
  ];

  const el = {
    canvas: document.querySelector("#priceCanvas"),
    tooltip: document.querySelector("#tooltip"),
    dataSourceSelect: document.querySelector("#dataSourceSelect"),
    backendUrlInput: document.querySelector("#backendUrlInput"),
    symbolInput: document.querySelector("#symbolInput"),
    startDate: document.querySelector("#startDate"),
    endDate: document.querySelector("#endDate"),
    frequencySelect: document.querySelector("#frequencySelect"),
    adjustSelect: document.querySelector("#adjustSelect"),
    loadDataBtn: document.querySelector("#loadDataBtn"),
    checkBackendBtn: document.querySelector("#checkBackendBtn"),
    resetViewBtn: document.querySelector("#resetViewBtn"),
    csvInput: document.querySelector("#csvInput"),
    configInput: document.querySelector("#configInput"),
    indicatorTypeSelect: document.querySelector("#indicatorTypeSelect"),
    addIndicatorBtn: document.querySelector("#addIndicatorBtn"),
    indicatorList: document.querySelector("#indicatorList"),
    autoRedraw: document.querySelector("#autoRedraw"),
    applyParamsBtn: document.querySelector("#applyParamsBtn"),
    savePresetBtn: document.querySelector("#savePresetBtn"),
    deletePresetBtn: document.querySelector("#deletePresetBtn"),
    presetSelect: document.querySelector("#presetSelect"),
    exportConfigBtn: document.querySelector("#exportConfigBtn"),
    shareConfigBtn: document.querySelector("#shareConfigBtn"),
    downloadCsvBtn: document.querySelector("#downloadCsvBtn"),
    chartTitle: document.querySelector("#chartTitle"),
    chartSubtitle: document.querySelector("#chartSubtitle"),
    statusText: document.querySelector("#statusText"),
    cursorText: document.querySelector("#cursorText"),
    metricStrip: document.querySelector("#metricStrip"),
    modeTabs: document.querySelectorAll(".mode-tab"),
    signalsPanel: document.querySelector("#signalsPanel"),
    comparePanel: document.querySelector("#comparePanel"),
    optimizePanel: document.querySelector("#optimizePanel"),
    backtestPanel: document.querySelector("#backtestPanel"),
    templatesPanel: document.querySelector("#templatesPanel"),
    aiPanel: document.querySelector("#aiPanel"),
    projectsPanel: document.querySelector("#projectsPanel"),
    researchPanel: document.querySelector("#researchPanel"),
    signalProfile: document.querySelector("#signalProfile"),
    rsiLow: document.querySelector("#rsiLow"),
    rsiHigh: document.querySelector("#rsiHigh"),
    feeBps: document.querySelector("#feeBps"),
    signalSummary: document.querySelector("#signalSummary"),
    tradeLedger: document.querySelector("#tradeLedger"),
    compareSymbols: document.querySelector("#compareSymbols"),
    compareSummary: document.querySelector("#compareSummary"),
    optFastStart: document.querySelector("#optFastStart"),
    optFastEnd: document.querySelector("#optFastEnd"),
    optSlowStart: document.querySelector("#optSlowStart"),
    optSlowEnd: document.querySelector("#optSlowEnd"),
    optStep: document.querySelector("#optStep"),
    runOptimizeBtn: document.querySelector("#runOptimizeBtn"),
    optimizeSummary: document.querySelector("#optimizeSummary"),
    optimizeTable: document.querySelector("#optimizeTable"),
    backtestEngine: document.querySelector("#backtestEngine"),
    initialCash: document.querySelector("#initialCash"),
    strategySelect: document.querySelector("#strategySelect"),
    runBacktestBtn: document.querySelector("#runBacktestBtn"),
    generateStrategyBtn: document.querySelector("#generateStrategyBtn"),
    backtestSummary: document.querySelector("#backtestSummary"),
    strategyDraft: document.querySelector("#strategyDraft"),
    templateMarket: document.querySelector("#templateMarket"),
    explainBtn: document.querySelector("#explainBtn"),
    draftFromAiBtn: document.querySelector("#draftFromAiBtn"),
    aiBrief: document.querySelector("#aiBrief"),
    projectNameInput: document.querySelector("#projectNameInput"),
    saveProjectBtn: document.querySelector("#saveProjectBtn"),
    loadProjectBtn: document.querySelector("#loadProjectBtn"),
    deleteProjectBtn: document.querySelector("#deleteProjectBtn"),
    projectSummary: document.querySelector("#projectSummary"),
    experimentTable: document.querySelector("#experimentTable"),
    researchBrief: document.querySelector("#researchBrief"),
    templateButtons: document.querySelectorAll(".template-button"),
  };

  const ctx = el.canvas.getContext("2d");
  const state = {
    candles: [],
    symbol: "000001.XSHE",
    securityName: "",
    sourceLabel: "示例行情",
    indicators: clone(DEFAULT_INDICATORS),
    computed: {},
    mode: "chart",
    stats: {},
    signals: { events: [], strategy: {}, equity: [] },
    compareSymbols: ["000001.XSHE", "600519.XSHG", "300750.XSHE"],
    compareData: [],
    optimization: { results: [], best: null },
    backtest: {},
    backend: { ok: false, providers: {}, message: "未连接" },
    aiCards: [],
    projects: [],
    research: [],
    visibleStart: 0,
    visibleEnd: 0,
    hoverIndex: null,
    mouse: null,
    dirty: false,
  };

  const fmt = new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const intFmt = new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: 0,
  });

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function parseDate(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function addDays(date, days) {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
  }

  function seedFromText(text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function randomFactory(seed) {
    return function random() {
      seed += 0x6d2b79f5;
      let t = seed;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function tradingDates(start, end) {
    const dates = [];
    for (let cur = new Date(start); cur <= end; cur = addDays(cur, 1)) {
      const day = cur.getDay();
      if (day !== 0 && day !== 6) {
        dates.push(formatDate(cur));
      }
    }
    return dates;
  }

  function normalLike(random) {
    let total = 0;
    for (let i = 0; i < 6; i += 1) total += random();
    return total - 3;
  }

  function generateDailySeries(symbol, start, end) {
    const meta = STOCKS[symbol] || STOCKS["000001.XSHE"];
    const random = randomFactory(seedFromText(symbol));
    const dates = tradingDates(start, end);
    let close = meta.base;
    const rows = [];

    dates.forEach((date, index) => {
      const cycle = Math.sin(index / 28) * meta.vol * 0.45;
      const shock = normalLike(random) * meta.vol;
      const ret = meta.drift + cycle + shock;
      const open = close * (1 + normalLike(random) * meta.vol * 0.25);
      close = Math.max(0.5, close * (1 + ret));
      const high = Math.max(open, close) * (1 + random() * meta.vol * 0.9);
      const low = Math.min(open, close) * (1 - random() * meta.vol * 0.9);
      const volumeBase = symbol.startsWith("6") ? 18000000 : 42000000;
      const volume = Math.max(
        500000,
        volumeBase * (1 + Math.abs(ret) * 12 + normalLike(random) * 0.12)
      );
      rows.push({
        date,
        open: round(open),
        high: round(high),
        low: round(low),
        close: round(close),
        volume: Math.round(volume),
      });
    });

    return rows;
  }

  function toWeekly(rows) {
    const weeks = [];
    let bucket = null;
    rows.forEach((row) => {
      const date = parseDate(row.date);
      const monday = addDays(date, -(date.getDay() === 0 ? 6 : date.getDay() - 1));
      const key = formatDate(monday);
      if (!bucket || bucket.key !== key) {
        bucket = {
          key,
          date: row.date,
          open: row.open,
          high: row.high,
          low: row.low,
          close: row.close,
          volume: row.volume,
        };
        weeks.push(bucket);
      } else {
        bucket.date = row.date;
        bucket.high = Math.max(bucket.high, row.high);
        bucket.low = Math.min(bucket.low, row.low);
        bucket.close = row.close;
        bucket.volume += row.volume;
      }
    });
    return weeks.map(({ key, ...row }) => row);
  }

  function round(value) {
    return Math.round(value * 100) / 100;
  }

  async function loadData() {
    const source = el.dataSourceSelect.value;
    el.symbolInput.value = normalizeSymbolInput(el.symbolInput.value);
    clampEndDateToToday();
    if (source === "sample") {
      loadGeneratedData();
      return;
    }
    try {
      setStatus(`正在通过 ${source} 获取真实行情...`);
      const result = await fetchRemoteCandles(source);
      const rows = result.candles;
      if (!rows.length) throw new Error("数据源返回空行情");
      state.candles = rows;
      state.symbol = result.symbol || el.symbolInput.value.trim();
      state.securityName = result.name || "";
      state.sourceLabel = sourceLabel(result.source || source);
      el.symbolInput.value = state.symbol;
      resetView();
      updateTitles();
      setStatus(`已通过 ${state.sourceLabel} 加载 ${rows.length} 根K线`);
    } catch (error) {
      setStatus(`${sourceLabel(source)} 加载失败，未更新图表：${error.message}`);
    }
  }

  function loadGeneratedData() {
    clampEndDateToToday();
    const start = parseDate(el.startDate.value);
    const end = parseDate(el.endDate.value);
    const symbol = normalizeSymbolInput(el.symbolInput.value) || "000001.XSHE";
    el.symbolInput.value = symbol;
    const daily = generateDailySeries(symbol, start, end);
    state.candles = el.frequencySelect.value === "1w" ? toWeekly(daily) : daily;
    state.symbol = symbol;
    state.securityName = STOCKS[symbol]?.name || "";
    state.sourceLabel = "示例行情";
    resetView();
    updateTitles();
    setStatus(`已加载 ${state.candles.length} 根K线`);
  }

  async function fetchRemoteCandles(source) {
    const params = new URLSearchParams({
      source,
      symbol: el.symbolInput.value.trim(),
      start: el.startDate.value,
      end: el.endDate.value,
      frequency: el.frequencySelect.value,
      adjust: el.adjustSelect.value,
    });
    const response = await fetch(`${backendBaseUrl()}/api/price?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
    return {
      source: payload.source,
      symbol: payload.symbol,
      name: payload.name,
      candles: payload.candles.map((row) => ({
        date: row.date,
        open: Number(row.open),
        high: Number(row.high),
        low: Number(row.low),
        close: Number(row.close),
        volume: Number(row.volume || 0),
      })),
    };
  }

  function normalizeSymbolInput(value) {
    const raw = String(value || "").trim().toUpperCase();
    if (!raw) return "";
    const compact = raw.replace(/\.(SH|SZ|SS)$/i, "").replace(/\.(XSHG|XSHE|XBSE)$/i, "");
    if (/^\d{6}$/.test(compact)) {
      if (/^(60|68|90|51|52|56|58)/.test(compact)) return `${compact}.XSHG`;
      if (/^(00|30|15|16|18|20)/.test(compact)) return `${compact}.XSHE`;
      if (/^(43|83|87|88)/.test(compact)) return `${compact}.XBSE`;
    }
    if (/^\d{6}\.SH$/i.test(raw)) return raw.replace(/\.SH$/i, ".XSHG");
    if (/^\d{6}\.SZ$/i.test(raw)) return raw.replace(/\.SZ$/i, ".XSHE");
    if (/^\d{6}\.SS$/i.test(raw)) return raw.replace(/\.SS$/i, ".XSHG");
    return raw;
  }

  function clampEndDateToToday() {
    const today = formatDate(new Date());
    if (el.endDate.value > today) {
      el.endDate.value = today;
    }
  }

  function backendBaseUrl() {
    return el.backendUrlInput.value.replace(/\/+$/, "");
  }

  function sourceLabel(source) {
    return {
      sample: "示例行情",
      auto: "自动选择",
      akshare: "AkShare",
      sina: "新浪财经",
      yfinance: "Yahoo Finance",
      rqdata: "RQData",
      tushare: "Tushare",
    }[source] || source;
  }

  function setStatus(text) {
    el.statusText.textContent = text;
  }

  function updateTitles() {
    const meta = STOCKS[state.symbol];
    const name = state.securityName || (meta ? meta.name : "自定义标的");
    el.chartTitle.textContent = `${state.symbol} ${name}`;
    const freq = el.frequencySelect.value === "1w" ? "周线" : "日线";
    const adjust = el.adjustSelect.value === "pre" ? "前复权" : "不复权";
    el.chartSubtitle.textContent = `${state.sourceLabel} · ${freq} · ${adjust}`;
  }

  function resetView() {
    state.visibleEnd = state.candles.length;
    state.visibleStart = Math.max(0, state.visibleEnd - 180);
    recomputeAndDraw();
  }

  function parsePeriods(value, fallback) {
    const periods = String(value)
      .split(/[,\s，]+/)
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isFinite(item) && item > 0)
      .map(Math.round);
    return periods.length ? periods : fallback;
  }

  function valuesOf(field) {
    return state.candles.map((row) => Number(row[field]));
  }

  function sma(values, period) {
    const result = Array(values.length).fill(null);
    let sum = 0;
    for (let i = 0; i < values.length; i += 1) {
      sum += values[i];
      if (i >= period) sum -= values[i - period];
      if (i >= period - 1) result[i] = sum / period;
    }
    return result;
  }

  function ema(values, period) {
    const result = Array(values.length).fill(null);
    const alpha = 2 / (period + 1);
    let prev = null;
    for (let i = 0; i < values.length; i += 1) {
      const value = values[i];
      if (value == null || Number.isNaN(value)) continue;
      prev = prev == null ? value : value * alpha + prev * (1 - alpha);
      result[i] = prev;
    }
    return result;
  }

  function rollingStd(values, period, meanValues) {
    const result = Array(values.length).fill(null);
    for (let i = period - 1; i < values.length; i += 1) {
      const mean = meanValues[i];
      let total = 0;
      for (let j = i - period + 1; j <= i; j += 1) {
        total += (values[j] - mean) ** 2;
      }
      result[i] = Math.sqrt(total / period);
    }
    return result;
  }

  function calcMacd(closes, fast, slow, signal) {
    const fastLine = ema(closes, fast);
    const slowLine = ema(closes, slow);
    const dif = closes.map((_, index) => {
      if (fastLine[index] == null || slowLine[index] == null) return null;
      return fastLine[index] - slowLine[index];
    });
    const dea = ema(dif, signal);
    const hist = dif.map((value, index) => {
      if (value == null || dea[index] == null) return null;
      return (value - dea[index]) * 2;
    });
    return { dif, dea, hist };
  }

  function calcRsi(closes, period) {
    const result = Array(closes.length).fill(null);
    let avgGain = 0;
    let avgLoss = 0;
    for (let i = 1; i < closes.length; i += 1) {
      const change = closes[i] - closes[i - 1];
      const gain = Math.max(change, 0);
      const loss = Math.max(-change, 0);
      if (i <= period) {
        avgGain += gain;
        avgLoss += loss;
        if (i === period) {
          avgGain /= period;
          avgLoss /= period;
        }
      } else {
        avgGain = (avgGain * (period - 1) + gain) / period;
        avgLoss = (avgLoss * (period - 1) + loss) / period;
      }
      if (i >= period) {
        result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
      }
    }
    return result;
  }

  function calcKdj(period, m1, m2) {
    const highs = valuesOf("high");
    const lows = valuesOf("low");
    const closes = valuesOf("close");
    const k = Array(closes.length).fill(null);
    const d = Array(closes.length).fill(null);
    const j = Array(closes.length).fill(null);
    let prevK = 50;
    let prevD = 50;
    for (let i = period - 1; i < closes.length; i += 1) {
      let high = -Infinity;
      let low = Infinity;
      for (let n = i - period + 1; n <= i; n += 1) {
        high = Math.max(high, highs[n]);
        low = Math.min(low, lows[n]);
      }
      const rsv = high === low ? 50 : ((closes[i] - low) / (high - low)) * 100;
      prevK = ((m1 - 1) * prevK + rsv) / m1;
      prevD = ((m2 - 1) * prevD + prevK) / m2;
      k[i] = prevK;
      d[i] = prevD;
      j[i] = 3 * prevK - 2 * prevD;
    }
    return { k, d, j };
  }

  function calcAtr(period) {
    const tr = state.candles.map((row, index) => {
      if (index === 0) return row.high - row.low;
      const prevClose = state.candles[index - 1].close;
      return Math.max(row.high - row.low, Math.abs(row.high - prevClose), Math.abs(row.low - prevClose));
    });
    const result = Array(tr.length).fill(null);
    let prev = null;
    for (let i = 0; i < tr.length; i += 1) {
      if (i < period - 1) continue;
      if (i === period - 1) {
        let sum = 0;
        for (let j = 0; j < period; j += 1) sum += tr[j];
        prev = sum / period;
      } else {
        prev = (prev * (period - 1) + tr[i]) / period;
      }
      result[i] = prev;
    }
    return result;
  }

  function recomputeAndDraw() {
    const closes = valuesOf("close");
    const volumes = valuesOf("volume");
    const computed = {};

    state.indicators.forEach((indicator) => {
      const key = indicator.id;
      if (indicator.type === "MA") {
        computed[key] = parsePeriods(indicator.params.periods, [5, 10, 20]).map((period) => ({
          period,
          values: sma(closes, period),
        }));
      }
      if (indicator.type === "EMA") {
        computed[key] = parsePeriods(indicator.params.periods, [12, 26]).map((period) => ({
          period,
          values: ema(closes, period),
        }));
      }
      if (indicator.type === "BOLL") {
        const period = cleanPeriod(indicator.params.period, 20);
        const multiplier = cleanNumber(indicator.params.multiplier, 2);
        const middle = sma(closes, period);
        const deviation = rollingStd(closes, period, middle);
        computed[key] = {
          middle,
          upper: middle.map((value, i) => (value == null ? null : value + deviation[i] * multiplier)),
          lower: middle.map((value, i) => (value == null ? null : value - deviation[i] * multiplier)),
        };
      }
      if (indicator.type === "MACD") {
        computed[key] = calcMacd(
          closes,
          cleanPeriod(indicator.params.fast, 12),
          cleanPeriod(indicator.params.slow, 26),
          cleanPeriod(indicator.params.signal, 9)
        );
      }
      if (indicator.type === "RSI") {
        computed[key] = calcRsi(closes, cleanPeriod(indicator.params.period, 14));
      }
      if (indicator.type === "KDJ") {
        computed[key] = calcKdj(
          cleanPeriod(indicator.params.period, 9),
          cleanPeriod(indicator.params.m1, 3),
          cleanPeriod(indicator.params.m2, 3)
        );
      }
      if (indicator.type === "ATR") {
        computed[key] = calcAtr(cleanPeriod(indicator.params.period, 14));
      }
      if (indicator.type === "VOLMA") {
        computed[key] = parsePeriods(indicator.params.periods, [5, 20]).map((period) => ({
          period,
          values: sma(volumes, period),
        }));
      }
    });

    state.computed = computed;
    updateAnalytics();
    state.dirty = false;
    el.applyParamsBtn.classList.add("hidden");
    draw();
  }

  function cleanPeriod(value, fallback) {
    const next = Math.round(Number(value));
    return Number.isFinite(next) && next > 0 ? next : fallback;
  }

  function cleanNumber(value, fallback) {
    const next = Number(value);
    return Number.isFinite(next) && next > 0 ? next : fallback;
  }

  function updateAnalytics() {
    state.stats = calcStats(state.candles);
    state.signals = calcSignalsAndStrategy();
    state.compareData = calcCompareData();
    state.optimization = calcOptimizationGrid();
    state.research = buildResearchBrief();
    renderMetricStrip();
    renderSignalSummary();
    renderTradeLedger();
    renderCompareSummary();
    renderOptimizeSummary();
    renderBacktestSummary();
    renderAiBrief();
    renderProjectPanel();
    renderResearchBrief();
  }

  function calcStats(rows) {
    if (!rows.length) return {};
    const closes = rows.map((row) => row.close);
    const returns = dailyReturns(closes);
    const first = closes[0];
    const last = closes[closes.length - 1];
    const totalReturn = first ? last / first - 1 : 0;
    const annualVol = stdev(returns) * Math.sqrt(el.frequencySelect.value === "1w" ? 52 : 252);
    const maxDd = maxDrawdown(closes);
    const high = Math.max(...rows.map((row) => row.high));
    const low = Math.min(...rows.map((row) => row.low));
    return {
      first,
      last,
      totalReturn,
      annualVol,
      maxDd,
      high,
      low,
      count: rows.length,
      start: rows[0].date,
      end: rows[rows.length - 1].date,
    };
  }

  function dailyReturns(values) {
    const returns = [];
    for (let i = 1; i < values.length; i += 1) {
      if (values[i - 1]) returns.push(values[i] / values[i - 1] - 1);
    }
    return returns;
  }

  function stdev(values) {
    if (!values.length) return 0;
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
    return Math.sqrt(variance);
  }

  function maxDrawdown(values) {
    let peak = values[0] || 1;
    let drawdown = 0;
    values.forEach((value) => {
      peak = Math.max(peak, value);
      drawdown = Math.min(drawdown, value / peak - 1);
    });
    return drawdown;
  }

  function latestNonNull(values) {
    for (let i = values.length - 1; i >= 0; i -= 1) {
      if (values[i] != null && Number.isFinite(values[i])) return values[i];
    }
    return null;
  }

  function calcSignalsAndStrategy() {
    if (state.candles.length < 30) return { events: [], strategy: {}, equity: [] };
    const closes = valuesOf("close");
    const volumes = valuesOf("volume");
    const maFast = sma(closes, 5);
    const maSlow = sma(closes, 20);
    const macd = calcMacd(closes, 12, 26, 9);
    const rsi = calcRsi(closes, 14);
    const middle = sma(closes, 20);
    const deviation = rollingStd(closes, 20, middle);
    const lower = middle.map((value, i) => (value == null ? null : value - deviation[i] * 2));
    const upper = middle.map((value, i) => (value == null ? null : value + deviation[i] * 2));
    const volMean = sma(volumes, 20);
    const lowLine = Number(el.rsiLow.value) || 30;
    const highLine = Number(el.rsiHigh.value) || 70;
    const profile = el.signalProfile.value;
    const events = [];

    for (let i = 1; i < state.candles.length; i += 1) {
      const buyReasons = [];
      const sellReasons = [];
      if (crossUp(maFast, maSlow, i)) buyReasons.push("MA5 上穿 MA20");
      if (crossDown(maFast, maSlow, i)) sellReasons.push("MA5 下穿 MA20");
      if (crossUp(macd.dif, macd.dea, i)) buyReasons.push("MACD 金叉");
      if (crossDown(macd.dif, macd.dea, i)) sellReasons.push("MACD 死叉");
      if (rsi[i - 1] != null && rsi[i] != null && rsi[i - 1] < lowLine && rsi[i] >= lowLine) {
        buyReasons.push("RSI 低位回升");
      }
      if (rsi[i - 1] != null && rsi[i] != null && rsi[i - 1] > highLine && rsi[i] <= highLine) {
        sellReasons.push("RSI 高位回落");
      }
      if (lower[i - 1] != null && closes[i - 1] < lower[i - 1] && closes[i] > lower[i]) {
        buyReasons.push("收复布林下轨");
      }
      if (upper[i - 1] != null && closes[i - 1] > upper[i - 1] && closes[i] < upper[i]) {
        sellReasons.push("跌回布林上轨");
      }
      if (volMean[i] != null && volumes[i] > volMean[i] * 1.6) {
        if (closes[i] > closes[i - 1]) buyReasons.push("放量上行");
        if (closes[i] < closes[i - 1]) sellReasons.push("放量下行");
      }

      const buyScore = profileScore(profile, buyReasons, closes, maSlow, rsi, i, "buy");
      const sellScore = profileScore(profile, sellReasons, closes, maSlow, rsi, i, "sell");
      if (buyScore.pass) events.push(signalEvent(i, "buy", buyReasons, buyScore.score));
      if (sellScore.pass) events.push(signalEvent(i, "sell", sellReasons, sellScore.score));
    }

    return {
      events,
      strategy: runSignalStrategy(events),
      equity: runEquitySeries(events),
    };
  }

  function crossUp(a, b, i) {
    return a[i - 1] != null && b[i - 1] != null && a[i] != null && b[i] != null && a[i - 1] <= b[i - 1] && a[i] > b[i];
  }

  function crossDown(a, b, i) {
    return a[i - 1] != null && b[i - 1] != null && a[i] != null && b[i] != null && a[i - 1] >= b[i - 1] && a[i] < b[i];
  }

  function profileScore(profile, reasons, closes, maSlow, rsi, i, side) {
    let score = reasons.length;
    let threshold = 2;
    if (profile === "trend") {
      const trendOk = side === "buy" ? closes[i] > maSlow[i] : closes[i] < maSlow[i];
      if (trendOk) score += 1;
      threshold = 2;
    }
    if (profile === "momentum") {
      const rsiOk = side === "buy" ? rsi[i] != null && rsi[i] < 45 : rsi[i] != null && rsi[i] > 55;
      if (rsiOk) score += 1;
      threshold = 1;
    }
    return { score, pass: score >= threshold && reasons.length > 0 };
  }

  function signalEvent(index, type, reasons, score) {
    const row = state.candles[index];
    return {
      index,
      type,
      score,
      reasons,
      date: row.date,
      price: row.close,
    };
  }

  function runSignalStrategy(events) {
    const equity = runEquitySeries(events);
    if (!equity.length) return {};
    const trades = buildTrades(events);
    const wins = trades.filter((trade) => trade.exitPrice > trade.entryPrice).length;
    return {
      totalReturn: equity[equity.length - 1] / equity[0] - 1,
      maxDd: maxDrawdown(equity),
      trades: trades.length,
      winRate: trades.length ? wins / trades.length : 0,
      lastSignal: events.length ? events[events.length - 1] : null,
    };
  }

  function runEquitySeries(events) {
    if (!state.candles.length) return [];
    const fee = (Number(el.feeBps.value) || 0) / 10000;
    const eventByIndex = new Map(events.map((event) => [event.index, event]));
    let cash = 100000;
    let shares = 0;
    const equity = [];
    state.candles.forEach((row, index) => {
      const event = eventByIndex.get(index);
      if (event?.type === "buy" && shares === 0) {
        shares = (cash * (1 - fee)) / row.close;
        cash = 0;
      }
      if (event?.type === "sell" && shares > 0) {
        cash = shares * row.close * (1 - fee);
        shares = 0;
      }
      equity.push(cash + shares * row.close);
    });
    return equity;
  }

  function buildTrades(events) {
    const trades = [];
    let entry = null;
    events.forEach((event) => {
      if (event.type === "buy" && !entry) entry = event;
      if (event.type === "sell" && entry) {
        trades.push({
          entryDate: entry.date,
          entryPrice: entry.price,
          exitDate: event.date,
          exitPrice: event.price,
        });
        entry = null;
      }
    });
    return trades;
  }

  function calcCompareData() {
    const start = parseDate(el.startDate.value);
    const end = parseDate(el.endDate.value);
    return state.compareSymbols.map((symbol) => {
      const rows = generateDailySeries(symbol, start, end);
      const data = el.frequencySelect.value === "1w" ? toWeekly(rows) : rows;
      const first = data[0]?.close || 1;
      const normalized = data.map((row) => ({
        date: row.date,
        value: (row.close / first) * 100,
        close: row.close,
      }));
      return {
        symbol,
        name: STOCKS[symbol]?.name || symbol,
        color: compareColor(symbol),
        data: normalized,
        returnValue: normalized.length ? normalized[normalized.length - 1].value / 100 - 1 : 0,
      };
    });
  }

  function calcOptimizationGrid() {
    const fastStart = cleanPeriod(el.optFastStart.value, 3);
    const fastEnd = cleanPeriod(el.optFastEnd.value, 18);
    const slowStart = cleanPeriod(el.optSlowStart.value, 20);
    const slowEnd = cleanPeriod(el.optSlowEnd.value, 80);
    const step = clamp(cleanPeriod(el.optStep.value, 5), 1, 20);
    const fastMin = Math.min(fastStart, fastEnd);
    const fastMax = Math.max(fastStart, fastEnd);
    const slowMin = Math.min(slowStart, slowEnd);
    const slowMax = Math.max(slowStart, slowEnd);
    const results = [];

    for (let fast = fastMin; fast <= fastMax; fast += step) {
      for (let slow = slowMin; slow <= slowMax; slow += step) {
        if (fast >= slow) continue;
        results.push(simulateMaStrategy(fast, slow));
      }
    }

    results.sort((a, b) => b.score - a.score);
    return {
      results,
      best: results[0] || null,
      ranges: { fastMin, fastMax, slowMin, slowMax, step },
    };
  }

  function simulateMaStrategy(fast, slow) {
    const closes = valuesOf("close");
    const fastLine = sma(closes, fast);
    const slowLine = sma(closes, slow);
    const fee = (Number(el.feeBps.value) || 0) / 10000;
    let cash = 100000;
    let shares = 0;
    let trades = 0;
    const equity = [];

    for (let i = 0; i < state.candles.length; i += 1) {
      if (i > 0 && crossUp(fastLine, slowLine, i) && shares === 0) {
        shares = (cash * (1 - fee)) / closes[i];
        cash = 0;
        trades += 1;
      }
      if (i > 0 && crossDown(fastLine, slowLine, i) && shares > 0) {
        cash = shares * closes[i] * (1 - fee);
        shares = 0;
      }
      equity.push(cash + shares * closes[i]);
    }

    const totalReturn = equity.length ? equity[equity.length - 1] / equity[0] - 1 : 0;
    const drawdown = maxDrawdown(equity);
    const score = totalReturn + drawdown * 0.65 - Math.max(0, trades - 18) * 0.002;
    return {
      fast,
      slow,
      totalReturn,
      maxDd: drawdown,
      trades,
      score,
      equity,
    };
  }

  function compareColor(symbol) {
    const palette = {
      "000001.XSHE": "#1f6feb",
      "600519.XSHG": "#d97706",
      "300750.XSHE": "#7c3aed",
      "002050.XSHE": "#1f9d72",
    };
    return palette[symbol] || "#475569";
  }

  function buildResearchBrief() {
    const closes = valuesOf("close");
    const ma20 = sma(closes, 20);
    const ma60 = sma(closes, 60);
    const rsi = calcRsi(closes, 14);
    const atr = calcAtr(14);
    const lastClose = closes[closes.length - 1];
    const lastMa20 = latestNonNull(ma20);
    const lastMa60 = latestNonNull(ma60);
    const lastRsi = latestNonNull(rsi);
    const lastAtr = latestNonNull(atr);
    const trend =
      lastMa20 != null && lastMa60 != null && lastClose > lastMa20 && lastMa20 > lastMa60
        ? ["good", "趋势结构", "价格位于 MA20 上方，且 MA20 高于 MA60，趋势结构偏强。"]
        : ["warn", "趋势结构", "趋势结构尚未形成明显多头排列，适合继续观察确认信号。"];
    const momentum =
      lastRsi != null && lastRsi > 70
        ? ["warn", "动量状态", "RSI 已进入偏热区域，继续追踪回落或背离风险。"]
        : lastRsi != null && lastRsi < 30
          ? ["info", "动量状态", "RSI 位于低位区域，可观察是否出现修复性反弹。"]
          : ["good", "动量状态", "RSI 处于中性区间，短线动量没有明显极端化。"];
    const risk =
      lastAtr != null && lastClose
        ? lastAtr / lastClose > 0.045
          ? ["warn", "波动风险", `ATR/收盘价约 ${formatPercent(lastAtr / lastClose)}，波动显著放大。`]
          : ["good", "波动风险", `ATR/收盘价约 ${formatPercent(lastAtr / lastClose)}，当前波动相对可控。`]
        : ["info", "波动风险", "样本长度不足，暂未形成稳定波动判断。"];
    const signal = state.signals.events.length
      ? ["info", "最近信号", `${state.signals.events.at(-1).date} 出现${state.signals.events.at(-1).type === "buy" ? "买入" : "卖出"}信号：${state.signals.events.at(-1).reasons.join("、")}。`]
      : ["info", "最近信号", "当前规则组合在样本内暂无确认信号。"];
    const best = state.optimization.best;
    const optimize = best
      ? ["info", "参数扫描", `当前 MA 扫描中表现较好的组合是 Fast ${best.fast} / Slow ${best.slow}，综合评分 ${best.score.toFixed(3)}。`]
      : ["info", "参数扫描", "样本长度不足或参数范围无有效组合，暂未形成优化结果。"];
    return [trend, momentum, risk, signal, optimize];
  }

  function renderMetricStrip() {
    const stats = state.stats;
    el.metricStrip.innerHTML = [
      metricItem("最新收盘", stats.last == null ? "--" : fmt.format(stats.last), `${stats.count || 0} 根K线`),
      metricItem("区间收益", formatPercent(stats.totalReturn || 0), `${stats.start || "--"} 至 ${stats.end || "--"}`, stats.totalReturn),
      metricItem("年化波动", formatPercent(stats.annualVol || 0), "按当前周期估算"),
      metricItem("最大回撤", formatPercent(stats.maxDd || 0), "基于收盘价序列", stats.maxDd),
      metricItem("区间高低", `${fmt.format(stats.high || 0)} / ${fmt.format(stats.low || 0)}`, "最高价 / 最低价"),
    ].join("");
  }

  function metricItem(label, value, note, polarity) {
    const cls = polarity == null ? "" : polarity >= 0 ? " positive" : " negative";
    return `<div class="metric-item${cls}"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  }

  function renderSignalSummary() {
    const events = state.signals.events;
    const strategy = state.signals.strategy || {};
    const buys = events.filter((event) => event.type === "buy").length;
    const sells = events.filter((event) => event.type === "sell").length;
    const last = strategy.lastSignal;
    el.signalSummary.innerHTML = [
      summaryItem("信号数量", `${buys} 买 / ${sells} 卖`, last ? `最近 ${last.date}` : "暂无信号"),
      summaryItem("策略收益", formatPercent(strategy.totalReturn || 0), "满仓买卖的简化模拟", strategy.totalReturn),
      summaryItem("策略回撤", formatPercent(strategy.maxDd || 0), `${strategy.trades || 0} 笔完整交易`, strategy.maxDd),
      summaryItem("胜率", formatPercent(strategy.winRate || 0), "仅统计完整买卖闭环"),
    ].join("");
  }

  function renderTradeLedger() {
    const events = state.signals.events.slice(-18).reverse();
    if (!events.length) {
      el.tradeLedger.innerHTML = `<tr><td colspan="5">暂无确认信号</td></tr>`;
      return;
    }
    el.tradeLedger.innerHTML = events
      .map(
        (event) => `
          <tr>
            <td>${event.date}</td>
            <td><span class="badge ${event.type}">${event.type === "buy" ? "买入" : "卖出"}</span></td>
            <td class="numeric">${fmt.format(event.price)}</td>
            <td class="numeric">${event.score}</td>
            <td>${event.reasons.join("、")}</td>
          </tr>
        `
      )
      .join("");
  }

  function renderCompareSummary() {
    el.compareSummary.innerHTML = state.compareData
      .map((item) => summaryItem(`${item.symbol}`, formatPercent(item.returnValue), item.name, item.returnValue))
      .join("");
  }

  function renderOptimizeSummary() {
    const { results, best } = state.optimization;
    if (!best) {
      el.optimizeSummary.innerHTML = summaryItem("优化状态", "暂无结果", "请调整参数范围后运行");
      el.optimizeTable.innerHTML = `<tr><td colspan="7">暂无有效参数组合</td></tr>`;
      return;
    }
    const median = results[Math.floor(results.length / 2)];
    el.optimizeSummary.innerHTML = [
      summaryItem("最佳组合", `${best.fast} / ${best.slow}`, `Fast / Slow，样本 ${state.candles.length} 根K线`),
      summaryItem("最佳收益", formatPercent(best.totalReturn), `回撤 ${formatPercent(best.maxDd)}`, best.totalReturn),
      summaryItem("参数数量", `${results.length}`, `中位评分 ${median ? median.score.toFixed(3) : "--"}`),
      summaryItem("交易次数", `${best.trades}`, "MA 金叉买入，死叉卖出"),
    ].join("");
    el.optimizeTable.innerHTML = results
      .slice(0, 12)
      .map(
        (item, index) => `
          <tr>
            <td>${index + 1}</td>
            <td class="numeric">${item.fast}</td>
            <td class="numeric">${item.slow}</td>
            <td class="numeric">${formatPercent(item.totalReturn)}</td>
            <td class="numeric">${formatPercent(item.maxDd)}</td>
            <td class="numeric">${item.trades}</td>
            <td class="numeric">${item.score.toFixed(3)}</td>
          </tr>
        `
      )
      .join("");
  }

  function renderBacktestSummary() {
    const bt = state.backtest.summary || state.signals.strategy || {};
    el.backtestSummary.innerHTML = [
      summaryItem("回测引擎", state.backtest.engine || "浏览器轻量回测", state.backtest.note || "基于当前信号规则"),
      summaryItem("回测收益", formatPercent(bt.totalReturn || 0), `初始资金 ${intFmt.format(Number(el.initialCash.value) || 100000)}`, bt.totalReturn),
      summaryItem("最大回撤", formatPercent(bt.maxDd || 0), `${bt.trades || 0} 笔交易`, bt.maxDd),
      summaryItem("胜率", formatPercent(bt.winRate || 0), state.backtest.error || "仅作研究辅助"),
    ].join("");
  }

  function renderTemplateMarket() {
    el.templateMarket.innerHTML = MARKET_TEMPLATES.map(
      (item) => `
        <article class="template-card">
          <span>${item.tag}</span>
          <strong>${item.name}</strong>
          <p>${item.desc}</p>
          <footer>
            <button class="primary-button" data-template-market="${item.id}">应用</button>
            <button class="ghost-button" data-preview-template="${item.id}">预览</button>
          </footer>
        </article>
      `
    ).join("");
  }

  function renderAiBrief() {
    const cards = state.aiCards.length ? state.aiCards : buildAiCards();
    el.aiBrief.innerHTML = cards
      .map((card) => `<article class="ai-card"><span>${card.tag}</span><strong>${card.title}</strong><p>${card.body}</p></article>`)
      .join("");
  }

  function buildAiCards() {
    const stats = state.stats || {};
    const lastSignal = state.signals.events.at(-1);
    const best = state.optimization.best;
    return [
      {
        tag: "市场状态",
        title: stats.totalReturn >= 0 ? "区间偏强" : "区间承压",
        body: `当前样本区间收益为 ${formatPercent(stats.totalReturn || 0)}，最大回撤为 ${formatPercent(stats.maxDd || 0)}。先观察趋势结构，再决定是否提高信号确认强度。`,
      },
      {
        tag: "信号解释",
        title: lastSignal ? `${lastSignal.date} ${lastSignal.type === "buy" ? "买入" : "卖出"}信号` : "暂无确认信号",
        body: lastSignal ? `触发原因：${lastSignal.reasons.join("、")}。建议结合成交量和波动状态复核，避免只看单个指标。` : "当前参数组合没有形成确认信号，可降低阈值或切换模板进行对比。",
      },
      {
        tag: "策略草稿",
        title: best ? `MA ${best.fast}/${best.slow}` : "等待参数扫描",
        body: best ? `参数扫描中该组合评分较高，收益 ${formatPercent(best.totalReturn)}，回撤 ${formatPercent(best.maxDd)}。下一步适合用 rqalpha 做交易成本和撮合验证。` : "运行优化后，可把最佳参数写入策略草稿，再进入回测视图验证。",
      },
    ];
  }

  function renderProjectPanel() {
    const projects = loadProjects();
    state.projects = projects;
    const current = projects.filter((item) => item.name === el.projectNameInput.value.trim());
    el.projectSummary.innerHTML = [
      summaryItem("项目数", `${new Set(projects.map((item) => item.name)).size}`, "localStorage 本地保存"),
      summaryItem("实验数", `${projects.length}`, `当前项目 ${current.length} 条`),
      summaryItem("最近收益", projects[0] ? formatPercent(projects[0].returnValue) : "--", projects[0]?.symbol || "暂无实验", projects[0]?.returnValue),
      summaryItem("版本对比", current.length >= 2 ? `${current.length} 个版本` : "版本不足", "保存多次实验后可比较"),
    ].join("");
    el.experimentTable.innerHTML = projects.slice(0, 30).map(
      (item) => `
        <tr data-experiment-id="${item.id}">
          <td>${item.time}</td>
          <td>${item.name}</td>
          <td>${item.symbol}</td>
          <td>${item.source}</td>
          <td class="numeric">${formatPercent(item.returnValue)}</td>
          <td class="numeric">${formatPercent(item.maxDd)}</td>
          <td>${item.template || "自定义"}</td>
        </tr>
      `
    ).join("") || `<tr><td colspan="7">暂无实验历史</td></tr>`;
  }

  function renderResearchBrief() {
    el.researchBrief.innerHTML = state.research
      .map(
        ([tone, title, body]) =>
          `<article class="research-item ${tone}"><span>${title}</span><strong>${toneLabel(tone)}</strong><small>${body}</small></article>`
      )
      .join("");
  }

  function summaryItem(label, value, note, polarity) {
    const cls = polarity == null ? "" : polarity >= 0 ? " positive" : " negative";
    return `<div class="summary-item${cls}"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
  }

  function toneLabel(tone) {
    if (tone === "good") return "状态较好";
    if (tone === "warn") return "需要观察";
    return "中性提示";
  }

  function formatPercent(value) {
    if (!Number.isFinite(value)) return "--";
    return `${(value * 100).toFixed(2)}%`;
  }

  function resizeCanvas() {
    const rect = el.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    el.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    el.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function draw() {
    const rect = el.canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);

    if (!state.candles.length) {
      drawEmpty(width, height, "暂无数据");
      return;
    }

    if (state.mode === "compare") {
      drawCompareCanvas(width, height);
      return;
    }

    if (state.mode === "optimize") {
      drawOptimizationCanvas(width, height);
      return;
    }

    const panels = buildPanels(width, height);
    const visible = state.candles.slice(state.visibleStart, state.visibleEnd);
    if (!visible.length) return;

    drawPanelBackground(panels);
    drawMainPanel(panels.main, visible);
    drawVolumePanel(panels.volume, visible);
    panels.subs.forEach((panel) => drawSubPanel(panel, visible));
    drawTimeAxis(panels.time, visible);

    if (state.hoverIndex != null) {
      drawCrosshair(panels, visible);
    }
  }

  function drawEmpty(width, height, text) {
    ctx.fillStyle = "#687386";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(text, width / 2, height / 2);
  }

  function buildPanels(width, height) {
    const left = 58;
    const right = 16;
    const top = 16;
    const timeHeight = 26;
    const gap = 10;
    const innerWidth = width - left - right;
    const visibleSubIndicators = state.indicators.filter(
      (item) => item.visible && ["MACD", "RSI", "KDJ", "ATR"].includes(item.type)
    );
    const subCount = visibleSubIndicators.length;
    const usableHeight = height - top - timeHeight - gap * (2 + subCount);
    const mainHeight = Math.max(220, usableHeight * (subCount ? 0.52 : 0.7));
    const volumeHeight = Math.max(90, usableHeight * 0.17);
    const remaining = Math.max(90 * subCount, usableHeight - mainHeight - volumeHeight);
    const subHeight = subCount ? remaining / subCount : 0;

    let y = top;
    const main = { x: left, y, w: innerWidth, h: mainHeight, kind: "main" };
    y += mainHeight + gap;
    const volume = { x: left, y, w: innerWidth, h: volumeHeight, kind: "volume" };
    y += volumeHeight + gap;
    const subs = visibleSubIndicators.map((indicator) => {
      const panel = { x: left, y, w: innerWidth, h: subHeight, kind: indicator.type, indicator };
      y += subHeight + gap;
      return panel;
    });
    const time = { x: left, y: height - timeHeight, w: innerWidth, h: timeHeight };
    return { left, right, top, main, volume, subs, time };
  }

  function drawPanelBackground(panels) {
    [panels.main, panels.volume, ...panels.subs].forEach((panel) => {
      ctx.strokeStyle = "#dfe4ea";
      ctx.lineWidth = 1;
      ctx.strokeRect(panel.x, panel.y, panel.w, panel.h);
      ctx.strokeStyle = "#edf1f5";
      for (let i = 1; i < 4; i += 1) {
        const y = panel.y + (panel.h / 4) * i;
        drawLine(panel.x, y, panel.x + panel.w, y);
      }
    });
  }

  function drawMainPanel(panel, visible) {
    const priceRange = getPriceRange(visible);
    const toX = xScale(panel, visible.length);
    const toY = yScale(panel, priceRange.min, priceRange.max);
    const candleWidth = Math.max(2, Math.min(14, panel.w / visible.length * 0.62));

    drawAxisLabels(panel, priceRange.min, priceRange.max, fmt);

    if (state.hoverIndex != null) {
      const hoverOffset = state.hoverIndex - state.visibleStart;
      if (hoverOffset >= 0 && hoverOffset < visible.length) {
        const hoverX = toX(hoverOffset);
        ctx.fillStyle = "rgba(31,111,235,0.08)";
        ctx.fillRect(hoverX - candleWidth / 1.2, panel.y, candleWidth * 1.7, panel.h);
      }
    }

    visible.forEach((row, offset) => {
      const x = toX(offset);
      const openY = toY(row.open);
      const closeY = toY(row.close);
      const highY = toY(row.high);
      const lowY = toY(row.low);
      const up = row.close >= row.open;
      ctx.strokeStyle = up ? "#d94a38" : "#1f9d72";
      ctx.fillStyle = up ? "#d94a38" : "#1f9d72";
      drawLine(x, highY, x, lowY);
      const bodyY = Math.min(openY, closeY);
      const bodyH = Math.max(1, Math.abs(closeY - openY));
      if (up) {
        ctx.fillRect(x - candleWidth / 2, bodyY, candleWidth, bodyH);
      } else {
        ctx.strokeRect(x - candleWidth / 2, bodyY, candleWidth, bodyH);
      }
    });

    state.indicators
      .filter((indicator) => indicator.visible && ["MA", "EMA", "BOLL"].includes(indicator.type))
      .forEach((indicator) => drawMainIndicator(indicator, panel, visible, toX, toY));

    if (state.mode === "signals") {
      drawSignalMarkers(panel, visible, toX, toY);
    }

    drawPanelTitle(panel, "价格");
  }

  function getPriceRange(visible) {
    let min = Infinity;
    let max = -Infinity;
    visible.forEach((row) => {
      min = Math.min(min, row.low);
      max = Math.max(max, row.high);
    });

    state.indicators
      .filter((indicator) => indicator.visible && ["MA", "EMA", "BOLL"].includes(indicator.type))
      .forEach((indicator) => {
        const data = state.computed[indicator.id];
        if (!data) return;
        const series = Array.isArray(data) ? data.map((line) => line.values) : [data.middle, data.upper, data.lower];
        series.forEach((values) => {
          for (let i = state.visibleStart; i < state.visibleEnd; i += 1) {
            const value = values[i];
            if (value != null) {
              min = Math.min(min, value);
              max = Math.max(max, value);
            }
          }
        });
      });

    const pad = (max - min) * 0.08 || 1;
    return { min: min - pad, max: max + pad };
  }

  function drawMainIndicator(indicator, panel, visible, toX, toY) {
    const data = state.computed[indicator.id];
    if (!data) return;
    if (indicator.type === "BOLL") {
      drawSeries(data.upper, panel, visible, toX, toY, indicator.colors[1] || "#d94a38", "BOLL 上轨");
      drawSeries(data.middle, panel, visible, toX, toY, indicator.colors[0] || "#475569", "BOLL 中轨");
      drawSeries(data.lower, panel, visible, toX, toY, indicator.colors[2] || "#1f9d72", "BOLL 下轨");
      return;
    }
    data.forEach((line, lineIndex) => {
      const color = indicator.colors[lineIndex] || ["#1f6feb", "#d97706", "#7c3aed"][lineIndex % 3];
      drawSeries(line.values, panel, visible, toX, toY, color, `${indicator.type}${line.period}`);
    });
  }

  function drawSignalMarkers(panel, visible, toX, toY) {
    const events = state.signals.events.filter(
      (event) => event.index >= state.visibleStart && event.index < state.visibleEnd
    );
    events.forEach((event) => {
      const offset = event.index - state.visibleStart;
      const row = state.candles[event.index];
      const x = toX(offset);
      const baseY = event.type === "buy" ? toY(row.low) + 12 : toY(row.high) - 12;
      ctx.beginPath();
      if (event.type === "buy") {
        ctx.moveTo(x, baseY - 12);
        ctx.lineTo(x - 7, baseY);
        ctx.lineTo(x + 7, baseY);
        ctx.fillStyle = "#d94a38";
      } else {
        ctx.moveTo(x, baseY + 12);
        ctx.lineTo(x - 7, baseY);
        ctx.lineTo(x + 7, baseY);
        ctx.fillStyle = "#1f9d72";
      }
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  function drawCompareCanvas(width, height) {
    const panel = { x: 58, y: 22, w: width - 80, h: height - 76 };
    const allValues = state.compareData.flatMap((item) => item.data.map((point) => point.value));
    if (!allValues.length) {
      drawEmpty(width, height, "请选择对比股票");
      return;
    }
    const min = Math.min(...allValues, 100) * 0.98;
    const max = Math.max(...allValues, 100) * 1.02;
    const toY = yScale(panel, min, max);
    const maxLen = Math.max(...state.compareData.map((item) => item.data.length));
    const toX = (index, length) => {
      const ratio = length <= 1 ? 0 : index / (length - 1);
      return panel.x + ratio * panel.w;
    };

    drawSinglePanelGrid(panel);
    ctx.strokeStyle = "#cbd5e1";
    ctx.setLineDash([4, 4]);
    drawLine(panel.x, toY(100), panel.x + panel.w, toY(100));
    ctx.setLineDash([]);
    drawAxisLabels(panel, min, max, (value) => `${value.toFixed(0)}`);
    drawPanelTitle(panel, "归一化表现 100 起点");

    state.compareData.forEach((item) => {
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      item.data.forEach((point, index) => {
        const x = toX(index, item.data.length);
        const y = toY(point.value);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      const last = item.data[item.data.length - 1];
      if (last) {
        const labelX = toX(item.data.length - 1, item.data.length);
        const labelY = toY(last.value);
        ctx.fillStyle = item.color;
        ctx.font = "12px sans-serif";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        ctx.fillText(`${item.name} ${formatPercent(item.returnValue)}`, labelX - 6, labelY);
      }
    });

    const dates = state.compareData[0]?.data || [];
    ctx.fillStyle = "#687386";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const ticks = Math.min(6, dates.length);
    for (let i = 0; i < ticks; i += 1) {
      const index = Math.round((dates.length - 1) * (i / Math.max(1, ticks - 1)));
      ctx.fillText(dates[index].date.slice(5), toX(index, dates.length), panel.y + panel.h + 12);
    }
  }

  function drawOptimizationCanvas(width, height) {
    const panel = { x: 72, y: 26, w: width - 112, h: height - 90 };
    const results = state.optimization.results || [];
    if (!results.length) {
      drawEmpty(width, height, "暂无优化结果");
      return;
    }

    drawSinglePanelGrid(panel);
    const fastValues = [...new Set(results.map((item) => item.fast))].sort((a, b) => a - b);
    const slowValues = [...new Set(results.map((item) => item.slow))].sort((a, b) => a - b);
    const scoreValues = results.map((item) => item.score);
    const minScore = Math.min(...scoreValues);
    const maxScore = Math.max(...scoreValues);
    const cellW = panel.w / Math.max(1, slowValues.length);
    const cellH = panel.h / Math.max(1, fastValues.length);
    const byKey = new Map(results.map((item) => [`${item.fast}:${item.slow}`, item]));

    fastValues.forEach((fast, row) => {
      slowValues.forEach((slow, col) => {
        const item = byKey.get(`${fast}:${slow}`);
        if (!item) return;
        const ratio = (item.score - minScore) / (maxScore - minScore || 1);
        ctx.fillStyle = heatColor(ratio);
        ctx.fillRect(panel.x + col * cellW, panel.y + row * cellH, Math.ceil(cellW), Math.ceil(cellH));
      });
    });

    const best = state.optimization.best;
    if (best) {
      const bestCol = slowValues.indexOf(best.slow);
      const bestRow = fastValues.indexOf(best.fast);
      ctx.strokeStyle = "#17212b";
      ctx.lineWidth = 2;
      ctx.strokeRect(panel.x + bestCol * cellW + 1, panel.y + bestRow * cellH + 1, cellW - 2, cellH - 2);
    }

    ctx.fillStyle = "#16212e";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText("MA 参数评分热力图", panel.x, panel.y - 18);
    ctx.fillStyle = "#687386";
    ctx.textAlign = "center";
    slowValues.forEach((slow, col) => {
      if (col % Math.max(1, Math.ceil(slowValues.length / 8)) === 0) {
        ctx.fillText(String(slow), panel.x + col * cellW + cellW / 2, panel.y + panel.h + 12);
      }
    });
    ctx.textAlign = "right";
    fastValues.forEach((fast, row) => {
      if (row % Math.max(1, Math.ceil(fastValues.length / 8)) === 0) {
        ctx.fillText(String(fast), panel.x - 8, panel.y + row * cellH + cellH / 2 - 6);
      }
    });
    ctx.textAlign = "left";
    ctx.fillText("Slow", panel.x + panel.w - 30, panel.y + panel.h + 32);
    ctx.save();
    ctx.translate(panel.x - 48, panel.y + 22);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("Fast", 0, 0);
    ctx.restore();
  }

  function heatColor(ratio) {
    const r = Math.round(31 + ratio * 186);
    const g = Math.round(157 - ratio * 83);
    const b = Math.round(114 - ratio * 56);
    return `rgb(${r}, ${g}, ${b})`;
  }

  function drawSinglePanelGrid(panel) {
    ctx.strokeStyle = "#dfe4ea";
    ctx.lineWidth = 1;
    ctx.strokeRect(panel.x, panel.y, panel.w, panel.h);
    ctx.strokeStyle = "#edf1f5";
    for (let i = 1; i < 4; i += 1) {
      const y = panel.y + (panel.h / 4) * i;
      drawLine(panel.x, y, panel.x + panel.w, y);
    }
  }

  function drawVolumePanel(panel, visible) {
    const maxVolume = Math.max(...visible.map((row) => row.volume), 1);
    const toX = xScale(panel, visible.length);
    const barWidth = Math.max(2, Math.min(14, panel.w / visible.length * 0.62));
    drawAxisLabels(panel, 0, maxVolume, shortNumber);

    visible.forEach((row, offset) => {
      const x = toX(offset);
      const h = (row.volume / maxVolume) * (panel.h - 18);
      const y = panel.y + panel.h - h;
      ctx.fillStyle = row.close >= row.open ? "rgba(217,74,56,0.72)" : "rgba(31,157,114,0.72)";
      ctx.fillRect(x - barWidth / 2, y, barWidth, h);
    });

    state.indicators
      .filter((indicator) => indicator.visible && indicator.type === "VOLMA")
      .forEach((indicator) => {
        const data = state.computed[indicator.id] || [];
        data.forEach((line, lineIndex) => {
          const color = indicator.colors[lineIndex] || ["#1f6feb", "#d97706"][lineIndex % 2];
          drawSeries(
            line.values,
            panel,
            visible,
            toX,
            (value) => panel.y + panel.h - (value / maxVolume) * (panel.h - 18),
            color,
            `VOLMA${line.period}`
          );
        });
      });

    drawPanelTitle(panel, "成交量");
  }

  function drawSubPanel(panel, visible) {
    const indicator = panel.indicator;
    const data = state.computed[indicator.id];
    if (!data) return;
    const toX = xScale(panel, visible.length);

    if (indicator.type === "MACD") {
      const all = visibleSeriesValues(data.dif, data.dea, data.hist);
      const maxAbs = Math.max(0.01, ...all.map((value) => Math.abs(value)));
      const toY = yScale(panel, -maxAbs, maxAbs);
      const zeroY = toY(0);
      ctx.strokeStyle = "#cbd5e1";
      drawLine(panel.x, zeroY, panel.x + panel.w, zeroY);
      const barWidth = Math.max(2, Math.min(12, panel.w / visible.length * 0.58));
      visible.forEach((_, offset) => {
        const index = state.visibleStart + offset;
        const value = data.hist[index];
        if (value == null) return;
        const x = toX(offset);
        const y = toY(value);
        ctx.fillStyle = value >= 0 ? "rgba(217,74,56,0.72)" : "rgba(31,157,114,0.72)";
        ctx.fillRect(x - barWidth / 2, Math.min(y, zeroY), barWidth, Math.max(1, Math.abs(y - zeroY)));
      });
      drawSeries(data.dif, panel, visible, toX, toY, indicator.colors[0] || "#1f6feb", "DIF");
      drawSeries(data.dea, panel, visible, toX, toY, indicator.colors[1] || "#d97706", "DEA");
      drawAxisLabels(panel, -maxAbs, maxAbs, fmt);
      drawPanelTitle(panel, "MACD");
    }

    if (indicator.type === "RSI") {
      const toY = yScale(panel, 0, 100);
      drawThreshold(panel, toY(70), "70");
      drawThreshold(panel, toY(30), "30");
      drawSeries(data, panel, visible, toX, toY, indicator.colors[0] || "#7c3aed", "RSI");
      drawAxisLabels(panel, 0, 100, intFmt.format.bind(intFmt));
      drawPanelTitle(panel, "RSI");
    }

    if (indicator.type === "KDJ") {
      const values = visibleSeriesValues(data.k, data.d, data.j);
      const min = Math.min(0, ...values);
      const max = Math.max(100, ...values);
      const toY = yScale(panel, min, max);
      drawThreshold(panel, toY(80), "80");
      drawThreshold(panel, toY(20), "20");
      drawSeries(data.k, panel, visible, toX, toY, indicator.colors[0] || "#1f6feb", "K");
      drawSeries(data.d, panel, visible, toX, toY, indicator.colors[1] || "#d97706", "D");
      drawSeries(data.j, panel, visible, toX, toY, indicator.colors[2] || "#7c3aed", "J");
      drawAxisLabels(panel, min, max, intFmt.format.bind(intFmt));
      drawPanelTitle(panel, "KDJ");
    }

    if (indicator.type === "ATR") {
      const values = data.slice(state.visibleStart, state.visibleEnd).filter((value) => value != null);
      const max = Math.max(1, ...values);
      const toY = yScale(panel, 0, max * 1.15);
      drawSeries(data, panel, visible, toX, toY, indicator.colors[0] || "#d97706", "ATR");
      drawAxisLabels(panel, 0, max * 1.15, fmt);
      drawPanelTitle(panel, "ATR");
    }
  }

  function visibleSeriesValues(...seriesList) {
    const values = [];
    seriesList.forEach((series) => {
      for (let i = state.visibleStart; i < state.visibleEnd; i += 1) {
        const value = series[i];
        if (value != null && Number.isFinite(value)) values.push(value);
      }
    });
    return values;
  }

  function drawSeries(values, panel, visible, toX, toY, color) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(panel.x, panel.y, panel.w, panel.h);
    ctx.clip();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    let started = false;
    visible.forEach((_, offset) => {
      const index = state.visibleStart + offset;
      const value = values[index];
      if (value == null || Number.isNaN(value)) {
        started = false;
        return;
      }
      const x = toX(offset);
      const y = toY(value);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.restore();
  }

  function xScale(panel, count) {
    const step = panel.w / Math.max(count, 1);
    return (offset) => panel.x + step * offset + step / 2;
  }

  function yScale(panel, min, max) {
    const range = max - min || 1;
    return (value) => panel.y + panel.h - ((value - min) / range) * panel.h;
  }

  function drawAxisLabels(panel, min, max, formatter) {
    ctx.fillStyle = "#687386";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    [max, (max + min) / 2, min].forEach((value, index) => {
      const y = panel.y + (panel.h / 2) * index;
      ctx.fillText(typeof formatter === "function" ? formatter(value) : value, panel.x - 8, y);
    });
  }

  function drawPanelTitle(panel, title) {
    ctx.fillStyle = "#16212e";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(title, panel.x + 8, panel.y + 8);
  }

  function drawThreshold(panel, y, label) {
    ctx.strokeStyle = "#dfe4ea";
    ctx.setLineDash([5, 4]);
    drawLine(panel.x, y, panel.x + panel.w, y);
    ctx.setLineDash([]);
    ctx.fillStyle = "#687386";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(label, panel.x + 6, y - 4);
  }

  function drawTimeAxis(panel, visible) {
    ctx.fillStyle = "#687386";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const ticks = Math.min(6, visible.length);
    for (let i = 0; i < ticks; i += 1) {
      const offset = Math.round((visible.length - 1) * (i / Math.max(1, ticks - 1)));
      const x = panel.x + (panel.w / Math.max(1, visible.length)) * offset + panel.w / Math.max(1, visible.length) / 2;
      ctx.fillText(visible[offset].date.slice(5), x, panel.y + 6);
    }
  }

  function drawCrosshair(panels, visible) {
    const offset = state.hoverIndex - state.visibleStart;
    if (offset < 0 || offset >= visible.length) return;
    const x = xScale(panels.main, visible.length)(offset);
    ctx.strokeStyle = "rgba(22,33,46,0.42)";
    ctx.setLineDash([3, 4]);
    drawLine(x, panels.main.y, x, panels.time.y);
    if (state.mouse) drawLine(panels.main.x, state.mouse.y, panels.main.x + panels.main.w, state.mouse.y);
    ctx.setLineDash([]);
  }

  function drawLine(x1, y1, x2, y2) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  function shortNumber(value) {
    if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
    if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
    return intFmt.format(value);
  }

  function renderIndicatorList() {
    el.indicatorList.innerHTML = "";
    state.indicators.forEach((indicator) => {
      const card = document.createElement("section");
      card.className = `indicator-card${indicator.visible ? "" : " off"}`;
      card.dataset.id = indicator.id;
      card.innerHTML = `
        <header>
          <div class="indicator-title">
            <input type="checkbox" data-action="visible" ${indicator.visible ? "checked" : ""} title="显示或隐藏指标" />
            <div>
              <strong>${INDICATOR_LABELS[indicator.type]}</strong>
              <small>${indicatorSummary(indicator)}</small>
            </div>
          </div>
          <div class="indicator-actions">
            <button class="icon-button" data-action="up" title="上移">↑</button>
            <button class="icon-button" data-action="down" title="下移">↓</button>
            <button class="icon-button" data-action="delete" title="删除">×</button>
          </div>
        </header>
        <div class="form-grid">${renderFields(indicator)}</div>
      `;
      el.indicatorList.appendChild(card);
    });
  }

  function renderCompareSymbols() {
    el.compareSymbols.innerHTML = Object.entries(STOCKS)
      .map(([symbol, meta]) => {
        const checked = state.compareSymbols.includes(symbol) ? "checked" : "";
        return `
          <label class="compare-pill">
            <input type="checkbox" value="${symbol}" ${checked} />
            <span>${symbol} ${meta.name}</span>
          </label>
        `;
      })
      .join("");
  }

  function setMode(mode) {
    state.mode = mode;
    el.modeTabs.forEach((button) => {
      button.classList.toggle("active", button.dataset.mode === mode);
    });
    el.signalsPanel.classList.toggle("hidden", mode !== "signals");
    el.comparePanel.classList.toggle("hidden", mode !== "compare");
    el.optimizePanel.classList.toggle("hidden", mode !== "optimize");
    el.backtestPanel.classList.toggle("hidden", mode !== "backtest");
    el.templatesPanel.classList.toggle("hidden", mode !== "templates");
    el.aiPanel.classList.toggle("hidden", mode !== "ai");
    el.projectsPanel.classList.toggle("hidden", mode !== "projects");
    el.researchPanel.classList.toggle("hidden", mode !== "research");
    el.tooltip.classList.add("hidden");
    draw();
  }

  function applyIndicatorTemplate(templateName) {
    const template = INDICATOR_TEMPLATES[templateName];
    if (!template) return;
    state.indicators = clone(template).map((indicator) => ({
      ...indicator,
      id: `${indicator.id}-${Date.now()}`,
    }));
    renderIndicatorList();
    recomputeAndDraw();
    const label = templateName === "trend" ? "趋势" : templateName === "momentum" ? "动量" : "波动";
    setStatus(`已应用${label}模板`);
  }

  async function checkBackend() {
    try {
      const response = await fetch(`${backendBaseUrl()}/api/health`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || response.statusText);
      state.backend = { ok: true, providers: payload.providers || {}, message: payload.message || "已连接" };
      setStatus(`本地服务已连接：${Object.keys(state.backend.providers).filter((k) => state.backend.providers[k]).join(" / ") || "可用"}`);
    } catch (error) {
      state.backend = { ok: false, providers: {}, message: error.message };
      setStatus(`本地服务未连接：${error.message}`);
    }
  }

  async function runBacktest() {
    if (el.backtestEngine.value === "rqalpha") {
      try {
        const response = await fetch(`${backendBaseUrl()}/api/backtest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol: state.symbol,
            start: el.startDate.value,
            end: el.endDate.value,
            frequency: el.frequencySelect.value,
            initialCash: Number(el.initialCash.value) || 100000,
            strategy: el.strategySelect.value,
            candles: state.candles,
          }),
        });
        const payload = await response.json();
        if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
        state.backtest = payload;
        setStatus(`回测完成：${payload.engine}`);
        renderBacktestSummary();
        return;
      } catch (error) {
        state.backtest = runLocalBacktest(`rqalpha 不可用，已回退浏览器轻量回测：${error.message}`);
      }
    } else {
      state.backtest = runLocalBacktest("浏览器内置轻量回测");
    }
    renderBacktestSummary();
    setStatus("轻量回测完成");
  }

  function runLocalBacktest(note) {
    const summary = state.signals.strategy || {};
    return {
      engine: "local",
      note,
      summary: {
        totalReturn: summary.totalReturn || 0,
        maxDd: summary.maxDd || 0,
        trades: summary.trades || 0,
        winRate: summary.winRate || 0,
      },
    };
  }

  function generateStrategyDraft() {
    const best = state.optimization.best || { fast: 5, slow: 20 };
    const code = `# AI Quant Lab 策略草稿：MA 双均线
# 来源：Indicator Studio 当前研究配置

from rqalpha.api import order_target_percent, history_bars


def init(context):
    context.symbol = "${state.symbol}"
    context.fast = ${best.fast}
    context.slow = ${best.slow}


def handle_bar(context, bar_dict):
    closes = history_bars(context.symbol, context.slow + 2, "1d", "close")
    if closes is None or len(closes) < context.slow:
        return
    fast_ma = closes[-context.fast:].mean()
    slow_ma = closes[-context.slow:].mean()
    prev_fast = closes[-context.fast - 1:-1].mean()
    prev_slow = closes[-context.slow - 1:-1].mean()

    if prev_fast <= prev_slow and fast_ma > slow_ma:
        order_target_percent(context.symbol, 0.95)
    elif prev_fast >= prev_slow and fast_ma < slow_ma:
        order_target_percent(context.symbol, 0)
`;
    el.strategyDraft.textContent = code;
    el.strategyDraft.classList.remove("hidden");
    return code;
  }

  function saveExperiment() {
    const projects = loadProjects();
    const name = el.projectNameInput.value.trim() || "默认研究项目";
    const item = {
      id: `exp-${Date.now()}`,
      time: new Date().toLocaleString("zh-CN", { hour12: false }),
      name,
      symbol: state.symbol,
      source: state.sourceLabel,
      returnValue: state.stats.totalReturn || 0,
      maxDd: state.stats.maxDd || 0,
      template: inferTemplateName(),
      config: getConfig(),
      stats: state.stats,
      signals: state.signals.strategy,
      optimization: state.optimization.best,
    };
    projects.unshift(item);
    localStorage.setItem(PROJECT_KEY, JSON.stringify(projects.slice(0, 120)));
    renderProjectPanel();
    setStatus(`已保存实验：${name}`);
  }

  function loadProjects() {
    try {
      return JSON.parse(localStorage.getItem(PROJECT_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function loadLatestProject() {
    const name = el.projectNameInput.value.trim();
    const item = loadProjects().find((project) => !name || project.name === name);
    if (!item) {
      setStatus("没有可加载的项目实验");
      return;
    }
    applyConfig(item.config);
    setStatus(`已加载实验版本：${item.name} / ${item.time}`);
  }

  function deleteProject() {
    const name = el.projectNameInput.value.trim();
    if (!name) return;
    const next = loadProjects().filter((project) => project.name !== name);
    localStorage.setItem(PROJECT_KEY, JSON.stringify(next));
    renderProjectPanel();
    setStatus(`已删除项目：${name}`);
  }

  function inferTemplateName() {
    const types = state.indicators.filter((item) => item.visible).map((item) => item.type).sort().join(",");
    if (types.includes("MACD") && types.includes("EMA")) return "趋势跟随";
    if (types.includes("KDJ") && types.includes("RSI")) return "动量反转";
    if (types.includes("ATR")) return "波动风险";
    return "自定义";
  }

  function indicatorSummary(indicator) {
    if (indicator.type === "MA" || indicator.type === "EMA" || indicator.type === "VOLMA") {
      return `周期 ${indicator.params.periods}`;
    }
    if (indicator.type === "BOLL") {
      return `周期 ${indicator.params.period} · 倍数 ${indicator.params.multiplier}`;
    }
    if (indicator.type === "MACD") {
      return `${indicator.params.fast}, ${indicator.params.slow}, ${indicator.params.signal}`;
    }
    if (indicator.type === "KDJ") {
      return `${indicator.params.period}, ${indicator.params.m1}, ${indicator.params.m2}`;
    }
    return `周期 ${indicator.params.period}`;
  }

  function renderFields(indicator) {
    const type = indicator.type;
    if (type === "MA" || type === "EMA" || type === "VOLMA") {
      return `
        <label class="wide">周期
          <input type="text" data-param="periods" value="${escapeAttr(indicator.params.periods)}" />
        </label>
        ${renderColorFields(indicator, parsePeriods(indicator.params.periods, [5, 10, 20]).length)}
      `;
    }
    if (type === "BOLL") {
      return `
        ${numberField("period", "周期", indicator.params.period)}
        ${numberField("multiplier", "标准差倍数", indicator.params.multiplier, "0.1")}
        ${renderColorFields(indicator, 3)}
      `;
    }
    if (type === "MACD") {
      return `
        ${numberField("fast", "Fast", indicator.params.fast)}
        ${numberField("slow", "Slow", indicator.params.slow)}
        ${numberField("signal", "Signal", indicator.params.signal)}
        ${renderColorFields(indicator, 3)}
      `;
    }
    if (type === "KDJ") {
      return `
        ${numberField("period", "周期", indicator.params.period)}
        ${numberField("m1", "M1", indicator.params.m1)}
        ${numberField("m2", "M2", indicator.params.m2)}
        ${renderColorFields(indicator, 3)}
      `;
    }
    return `
      ${numberField("period", "周期", indicator.params.period)}
      ${renderColorFields(indicator, 1)}
    `;
  }

  function numberField(name, label, value, step = "1") {
    return `
      <label>${label}
        <input type="number" min="1" step="${step}" data-param="${name}" value="${escapeAttr(value)}" />
      </label>
    `;
  }

  function renderColorFields(indicator, count) {
    let html = `<label class="wide color-row-label"><span>颜色</span><div class="color-row">`;
    for (let i = 0; i < count; i += 1) {
      html += `
        <input type="color" data-color="${i}" value="${indicator.colors[i] || "#1f6feb"}" title="颜色 ${i + 1}" />
      `;
    }
    return `${html}</div></label>`;
  }

  function escapeAttr(value) {
    return String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;");
  }

  function markDirty() {
    if (el.autoRedraw.checked) {
      recomputeAndDraw();
      return;
    }
    state.dirty = true;
    el.applyParamsBtn.classList.remove("hidden");
    draw();
  }

  function addIndicator(type) {
    const id = `${type.toLowerCase()}-${Date.now()}`;
    const templates = {
      MA: { params: { periods: "5,10,20" }, colors: ["#1f6feb", "#d97706", "#7c3aed"] },
      EMA: { params: { periods: "12,26" }, colors: ["#2563eb", "#dc2626"] },
      BOLL: { params: { period: 20, multiplier: 2 }, colors: ["#475569", "#d94a38", "#1f9d72"] },
      MACD: { params: { fast: 12, slow: 26, signal: 9 }, colors: ["#1f6feb", "#d97706", "#94a3b8"] },
      RSI: { params: { period: 14 }, colors: ["#7c3aed"] },
      KDJ: { params: { period: 9, m1: 3, m2: 3 }, colors: ["#1f6feb", "#d97706", "#7c3aed"] },
      ATR: { params: { period: 14 }, colors: ["#d97706"] },
      VOLMA: { params: { periods: "5,20" }, colors: ["#1f6feb", "#d97706"] },
    };
    state.indicators.push({ id, type, visible: true, ...clone(templates[type]) });
    renderIndicatorList();
    recomputeAndDraw();
  }

  function moveIndicator(id, direction) {
    const index = state.indicators.findIndex((item) => item.id === id);
    const next = index + direction;
    if (index < 0 || next < 0 || next >= state.indicators.length) return;
    const [item] = state.indicators.splice(index, 1);
    state.indicators.splice(next, 0, item);
    renderIndicatorList();
    recomputeAndDraw();
  }

  function onIndicatorInput(event) {
    const card = event.target.closest(".indicator-card");
    if (!card) return;
    const indicator = state.indicators.find((item) => item.id === card.dataset.id);
    if (!indicator) return;

    const action = event.target.dataset.action;
    if (action === "visible") {
      indicator.visible = event.target.checked;
      renderIndicatorList();
      markDirty();
      return;
    }

    if (event.target.dataset.param) {
      indicator.params[event.target.dataset.param] = event.target.value;
      card.querySelector("small").textContent = indicatorSummary(indicator);
      markDirty();
    }

    if (event.target.dataset.color) {
      indicator.colors[Number(event.target.dataset.color)] = event.target.value;
      markDirty();
    }
  }

  function onIndicatorClick(event) {
    const button = event.target.closest("button[data-action]");
    const card = event.target.closest(".indicator-card");
    if (!button || !card) return;
    const id = card.dataset.id;
    const action = button.dataset.action;
    if (action === "delete") {
      state.indicators = state.indicators.filter((item) => item.id !== id);
      renderIndicatorList();
      recomputeAndDraw();
    }
    if (action === "up") moveIndicator(id, -1);
    if (action === "down") moveIndicator(id, 1);
  }

  function getConfig() {
    return {
      symbol: state.symbol,
      dataSource: el.dataSourceSelect.value,
      backendUrl: el.backendUrlInput.value,
      startDate: el.startDate.value,
      endDate: el.endDate.value,
      frequency: el.frequencySelect.value,
      adjust: el.adjustSelect.value,
      sourceLabel: state.sourceLabel,
      mode: state.mode,
      signal: {
        profile: el.signalProfile.value,
        rsiLow: el.rsiLow.value,
        rsiHigh: el.rsiHigh.value,
        feeBps: el.feeBps.value,
      },
      optimize: {
        fastStart: el.optFastStart.value,
        fastEnd: el.optFastEnd.value,
        slowStart: el.optSlowStart.value,
        slowEnd: el.optSlowEnd.value,
        step: el.optStep.value,
      },
      compareSymbols: state.compareSymbols,
      indicators: state.indicators,
    };
  }

  function applyConfig(config) {
    if (config.symbol) el.symbolInput.value = config.symbol;
    if (config.dataSource) el.dataSourceSelect.value = config.dataSource;
    if (config.backendUrl) el.backendUrlInput.value = config.backendUrl;
    if (config.startDate) el.startDate.value = config.startDate;
    if (config.endDate) el.endDate.value = config.endDate;
    if (config.frequency) el.frequencySelect.value = config.frequency;
    if (config.adjust) el.adjustSelect.value = config.adjust;
    if (config.signal) {
      if (config.signal.profile) el.signalProfile.value = config.signal.profile;
      if (config.signal.rsiLow) el.rsiLow.value = config.signal.rsiLow;
      if (config.signal.rsiHigh) el.rsiHigh.value = config.signal.rsiHigh;
      if (config.signal.feeBps) el.feeBps.value = config.signal.feeBps;
    }
    if (config.optimize) {
      if (config.optimize.fastStart) el.optFastStart.value = config.optimize.fastStart;
      if (config.optimize.fastEnd) el.optFastEnd.value = config.optimize.fastEnd;
      if (config.optimize.slowStart) el.optSlowStart.value = config.optimize.slowStart;
      if (config.optimize.slowEnd) el.optSlowEnd.value = config.optimize.slowEnd;
      if (config.optimize.step) el.optStep.value = config.optimize.step;
    }
    if (Array.isArray(config.compareSymbols)) state.compareSymbols = config.compareSymbols;
    if (Array.isArray(config.indicators)) state.indicators = clone(config.indicators);
    renderIndicatorList();
    renderCompareSymbols();
    loadData();
    if (config.mode) setMode(config.mode);
  }

  function loadPresets() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function savePresets(presets) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
    refreshPresetSelect();
  }

  function refreshPresetSelect() {
    const current = el.presetSelect.value;
    const presets = loadPresets();
    el.presetSelect.innerHTML = '<option value="">配置模板</option>';
    Object.keys(presets)
      .sort()
      .forEach((name) => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        el.presetSelect.appendChild(option);
      });
    if (presets[current]) el.presetSelect.value = current;
  }

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) throw new Error("CSV 至少需要表头和一行数据");
    const headers = splitCsvLine(lines[0]).map((item) => item.trim().toLowerCase());
    const required = ["date", "open", "high", "low", "close", "volume"];
    const index = Object.fromEntries(headers.map((name, i) => [name, i]));
    required.forEach((name) => {
      if (index[name] == null) throw new Error(`缺少字段 ${name}`);
    });
    return lines
      .slice(1)
      .map(splitCsvLine)
      .map((parts) => ({
        date: parts[index.date],
        open: Number(parts[index.open]),
        high: Number(parts[index.high]),
        low: Number(parts[index.low]),
        close: Number(parts[index.close]),
        volume: Number(parts[index.volume]),
      }))
      .filter((row) => row.date && [row.open, row.high, row.low, row.close, row.volume].every(Number.isFinite))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  function splitCsvLine(line) {
    const result = [];
    let current = "";
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        result.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    result.push(current);
    return result;
  }

  function handleCsv(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const rows = parseCsv(String(reader.result || ""));
        if (!rows.length) throw new Error("没有解析到有效行情");
        state.candles = rows;
        state.symbol = file.name.replace(/\.csv$/i, "");
        state.sourceLabel = "CSV 导入";
        el.frequencySelect.value = "1d";
        el.startDate.value = rows[0].date;
        el.endDate.value = rows[rows.length - 1].date;
        resetView();
        updateTitles();
        setStatus(`已导入 ${rows.length} 根K线：${file.name}`);
      } catch (error) {
        setStatus(error.message);
      }
    };
    reader.readAsText(file);
  }

  function handleConfigFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const config = JSON.parse(String(reader.result || "{}"));
        applyConfig(config);
        setStatus(`已导入配置：${file.name}`);
      } catch (error) {
        setStatus(`配置导入失败：${error.message}`);
      }
    };
    reader.readAsText(file);
  }

  function downloadTextFile(filename, text, type = "text/plain") {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function downloadCurrentCsv() {
    const header = "date,open,high,low,close,volume";
    const rows = state.candles.map((row) =>
      [row.date, row.open, row.high, row.low, row.close, row.volume].join(",")
    );
    const filename = `${state.symbol || "indicator-studio"}-${el.frequencySelect.value}.csv`;
    downloadTextFile(filename, [header, ...rows].join("\n"), "text/csv");
    setStatus(`已下载 CSV：${filename}`);
  }

  function encodeConfig(config) {
    const json = JSON.stringify(config);
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return btoa(binary);
  }

  function decodeConfig(payload) {
    const binary = atob(payload);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  async function shareConfigLink() {
    const url = new URL(window.location.href);
    url.hash = `config=${encodeConfig(getConfig())}`;
    try {
      await navigator.clipboard.writeText(url.toString());
      setStatus("分享链接已复制到剪贴板");
    } catch {
      window.prompt("复制分享链接", url.toString());
    }
  }

  function loadConfigFromHash() {
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash.startsWith("config=")) return false;
    try {
      const config = decodeConfig(hash.slice("config=".length));
      applyConfig(config);
      setStatus("已从分享链接恢复研究配置");
      return true;
    } catch {
      setStatus("分享链接中的配置无法解析");
      return false;
    }
  }

  function updateHover(event) {
    if (state.mode === "compare" || state.mode === "optimize") {
      clearHover();
      return;
    }
    const rect = el.canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const panels = buildPanels(rect.width, rect.height);
    const count = state.visibleEnd - state.visibleStart;
    const offset = Math.floor(((x - panels.main.x) / panels.main.w) * count);
    if (offset < 0 || offset >= count) {
      clearHover();
      return;
    }
    state.hoverIndex = state.visibleStart + offset;
    state.mouse = { x, y };
    updateTooltip(event);
    draw();
  }

  function updateTooltip(event) {
    const row = state.candles[state.hoverIndex];
    if (!row) return;
    const change = row.close - row.open;
    const pct = row.open ? (change / row.open) * 100 : 0;
    el.tooltip.innerHTML = `
      <b>${row.date}</b>
      开 ${fmt.format(row.open)}　高 ${fmt.format(row.high)}<br>
      低 ${fmt.format(row.low)}　收 ${fmt.format(row.close)}<br>
      涨跌 ${fmt.format(change)} (${pct.toFixed(2)}%)<br>
      成交量 ${shortNumber(row.volume)}
    `;
    const wrap = el.canvas.parentElement.getBoundingClientRect();
    const left = event.clientX - wrap.left;
    const top = event.clientY - wrap.top;
    el.tooltip.style.left = `${Math.min(left + 14, wrap.width - 230)}px`;
    el.tooltip.style.top = `${Math.min(top + 14, wrap.height - 120)}px`;
    el.tooltip.classList.remove("hidden");
    el.cursorText.textContent = `${row.date} 收盘 ${fmt.format(row.close)} 成交量 ${shortNumber(row.volume)}`;
  }

  function clearHover() {
    state.hoverIndex = null;
    state.mouse = null;
    el.tooltip.classList.add("hidden");
    el.cursorText.textContent = "移动鼠标查看 K 线详情";
    draw();
  }

  function onWheel(event) {
    if (!state.candles.length) return;
    event.preventDefault();
    const visibleCount = state.visibleEnd - state.visibleStart;
    const nextCount = clamp(
      Math.round(visibleCount * (event.deltaY > 0 ? 1.15 : 0.85)),
      30,
      state.candles.length
    );
    const rect = el.canvas.getBoundingClientRect();
    const panels = buildPanels(rect.width, rect.height);
    const ratio = clamp((event.clientX - rect.left - panels.main.x) / panels.main.w, 0, 1);
    const centerIndex = state.visibleStart + visibleCount * ratio;
    state.visibleStart = clamp(Math.round(centerIndex - nextCount * ratio), 0, state.candles.length - nextCount);
    state.visibleEnd = state.visibleStart + nextCount;
    draw();
  }

  function bindEvents() {
    el.loadDataBtn.addEventListener("click", loadData);
    el.checkBackendBtn.addEventListener("click", checkBackend);
    el.resetViewBtn.addEventListener("click", resetView);
    el.addIndicatorBtn.addEventListener("click", () => addIndicator(el.indicatorTypeSelect.value));
    el.applyParamsBtn.addEventListener("click", recomputeAndDraw);
    el.modeTabs.forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.mode));
    });
    el.templateButtons.forEach((button) => {
      button.addEventListener("click", () => applyIndicatorTemplate(button.dataset.template));
    });
    [el.signalProfile, el.rsiLow, el.rsiHigh, el.feeBps].forEach((input) => {
      input.addEventListener("input", recomputeAndDraw);
    });
    [el.optFastStart, el.optFastEnd, el.optSlowStart, el.optSlowEnd, el.optStep].forEach((input) => {
      input.addEventListener("input", recomputeAndDraw);
    });
    el.runOptimizeBtn.addEventListener("click", () => {
      updateAnalytics();
      setMode("optimize");
      setStatus("参数优化已完成");
    });
    el.runBacktestBtn.addEventListener("click", runBacktest);
    el.generateStrategyBtn.addEventListener("click", generateStrategyDraft);
    el.explainBtn.addEventListener("click", () => {
      state.aiCards = buildAiCards();
      renderAiBrief();
      setStatus("已生成指标解释");
    });
    el.draftFromAiBtn.addEventListener("click", () => {
      generateStrategyDraft();
      setMode("backtest");
      setStatus("已生成策略草稿");
    });
    el.saveProjectBtn.addEventListener("click", saveExperiment);
    el.loadProjectBtn.addEventListener("click", loadLatestProject);
    el.deleteProjectBtn.addEventListener("click", deleteProject);
    el.templateMarket.addEventListener("click", (event) => {
      const applyButton = event.target.closest("[data-template-market]");
      const previewButton = event.target.closest("[data-preview-template]");
      if (applyButton) {
        applyIndicatorTemplate(applyButton.dataset.templateMarket);
        setMode("chart");
      }
      if (previewButton) {
        state.aiCards = [
          {
            tag: "模板预览",
            title: MARKET_TEMPLATES.find((item) => item.id === previewButton.dataset.previewTemplate)?.name || "模板",
            body: MARKET_TEMPLATES.find((item) => item.id === previewButton.dataset.previewTemplate)?.desc || "",
          },
        ];
        renderAiBrief();
        setMode("ai");
      }
    });
    el.compareSymbols.addEventListener("change", () => {
      state.compareSymbols = Array.from(el.compareSymbols.querySelectorAll("input:checked")).map((input) => input.value);
      updateAnalytics();
      draw();
    });
    el.indicatorList.addEventListener("input", onIndicatorInput);
    el.indicatorList.addEventListener("click", onIndicatorClick);
    el.autoRedraw.addEventListener("change", () => {
      if (el.autoRedraw.checked && state.dirty) recomputeAndDraw();
    });
    el.csvInput.addEventListener("change", (event) => {
      const [file] = event.target.files;
      if (file) handleCsv(file);
    });
    el.configInput.addEventListener("change", (event) => {
      const [file] = event.target.files;
      if (file) handleConfigFile(file);
    });
    el.savePresetBtn.addEventListener("click", () => {
      const name = window.prompt("请输入配置名称", el.presetSelect.value || "默认指标模板");
      if (!name) return;
      const presets = loadPresets();
      presets[name] = getConfig();
      savePresets(presets);
      el.presetSelect.value = name;
      setStatus(`已保存配置：${name}`);
    });
    el.deletePresetBtn.addEventListener("click", () => {
      const name = el.presetSelect.value;
      if (!name) return;
      const presets = loadPresets();
      delete presets[name];
      savePresets(presets);
      setStatus(`已删除配置：${name}`);
    });
    el.presetSelect.addEventListener("change", () => {
      const name = el.presetSelect.value;
      if (!name) return;
      const presets = loadPresets();
      if (presets[name]) {
        applyConfig(presets[name]);
        setStatus(`已加载配置：${name}`);
      }
    });
    el.exportConfigBtn.addEventListener("click", async () => {
      const json = JSON.stringify(getConfig(), null, 2);
      downloadTextFile(`indicator-studio-config-${formatDate(new Date())}.json`, json, "application/json");
      try {
        await navigator.clipboard.writeText(json);
        setStatus("当前配置 JSON 已下载并复制到剪贴板");
      } catch {
        setStatus("当前配置 JSON 已下载");
      }
    });
    el.shareConfigBtn.addEventListener("click", shareConfigLink);
    el.downloadCsvBtn.addEventListener("click", downloadCurrentCsv);
    el.canvas.addEventListener("mousemove", updateHover);
    el.canvas.addEventListener("mouseleave", clearHover);
    el.canvas.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("resize", resizeCanvas);
  }

  function initDates() {
    const end = new Date();
    const start = addDays(end, -560);
    el.startDate.value = formatDate(start);
    el.endDate.value = formatDate(end);
  }

  function init() {
    initDates();
    renderIndicatorList();
    renderCompareSymbols();
    renderTemplateMarket();
    renderProjectPanel();
    refreshPresetSelect();
    bindEvents();
    loadData();
    loadConfigFromHash();
    const observer = new ResizeObserver(resizeCanvas);
    observer.observe(el.canvas.parentElement);
  }

  init();
})();
