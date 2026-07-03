import { useState } from "react";
import { api } from "../api/client";
import { SourceLink, Confidence } from "../components/ui";
import { useLang } from "../lib/context";
import { categoryLabel } from "../lib/i18n";
import { factValueWithUnit } from "../lib/format";
import type { SearchResponse } from "../types";

const SUGGESTIONS = ["毛利率", "营业收入", "net profit", "现金流", "risk", "guidance"];

export function SearchPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const [q, setQ] = useState("");
  const [res, setRes] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (query: string) => {
    const term = query.trim();
    if (!term) return;
    setLoading(true);
    try {
      setRes(await api.search(documentId, term));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="row" style={{ marginBottom: 12 }}>
        <input
          style={{ flex: 1 }}
          value={q}
          placeholder={lang === "zh" ? "搜索财报 / 指标 / 关键词…" : "Search metrics, keywords…"}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(q)}
        />
        <button className="btn primary" onClick={() => run(q)}>{lang === "zh" ? "搜索" : "Search"}</button>
      </div>
      <div className="row" style={{ flexWrap: "wrap", marginBottom: 16 }}>
        {SUGGESTIONS.map((s) => (
          <button key={s} className="pill gray" style={{ border: "none" }} onClick={() => { setQ(s); run(s); }}>{s}</button>
        ))}
      </div>

      {loading && <div className="center"><div className="spinner" /></div>}

      {res && (
        <>
          <div className="muted" style={{ marginBottom: 10, fontSize: 12.5 }}>
            {lang === "zh" ? `找到 ${res.total} 条结果` : `${res.total} results`} · “{res.query}”
          </div>
          <div className="grid">
            {res.hits.map((h, i) => (
              <div key={i} className="card card-pad">
                <div className="row" style={{ justifyContent: "space-between", alignItems: "start" }}>
                  <div style={{ minWidth: 0 }}>
                    {h.fact ? (
                      <>
                        <strong>
                          {lang === "zh" ? h.fact.metric_label || h.fact.metric_name : h.fact.metric_name}
                          {" · "}
                          {factValueWithUnit(h.fact)}
                        </strong>
                        <span className="pill blue" style={{ marginLeft: 8 }}>{categoryLabel(h.fact.category, lang)}</span>
                      </>
                    ) : (
                      <span className="pill gray">{lang === "zh" ? "原文" : "text"}</span>
                    )}
                    <div className="snippet" style={{ marginTop: 8 }}>{h.snippet}</div>
                  </div>
                  <div style={{ textAlign: "right", whiteSpace: "nowrap", marginLeft: 12 }}>
                    {h.fact && <div style={{ marginBottom: 6 }}><Confidence score={h.fact.confidence_score} /></div>}
                    <SourceLink
                      documentId={documentId}
                      source={h.fact ? h.fact.source : { page_number: h.page_number, section: h.section, snippet: h.snippet, bbox: h.bbox, table_cell: null }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          {res.hits.length === 0 && <div className="empty">{lang === "zh" ? "未找到结果" : "No results"}</div>}
        </>
      )}
    </div>
  );
}
