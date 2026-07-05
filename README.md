# 财报分析助手 · Financial Report Analyzer

A **stock-research–focused** financial report analysis app. It extracts key
financial and business data from Chinese **and** English company reports,
**preserves source traceability**, and makes every extracted item verifiable
in the original document.

> This is **not** a generic PDF reader. Every number, metric, or conclusion
> points back to its exact location in the source report (page, text snippet,
> table cell, bounding box) with a confidence score.

## Core principles

- **Source-first** — every fact links back to the original report location.
- **Stock-research oriented** — optimized for financial analysis, not reading.
- **Bilingual** — Chinese and English reports, unified into one concept layer.
- **Practical MVP first** — the core workflow before advanced features.
- **Trustworthy** — evidence, source locations, and confidence are always shown.

## Architecture

The product's eight layers map onto backend modules with clean boundaries:

```
Upload ─► Ingestion ─► Parsing / OCR ─► Extraction ─► Normalization
                                                          │
        UI ◄─ API ◄─ Summary/Export ◄─ Search/Compare ◄─ SourceMap
```

| Layer                 | Module                    | Responsibility                                        |
| --------------------- | ------------------------- | ----------------------------------------------------- |
| Document ingestion    | `app/ingestion`           | Store uploads, register documents, orchestrate ingest |
| OCR & parsing         | `app/parsing`             | Digital PDF parse (words+bbox+tables), pluggable OCR   |
| Financial extraction  | `app/extraction`          | Rule-based bilingual metric/business-signal extractors |
| Terminology normalize | `app/normalization`       | CN/EN dictionary → unified internal concept layer      |
| Source mapping        | `app/sourcemap`           | Resolve highlights / bounding boxes for any fact       |
| Search & comparison   | `app/search`              | In-report search, cross-period / cross-company compare |
| Summary & export      | `app/summary`             | Evidence-linked summaries, CSV/JSON export             |
| UI presentation       | `app/api` + `frontend/`   | FastAPI routes + React UI                              |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the phased MVP plan.

## Repository layout

```
backend/     FastAPI service — the extraction engine & source-of-truth data model
frontend/    React + TypeScript (Vite) UI matching the product screens
docs/        Architecture & roadmap
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload            # http://localhost:8000  (docs at /docs)
```

Create an account in the UI (or `POST /api/auth/register`), then the
`POST /api/documents/seed` endpoint ingests a built-in bilingual sample report
into your library so you can explore the full workflow without uploading a file.

Local dev uses SQLite by default. For Postgres locally, set `FRA_DATABASE_URL`
and run `alembic upgrade head` (see below).

### Frontend

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173 (proxies /api → :8000)
```

## v0.2.0 — multi-user

- **Accounts** — email + password registration / login; JWT bearer tokens.
- **Per-user libraries** — every document, fact, summary, search, comparison,
  and parse snapshot belongs to a user; all endpoints are owner-scoped. Another
  user's document returns `404`, never leaks.
- **Parse history** — each parse writes an immutable, versioned `ParseSnapshot`
  (structured facts + summary), so past runs stay reviewable **even after the
  raw PDF is removed**. Source traceability is preserved in every snapshot.
- **PostgreSQL in production** — env-driven `DATABASE_URL` (auto-normalized to
  psycopg); Alembic migrations. SQLite still works for local dev.
- **Retention** — keeps only the newest N raw uploads per user
  (`FRA_MAX_UPLOADS_PER_USER`); structured data is never deleted by cleanup.
- **Upload safety** — hard size cap (`FRA_MAX_UPLOAD_MB`) with a clear 413
  message, plus optional lossless `pikepdf` compression for large PDFs.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FRA_DATABASE_URL` / `DATABASE_URL` | SQLite file | DB connection (Postgres in prod) |
| `FRA_SECRET_KEY` / `SECRET_KEY` | dev placeholder | **JWT signing key — set in prod** |
| `FRA_ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (7 days) |
| `FRA_MAX_UPLOADS_PER_USER` | `10` | Raw-PDF retention cap per user |
| `FRA_MAX_UPLOAD_MB` | `15` | Hard upload size limit |
| `FRA_PREPROCESS_ENABLED` | `true` | Compress large PDFs before parsing |
| `FRA_PREPROCESS_THRESHOLD_MB` | `4` | Only preprocess files larger than this |
| `FRA_CORS_ORIGINS` | localhost + vercel | Allowed browser origins (comma-sep) |

See [`backend/.env.example`](backend/.env.example) for the full list.

### Migrations

```bash
cd backend
alembic upgrade head          # apply migrations (uses FRA_DATABASE_URL/DATABASE_URL)
alembic revision --autogenerate -m "describe change"   # after model changes
```

`create_all` also runs on startup as an idempotent safety net, so a fresh
database is usable even before migrations are applied.

### Deployment

- **Backend (Render):** [`render.yaml`](render.yaml) provisions free Postgres +
  a web service; start command runs `alembic upgrade head` then uvicorn.
  Install with the `postgres` extra: `pip install -e '.[postgres,preprocess]'`.
- **Frontend (Vercel):** [`frontend/vercel.json`](frontend/vercel.json) rewrites
  `/api/*` to the Render backend, keeping the `/api` contract and making browser
  requests same-origin.

## Data model — every extracted fact carries

`company_name · report_type · report_period · metric_name · metric_value ·
unit · language · source_page_number · source_text_snippet · source_bbox ·
source_table_cell_reference · confidence_score · extraction_timestamp ·
version_id`

## Status

**v0.2.0** — multi-user, source-traceable financial report analysis:
accounts + per-user libraries, versioned parse history, PostgreSQL + Alembic,
per-user raw-file retention, and upload size/preprocessing safeguards — on top
of the v0.1.0 pipeline (upload → parse → extract with traceability →
view/search/compare/export). OCR for scanned PDFs remains a pluggable interface
with graceful fallback. See the roadmap for what's next.
