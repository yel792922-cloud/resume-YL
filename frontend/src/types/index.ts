// Types mirroring the backend Pydantic schemas (app/models/schemas.py).

export interface User {
  id: number;
  email: string;
  is_guest: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type ReportType = "annual" | "interim" | "quarterly" | "prospectus" | "other";
export type DocumentStatus = "uploaded" | "parsing" | "extracting" | "ready" | "failed";
export type FactCategory =
  | "income_statement"
  | "balance_sheet"
  | "cash_flow"
  | "business"
  | "guidance"
  | "management"
  | "risk";

export interface SourceRef {
  page_number: number | null;
  section: string | null;
  snippet: string | null;
  bbox: number[] | null; // [x0, top, x1, bottom] normalized 0..1
  table_cell: string | null;
}

export interface Fact {
  id: number;
  document_id: string;
  category: FactCategory;
  concept_id: string | null;
  metric_name: string;
  metric_label: string | null;
  raw_label: string | null;
  metric_value: number | null;
  value_text: string | null;
  unit: string | null;
  language: string;
  report_period: string | null;
  confidence_score: number;
  extraction_method: string | null;
  version_id: string;
  scope_type: string; // "consolidated" | "segment" | "geography" | "per_share" | ""
  scope_label: string;
  metric_kind: string; // amount | ratio | growth | per_share | count | segment_total | geography_total | regulatory | user | uncertain
  source: SourceRef;
}

export interface ReportPolicy {
  merge_aggressiveness: string;      // aggressive | conservative
  scope_preservation: string;        // low | high
  unit_inference_threshold: string;  // permissive | conservative
  cleaning_strictness: string;       // strict | lenient
  conservative_classification: boolean;
  preferred_metric_families: string[];
  forecast_driver_weights: Record<string, number>;
  notes: string[];
}

export interface ReportProfile {
  business_structure: string; // single | multi | conglomerate | auto | unknown
  geo_scope: string;          // single_region | multi_region | global | auto | unknown
  industry: string;
  report_type: string;
  source: string;             // user | auto | mixed
  complexity: string;         // simple | complex
  rationale: string[];
  policy: ReportPolicy | null;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  company_name: string | null;
  ticker: string | null;
  report_type: ReportType;
  report_period: string | null;
  language: string;
  page_count: number;
  is_scanned: boolean;
  status: DocumentStatus;
  status_detail: string | null;
  is_favorite: boolean;
  raw_available: boolean;
  fact_count: number;
  version_count: number;
  profile: ReportProfile | null;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  pages: number[];
}

export interface SnapshotSummary {
  id: number;
  document_id: string;
  version: number;
  engine_version: string;
  fact_count: number;
  page_count: number;
  language: string;
  note: string | null;
  created_at: string;
}

export interface SnapshotDetail extends SnapshotSummary {
  facts: Fact[];
  summary: ReportSummary | null;
}

export interface Word {
  text: string;
  x0: number;
  top: number;
  x1: number;
  bottom: number;
}

export interface PageOut {
  page_number: number;
  width: number;
  height: number;
  text: string;
  source: string;
  words: Word[];
  tables: { bbox: number[]; rows: (string | null)[][] }[];
}

export interface SearchHit {
  kind: "fact" | "text";
  page_number: number | null;
  section: string | null;
  snippet: string;
  bbox: number[] | null;
  fact: Fact | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  hits: SearchHit[];
}

export interface SummaryHighlight {
  text: string;
  fact_id: number | null;
  source: SourceRef | null;
}

export interface ReportSummary {
  document_id: string;
  company_name: string | null;
  report_period: string | null;
  headline_metrics: Fact[];
  highlights: SummaryHighlight[];
  risks: SummaryHighlight[];
}

export interface CompareCell {
  period: string;
  document_id: string;
  fact: Fact | null;
}

export interface CompareRow {
  concept_id: string;
  metric_name: string;
  metric_label: string;
  unit: string | null;
  cells: CompareCell[];
}

export interface CompareResponse {
  dimension: "period" | "company";
  mode: string;
  columns: string[];
  document_ids: string[];
  rows: CompareRow[];
}

// ---- v3: data cleaning ----
export interface CleaningAuditEntry {
  action: "removed" | "deduped" | "normalized";
  reason: string;
  fact_id: number | null;
  concept_id: string | null;
  metric_name: string | null;
  snippet: string | null;
  detail: string | null;
  confidence: number | null;
  page_number: number | null;
  report_section: string | null;
}

export interface CleanedFactsResponse {
  document_id: string;
  stats: { retained: number; removed: number; deduped: number; normalized: number };
  rules: string[];
  retained: Fact[];
  audit: CleaningAuditEntry[];
}

// ---- v3: scenario forecasting ----
export type ScenarioName = "base" | "bull" | "bear" | "custom";
export type ConfidenceLevel = "low" | "medium" | "high";

export interface ScenarioForecast {
  scenario: ScenarioName;
  period: string;
  predicted_value: number;
  annualized_value: number | null;
  growth_pct: number | null;
  direction: "up" | "down" | "flat";
  confidence: ConfidenceLevel;
  assumptions: string[];
  explanation: string;
}

export interface ForecastMetric {
  concept_id: string;
  metric_name: string;
  metric_label: string | null;
  unit: string | null;
  is_percent: boolean;
  current_value: number;
  prior_value: number | null;
  observed_growth_pct: number | null;
  source: SourceRef | null;
  scenarios: ScenarioForecast[];
}

export interface ScenarioAssumptions {
  scenario: string;
  external_factors: string[];
}

// ---- v4.x: configurable factors + custom scenario + impact ----
export interface ForecastFactor {
  id: string;
  label_en: string;
  label_zh: string;
}

export interface FactorImpact {
  id: string;
  label_en: string;
  label_zh: string;
  weight: number;
  contribution_pp: number;
}

export interface ImpactDriver {
  label: string;
  detail: string;
  magnitude_pp: number | null;
}

export interface ImpactSummary {
  headline: string;
  internal_drivers: ImpactDriver[];
  external_drivers: FactorImpact[];
  notes: string | null;
}

export interface ForecastResponse {
  document_id: string;
  company_name: string | null;
  report_type: string;
  mode: string;
  base_period: string | null;
  forecast_period: string;
  cadence: string;
  annualized: boolean;
  annualized_note: string | null;
  growth_override_pct: number | null;
  disclaimer: string;
  metrics: ForecastMetric[];
  guidance: SummaryHighlight[];
  key_risks: SummaryHighlight[];
  external_assumptions: ScenarioAssumptions[];
  external_note: string | null;
  factors: ForecastFactor[];
  factor_weights: Record<string, number>;
  custom_notes: string | null;
  impact_summary: ImpactSummary | null;
  policy_emphasis: PolicyEmphasis | null;
}

export interface PolicyEmphasis {
  preferred_metric_families: string[];
  suggested_factor_weights: Record<string, number>;
  note: string | null;
}

export interface CustomForecastRequest {
  growth_override_pct?: number | null;
  factor_weights?: Record<string, number>;
  notes?: string | null;
  value_delta_pp?: number | null;
  margin_delta_pp?: number | null;
  mode?: string;
}

// ---- v4: evidence-based Q&A ----
export interface EvidenceItem {
  text: string;
  kind: "fact" | "management" | "guidance" | "risk" | "text";
  source: SourceRef | null;
  fact: Fact | null;
  score: number;
}

export interface AnswerResponse {
  document_id: string;
  question: string;
  intent: string;
  answer: string;
  confidence: ConfidenceLevel;
  insufficient: boolean;
  evidence: EvidenceItem[];
  note: string | null;
}
