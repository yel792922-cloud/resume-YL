import { SourceLink, Confidence } from "../components/ui";
import { useLang } from "../lib/context";
import { factValue } from "../lib/format";
import type { Fact } from "../types";

/** A financial-statement table: one row per metric, fully source-linked. */
export function FactTable({ facts }: { facts: Fact[] }) {
  const { lang } = useLang();
  if (facts.length === 0) return <div className="empty">{lang === "zh" ? "本表暂无提取数据" : "No data extracted for this statement"}</div>;
  return (
    <table className="fin">
      <thead>
        <tr>
          <th>{lang === "zh" ? "项目" : "Item"}</th>
          <th className="num">{lang === "zh" ? "数值" : "Value"}</th>
          <th>{lang === "zh" ? "单位" : "Unit"}</th>
          <th>{lang === "zh" ? "置信度" : "Confidence"}</th>
          <th>{lang === "zh" ? "原文" : "Source"}</th>
        </tr>
      </thead>
      <tbody>
        {facts.map((f) => (
          <tr key={f.id}>
            <td>
              <strong>{lang === "zh" ? f.metric_label || f.metric_name : f.metric_name}</strong>
              {f.raw_label && <div className="muted" style={{ fontSize: 11 }}>{f.raw_label}</div>}
            </td>
            <td className="num" style={{ fontWeight: 600 }}>{factValue(f)}</td>
            <td className="muted">{f.unit && f.unit !== "%" ? f.unit : "—"}</td>
            <td><Confidence score={f.confidence_score} /></td>
            <td><SourceLink documentId={f.document_id} source={f.source} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
