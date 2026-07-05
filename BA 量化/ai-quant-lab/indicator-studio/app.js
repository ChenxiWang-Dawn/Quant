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

  const el = {
    canvas: document.querySelector("#priceCanvas"),
    tooltip: document.querySelector("#tooltip"),
    symbolSelect: document.querySelector("#symbolSelect"),
    startDate: document.querySelector("#startDate"),
    endDate: document.querySelector("#endDate"),
    frequencySelect: document.querySelector("#frequencySelect"),
    adjustSelect: document.querySelector("#adjustSelect"),
    loadDataBtn: document.querySelector("#loadDataBtn"),
    resetViewBtn: document.querySelector("#resetViewBtn"),
    csvInput: document.querySelector("#csvInput"),
    indicatorTypeSelect: document.querySelector("#indicatorTypeSelect"),
    addIndicatorBtn: document.querySelector("#addIndicatorBtn"),
    indicatorList: document.querySelector("#indicatorList"),
    autoRedraw: document.querySelector("#autoRedraw"),
    applyParamsBtn: document.querySelector("#applyParamsBtn"),
    savePresetBtn: document.querySelector("#savePresetBtn"),
    deletePresetBtn: document.querySelector("#deletePresetBtn"),
    presetSelect: document.querySelector("#presetSelect"),
    exportConfigBtn: document.querySelector("#exportConfigBtn"),
    chartTitle: document.querySelector("#chartTitle"),
    chartSubtitle: document.querySelector("#chartSubtitle"),
    statusText: document.querySelector("#statusText"),
    cursorText: document.querySelector("#cursorText"),
    metricStrip: document.querySelector("#metricStrip"),
    modeTabs: document.querySelectorAll(".mode-tab"),
    signalsPanel: document.querySelector("#signalsPanel"),
    comparePanel: document.querySelector("#comparePanel"),
    researchPanel: document.querySelector("#researchPanel"),
    signalProfile: document.querySelector("#signalProfile"),
    rsiLow: document.querySelector("#rsiLow"),
    rsiHigh: document.querySelector("#rsiHigh"),
    feeBps: document.querySelector("#feeBps"),
    signalSummary: document.querySelector("#signalSummary"),
    compareSymbols: document.querySelector("#compareSymbols"),
    compareSummary: document.querySelector("#compareSummary"),
    researchBrief: document.querySelector("#researchBrief"),
    templateButtons: document.querySelectorAll(".template-button"),
  };

  const ctx = el.canvas.getContext("2d");
  const state = {
    candles: [],
    symbol: "000001.XSHE",
    sourceLabel: "示例行情",
    indicators: clone(DEFAULT_INDICATORS),
    computed: {},
    mode: "chart",
    stats: {},
    signals: { events: [], strategy: {}, equity: [] },
    compareSymbols: ["000001.XSHE", "600519.XSHG", "300750.XSHE"],
    compareData: [],
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

  function loadGeneratedData() {
    const start = parseDate(el.startDate.value);
    const end = parseDate(el.endDate.value);
    const daily = generateDailySeries(el.symbolSelect.value, start, end);
    state.candles = el.frequencySelect.value === "1w" ? toWeekly(daily) : daily;
    state.symbol = el.symbolSelect.value;
    state.sourceLabel = "示例行情";
    resetView();
    updateTitles();
    setStatus(`已加载 ${state.candles.length} 根K线`);
  }

  function setStatus(text) {
    el.statusText.textContent = text;
  }

  function updateTitles() {
    const meta = STOCKS[state.symbol];
    const name = meta ? meta.name : "CSV 数据";
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
    state.research = buildResearchBrief();
    renderMetricStrip();
    renderSignalSummary();
    renderCompareSummary();
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
    return [trend, momentum, risk, signal];
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

  function renderCompareSummary() {
    el.compareSummary.innerHTML = state.compareData
      .map((item) => summaryItem(`${item.symbol}`, formatPercent(item.returnValue), item.name, item.returnValue))
      .join("");
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
    let html = "";
    for (let i = 0; i < count; i += 1) {
      html += `
        <label>颜色 ${i + 1}
          <input type="color" data-color="${i}" value="${indicator.colors[i] || "#1f6feb"}" />
        </label>
      `;
    }
    return html;
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
      compareSymbols: state.compareSymbols,
      indicators: state.indicators,
    };
  }

  function applyConfig(config) {
    if (config.symbol && STOCKS[config.symbol]) el.symbolSelect.value = config.symbol;
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
    if (Array.isArray(config.compareSymbols)) state.compareSymbols = config.compareSymbols;
    if (Array.isArray(config.indicators)) state.indicators = clone(config.indicators);
    renderIndicatorList();
    renderCompareSymbols();
    loadGeneratedData();
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

  function updateHover(event) {
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
    el.loadDataBtn.addEventListener("click", loadGeneratedData);
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
      try {
        await navigator.clipboard.writeText(json);
        setStatus("当前配置 JSON 已复制到剪贴板");
      } catch {
        window.alert(json);
      }
    });
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
    refreshPresetSelect();
    bindEvents();
    loadGeneratedData();
    const observer = new ResizeObserver(resizeCanvas);
    observer.observe(el.canvas.parentElement);
  }

  init();
})();
