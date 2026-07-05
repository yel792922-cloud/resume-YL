# Architecture

The product is a **source-first financial report analyzer**. Its non-negotiable
invariant: every value the UI shows can be traced back to an exact location in
the original report (page, text snippet, table cell, bounding box) with a
confidence score. The architecture exists to preserve that invariant end to end.

## Layered pipeline

```
        ┌──────────────┐
Upload ─┤  Ingestion   │  store file, register Document
        └──────┬───────┘
        ┌──────▼───────┐
        │ Parsing/OCR  │  pdfplumber (digital) · pluggable OCR (scanned)
        └──────┬───────┘  → ParsedPage(words+bbox, tables), normalized 0..1
        ┌──────▼───────┐
        │  Extraction  │  table → text → section extractors → FactDraft
        └──────┬───────┘
        ┌──────▼───────┐
        │Normalization │  CN/EN concept dictionary → one internal concept layer
        └──────┬───────┘
        ┌──────▼───────┐
        │  SourceMap   │  snippet/cell → highlight bbox (click-to-jump)
        └──────┬───────┘
        ┌──────▼───────┐
        │Search/Compare│  in-report search · cross-period / cross-company
        └──────┬───────┘
        ┌──────▼───────┐
        │Summary/Export│  evidence-linked summary · CSV / JSON
        └──────┬───────┘
        ┌──────▼───────┐
        │   API / UI   │  FastAPI routes · React (Vite) screens
        └──────────────┘
```

Each layer is a Python package under `backend/app/` with a single
responsibility and a narrow interface, so any stage can be swapped (e.g. a
better OCR backend, an ML extractor) without touching the others.

## Data model (source of truth)

- **Document** — an uploaded report (company, type, period, language, status).
- **Page** — parsed page: full text + positioned `words` and `tables` (JSON),
  in normalized 0..1 coordinates.
- **ExtractedFact** — the traceable unit. Carries the value **and** its
  provenance: `metric_name, value, unit, language, source_page_number,
  report_section, source_text_snippet, source_bbox, source_table_cell_reference,
  confidence_score, extraction_method, extraction_timestamp, version_id`.

## Why rule-based extraction (for the MVP)

Extraction is deterministic (dictionary + table geometry + number parsing).
For a trust-critical research tool this is a feature: every fact is auditable
and reproducible, and the confidence score reflects the *source* (table 0.9 >
narrative 0.6 > derived 0.55 > section signal 0.5). ML extractors can be added
behind the same `FactDraft` interface later without weakening traceability.

## Terminology normalization

`app/normalization/concepts.py` defines canonical concepts, each with Chinese
and English aliases. The `TermMatcher` maps any printed label onto a concept.
This is what makes the app bilingual: "营业收入", "营收", "Revenue", and
"Total revenue" all resolve to the `revenue` concept, so search, comparison,
and summaries work across languages.

## Source mapping / highlighting

`app/sourcemap/highlight.py` resolves a snippet or table cell to a union
bounding box over the page's positioned words. The frontend reconstructs the
page from those same word coordinates and overlays the highlight — so
click-to-jump works without shipping a PDF renderer, and the highlight is
always consistent with what the backend extracted.

## Frontend

React + TypeScript (Vite). A shared `SourceLink` component and a global source
drawer mean *any* number, anywhere in the UI, is one click from its highlighted
origin. Screens mirror the product map: Home, Upload, My Reports, Search,
Comparison, Favorites, Settings; report detail tabs: Overview, Financial
Metrics, Management, Risks, Search, Source View, History.

---

## v0.2.0 — multi-user, history, production storage

New concerns are added as their own packages, each independent of the
extraction pipeline so v0.1.0 behavior is unchanged:

| Concern | Module | Notes |
| --- | --- | --- |
| Authentication | `app/auth` | bcrypt hashing + stateless JWT bearer tokens; `get_current_user` dependency. Stateless tokens suit the split Vercel/Render deploy (no shared session store). |
| Document ownership | `app/api/ownership` | `get_owned_document` gate used by every document-scoped route. Returns 404 (not 403) for another user's id so existence never leaks. |
| Parse history | `app/history` + `ParseSnapshot` | Immutable, versioned JSON snapshot of facts + summary per parse run. |
| Retention | `app/storage` | Caps raw PDFs per user; clears `storage_path`/`raw_available` but keeps all structured data. |
| Preprocessing | `app/ingestion/preprocess` | Hard size check + optional lossless `pikepdf` compression, with fallback to the original. |

**Data-model changes:** new `User` and `ParseSnapshot` tables; `Document`
gains `user_id` (FK, indexed) and `raw_available`, and `storage_path` becomes
nullable. Schema is managed by **Alembic** (`backend/alembic`); `create_all`
remains as an idempotent startup safety net.

**Why raw files are disposable.** The source view is reconstructed from each
page's stored word coordinates (`Page.words_json`), not from the PDF. So
retention can delete the original file while highlights, click-to-jump, facts,
and history all keep working — traceability is preserved without unbounded
raw-file storage on free-tier disk.

**Database URL handling.** `DATABASE_URL` / `FRA_DATABASE_URL` is normalized
(`postgres://` → `postgresql+psycopg://`). Local dev defaults to SQLite; the
same code runs on Postgres in production via env config only.

**Auth transport.** The frontend keeps the `/api/*` pattern; Vercel rewrites it
to Render, so browser calls are same-origin and the JWT travels in the
`Authorization` header (no cross-site cookies).
