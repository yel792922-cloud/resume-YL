import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { SourceLink, ModeToggle } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { useMode } from "../lib/mode";
import { t } from "../lib/i18n";
import { factValue } from "../lib/format";
import type { CompareResponse, DocumentSummary } from "../types";

export function Comparison() {
  const { lang } = useLang();
  const { mode } = useMode();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [dimension, setDimension] = useState<"period" | "company">("period");
  const [result, setResult] = useState<CompareResponse | null>(null);

  useEffect(() => {
    api.listDocuments().then((d) => setDocs(d.filter((x) => x.status === "ready")));
  }, []);

  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  useEffect(() => {
    if (selected.length >= 1) api.compare(selected, dimension, mode).then(setResult);
    else setResult(null);
  }, [selected, dimension, mode]);

  return (
    <Layout title={t("comparison", lang)}>
      <div className="card card-pad" style={{ marginBottom: 18 }}>
        <p className="section-title">{lang === "zh" ? "选择报告（可多选，支持跨期 / 跨公司）" : "Select reports (period / company)"}</p>
        <div className="row" style={{ flexWrap: "wrap", marginBottom: 14 }}>
          {docs.map((d) => (
            <button
              key={d.id}
              className={`btn sm ${selected.includes(d.id) ? "primary" : ""}`}
              onClick={() => toggle(d.id)}
            >
              {d.company_name || d.filename} · {d.report_period}
            </button>
          ))}
          {docs.length === 0 && <span className="muted">{t("noData", lang)}</span>}
        </div>
        <div className="row" style={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div className="row" style={{ alignItems: "center" }}>
            <span className="muted">{lang === "zh" ? "对比维度：" : "Dimension:"}</span>
            <select value={dimension} onChange={(e) => setDimension(e.target.value as "period" | "company")}>
              <option value="period">{lang === "zh" ? "纵向 · 按报告期" : "By period"}</option>
              <option value="company">{lang === "zh" ? "横向 · 按公司" : "By company"}</option>
            </select>
          </div>
          <ModeToggle />
        </div>
      </div>

      {result && result.rows.length > 0 ? (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="fin">
            <thead>
              <tr>
                <th>{lang === "zh" ? "指标" : "Metric"}</th>
                {result.columns.map((c, i) => (
                  <th key={i} className="num">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((r) => (
                <tr key={r.concept_id}>
                  <td>
                    <strong>{lang === "zh" ? r.metric_label : r.metric_name}</strong>
                    {r.unit && r.unit !== "%" && <span className="muted" style={{ fontSize: 11 }}> ({r.unit})</span>}
                  </td>
                  {r.cells.map((cell, i) => (
                    <td key={i} className="num">
                      {cell.fact ? (
                        <div style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                          {factValue(cell.fact)}
                          <SourceLink documentId={cell.document_id} source={cell.fact.source} label="◎" />
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card empty">{lang === "zh" ? "选择至少一份报告以开始对比" : "Select at least one report to compare"}</div>
      )}
    </Layout>
  );
}
