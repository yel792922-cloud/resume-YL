import { useEffect, useState } from "react";
import { SourceLink, Confidence } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { factValueWithUnit, formatDate } from "../lib/format";
import type { SnapshotDetail, SnapshotSummary } from "../types";

/** Historical parse runs: pick a version to inspect its structured snapshot. */
export function HistoryPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const [snaps, setSnaps] = useState<SnapshotSummary[]>([]);
  const [active, setActive] = useState<SnapshotDetail | null>(null);

  useEffect(() => {
    api.getHistory(documentId).then((s) => {
      setSnaps(s);
      if (s[0]) api.getSnapshot(documentId, s[0].version).then(setActive);
    });
  }, [documentId]);

  const pick = (version: number) => api.getSnapshot(documentId, version).then(setActive);

  if (snaps.length === 0) return <div className="card empty">{lang === "zh" ? "暂无解析历史" : "No parse history yet"}</div>;

  return (
    <div className="row" style={{ alignItems: "start", gap: 20, flexWrap: "wrap" }}>
      <div className="card card-pad" style={{ width: 220 }}>
        <p className="section-title">{lang === "zh" ? "解析版本" : "Parse versions"}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {snaps.map((s) => (
            <button
              key={s.version}
              className={`btn sm ${active?.version === s.version ? "primary" : "ghost"}`}
              style={{ justifyContent: "space-between" }}
              onClick={() => pick(s.version)}
            >
              <span>v{s.version}</span>
              <span style={{ fontSize: 11, opacity: 0.8 }}>{s.fact_count} · {formatDate(s.created_at)}</span>
            </button>
          ))}
        </div>
        <div className="muted" style={{ fontSize: 11, marginTop: 12 }}>
          {lang === "zh"
            ? "结构化解析结果长期保存，即使原始 PDF 已按保留策略清理。"
            : "Structured results are kept long-term, even after the raw PDF is cleaned up."}
        </div>
      </div>

      <div className="card" style={{ flex: 1, minWidth: 320 }}>
        {active && (
          <>
            <div className="card-pad" style={{ paddingBottom: 0 }}>
              <p className="section-title">
                v{active.version} · {active.fact_count} {lang === "zh" ? "项数据" : "facts"} · {formatDate(active.created_at)}
                {active.note ? ` · ${active.note}` : ""}
              </p>
            </div>
            <table className="fin">
              <thead>
                <tr>
                  <th>{lang === "zh" ? "指标" : "Metric"}</th>
                  <th className="num">{lang === "zh" ? "数值" : "Value"}</th>
                  <th>{lang === "zh" ? "置信度" : "Confidence"}</th>
                  <th>{lang === "zh" ? "原文" : "Source"}</th>
                </tr>
              </thead>
              <tbody>
                {active.facts
                  .filter((f) => f.concept_id)
                  .map((f) => (
                    <tr key={f.id}>
                      <td><strong>{lang === "zh" ? f.metric_label || f.metric_name : f.metric_name}</strong></td>
                      <td className="num">{factValueWithUnit(f)}</td>
                      <td><Confidence score={f.confidence_score} /></td>
                      <td><SourceLink documentId={documentId} source={f.source} /></td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
