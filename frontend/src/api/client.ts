// Typed API client for the Financial Report Analyzer backend.
import type {
  AnswerResponse,
  AuthResponse,
  CleanedFactsResponse,
  CompareResponse,
  CustomForecastRequest,
  DocumentDetail,
  DocumentSummary,
  Fact,
  FactCategory,
  ForecastResponse,
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

async function req<T>(path: string, init?: RequestInit, timeoutMs?: number): Promise<T> {
  // Optional client-side timeout so a hung request surfaces a clear error
  // instead of spinning forever. Existing calls (no timeoutMs) are unchanged.
  let signal = init?.signal ?? undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  if (timeoutMs) {
    const ctrl = new AbortController();
    timer = setTimeout(() => ctrl.abort(), timeoutMs);
    signal = ctrl.signal;
  }
  try {
    const res = await handle(await fetch(`${BASE}${path}`, { ...init, headers: authHeaders(init?.headers), signal }));
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError(0, "Request timed out. Please try again.");
    }
    throw e;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

// Small in-memory cache for deterministic, read-only analytics responses so
// switching between report tabs doesn't refetch. Cleared on full page reload.
const analyticsCache = new Map<string, Promise<unknown>>();
function cached<T>(key: string, factory: () => Promise<T>): Promise<T> {
  const hit = analyticsCache.get(key);
  if (hit) return hit as Promise<T>;
  const p = factory().catch((e) => {
    analyticsCache.delete(key); // don't cache failures — allow retry
    throw e;
  });
  analyticsCache.set(key, p);
  return p as Promise<T>;
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
  uploadDocument: (
    file: File,
    companyName?: string,
    reportPeriod?: string,
    profile?: { business_structure?: string; geo_scope?: string; industry?: string; report_type?: string },
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (companyName) form.append("company_name", companyName);
    if (reportPeriod) form.append("report_period", reportPeriod);
    for (const k of ["business_structure", "geo_scope", "industry", "report_type"] as const) {
      if (profile?.[k]) form.append(k, profile[k]!);
    }
    return req<DocumentSummary>(`/documents/upload`, { method: "POST", body: form });
  },
  deleteDocument: (id: string) => req<{ deleted: string }>(`/documents/${id}`, { method: "DELETE" }),
  toggleFavorite: (id: string) => req<DocumentSummary>(`/documents/${id}/favorite`, { method: "POST" }),
  getFacts: (id: string, category?: FactCategory) =>
    req<Fact[]>(`/documents/${id}/facts${category ? `?category=${category}` : ""}`),
  getPage: (id: string, page: number) => req<PageOut>(`/documents/${id}/pages/${page}`),
  getSummary: (id: string) => req<ReportSummary>(`/documents/${id}/summary`),
  search: (id: string, q: string) => req<SearchResponse>(`/documents/${id}/search?q=${encodeURIComponent(q)}`),
  compare: (ids: string[], dimension: "period" | "company" = "period", mode: string = "clean") => {
    const params = ids.map((i) => `document_ids=${encodeURIComponent(i)}`).join("&");
    return req<CompareResponse>(`/compare?${params}&dimension=${dimension}&mode=${mode}`);
  },

  // ---- History ----
  getHistory: (id: string) => req<SnapshotSummary[]>(`/documents/${id}/history`),
  getSnapshot: (id: string, version: number) => req<SnapshotDetail>(`/documents/${id}/history/${version}`),

  // ---- v3 analytics (cached per session; 20s timeout) ----
  getCleaned: (id: string) =>
    cached(`cleaned:${id}`, () => req<CleanedFactsResponse>(`/documents/${id}/cleaned`, undefined, 20000)),
  getForecast: (id: string, growthOverridePct?: number | null, mode: string = "clean") => {
    const params = new URLSearchParams();
    if (growthOverridePct != null) params.set("growth_override_pct", String(growthOverridePct));
    params.set("mode", mode);
    const q = `?${params.toString()}`;
    return cached(`forecast:${id}:${growthOverridePct ?? ""}:${mode}`, () =>
      req<ForecastResponse>(`/documents/${id}/forecast${q}`, undefined, 20000),
    );
  },
  // Custom scenario: growth override (±) + weighted external factors + notes.
  // Not cached — it's a live "what-if" the user drives.
  customForecast: (id: string, body: CustomForecastRequest) =>
    req<ForecastResponse>(
      `/documents/${id}/forecast/custom`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
      20000,
    ),

  // ---- v4 Q&A (POST; 20s timeout; not cached — each question is a user action) ----
  ask: (id: string, question: string, mode: string = "clean") =>
    req<AnswerResponse>(
      `/documents/${id}/ask?mode=${mode}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) },
      20000,
    ),

  // ---- Export (authorized blob download) ----
  downloadExport: async (id: string, fmt: "csv" | "json" | "xlsx", filename: string, mode: string = "clean") => {
    const res = await handle(
      await fetch(`${BASE}/documents/${id}/export.${fmt}?mode=${mode}`, { headers: authHeaders() }),
    );
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
