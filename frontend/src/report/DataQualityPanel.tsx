import { useState } from "react";
import { PanelStates, Collapsible } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { useAsync } from "../lib/async";
import { t, type Lang } from "../lib/i18n";
import type { CleaningAuditEntry } from "../types";

// Map a backend cleaning reason to a friendly bilingual label + pill color.
function reasonMeta(entry: CleaningAuditEntry, lang: Lang): { label: string; cls: string } {
  const r = entry.reason.toLowerCase();
  const pick = (zh: string, en: string, cls: string) => ({ label: lang === "zh" ? zh : en, cls });
  if (entry.action === "deduped" || r.includes("duplicate")) return pick("重复", "Duplicate", "gray");
  if (r.includes("ocr")) return pick("OCR 噪声", "OCR noise", "amber");
  if (r.includes("confidence")) return pick("低置信度", "Low confidence", "amber");
  if (r.includes("page-number") || r.includes("header") || r.includes("boilerplate"))
    return pick("模板 / 页眉页脚", "Boilerplate / header", "gray");
  if (r.includes("low-information")) return pick("低信息量", "Low-information", "gray");
  if (r.includes("unit")) return pick("单位规范化", "Unit normalized", "blue");
  return pick(entry.reason, entry.reason, "gray");
}

function StatTile({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="card card-pad" style={{ flex: "1 1 130px", minWidth: 120 }}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 650, marginTop: 4, color: accent }}>{value}</div>
    </div>
  );
}

function FilteredRow({ entry, lang }: { entry: CleaningAuditEntry; lang: Lang }) {
  const meta = reasonMeta(entry, lang);
  const original = entry.snippet || entry.metric_name || "—";
  return (
    <li className="row" style={{ justifyContent: "space-between", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--line)", alignItems: "start" }}>
      <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={original}>
        {original}
      </span>
      <span className={`pill ${meta.cls}`} style={{ flexShrink: 0 }}>{meta.label}</span>
    </li>
  );
}

/** Data Quality: how much noise cleaning removed, and exactly what + why. */
export function DataQualityPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const { data, loading, error, reload } = useAsync(() => api.getCleaned(documentId), [documentId]);
  const [expanded, setExpanded] = useState(false);

  return (
    <PanelStates loading={loading} error={error} onRetry={reload}>
      {data && (
        <div className="grid" style={{ gap: 20 }}>
          {(() => {
            const { retained, removed, deduped, normalized } = data.stats;
            const filtered = removed + deduped;
            const total = retained + filtered;
            const rate = total > 0 ? Math.round((filtered / total) * 100) : 0;
            const filteredEntries = data.audit.filter((a) => a.action === "removed" || a.action === "deduped");
            const normalizedEntries = data.audit.filter((a) => a.action === "normalized");
            const VISIBLE = 6;
            const shown = expanded ? filteredEntries : filteredEntries.slice(0, VISIBLE);
            return (
              <>
                <div className="row" style={{ flexWrap: "wrap", gap: 14 }}>
                  <StatTile label={t("totalExtracted", lang)} value={String(total)} />
                  <StatTile label={t("retained", lang)} value={String(retained)} accent="var(--up)" />
                  <StatTile label={t("filtered", lang)} value={String(filtered)} accent={filtered ? "var(--warn)" : undefined} />
                  <StatTile label={t("cleaningRate", lang)} value={`${rate}%`} />
                </div>

                <div className="card card-pad">
                  <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <p className="section-title" style={{ margin: 0 }}>{t("filteredItems", lang)}</p>
                    {normalized > 0 && (
                      <span className="muted" style={{ fontSize: 12 }}>
                        {normalized} {t("normalized", lang)}
                      </span>
                    )}
                  </div>

                  {filtered === 0 ? (
                    <div className="pill green" style={{ whiteSpace: "normal" }}>✓ {t("noNoise", lang)}</div>
                  ) : (
                    <>
                      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                        {shown.map((e, i) => <FilteredRow key={i} entry={e} lang={lang} />)}
                      </ul>
                      {filteredEntries.length > VISIBLE && (
                        <button className="btn ghost sm" style={{ marginTop: 10 }} onClick={() => setExpanded((v) => !v)} aria-expanded={expanded}>
                          {expanded ? t("showLess", lang) : `${t("showAll", lang)} (${filteredEntries.length})`}
                        </button>
                      )}
                    </>
                  )}

                  {normalizedEntries.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                      <Collapsible title={t("normalized", lang)} count={normalizedEntries.length}>
                        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                          {normalizedEntries.map((e, i) => (
                            <li key={i} className="muted" style={{ fontSize: 12.5, padding: "5px 0", borderBottom: "1px solid var(--line)" }}>
                              {e.metric_name || e.concept_id}: {e.detail}
                            </li>
                          ))}
                        </ul>
                      </Collapsible>
                    </div>
                  )}
                </div>

                <div className="muted" style={{ fontSize: 12 }}>{t("cleaningNote", lang)}</div>
              </>
            );
          })()}
        </div>
      )}
    </PanelStates>
  );
}
