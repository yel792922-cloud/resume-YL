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
    is_guest: bool = False
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
    # Reporting scope that disambiguates same-named metrics (consolidated total
    # vs a segment / geography / per-share figure). Derived, not stored.
    scope_type: str = ""              # consolidated | segment | geography | per_share | ""
    scope_label: str = ""            # e.g. "Consolidated total" or a segment/region name
    # What kind of quantity this is (amount / ratio / growth / per_share / …), so
    # ratios and growth rates are never read as amounts. Derived, not stored.
    metric_kind: str = "uncertain"
    source: SourceRef


class ReportPolicyOut(BaseModel):
    """The *active* analysis policy derived from the profile — what actually
    changes in grouping / cleaning / classification / forecasting."""

    merge_aggressiveness: str = "aggressive"     # aggressive | conservative
    scope_preservation: str = "low"              # low | high
    unit_inference_threshold: str = "permissive" # permissive | conservative
    cleaning_strictness: str = "strict"          # strict | lenient
    conservative_classification: bool = False
    preferred_metric_families: list[str] = []
    forecast_driver_weights: dict[str, int] = {}
    notes: list[str] = []


class ReportProfileOut(BaseModel):
    """Report structure hint/inference, used to adapt behavior + explain it."""

    business_structure: str = "auto"   # single | multi | conglomerate | auto | unknown
    geo_scope: str = "auto"            # single_region | multi_region | global | ...
    industry: str = "auto"
    report_type: str = "auto"
    source: str = "auto"               # user | auto | mixed
    complexity: str = "simple"         # simple | complex
    rationale: list[str] = []
    policy: ReportPolicyOut | None = None   # active analysis policy from this profile


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
    profile: ReportProfileOut | None = None   # report structure hint/inference
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
    mode: str = "raw"                # raw | clean — which fact pool was compared
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
    page_number: int | None = None   # where the filtered item came from
    report_section: str | None = None


class CleanedFactsResponse(BaseModel):
    document_id: str
    stats: dict[str, int]            # {retained, removed, deduped, normalized}
    rules: list[str] = []            # active cleaning-rule ids (UI localizes labels)
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


class ScenarioAssumptions(BaseModel):
    scenario: str                    # base | bull | bear
    # External, qualitative scenario assumptions (NOT facts from the report).
    external_factors: list[str] = []


class ForecastFactor(BaseModel):
    """A configurable external driver the user can weight (-2..+2)."""

    id: str
    label_en: str
    label_zh: str


class FactorImpact(BaseModel):
    """How much a weighted factor moved the Custom scenario's growth."""

    id: str
    label_en: str
    label_zh: str
    weight: int
    contribution_pp: float           # growth pp added (may be negative)


class ImpactDriver(BaseModel):
    """One 'why' line: an internal metric or external factor that mattered."""

    label: str
    detail: str
    magnitude_pp: float | None = None  # signed pp/growth magnitude when numeric


class ImpactSummary(BaseModel):
    """Explains the forecast: what drove it, and which assumptions mattered most."""

    headline: str
    internal_drivers: list[ImpactDriver] = []   # from the report's own metrics
    external_drivers: list[FactorImpact] = []   # from user factor weights
    notes: str | None = None


class PolicyEmphasis(BaseModel):
    """How the report profile shapes the forecast (suggestions, not auto-applied)."""

    preferred_metric_families: list[str] = []
    suggested_factor_weights: dict[str, int] = {}
    note: str | None = None


class ForecastResponse(BaseModel):
    document_id: str
    company_name: str | None = None
    report_type: str
    mode: str = "clean"              # raw | clean — which fact pool was used
    base_period: str | None = None
    forecast_period: str
    cadence: str                     # quarter | half-year | year
    annualized: bool = False         # whether an OPTIONAL annualized view is provided
    annualized_note: str | None = None  # explains the annualized view is optional
    growth_override_pct: float | None = None
    disclaimer: str
    metrics: list[ForecastMetric] = []
    guidance: list[SummaryHighlight] = []
    key_risks: list[SummaryHighlight] = []
    # Expanded drivers: external scenario assumptions per scenario, plus a note
    # making clear these are assumptions, not report facts.
    external_assumptions: list[ScenarioAssumptions] = []
    external_note: str | None = None
    # v4.x: configurable factors + custom scenario + impact explanation.
    factors: list[ForecastFactor] = []          # catalog for the UI
    factor_weights: dict[str, int] = {}          # echoed weights used for Custom
    custom_notes: str | None = None
    impact_summary: ImpactSummary | None = None
    policy_emphasis: PolicyEmphasis | None = None   # how the profile shapes the forecast


class CustomForecastRequest(BaseModel):
    growth_override_pct: float | None = Field(default=None, ge=-100, le=1000)
    factor_weights: dict[str, int] = {}
    notes: str | None = Field(default=None, max_length=500)
    value_delta_pp: float | None = Field(default=None, ge=0, le=200)
    margin_delta_pp: float | None = Field(default=None, ge=0, le=100)
    mode: str = Field(default="clean", pattern="^(raw|clean)$")


# ---------------------------- v4: evidence-based Q&A ----------------------------
class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class EvidenceItem(BaseModel):
    text: str                        # the cited statement / snippet
    kind: str                        # fact | management | guidance | risk | text
    source: SourceRef | None = None  # jump target back to the report
    fact: FactOut | None = None      # present when the evidence is a structured fact
    score: float = 0.0


class AnswerResponse(BaseModel):
    document_id: str
    question: str
    intent: str                      # metric_lookup | why_change | period_change | cash_health | risks | general
    answer: str                      # concise, grounded answer text
    confidence: str                  # low | medium | high
    insufficient: bool = False       # true when the report lacks evidence to answer confidently
    evidence: list[EvidenceItem] = []
    note: str | None = None          # conservative caveat / disclaimer
