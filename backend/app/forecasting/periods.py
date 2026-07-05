"""Report-period handling: horizon cadence and next-period labels.

The forecast horizon adapts to the report's reporting period:
quarterly -> next quarter, half-year -> next half, annual -> next year.
"""
from __future__ import annotations

import re

from app.models.document import ReportType

# cadence key -> (human cadence label, annualization factor)
_CADENCE = {
    "quarter": ("quarter", 4),
    "half": ("half-year", 2),
    "year": ("year", 1),
}


def cadence_for(report_type: ReportType) -> str:
    if report_type == ReportType.QUARTERLY:
        return "quarter"
    if report_type == ReportType.INTERIM:
        return "half"
    # Annual, prospectus, or unknown default to annual cadence.
    return "year"


def annualization_factor(report_type: ReportType) -> int:
    return _CADENCE[cadence_for(report_type)][1]


def cadence_label(report_type: ReportType) -> str:
    return _CADENCE[cadence_for(report_type)][0]


def _year(period: str | None) -> int | None:
    if not period:
        return None
    m = re.search(r"(20\d{2})", period)
    return int(m.group(1)) if m else None


def next_period_label(report_period: str | None, report_type: ReportType) -> str:
    """Best-effort label for the forecasted period, e.g. '2025 FY', '2024 Q4',
    '2025 H1'. Falls back to a generic label when the period can't be parsed."""
    cadence = cadence_for(report_type)
    year = _year(report_period)

    if cadence == "quarter":
        m = re.search(r"Q\s*([1-4])", report_period or "", re.I)
        if year and m:
            q = int(m.group(1))
            return f"{year} Q{q + 1}" if q < 4 else f"{year + 1} Q1"
        return f"{year} next quarter" if year else "next quarter"

    if cadence == "half":
        m = re.search(r"H\s*([12])", report_period or "", re.I)
        if year and m:
            h = int(m.group(1))
            return f"{year} H2" if h == 1 else f"{year + 1} H1"
        return f"{year + 1} H1" if year else "next half-year"

    # annual
    return f"{year + 1} FY" if year else "next year"
