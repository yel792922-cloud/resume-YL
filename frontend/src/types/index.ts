// Types mirroring the backend Pydantic schemas (app/models/schemas.py).

export interface User {
  id: number;
  email: string;
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
  source: SourceRef;
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
  columns: string[];
  document_ids: string[];
  rows: CompareRow[];
}
