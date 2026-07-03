# Roadmap

Built in phases, core workflow first (per the product's MVP priorities).

## ✅ MVP (done)

Implemented priorities 1–7:

1. **Data models first** — `Document`, `Page`, `ExtractedFact` with full
   traceability; bilingual concept dictionary.
2. **Ingestion & parsing** — pdfplumber digital parse (words + bbox + tables);
   pluggable OCR interface with graceful fallback for scanned PDFs.
3. **Source mapping / highlight** — snippet/cell → bounding box; click-to-jump.
4. **Extraction pipeline** — table → text → section extractors; income
   statement, balance sheet, cash flow, business signals, guidance, risks;
   derived gross margin; report identity detection.
5. **Report detail UI** — Overview, Financial Metrics, Management, Risks,
   Search, Source View; every value source-linked with confidence.
6. **Search & comparison** — bilingual in-report search; cross-period /
   cross-company metric matrix, every cell source-linked.
7. **Summary & export** — evidence-linked summary; CSV / JSON export carrying
   the full per-fact traceability.

Verified end to end: `pytest` (backend pipeline), production `tsc`/Vite build,
and a live uvicorn + Vite run with UI screenshots of the source-jump flow.

## 🔜 Next (priority 8: polish & advanced analytics)

- **OCR in production** — ship the tesseract backend image (`chi_sim`, `eng`);
  add layout-aware OCR for tables in scanned reports.
- **Multi-column periods** — persist every period column per fact (not just the
  current period) for richer in-document trend rows.
- **Exact table-cell geometry** — replace the uniform cell-bbox approximation
  with pdfplumber's per-cell coordinates for pixel-accurate highlights.
- **Async ingestion** — move parse+extract to a background task/queue with live
  status polling for large reports.
- **Units & FX normalization** — normalize 亿/万/million into a canonical scale
  and optional currency conversion (source value always preserved).
- **Confidence model** — calibrate scores; flag low-confidence facts for review.
- **ML-assisted extraction** — plug an extractor behind `FactDraft` for
  narrative metrics and segment tables, keeping deterministic facts primary.
- **Auth & multi-user**, watchlists, saved comparisons, PDF/Markdown export of
  the research summary.
