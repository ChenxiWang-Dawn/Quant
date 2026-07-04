from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sanhua_002050_xshe_daily_last_year.json"
OUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
REPORT_PATH = OUT_DIR / "sanhua_002050_stock_analysis_report.pdf"
CHART_PATH = TMP_DIR / "sanhua_002050_price_volume.png"

FONT_PATH = Path("/System/Library/Fonts/Supplemental/Songti.ttc")
FONT_NAME = "STSong-Light"
FONT_SIZE = 10.5
LINE_HEIGHT = FONT_SIZE * 1.5


def setup_fonts() -> None:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))
    else:
        raise FileNotFoundError(f"中文字体不存在：{FONT_PATH}")


def load_data() -> tuple[dict, pd.DataFrame]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    metadata = payload["metadata"]
    df = pd.DataFrame(payload["data"])
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "price_change",
        "pct_change",
        "volume_shares",
        "amount_yuan",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return metadata, df


def format_num(value: float, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"


def format_pct(value: float, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.{digits}f}%"


def format_compact(value: float) -> str:
    if value is None or pd.isna(value):
        return "-"
    abs_value = abs(value)
    if abs_value >= 100_000_000:
        return f"{value / 100_000_000:,.2f} 亿"
    if abs_value >= 10_000:
        return f"{value / 10_000:,.2f} 万"
    return f"{value:,.0f}"


def compute_metrics(df: pd.DataFrame) -> dict:
    first = df.iloc[0]
    last = df.iloc[-1]
    close = df["close"]
    returns = close.pct_change().dropna()
    cummax = close.cummax()
    drawdown = close / cummax - 1
    high_idx = df["high"].idxmax()
    low_idx = df["low"].idxmin()
    max_vol_idx = df["volume_shares"].idxmax()

    return {
        "start_date": first["date"].strftime("%Y-%m-%d"),
        "end_date": last["date"].strftime("%Y-%m-%d"),
        "records": int(len(df)),
        "start_close": float(first["close"]),
        "last_close": float(last["close"]),
        "total_return": float((last["close"] / first["close"] - 1) * 100),
        "latest_change": float(last["price_change"]),
        "latest_pct": float(last["pct_change"]),
        "period_high": float(df["high"].max()),
        "period_high_date": df.loc[high_idx, "date"].strftime("%Y-%m-%d"),
        "period_low": float(df["low"].min()),
        "period_low_date": df.loc[low_idx, "date"].strftime("%Y-%m-%d"),
        "avg_volume": float(df["volume_shares"].mean()),
        "avg_amount": float(df["amount_yuan"].mean()),
        "max_volume": float(df["volume_shares"].max()),
        "max_volume_date": df.loc[max_vol_idx, "date"].strftime("%Y-%m-%d"),
        "annualized_vol": float(returns.std() * math.sqrt(252) * 100),
        "max_drawdown": float(drawdown.min() * 100),
        "up_days": int((df["close"] >= df["open"]).sum()),
        "down_days": int((df["close"] < df["open"]).sum()),
        "last_volume": float(last["volume_shares"]),
        "last_amount": float(last["amount_yuan"]),
    }


def make_chart(df: pd.DataFrame) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1800, 980
    margin_left, margin_right, margin_top, margin_bottom = 115, 120, 70, 92
    gap = 34
    price_h = 590
    volume_top = margin_top + price_h + gap
    volume_h = height - volume_top - margin_bottom
    plot_w = width - margin_left - margin_right

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font_regular = ImageFont.truetype(str(FONT_PATH), 26)
    font_small = ImageFont.truetype(str(FONT_PATH), 22)
    font_title = ImageFont.truetype(str(FONT_PATH), 34)

    bg = (250, 251, 253)
    grid = (224, 229, 237)
    text = (47, 56, 71)
    muted = (102, 112, 133)
    up = (217, 45, 32)
    down = (3, 152, 85)
    border = (184, 193, 207)

    draw.rectangle([0, 0, width, height], fill=bg)
    draw.rectangle(
        [margin_left - 20, margin_top - 28, width - margin_right + 26, height - margin_bottom + 32],
        fill="white",
        outline=(216, 222, 232),
    )

    draw.text(
        (margin_left, 22),
        "三花智控（002050.XSHE）近一年日线 K 线与成交量",
        font=font_title,
        fill=text,
    )

    price_min = df["low"].min()
    price_max = df["high"].max()
    pad = max((price_max - price_min) * 0.08, 0.5)
    y_min = price_min - pad
    y_max = price_max + pad
    max_volume = df["volume_shares"].max()

    n = len(df)
    x_step = plot_w / n
    candle_w = max(3, min(14, x_step * 0.62))

    def x_of(index: int) -> float:
        return margin_left + index * x_step + x_step / 2

    def y_price(value: float) -> float:
        return margin_top + (y_max - value) / (y_max - y_min) * price_h

    def y_vol(value: float) -> float:
        return volume_top + (1 - value / max_volume) * volume_h

    for i in range(6):
        y = margin_top + price_h * i / 5
        price = y_max - (y_max - y_min) * i / 5
        draw.line([margin_left, y, width - margin_right, y], fill=grid, width=2)
        draw.text((width - margin_right + 18, y - 14), format_num(price), font=font_small, fill=muted)

    for i in range(4):
        y = volume_top + volume_h * i / 3
        volume = max_volume * (1 - i / 3)
        draw.line([margin_left, y, width - margin_right, y], fill=grid, width=2)
        draw.text((width - margin_right + 18, y - 14), f"{volume / 10000:,.0f}万", font=font_small, fill=muted)

    draw.line([margin_left, margin_top, margin_left, volume_top + volume_h], fill=border, width=2)
    draw.line([margin_left, volume_top + volume_h, width - margin_right, volume_top + volume_h], fill=border, width=2)

    for idx, row in df.reset_index(drop=True).iterrows():
        x = x_of(idx)
        color = up if row["close"] >= row["open"] else down
        draw.line([x, y_price(row["low"]), x, y_price(row["high"])], fill=color, width=2)
        open_y = y_price(row["open"])
        close_y = y_price(row["close"])
        top = min(open_y, close_y)
        bottom = max(open_y, close_y)
        if bottom - top < 2:
            bottom = top + 2
        rect = [x - candle_w / 2, top, x + candle_w / 2, bottom]
        fill = "white" if row["close"] >= row["open"] else color
        draw.rectangle(rect, fill=fill, outline=color, width=2)

        vol_y = y_vol(row["volume_shares"])
        draw.rectangle([x - candle_w / 2, vol_y, x + candle_w / 2, volume_top + volume_h], fill=color)

    label_count = 8
    for i in range(label_count):
        idx = round(i * (n - 1) / (label_count - 1))
        x = x_of(idx)
        label = df.iloc[idx]["date"].strftime("%Y-%m")
        bbox = draw.textbbox((0, 0), label, font=font_small)
        draw.text((x - (bbox[2] - bbox[0]) / 2, volume_top + volume_h + 25), label, font=font_small, fill=muted)

    draw.text((30, margin_top + price_h / 2 - 40), "前复权价格（元）", font=font_regular, fill=muted)
    draw.text((30, volume_top + volume_h / 2 - 20), "成交量", font=font_regular, fill=muted)

    image.save(CHART_PATH, quality=95)
    return CHART_PATH


def make_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCN",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17202A"),
            spaceBefore=0,
            spaceAfter=0,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCN",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#667085"),
            spaceBefore=0,
            spaceAfter=0,
        ),
        "h1": ParagraphStyle(
            "H1CN",
            parent=base["Heading1"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#2057A8"),
            spaceBefore=0,
            spaceAfter=0,
        ),
        "h2": ParagraphStyle(
            "H2CN",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#17202A"),
            spaceBefore=0,
            spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "BodyCN",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#344054"),
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "small": ParagraphStyle(
            "SmallCN",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#667085"),
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "table_cell": ParagraphStyle(
            "TableCellCN",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#17202A"),
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=0,
            wordWrap="CJK",
        ),
        "caption": ParagraphStyle(
            "CaptionCN",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            textColor=colors.HexColor("#17202A"),
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "right": ParagraphStyle(
            "RightCN",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=FONT_SIZE,
            leading=LINE_HEIGHT,
            alignment=TA_RIGHT,
            spaceBefore=0,
            spaceAfter=0,
        ),
    }


def paragraph(text: str, styles: dict, style: str = "body") -> Paragraph:
    return Paragraph(text, styles[style])


def add_numbered_items(story: list, items: list[str], styles: dict) -> None:
    for index, item in enumerate(items, start=1):
        story.append(paragraph(f"（{index}）{item}", styles))


def style_table(table: Table, header_rows: int = 1) -> Table:
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
                ("LEADING", (0, 0), (-1, -1), LINE_HEIGHT),
                ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#EAF1FB")),
                ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.HexColor("#17202A")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8DEE8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, colors.HexColor("#FAFBFD")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def make_summary_table(metrics: dict) -> Table:
    rows = [
        ["指标", "数值", "指标", "数值"],
        ["区间", f"{metrics['start_date']} 至 {metrics['end_date']}", "交易日", f"{metrics['records']}"],
        ["首日收盘", f"{format_num(metrics['start_close'])} 元", "最新收盘", f"{format_num(metrics['last_close'])} 元"],
        ["区间涨跌幅", format_pct(metrics["total_return"]), "最新日涨跌幅", format_pct(metrics["latest_pct"])],
        ["区间最高", f"{format_num(metrics['period_high'])} 元 ({metrics['period_high_date']})", "区间最低", f"{format_num(metrics['period_low'])} 元 ({metrics['period_low_date']})"],
        ["年化波动率", format_pct(metrics["annualized_vol"]), "最大回撤", format_pct(metrics["max_drawdown"])],
        ["日均成交量", f"{format_compact(metrics['avg_volume'])} 股", "日均成交额", f"{format_compact(metrics['avg_amount'])} 元"],
        ["最大成交量", f"{format_compact(metrics['max_volume'])} 股 ({metrics['max_volume_date']})", "最新成交额", f"{format_compact(metrics['last_amount'])} 元"],
    ]
    table = Table(rows, colWidths=[3.0 * cm, 5.0 * cm, 3.0 * cm, 5.0 * cm])
    return style_table(table)


def make_recent_table(df: pd.DataFrame) -> Table:
    rows = [["日期", "开盘", "最高", "最低", "收盘", "涨跌幅", "成交量(万股)", "成交额(亿元)"]]
    for _, row in df.tail(12).iterrows():
        rows.append(
            [
                row["date"].strftime("%Y-%m-%d"),
                format_num(row["open"]),
                format_num(row["high"]),
                format_num(row["low"]),
                format_num(row["close"]),
                format_pct(row["pct_change"]),
                format_num(row["volume_shares"] / 10000, 1),
                format_num(row["amount_yuan"] / 100000000, 2),
            ]
        )
    table = Table(rows, colWidths=[2.35 * cm, 1.55 * cm, 1.55 * cm, 1.55 * cm, 1.55 * cm, 1.75 * cm, 2.25 * cm, 2.25 * cm])
    return style_table(table)


def make_concept_table(styles: dict) -> Table:
    cell = styles["table_cell"]
    rows = [
        [Paragraph("概念", cell), Paragraph("解释", cell), Paragraph("在本报告中的作用", cell)],
        [
            Paragraph("K 线", cell),
            Paragraph("K 线用开盘价、最高价、最低价、收盘价描述一个交易周期内的价格变化。实体反映开盘和收盘之间的区间，上下影线反映盘中高低点。", cell),
            Paragraph("用于展示三花智控近一年每日价格波动、趋势和多空力量变化。", cell),
        ],
        [
            Paragraph("基本面", cell),
            Paragraph("基本面关注公司的经营质量、盈利能力、成长性、现金流、资产负债、行业竞争格局和估值水平等因素。", cell),
            Paragraph("本报告未展开基本面研究，后续可结合财报、行业景气和估值指标补充判断。", cell),
        ],
        [
            Paragraph("技术面", cell),
            Paragraph("技术面主要研究价格、成交量、趋势、波动率、支撑阻力、形态和量价关系等市场交易数据。", cell),
            Paragraph("本报告主要属于技术面和量价展示，核心依据是日线价格与成交量。", cell),
        ],
    ]
    table = Table(rows, colWidths=[2.0 * cm, 7.5 * cm, 6.8 * cm])
    return style_table(table)


def make_observations(metrics: dict) -> list[str]:
    trend = "上涨" if metrics["total_return"] >= 0 else "下跌"
    return [
        f"观察期内，收盘价从 {format_num(metrics['start_close'])} 元变动至 {format_num(metrics['last_close'])} 元，区间累计{trend} {format_pct(metrics['total_return'])}。",
        f"区间最高价出现在 {metrics['period_high_date']}，为 {format_num(metrics['period_high'])} 元；区间最低价出现在 {metrics['period_low_date']}，为 {format_num(metrics['period_low'])} 元。",
        f"最近交易日成交量为 {format_compact(metrics['last_volume'])} 股，成交额为 {format_compact(metrics['last_amount'])} 元，明显高于区间日均成交水平。",
        f"观察期内年化波动率约 {format_pct(metrics['annualized_vol'])}，最大回撤约 {format_pct(metrics['max_drawdown'])}，显示价格弹性和波动均处于较高水平。",
        "本报告仅基于历史日线价格与成交量数据做技术与量价描述，不包含基本面预测、目标价或个性化交易建议。",
    ]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, FONT_SIZE)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(doc.leftMargin, 1.05 * cm, "数据源：Ricequant RQData / rqdatac.get_price")
    canvas.drawRightString(A4[0] - doc.rightMargin, 1.05 * cm, f"第 {doc.page} 页")
    canvas.restoreState()


def build_pdf(metadata: dict, df: pd.DataFrame, metrics: dict, chart_path: Path) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(REPORT_PATH),
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.6 * cm,
        title="三花智控股票分析报告",
        author="Codex / Ricequant RQData",
    )

    story = []
    story.append(paragraph("三花智控股票分析报告", styles, "title"))
    story.append(
        paragraph(
            f"{metadata['symbol']}（{metadata['order_book_id']}） | 日线数据 | {metrics['start_date']} 至 {metrics['end_date']} | 前复权",
            styles,
            "subtitle",
        )
    )
    story.append(paragraph("一、核心结论", styles, "h1"))
    add_numbered_items(story, make_observations(metrics), styles)
    story.append(paragraph("二、关键指标", styles, "h1"))
    story.append(make_summary_table(metrics))
    story.append(
        paragraph(
            f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}；原始数据文件：data/sanhua_002050_xshe_daily_last_year.json。",
            styles,
            "small",
        )
    )
    story.append(PageBreak())

    story.append(paragraph("三、价格与成交量走势", styles, "h1"))
    story.append(
        paragraph(
            "下图展示近一年日线 K 线及成交量。红色为空心上涨 K 线，绿色为实体下跌 K 线；成交量以股数为基础绘制。",
            styles,
        )
    )
    story.append(RLImage(str(chart_path), width=17.2 * cm, height=9.36 * cm))
    story.append(paragraph("图 1  三花智控（002050.XSHE）近一年日线 K 线与成交量", styles, "caption"))
    story.append(paragraph("四、量价解读", styles, "h1"))
    story.append(
        paragraph(
            f"从区间表现看，股价整体呈现较强趋势性，上行过程中伴随成交量阶段性放大。最近交易日收盘价 {format_num(metrics['last_close'])} 元，单日涨跌幅 {format_pct(metrics['latest_pct'])}，成交量 {format_compact(metrics['last_volume'])} 股，为观察期内成交活跃阶段之一。",
            styles,
        )
    )
    story.append(
        paragraph(
            "需要注意的是，历史量价关系只能描述已发生的市场交易结果，不能单独推导未来收益。后续若用于策略研究，应继续结合行业景气、财报指标、资金流、估值和组合风险约束。",
            styles,
        )
    )
    story.append(PageBreak())

    story.append(paragraph("五、最近 12 个交易日明细", styles, "h1"))
    story.append(make_recent_table(df))
    story.append(PageBreak())

    story.append(paragraph("六、量化交易基础说明", styles, "h1"))
    story.append(paragraph("1. 相较于传统手工操作交易，量化交易的优势", styles, "h2"))
    quant_advantages = [
        "纪律性更强：量化交易把交易条件、仓位控制、止损止盈、调仓频率等规则写成可执行程序，减少临场情绪、主观犹豫和事后随意改规则。",
        "可回测和可复盘：策略可以在历史数据上检验，评估收益、回撤、胜率、换手率、交易成本和极端行情表现，便于迭代优化。",
        "执行速度和覆盖面更高：程序可以同时监控大量标的、因子和信号，快速完成筛选、下单和风控检查，这是手工交易很难稳定做到的。",
        "风控更系统：量化框架可以将单票权重、行业暴露、波动率、回撤、流动性、交易成本等约束前置，避免单一判断过度集中。",
        "决策可重复：同一套策略在相同数据和参数下会得到一致结果，便于团队协作、审计和长期跟踪。",
        "更适合数据驱动研究：量化方法可以把价格、成交量、财务、估值、新闻、宏观等多源数据转化为可检验的信号。",
    ]
    add_numbered_items(story, quant_advantages, styles)
    story.append(paragraph("2. 基本概念：K 线、基本面、技术面", styles, "h2"))
    story.append(make_concept_table(styles))
    story.append(PageBreak())

    story.append(paragraph("七、方法说明与风险提示", styles, "h1"))
    method_items = [
        "证券代码通过 RQData instruments 接口确认为 002050.XSHE，名称为三花智控。",
        "行情数据通过 rqdatac.get_price 获取，频率为 1d，字段包括 open、high、low、close、volume、total_turnover。",
        "价格字段采用前复权口径；成交量和成交额以 RQData 返回字段为准。",
        "年化波动率基于日收益率标准差并按 252 个交易日折算；最大回撤基于收盘价序列计算。",
        "本报告仅供量化研究与数据展示参考，不构成任何投资建议或收益承诺。",
    ]
    add_numbered_items(story, method_items, styles)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return REPORT_PATH


def main() -> None:
    setup_fonts()
    metadata, df = load_data()
    metrics = compute_metrics(df)
    chart_path = make_chart(df)
    report_path = build_pdf(metadata, df, metrics, chart_path)
    print(report_path)


if __name__ == "__main__":
    main()
