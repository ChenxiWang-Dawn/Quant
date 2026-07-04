from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import rqdatac


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"
ORDER_BOOK_ID = "002050.XSHE"
SYMBOL_NAME = "三花智控"


def _date_text(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def get_date_window() -> tuple[str, str]:
    today = date.today()
    recent_dates = rqdatac.get_trading_dates(today - timedelta(days=21), today)
    if not recent_dates:
        raise RuntimeError("未能获取最近交易日，请检查 RQData 权限或网络。")

    end_date = recent_dates[-1]
    raw_start = end_date - pd.DateOffset(years=1)
    trading_dates = rqdatac.get_trading_dates(raw_start.date(), end_date)
    if not trading_dates:
        raise RuntimeError("未能获取近一年交易日，请检查 RQData 权限或网络。")

    return _date_text(trading_dates[0]), _date_text(end_date)


def fetch_price_data(start_date: str, end_date: str) -> pd.DataFrame:
    fields = ["open", "high", "low", "close", "volume", "total_turnover"]
    data = rqdatac.get_price(
        ORDER_BOOK_ID,
        start_date=start_date,
        end_date=end_date,
        frequency="1d",
        fields=fields,
        adjust_type="pre",
        skip_suspended=False,
        expect_df=True,
    )
    if data is None or data.empty:
        raise RuntimeError(f"{ORDER_BOOK_ID} 在 {start_date} 至 {end_date} 无行情数据。")

    df = data.reset_index()
    if "date" not in df.columns:
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    if "order_book_id" not in df.columns:
        df.insert(1, "order_book_id", ORDER_BOOK_ID)
    df["order_book_id"] = ORDER_BOOK_ID
    if "symbol" not in df.columns:
        df.insert(2, "symbol", SYMBOL_NAME)
    df["symbol"] = SYMBOL_NAME

    numeric_cols = ["open", "high", "low", "close", "volume", "total_turnover"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["price_change"] = df["close"].diff()
    df["pct_change"] = df["close"].pct_change() * 100
    df["amount_yuan"] = df["total_turnover"]
    df["volume_shares"] = df["volume"]
    df = df[
        [
            "date",
            "order_book_id",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "price_change",
            "pct_change",
            "volume_shares",
            "amount_yuan",
            "volume",
            "total_turnover",
        ]
    ]
    return df


def frame_to_records(df: pd.DataFrame) -> list[dict]:
    object_df = df.astype(object).where(pd.notnull(df), None)
    records = object_df.to_dict(orient="records")
    for record in records:
        for key, value in list(record.items()):
            if hasattr(value, "item"):
                record[key] = value.item()
    return records


def write_outputs(df: pd.DataFrame, start_date: str, end_date: str) -> tuple[Path, Path, Path]:
    DATA_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    csv_path = DATA_DIR / "sanhua_002050_xshe_daily_last_year.csv"
    json_path = DATA_DIR / "sanhua_002050_xshe_daily_last_year.json"
    html_path = REPORT_DIR / "sanhua_002050_xshe_panel.html"

    metadata = {
        "symbol": SYMBOL_NAME,
        "order_book_id": ORDER_BOOK_ID,
        "start_date": start_date,
        "end_date": end_date,
        "frequency": "1d",
        "adjust_type": "pre",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "Ricequant RQData rqdatac.get_price",
        "record_count": int(len(df)),
    }

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(
        json.dumps(
            {"metadata": metadata, "data": frame_to_records(df)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    html_path.write_text(render_html(metadata, frame_to_records(df)), encoding="utf-8")
    return csv_path, json_path, html_path


def render_html(metadata: dict, records: list[dict]) -> str:
    payload = json.dumps({"metadata": metadata, "data": records}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{SYMBOL_NAME} 近一年日线面板</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --grid: #e6e9ef;
      --up: #d92d20;
      --down: #039855;
      --accent: #2057a8;
      --border: #d8dee8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    .shell {{
      width: min(1440px, 100%);
      margin: 0 auto;
      padding: 20px;
    }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.2;
      font-weight: 760;
      letter-spacing: 0;
    }}
    .subline {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
    }}
    .actions {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    button {{
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 12px;
      cursor: pointer;
      font-size: 14px;
    }}
    button.active {{
      color: #fff;
      border-color: var(--accent);
      background: var(--accent);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    .stat {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 8px;
      padding: 10px 12px;
      min-height: 74px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }}
    .value {{
      font-size: 20px;
      line-height: 1.15;
      font-weight: 720;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .chart-panel {{
      position: relative;
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
      min-height: 680px;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 640px;
    }}
    .tooltip {{
      position: absolute;
      pointer-events: none;
      display: none;
      background: rgba(23, 32, 42, 0.92);
      color: #fff;
      border-radius: 6px;
      padding: 9px 10px;
      font-size: 12px;
      line-height: 1.55;
      min-width: 188px;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
      z-index: 5;
    }}
    .note {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }}
    @media (max-width: 920px) {{
      header {{ align-items: flex-start; flex-direction: column; }}
      .actions {{ justify-content: flex-start; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      canvas {{ height: 560px; }}
      .chart-panel {{ min-height: 600px; }}
    }}
    @media (max-width: 560px) {{
      .shell {{ padding: 12px; }}
      h1 {{ font-size: 22px; }}
      .stats {{ grid-template-columns: 1fr; }}
      button {{ flex: 1 1 auto; }}
      canvas {{ height: 520px; }}
      .chart-panel {{ min-height: 560px; padding: 8px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>{SYMBOL_NAME}（{ORDER_BOOK_ID}）近一年日线</h1>
        <div class="subline" id="subtitle"></div>
      </div>
      <div class="actions" aria-label="图表区间">
        <button type="button" data-window="60">近60日</button>
        <button type="button" data-window="120">近120日</button>
        <button type="button" data-window="all" class="active">近一年</button>
      </div>
    </header>
    <section class="stats" id="stats"></section>
    <section class="chart-panel">
      <canvas id="chart"></canvas>
      <div class="tooltip" id="tooltip"></div>
      <div class="note">价格为前复权日线，成交量单位为股；数据由 Ricequant RQData 的 rqdatac.get_price 获取。</div>
    </section>
  </main>
  <script>
    const payload = {payload};
    const fullData = payload.data;
    let activeWindow = "all";

    const canvas = document.getElementById("chart");
    const ctx = canvas.getContext("2d");
    const tooltip = document.getElementById("tooltip");
    const subtitle = document.getElementById("subtitle");
    const stats = document.getElementById("stats");

    function formatNumber(value, digits = 2) {{
      if (value === null || value === undefined || Number.isNaN(value)) return "-";
      return Number(value).toLocaleString("zh-CN", {{ maximumFractionDigits: digits, minimumFractionDigits: digits }});
    }}

    function formatCompact(value) {{
      if (value === null || value === undefined || Number.isNaN(value)) return "-";
      const abs = Math.abs(value);
      if (abs >= 100000000) return `${{formatNumber(value / 100000000, 2)}}亿`;
      if (abs >= 10000) return `${{formatNumber(value / 10000, 2)}}万`;
      return formatNumber(value, 0);
    }}

    function visibleData() {{
      if (activeWindow === "all") return fullData;
      return fullData.slice(-Number(activeWindow));
    }}

    function setStats(data) {{
      const last = data[data.length - 1];
      const first = data[0];
      const high = Math.max(...data.map(d => d.high));
      const low = Math.min(...data.map(d => d.low));
      const totalReturn = (last.close / first.close - 1) * 100;
      const avgVolume = data.reduce((sum, d) => sum + d.volume_shares, 0) / data.length;
      const cards = [
        ["最新收盘", `${{formatNumber(last.close)}} 元`],
        ["区间涨跌幅", `${{totalReturn >= 0 ? "+" : ""}}${{formatNumber(totalReturn)}}%`],
        ["区间最高", `${{formatNumber(high)}} 元`],
        ["区间最低", `${{formatNumber(low)}} 元`],
        ["日均成交量", `${{formatCompact(avgVolume)}}股`],
      ];
      stats.innerHTML = cards.map(([label, value]) => `
        <div class="stat">
          <div class="label">${{label}}</div>
          <div class="value">${{value}}</div>
        </div>
      `).join("");
      subtitle.textContent = `${{payload.metadata.start_date}} 至 ${{payload.metadata.end_date}} · ${{payload.metadata.record_count}} 个交易日 · 生成于 ${{payload.metadata.generated_at}}`;
    }}

    function resizeCanvas() {{
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }}

    function drawChart() {{
      const data = visibleData();
      if (!data.length) return;
      setStats(data);
      resizeCanvas();

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      ctx.clearRect(0, 0, width, height);

      const margin = {{ left: 54, right: 64, top: 18, bottom: 34 }};
      const gap = 16;
      const priceHeight = Math.round((height - margin.top - margin.bottom - gap) * 0.7);
      const volumeTop = margin.top + priceHeight + gap;
      const volumeHeight = height - volumeTop - margin.bottom;
      const plotWidth = width - margin.left - margin.right;

      const highs = data.map(d => d.high);
      const lows = data.map(d => d.low);
      const maxPrice = Math.max(...highs);
      const minPrice = Math.min(...lows);
      const pricePad = Math.max((maxPrice - minPrice) * 0.08, 0.5);
      const priceMin = minPrice - pricePad;
      const priceMax = maxPrice + pricePad;
      const maxVolume = Math.max(...data.map(d => d.volume_shares));

      const xStep = plotWidth / data.length;
      const bodyWidth = Math.max(2, Math.min(12, xStep * 0.62));
      const xOf = index => margin.left + index * xStep + xStep / 2;
      const yPrice = value => margin.top + (priceMax - value) / (priceMax - priceMin) * priceHeight;
      const yVolume = value => volumeTop + (1 - value / maxVolume) * volumeHeight;

      ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
      ctx.textBaseline = "middle";
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--grid").trim();
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
      ctx.lineWidth = 1;

      for (let i = 0; i <= 5; i++) {{
        const y = margin.top + priceHeight * i / 5;
        const price = priceMax - (priceMax - priceMin) * i / 5;
        ctx.beginPath();
        ctx.moveTo(margin.left, y);
        ctx.lineTo(width - margin.right, y);
        ctx.stroke();
        ctx.fillText(formatNumber(price), width - margin.right + 8, y);
      }}
      for (let i = 0; i <= 3; i++) {{
        const y = volumeTop + volumeHeight * i / 3;
        const volume = maxVolume * (1 - i / 3);
        ctx.beginPath();
        ctx.moveTo(margin.left, y);
        ctx.lineTo(width - margin.right, y);
        ctx.stroke();
        ctx.fillText(formatCompact(volume), width - margin.right + 8, y);
      }}

      ctx.strokeStyle = "#b9c1cf";
      ctx.beginPath();
      ctx.moveTo(margin.left, margin.top);
      ctx.lineTo(margin.left, volumeTop + volumeHeight);
      ctx.lineTo(width - margin.right, volumeTop + volumeHeight);
      ctx.stroke();

      data.forEach((d, index) => {{
        const x = xOf(index);
        const rising = d.close >= d.open;
        const color = rising ? "#d92d20" : "#039855";
        ctx.strokeStyle = color;
        ctx.fillStyle = color;

        ctx.beginPath();
        ctx.moveTo(x, yPrice(d.high));
        ctx.lineTo(x, yPrice(d.low));
        ctx.stroke();

        const openY = yPrice(d.open);
        const closeY = yPrice(d.close);
        const top = Math.min(openY, closeY);
        const bodyH = Math.max(1, Math.abs(openY - closeY));
        if (rising) {{
          ctx.strokeRect(x - bodyWidth / 2, top, bodyWidth, bodyH);
        }} else {{
          ctx.fillRect(x - bodyWidth / 2, top, bodyWidth, bodyH);
        }}

        const volY = yVolume(d.volume_shares);
        ctx.globalAlpha = 0.72;
        ctx.fillRect(x - bodyWidth / 2, volY, bodyWidth, volumeTop + volumeHeight - volY);
        ctx.globalAlpha = 1;
      }});

      const labelCount = Math.min(8, data.length);
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      for (let i = 0; i < labelCount; i++) {{
        const index = Math.round(i * (data.length - 1) / Math.max(1, labelCount - 1));
        ctx.fillText(data[index].date.slice(5), xOf(index), volumeTop + volumeHeight + 10);
      }}

      canvas._chartState = {{ data, margin, plotWidth, xStep, xOf, yPrice, volumeTop, volumeHeight, priceBottom: margin.top + priceHeight }};
    }}

    function showTooltip(event) {{
      const state = canvas._chartState;
      if (!state) return;
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const index = Math.round((x - state.margin.left - state.xStep / 2) / state.xStep);
      if (index < 0 || index >= state.data.length || y < state.margin.top || y > state.volumeTop + state.volumeHeight) {{
        tooltip.style.display = "none";
        drawChart();
        return;
      }}
      const d = state.data[index];
      drawChart();
      const cx = state.xOf(index);
      ctx.strokeStyle = "rgba(32, 87, 168, 0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, state.margin.top);
      ctx.lineTo(cx, state.volumeTop + state.volumeHeight);
      ctx.stroke();
      tooltip.innerHTML = `
        <strong>${{d.date}}</strong><br>
        开盘：${{formatNumber(d.open)}}<br>
        最高：${{formatNumber(d.high)}}<br>
        最低：${{formatNumber(d.low)}}<br>
        收盘：${{formatNumber(d.close)}}<br>
        涨跌幅：${{d.pct_change == null ? "-" : (d.pct_change >= 0 ? "+" : "") + formatNumber(d.pct_change) + "%"}}<br>
        成交量：${{formatCompact(d.volume_shares)}}股<br>
        成交额：${{formatCompact(d.amount_yuan)}}元
      `;
      const left = Math.min(rect.width - 210, Math.max(8, x + 14));
      const top = Math.min(rect.height - 188, Math.max(8, y + 14));
      tooltip.style.left = `${{left}}px`;
      tooltip.style.top = `${{top}}px`;
      tooltip.style.display = "block";
    }}

    document.querySelectorAll("button[data-window]").forEach(button => {{
      button.addEventListener("click", () => {{
        activeWindow = button.dataset.window;
        document.querySelectorAll("button[data-window]").forEach(item => item.classList.toggle("active", item === button));
        tooltip.style.display = "none";
        drawChart();
      }});
    }});

    canvas.addEventListener("mousemove", showTooltip);
    canvas.addEventListener("mouseleave", () => {{
      tooltip.style.display = "none";
      drawChart();
    }});
    window.addEventListener("resize", drawChart);
    drawChart();
  </script>
</body>
</html>
"""


def main() -> None:
    rqdatac.init()
    instrument = rqdatac.instruments(ORDER_BOOK_ID)
    if getattr(instrument, "symbol", None) != SYMBOL_NAME:
        raise RuntimeError(f"证券代码校验失败：{ORDER_BOOK_ID} -> {instrument}")

    start_date, end_date = get_date_window()
    df = fetch_price_data(start_date, end_date)
    csv_path, json_path, html_path = write_outputs(df, start_date, end_date)

    print(f"saved csv: {csv_path}")
    print(f"saved json: {json_path}")
    print(f"saved html: {html_path}")
    print(f"date range: {start_date} to {end_date}, rows: {len(df)}")


if __name__ == "__main__":
    main()
