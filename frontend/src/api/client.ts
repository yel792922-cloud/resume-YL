// Typed API client for the Financial Report Analyzer backend.
import type {
  AuthResponse,
  CompareResponse,
  DocumentDetail,
  DocumentSummary,
  Fact,
  FactCategory,
  PageOut,
  ReportSummary,
  SearchResponse,
  SnapshotDetail,
  SnapshotSummary,
  User,
} from "../types";

const BASE = "/api";
const TOKEN_KEY = "fra_token";

// ---- Token storage (localStorage; JWT bearer, cross-origin friendly) ----
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Registered by AuthProvider so a 401 anywhere logs the user out cleanly.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return { ...(extra || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function handle(res: Response): Promise<Response> {
  if (res.status === 401) {
    onUnauthorized?.();
    throw new ApiError(401, "Session expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await handle(await fetch(`${BASE}${path}`, { ...init, headers: authHeaders(init?.headers) }));
  return (await res.json()) as T;
}

export interface HealthInfo {
  status: string;
  version: string;
  max_upload_mb: number;
  max_uploads_per_user: number;
}

export const api = {
  health: () => req<HealthInfo>("/health"),

  // ---- Auth ----
  register: (email: string, password: string) =>
    req<AuthResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    req<AuthResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
  me: () => req<User>("/auth/me"),
  logout: () => req<{ status: string }>("/auth/logout", { method: "POST" }),

  // ---- Documents ----
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
  deleteDocument: (id: string) => req<{ deleted: string }>(`/documents/${id}`, { method: "DELETE" }),
  toggleFavorite: (id: string) => req<DocumentSummary>(`/documents/${id}/favorite`, { method: "POST" }),
  getFacts: (id: string, category?: FactCategory) =>
    req<Fact[]>(`/documents/${id}/facts${category ? `?category=${category}` : ""}`),
  getPage: (id: string, page: number) => req<PageOut>(`/documents/${id}/pages/${page}`),
  getSummary: (id: string) => req<ReportSummary>(`/documents/${id}/summary`),
  search: (id: string, q: string) => req<SearchResponse>(`/documents/${id}/search?q=${encodeURIComponent(q)}`),
  compare: (ids: string[], dimension: "period" | "company" = "period") => {
    const params = ids.map((i) => `document_ids=${encodeURIComponent(i)}`).join("&");
    return req<CompareResponse>(`/compare?${params}&dimension=${dimension}`);
  },

  // ---- History ----
  getHistory: (id: string) => req<SnapshotSummary[]>(`/documents/${id}/history`),
  getSnapshot: (id: string, version: number) => req<SnapshotDetail>(`/documents/${id}/history/${version}`),

  // ---- Export (authorized blob download) ----
  downloadExport: async (id: string, fmt: "csv" | "json", filename: string) => {
    const res = await handle(await fetch(`${BASE}/documents/${id}/export.${fmt}`, { headers: authHeaders() }));
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
