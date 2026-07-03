"""Generate a small **bilingual** sample annual report as a real PDF.

Used by the ``/api/documents/seed`` endpoint so anyone can explore the full
pipeline (parse → extract → traceable view/search/compare/export) without
having to upload their own report. Financial statements are drawn as ruled
tables so the table extractor exercises its real code path.

Chinese text is rendered with reportlab's built-in ``STSong-Light`` CID font,
which embeds a ToUnicode map so pdfplumber can extract the characters back.
"""
from __future__ import annotations

from pathlib import Path

SAMPLE_COMPANY = "Skylark Technologies 天弘科技"
SAMPLE_PERIOD = "2024 FY"


def build_sample_pdf(dest: str | Path) -> Path:
    """Render the sample report to ``dest`` (idempotent) and return the path."""
    dest = Path(dest)
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    cjk = "STSong-Light"

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1cn", parent=styles["Title"], fontName=cjk, fontSize=20, leading=26)
    h2 = ParagraphStyle("h2cn", parent=styles["Heading2"], fontName=cjk, fontSize=13, leading=18)
    body = ParagraphStyle("bodycn", parent=styles["BodyText"], fontName=cjk, fontSize=10.5, leading=16)

    def tbl(header: list[str], rows: list[list[str]]) -> Table:
        data = [header] + rows
        t = Table(data, hAlign="LEFT", colWidths=[7 * cm, 3.5 * cm, 3.5 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), cjk),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return t

    doc = SimpleDocTemplate(str(dest), pagesize=A4, title="Skylark Technologies 2024 Annual Report")
    story: list = []

    # ---- Cover ----
    story += [
        Paragraph("天弘科技 Skylark Technologies", h1),
        Spacer(1, 6),
        Paragraph("2024 年度报告 · 2024 Annual Report", h2),
        Spacer(1, 4),
        Paragraph("股票代码 Ticker: 0700.DEMO　　报告期 Period: 2024 财年 (FY2024)", body),
        Spacer(1, 18),
        Paragraph("单位：人民币（亿元） Unit: RMB (100 million)", body),
    ]

    # ---- Income statement ----
    story += [Spacer(1, 10), Paragraph("合并利润表 Consolidated Income Statement", h2)]
    story += [
        tbl(
            ["项目 Item", "2024", "2023"],
            [
                ["营业收入 Revenue", "6,096.9", "5,626.5"],
                ["营业成本 Cost of Revenue", "2,867.7", "2,731.0"],
                ["毛利 Gross Profit", "3,229.2", "2,895.5"],
                ["毛利率 Gross Margin", "53.0%", "51.5%"],
                ["营业利润 Operating Profit", "2,315.6", "1,560.2"],
                ["净利润 Net Profit", "1,946.6", "1,156.6"],
                ["每股收益 EPS (元)", "20.40", "12.16"],
            ],
        )
    ]

    # ---- Balance sheet ----
    story += [Spacer(1, 14), Paragraph("合并资产负债表 Consolidated Balance Sheet", h2)]
    story += [
        tbl(
            ["项目 Item", "2024", "2023"],
            [
                ["货币资金 Cash and Cash Equivalents", "1,715.1", "1,289.0"],
                ["应收账款 Accounts Receivable", "521.4", "415.8"],
                ["存货 Inventory", "98.2", "83.1"],
                ["流动资产 Current Assets", "4,120.6", "3,530.4"],
                ["资产总计 Total Assets", "16,428.0", "14,290.3"],
                ["流动负债 Current Liabilities", "3,880.1", "3,410.7"],
                ["负债合计 Total Liabilities", "7,940.5", "7,120.9"],
                ["短期借款 Debt", "1,204.0", "1,150.6"],
            ],
        )
    ]

    story += [PageBreak()]

    # ---- Cash flow ----
    story += [Paragraph("合并现金流量表 Consolidated Cash Flow Statement", h2)]
    story += [
        tbl(
            ["项目 Item", "2024", "2023"],
            [
                ["经营活动产生的现金流量净额 Operating Cash Flow", "2,536.1", "2,111.2"],
                ["投资活动产生的现金流量净额 Investing Cash Flow", "(1,204.7)", "(980.3)"],
                ["筹资活动产生的现金流量净额 Financing Cash Flow", "(742.0)", "(510.9)"],
                ["自由现金流 Free Cash Flow", "1,331.4", "1,130.9"],
            ],
        )
    ]

    # ---- Business segments ----
    story += [Spacer(1, 14), Paragraph("分业务数据 Segment Revenue", h2)]
    story += [
        tbl(
            ["分部 Segment", "2024", "2023"],
            [
                ["增值服务 Value-Added Services", "3,120.5", "2,853.1"],
                ["网络广告 Online Advertising", "1,987.4", "1,760.2"],
                ["金融科技 FinTech & Business Services", "989.0", "1,013.2"],
            ],
        )
    ]

    # ---- Management discussion ----
    story += [Spacer(1, 16), Paragraph("管理层讨论与分析 Management Discussion & Analysis", h2)]
    story += [
        Paragraph(
            "本年度营业收入持续增长，同比增长 8.3%，主要由增值服务及网络广告业务驱动。"
            "净利润同比增长 68.4%，主要由于投资收益增加及经营效率提升。"
            "经营活动现金流保持健康增长。毛利率小幅上升至 53.0%。",
            body,
        ),
        Spacer(1, 6),
        Paragraph(
            "对未来的展望：我们预计 2025 年营业收入将保持双位数增长，并持续投入 AI 与云业务。"
            "管理层预期全年毛利率维持在 52% 至 54% 区间。",
            body,
        ),
    ]

    # ---- Risk factors ----
    story += [Spacer(1, 16), Paragraph("风险因素 Risk Factors", h2)]
    story += [
        Paragraph("宏观经济波动可能对广告业务收入造成不利影响。", body),
        Paragraph("应收账款增长较快，同比增长 25.6%，存在一定回款风险。", body),
        Paragraph("行业监管政策变化可能面临合规不确定性。", body),
        Paragraph("Foreign exchange volatility may adversely affect overseas revenue.", body),
    ]

    doc.build(story)
    return dest
