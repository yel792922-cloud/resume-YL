// Typed API client for the Financial Report Analyzer backend.
import type {
  CompareResponse,
  DocumentDetail,
  DocumentSummary,
  Fact,
  FactCategory,
  PageOut,
  ReportSummary,
  SearchResponse,
} from "../types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => req<{ status: string }>("/health"),

  listDocuments: (favoritesOnly = false) =>
    req<DocumentSummary[]>(`/documents${favoritesOnly ? "?favorites_only=true" : ""}`),

  getDocument: (id: string) => req<DocumentDetail>(`/documents/${id}`),

  seedSample: () => req<DocumentSummary>(`/documents/seed`, { method: "POST" }),

  uploadDocument: (file: File, companyName?: string, reportPeriod?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (companyName) form.append("company_name", companyName);
    if (reportPeriod) form.append("report_period", reportPeriod);
    return req<DocumentSummary>(`/documents/upload`, { method: "POST", body: form });
  },

  deleteDocument: (id: string) =>
    req<{ deleted: string }>(`/documents/${id}`, { method: "DELETE" }),

  toggleFavorite: (id: string) =>
    req<DocumentSummary>(`/documents/${id}/favorite`, { method: "POST" }),

  getFacts: (id: string, category?: FactCategory) =>
    req<Fact[]>(`/documents/${id}/facts${category ? `?category=${category}` : ""}`),

  getPage: (id: string, page: number) => req<PageOut>(`/documents/${id}/pages/${page}`),

  getSummary: (id: string) => req<ReportSummary>(`/documents/${id}/summary`),

  search: (id: string, q: string) =>
    req<SearchResponse>(`/documents/${id}/search?q=${encodeURIComponent(q)}`),

  compare: (ids: string[], dimension: "period" | "company" = "period") => {
    const params = ids.map((i) => `document_ids=${encodeURIComponent(i)}`).join("&");
    return req<CompareResponse>(`/compare?${params}&dimension=${dimension}`);
  },

  exportUrl: (id: string, fmt: "csv" | "json") => `${BASE}/documents/${id}/export.${fmt}`,
};
