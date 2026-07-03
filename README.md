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

The API ships with a `POST /api/documents/seed` endpoint that ingests a
built-in bilingual sample report so you can explore the full workflow without
uploading a file.

### Frontend

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

## Data model — every extracted fact carries

`company_name · report_type · report_period · metric_name · metric_value ·
unit · language · source_page_number · source_text_snippet · source_bbox ·
source_table_cell_reference · confidence_score · extraction_timestamp ·
version_id`

## Status

MVP skeleton with a working end-to-end pipeline for **digital** PDFs
(upload → parse → extract with traceability → view/search/compare → export).
OCR for scanned PDFs is a pluggable interface with a graceful fallback.
See the roadmap for what's next.
