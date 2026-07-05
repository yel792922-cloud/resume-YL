"""Pydantic schemas — the API's data contract (separate from ORM entities)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.document import DocumentStatus, ReportType
from app.models.fact import FactCategory


# ---------------------------- Auth ----------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SourceRef(BaseModel):
    """Everything the UI needs to jump to and highlight a fact's origin."""

    page_number: int | None = None
    section: str | None = None
    snippet: str | None = None
    bbox: list[float] | None = None            # [x0, top, x1, bottom] in 0..1
    table_cell: str | None = None              # "table=1;row=3;col=2"


class FactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    category: FactCategory
    concept_id: str | None
    metric_name: str
    metric_label: str | None
    raw_label: str | None
    metric_value: float | None
    value_text: str | None
    unit: str | None
    language: str
    report_period: str | None
    confidence_score: float
    extraction_method: str | None
    version_id: str
    source: SourceRef


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    company_name: str | None
    ticker: str | None
    report_type: ReportType
    report_period: str | None
    language: str
    page_count: int
    is_scanned: bool
    status: DocumentStatus
    status_detail: str | None
    is_favorite: bool
    raw_available: bool = True         # False once retention removed the raw PDF
    fact_count: int = 0
    version_count: int = 0             # number of historical parse snapshots
    created_at: datetime


class PageOut(BaseModel):
    page_number: int
    width: float
    height: float
    text: str
    source: str
    words: list[dict] = []
    tables: list[dict] = []


class DocumentDetail(DocumentSummary):
    pages: list[int] = []            # available page numbers


class SearchHit(BaseModel):
    kind: str                        # "fact" | "text"
    page_number: int | None
    section: str | None
    snippet: str
    bbox: list[float] | None = None
    fact: FactOut | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]


class SummaryHighlight(BaseModel):
    text: str
    fact_id: int | None = None
    source: SourceRef | None = None


class ReportSummary(BaseModel):
    document_id: str
    company_name: str | None
    report_period: str | None
    headline_metrics: list[FactOut] = []
    highlights: list[SummaryHighlight] = []
    risks: list[SummaryHighlight] = []


class CompareCell(BaseModel):
    period: str
    document_id: str
    fact: FactOut | None = None


class CompareRow(BaseModel):
    concept_id: str
    metric_name: str
    metric_label: str
    unit: str | None
    cells: list[CompareCell]


class CompareResponse(BaseModel):
    dimension: str                   # "period" | "company"
    columns: list[str]               # period labels or company names
    document_ids: list[str]
    rows: list[CompareRow]


# ---------------------------- Parse history ----------------------------
class SnapshotSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    version: int
    engine_version: str
    fact_count: int
    page_count: int
    language: str
    note: str | None
    created_at: datetime


class SnapshotDetail(SnapshotSummary):
    facts: list[FactOut] = []
    summary: ReportSummary | None = None


# ---------------------------- v3: data cleaning ----------------------------
class CleaningAuditEntry(BaseModel):
    action: str                      # "removed" | "deduped" | "normalized"
    reason: str
    fact_id: int | None = None
    concept_id: str | None = None
    metric_name: str | None = None
    snippet: str | None = None
    detail: str | None = None
    confidence: float | None = None


class CleanedFactsResponse(BaseModel):
    document_id: str
    stats: dict[str, int]            # {retained, removed, deduped, normalized}
    retained: list[FactOut] = []     # cleaned, source-traceable facts
    audit: list[CleaningAuditEntry] = []


# ---------------------------- v3: scenario forecasting ----------------------------
class ScenarioForecast(BaseModel):
    scenario: str                    # base | bull | bear
    period: str                      # forecasted period label
    predicted_value: float
    annualized_value: float | None = None
    growth_pct: float | None = None  # growth % (value) or pp change (margin)
    direction: str                   # up | down | flat
    confidence: str                  # low | medium | high
    assumptions: list[str] = []
    explanation: str


class ForecastMetric(BaseModel):
    concept_id: str
    metric_name: str
    metric_label: str | None = None
    unit: str | None = None
    is_percent: bool = False
    current_value: float
    prior_value: float | None = None
    observed_growth_pct: float | None = None
    source: SourceRef | None = None
    scenarios: list[ScenarioForecast] = []


class ForecastResponse(BaseModel):
    document_id: str
    company_name: str | None = None
    report_type: str
    base_period: str | None = None
    forecast_period: str
    cadence: str                     # quarter | half-year | year
    annualized: bool = False         # whether annualized_value is provided
    growth_override_pct: float | None = None
    disclaimer: str
    metrics: list[ForecastMetric] = []
    guidance: list[SummaryHighlight] = []
    key_risks: list[SummaryHighlight] = []
