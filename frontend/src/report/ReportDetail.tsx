import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { MetricCard, SourceLink, StatusPill } from "../components/ui";
import { FactTable } from "./FactTable";
import { SearchPanel } from "./SearchPanel";
import { SourceBrowser } from "./SourceBrowser";
import { HistoryPanel } from "./HistoryPanel";
import { api } from "../api/client";
import { useLang, useSource } from "../lib/context";
import { categoryLabel, reportTypeLabel, t } from "../lib/i18n";
import type { DocumentDetail, Fact, FactCategory, ReportSummary } from "../types";

// Analytics panels are code-split — loaded only when their tab is opened.
const ForecastPanel = lazy(() => import("./ForecastPanel").then((m) => ({ default: m.ForecastPanel })));
const DataQualityPanel = lazy(() => import("./DataQualityPanel").then((m) => ({ default: m.DataQualityPanel })));
const QAPanel = lazy(() => import("./QAPanel").then((m) => ({ default: m.QAPanel })));

type Tab =
  | "overview" | "ask" | "financials" | "forecast" | "management"
  | "risks" | "search" | "source" | "quality" | "history";

export function ReportDetail() {
  const { id = "" } = useParams();
  const { lang } = useLang();
  const { open } = useSource();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [tab, setTab] = useState<Tab>("overview");

  useEffect(() => {
    api.getDocument(id).then(setDoc);
    api.getFacts(id).then(setFacts);
    api.getSummary(id).then(setSummary).catch(() => setSummary(null));
  }, [id]);

  const byCat = useMemo(() => {
    const m: Record<string, Fact[]> = {};
    for (const f of facts) (m[f.category] ??= []).push(f);
    return m;
  }, [facts]);

  if (!doc) return <Layout title="…"><div className="center"><div className="spinner" /></div></Layout>;

  const cat = (c: FactCategory) => byCat[c] ?? [];

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: t("overview", lang) },
    { key: "ask", label: t("ask", lang) },
    { key: "financials", label: t("metrics", lang) },
    { key: "forecast", label: t("forecast", lang) },
    { key: "management", label: t("management", lang) },
    { key: "risks", label: t("risks", lang) },
    { key: "search", label: t("search", lang) },
    { key: "source", label: t("sourceView", lang) },
    { key: "quality", label: t("dataQuality", lang) },
    { key: "history", label: lang === "zh" ? `历史 (${doc.version_count})` : `History (${doc.version_count})` },
  ];

  const lazyFallback = <div className="center"><div className="spinner" role="status" aria-label="Loading" /></div>;

  const exportFile = (fmt: "csv" | "json") =>
    api.downloadExport(id, fmt, `${(doc.company_name || doc.filename).replace(/\s+/g, "_")}_facts.${fmt}`);

  return (
    <Layout
      title={doc.company_name || doc.filename}
      actions={
        <>
          <button className="btn sm" onClick={() => exportFile("csv")}>⬇ CSV</button>
          <button className="btn sm" onClick={() => exportFile("json")}>⬇ JSON</button>
        </>
      }
    >
      <div className="row" style={{ alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <Link to="/reports" className="btn ghost sm">← {t("myReports", lang)}</Link>
        <span className="pill blue">{reportTypeLabel(doc.report_type, lang)}</span>
        <span className="pill gray">{doc.report_period || "—"}</span>
        <span className="pill gray">{doc.language.toUpperCase()}</span>
        <span className="pill gray">{doc.page_count}p</span>
        <StatusPill status={doc.status} />
        {!doc.raw_available && (
          <span className="pill amber" title={lang === "zh" ? "原始 PDF 已按保留策略清理，结构化数据与原文定位仍完整保留" : "Raw PDF removed by retention policy; structured data & source view preserved"}>
            {lang === "zh" ? "原文件已清理" : "raw cleaned"}
          </span>
        )}
        <span className="muted" style={{ fontSize: 12 }}>{facts.length} {lang === "zh" ? "项可追溯数据" : "traceable facts"}</span>
      </div>

      <div className="tabs">
        {tabs.map((tb) => (
          <button key={tb.key} className={`tab ${tab === tb.key ? "active" : ""}`} onClick={() => setTab(tb.key)}>
            {tb.label}
          </button>
        ))}
      </div>

      {tab === "overview" && summary && (
        <div className="grid" style={{ gap: 22 }}>
          <div>
            <p className="section-title">{t("headlineMetrics", lang)}</p>
            <div className="metric-grid">
              {summary.headline_metrics.map((f) => <MetricCard key={f.id} fact={f} />)}
            </div>
          </div>
          <div className="row" style={{ alignItems: "start", flexWrap: "wrap" }}>
            <div className="card card-pad" style={{ flex: "1 1 340px" }}>
              <p className="section-title">{t("smartSummary", lang)}</p>
              {summary.highlights.map((h, i) => (
                <div key={i} className="row" style={{ justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--line)" }}>
                  <span>· {h.text}</span>
                  {h.source && <SourceLink documentId={id} source={h.source} />}
                </div>
              ))}
              {summary.highlights.length === 0 && <span className="muted">{t("noData", lang)}</span>}
            </div>
            <div className="card card-pad" style={{ flex: "1 1 300px" }}>
              <p className="section-title">{t("risks", lang)}</p>
              {summary.risks.map((r, i) => (
                <div key={i} className="row" style={{ justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--line)" }}>
                  <span style={{ color: "var(--down)" }}>⚠ {r.text}</span>
                  {r.source && <SourceLink documentId={id} source={r.source} />}
                </div>
              ))}
              {summary.risks.length === 0 && <span className="muted">{t("noData", lang)}</span>}
            </div>
          </div>
        </div>
      )}

      {tab === "financials" && (
        <div className="grid" style={{ gap: 22 }}>
          {(["income_statement", "balance_sheet", "cash_flow", "business"] as FactCategory[]).map((c) =>
            cat(c).length ? (
              <div key={c} className="card">
                <div className="card-pad" style={{ paddingBottom: 0 }}><p className="section-title">{categoryLabel(c, lang)}</p></div>
                <FactTable facts={cat(c)} />
              </div>
            ) : null
          )}
        </div>
      )}

      {tab === "management" && (
        <div className="grid">
          {[...cat("management"), ...cat("guidance")].map((f) => (
            <div key={f.id} className="card card-pad">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="pill blue">{categoryLabel(f.category, lang)}</span>
                <SourceLink documentId={id} source={f.source} />
              </div>
              <div className="snippet" style={{ marginTop: 10 }}>{f.value_text}</div>
            </div>
          ))}
          {cat("management").length + cat("guidance").length === 0 && <div className="card empty">{t("noData", lang)}</div>}
        </div>
      )}

      {tab === "risks" && (
        <div className="grid">
          {cat("risk").map((f) => (
            <div key={f.id} className="card card-pad" onClick={() => open(id, f.source)} style={{ cursor: "pointer" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="pill red">⚠ {t("risks", lang)}</span>
                <SourceLink documentId={id} source={f.source} />
              </div>
              <div style={{ marginTop: 8 }}>{f.value_text}</div>
            </div>
          ))}
          {cat("risk").length === 0 && <div className="card empty">{t("noData", lang)}</div>}
        </div>
      )}

      {tab === "ask" && (
        <Suspense fallback={lazyFallback}><QAPanel documentId={id} /></Suspense>
      )}

      {tab === "forecast" && (
        <Suspense fallback={lazyFallback}><ForecastPanel documentId={id} /></Suspense>
      )}

      {tab === "search" && <div className="card card-pad"><SearchPanel documentId={id} /></div>}

      {tab === "source" && <SourceBrowser documentId={id} pages={doc.pages} />}

      {tab === "quality" && (
        <Suspense fallback={lazyFallback}><DataQualityPanel documentId={id} /></Suspense>
      )}

      {tab === "history" && <HistoryPanel documentId={id} />}
    </Layout>
  );
}
