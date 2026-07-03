import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { StatusPill } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { reportTypeLabel, t } from "../lib/i18n";
import { formatDate } from "../lib/format";
import type { DocumentSummary } from "../types";

export function Home() {
  const { lang } = useLang();
  const nav = useNavigate();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [seeding, setSeeding] = useState(false);

  const load = () => api.listDocuments().then(setDocs).catch(() => setDocs([]));
  useEffect(() => {
    load();
  }, []);

  const seed = async () => {
    setSeeding(true);
    try {
      const doc = await api.seedSample();
      nav(`/reports/${doc.id}`);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <Layout title={t("home", lang)}>
      <div className="card card-pad" style={{ marginBottom: 20 }}>
        <h3 style={{ margin: "0 0 4px" }}>{lang === "zh" ? "早上好，投资者 👋" : "Welcome, investor 👋"}</h3>
        <div className="muted">{t("traceEvery", lang)}</div>
        <div className="row" style={{ marginTop: 16, flexWrap: "wrap" }}>
          <Link to="/upload" className="btn primary">⬆ {t("upload", lang)}</Link>
          <Link to="/search" className="btn">🔍 {t("search", lang)}</Link>
          <Link to="/compare" className="btn">📊 {t("comparison", lang)}</Link>
          <button className="btn" onClick={seed} disabled={seeding}>
            {seeding ? "…" : `✨ ${t("loadSample", lang)}`}
          </button>
        </div>
      </div>

      <p className="section-title">{lang === "zh" ? "最近打开" : "Recent reports"}</p>
      {docs.length === 0 ? (
        <div className="card empty">
          {t("noData", lang)} · <button className="btn sm" onClick={seed}>{t("loadSample", lang)}</button>
        </div>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
          {docs.slice(0, 9).map((d) => (
            <Link key={d.id} to={`/reports/${d.id}`} className="card card-pad" style={{ color: "inherit" }}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "start" }}>
                <strong>{d.company_name || d.filename}</strong>
                <StatusPill status={d.status} />
              </div>
              <div className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
                {reportTypeLabel(d.report_type, lang)} · {d.report_period || "—"} · {d.language.toUpperCase()}
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
                {d.fact_count} {lang === "zh" ? "项数据" : "facts"} · {d.page_count}p · {formatDate(d.created_at)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  );
}
