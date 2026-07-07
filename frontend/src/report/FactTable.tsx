import { SourceLink, Confidence, ScopeChip } from "../components/ui";
import { useLang } from "../lib/context";
import { factValue } from "../lib/format";
import type { Fact } from "../types";

const BREAKDOWN = new Set(["segment", "geography"]);

/** The bold row label. For a segment/geography breakdown the *scope* (the
 *  business or region name) is what distinguishes the row, so lead with it. */
function primaryLabel(f: Fact, lang: "zh" | "en"): string {
  if (BREAKDOWN.has(f.scope_type) && f.scope_label) return f.scope_label;
  return (lang === "zh" ? f.metric_label || f.metric_name : f.metric_name) || f.metric_name;
}

/** A financial-statement table: one row per metric, fully source-linked.
 *  Units are always shown ("—" when unknown) and each row carries its scope
 *  so repeated labels (e.g. "Revenue") stay unambiguous. */
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
        {facts.map((f) => {
          const primary = primaryLabel(f, lang);
          // Show the raw printed label underneath only when it adds info
          // beyond the bold label already shown.
          const sub = f.raw_label && f.raw_label !== primary ? f.raw_label : null;
          return (
            <tr key={f.id}>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  <strong>{primary}</strong>
                  <ScopeChip scopeType={f.scope_type} scopeLabel={f.scope_label} />
                </div>
                {sub && <div className="muted" style={{ fontSize: 11 }}>{sub}</div>}
              </td>
              <td className="num" style={{ fontWeight: 600 }}>{factValue(f)}</td>
              <td className="muted">{f.unit && f.unit !== "%" ? f.unit : "—"}</td>
              <td><Confidence score={f.confidence_score} /></td>
              <td><SourceLink documentId={f.document_id} source={f.source} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
