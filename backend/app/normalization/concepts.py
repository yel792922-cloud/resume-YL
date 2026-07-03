"""The unified internal concept layer.

Each :class:`Concept` is a canonical financial line item with its Chinese and
English aliases. This is the single source of truth for *what* we extract and
*how* terminology is normalized across languages.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.fact import FactCategory


@dataclass(frozen=True)
class Concept:
    id: str
    category: FactCategory
    canonical_en: str
    canonical_zh: str
    # Unit hint helps normalization pick a default unit when the report omits it.
    unit_hint: str | None = None            # "currency" | "percent" | "shares" | "count"
    # Aliases as they appear in real reports (matched case-insensitively).
    aliases_en: tuple[str, ...] = field(default_factory=tuple)
    aliases_zh: tuple[str, ...] = field(default_factory=tuple)
    # Higher priority wins when two concepts could match the same label.
    priority: int = 0

    @property
    def all_labels(self) -> list[tuple[str, str]]:
        """Return (label, language) pairs including canonical names."""
        pairs: list[tuple[str, str]] = [(self.canonical_en, "en"), (self.canonical_zh, "zh")]
        pairs += [(a, "en") for a in self.aliases_en]
        pairs += [(a, "zh") for a in self.aliases_zh]
        return pairs


# ---------------------------------------------------------------------------
# Concept catalog. Ordered by category; covers the spec's required metrics.
# ---------------------------------------------------------------------------
CONCEPTS: tuple[Concept, ...] = (
    # ----------------------- Income statement -----------------------
    Concept(
        "revenue", FactCategory.INCOME_STATEMENT, "Revenue", "营业收入", "currency",
        aliases_en=("total revenue", "net revenue", "net revenues", "turnover", "sales", "net sales", "total net revenues"),
        aliases_zh=("营收", "营业总收入", "收入", "总营收", "营业额"),
        priority=5,
    ),
    Concept(
        "cost_of_revenue", FactCategory.INCOME_STATEMENT, "Cost of Revenue", "营业成本", "currency",
        aliases_en=("cost of sales", "cost of goods sold", "cogs", "cost of revenues"),
        aliases_zh=("营业成本", "主营业务成本", "销售成本"),
    ),
    Concept(
        "gross_profit", FactCategory.INCOME_STATEMENT, "Gross Profit", "毛利", "currency",
        aliases_en=("gross margin amount",),
        aliases_zh=("毛利润", "毛利额"),
        priority=3,
    ),
    Concept(
        "gross_margin", FactCategory.INCOME_STATEMENT, "Gross Margin", "毛利率", "percent",
        aliases_en=("gross profit margin", "gross margin %", "gross margin ratio"),
        aliases_zh=("毛利率", "综合毛利率"),
        priority=4,
    ),
    Concept(
        "operating_profit", FactCategory.INCOME_STATEMENT, "Operating Profit", "营业利润", "currency",
        aliases_en=("operating income", "income from operations", "profit from operations", "operating profit/(loss)"),
        aliases_zh=("经营利润", "营业利润", "经营溢利"),
    ),
    Concept(
        "net_profit", FactCategory.INCOME_STATEMENT, "Net Profit", "净利润", "currency",
        aliases_en=("net income", "profit for the year", "profit for the period", "net profit attributable", "net earnings"),
        aliases_zh=("净利", "本期净利润", "归母净利润", "归属于母公司股东的净利润", "净利润(含少数股东损益)"),
        priority=3,
    ),
    Concept(
        "eps", FactCategory.INCOME_STATEMENT, "EPS", "每股收益", "shares",
        aliases_en=("earnings per share", "basic eps", "diluted eps", "basic earnings per share"),
        aliases_zh=("每股收益", "基本每股收益", "稀释每股收益", "eps"),
    ),
    # ----------------------- Cash flow -----------------------
    Concept(
        "operating_cash_flow", FactCategory.CASH_FLOW, "Operating Cash Flow", "经营活动现金流", "currency",
        aliases_en=("net cash from operating activities", "cash flow from operations", "cash generated from operations", "net cash provided by operating activities"),
        aliases_zh=("经营活动产生的现金流量净额", "经营现金流", "经营活动现金流量净额"),
    ),
    Concept(
        "investing_cash_flow", FactCategory.CASH_FLOW, "Investing Cash Flow", "投资活动现金流", "currency",
        aliases_en=("net cash used in investing activities", "cash flow from investing", "net cash from investing activities"),
        aliases_zh=("投资活动产生的现金流量净额", "投资现金流"),
    ),
    Concept(
        "financing_cash_flow", FactCategory.CASH_FLOW, "Financing Cash Flow", "筹资活动现金流", "currency",
        aliases_en=("net cash from financing activities", "cash flow from financing", "net cash used in financing activities"),
        aliases_zh=("筹资活动产生的现金流量净额", "融资活动现金流", "筹资现金流"),
    ),
    Concept(
        "free_cash_flow", FactCategory.CASH_FLOW, "Free Cash Flow", "自由现金流", "currency",
        aliases_en=("fcf",),
        aliases_zh=("自由现金流量",),
    ),
    # ----------------------- Balance sheet -----------------------
    Concept(
        "cash_and_equivalents", FactCategory.BALANCE_SHEET, "Cash and Cash Equivalents", "货币资金", "currency",
        aliases_en=("cash and equivalents", "cash & cash equivalents", "cash"),
        aliases_zh=("现金及现金等价物", "货币资金", "现金及等价物"),
    ),
    Concept(
        "total_assets", FactCategory.BALANCE_SHEET, "Total Assets", "资产总计", "currency",
        aliases_en=("total assets",),
        aliases_zh=("资产总额", "总资产", "资产合计"),
    ),
    Concept(
        "total_liabilities", FactCategory.BALANCE_SHEET, "Total Liabilities", "负债合计", "currency",
        aliases_en=("total liabilities",),
        aliases_zh=("负债总计", "总负债", "负债总额"),
    ),
    Concept(
        "debt", FactCategory.BALANCE_SHEET, "Total Debt", "有息负债", "currency",
        aliases_en=("total debt", "borrowings", "interest-bearing debt", "short-term and long-term debt"),
        aliases_zh=("有息负债", "借款", "短期借款", "长期借款", "带息负债"),
    ),
    Concept(
        "accounts_receivable", FactCategory.BALANCE_SHEET, "Accounts Receivable", "应收账款", "currency",
        aliases_en=("trade receivables", "receivables", "accounts receivables"),
        aliases_zh=("应收款项", "应收票据及应收账款", "应收帐款"),
    ),
    Concept(
        "inventory", FactCategory.BALANCE_SHEET, "Inventory", "存货", "currency",
        aliases_en=("inventories",),
        aliases_zh=("存货净额",),
    ),
    Concept(
        "current_assets", FactCategory.BALANCE_SHEET, "Current Assets", "流动资产", "currency",
        aliases_en=("total current assets",),
        aliases_zh=("流动资产合计", "流动资产总计"),
    ),
    Concept(
        "current_liabilities", FactCategory.BALANCE_SHEET, "Current Liabilities", "流动负债", "currency",
        aliases_en=("total current liabilities",),
        aliases_zh=("流动负债合计", "流动负债总计"),
    ),
    # ----------------------- Business / operating -----------------------
    Concept(
        "segment_revenue", FactCategory.BUSINESS, "Segment Revenue", "分部收入", "currency",
        aliases_en=("business segment revenue", "revenue by segment"),
        aliases_zh=("分业务收入", "业务分部收入", "分部营收"),
    ),
    Concept(
        "geographic_revenue", FactCategory.BUSINESS, "Geographic Revenue", "分地区收入", "currency",
        aliases_en=("revenue by geography", "revenue by region"),
        aliases_zh=("分地区收入", "分区域收入", "地区收入"),
    ),
    Concept(
        "user_metric", FactCategory.BUSINESS, "User Metric", "用户指标", "count",
        aliases_en=("mau", "dau", "monthly active users", "daily active users", "active users", "subscribers", "paying users"),
        aliases_zh=("月活跃用户", "日活跃用户", "活跃用户", "付费用户", "用户数"),
    ),
)


_BY_ID: dict[str, Concept] = {c.id: c for c in CONCEPTS}


def concept_by_id(concept_id: str) -> Concept | None:
    return _BY_ID.get(concept_id)


def iter_concepts() -> tuple[Concept, ...]:
    return CONCEPTS
