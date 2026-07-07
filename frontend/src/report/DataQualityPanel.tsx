import { PanelStates, Collapsible } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { useAsync } from "../lib/async";
import { t, type Lang } from "../lib/i18n";
import type { CleaningAuditEntry } from "../types";

// Active cleaning-rule ids (from the API) → localized label.
const RULE_LABEL: Record<string, "ruleBoilerplate" | "ruleOcrGarbage" | "ruleLowInformation" | "ruleMinConfidence" | "ruleDedup" | "ruleUnitNormalization"> = {
  boilerplate: "ruleBoilerplate",
  ocr_garbage: "ruleOcrGarbage",
  low_information: "ruleLowInformation",
  min_confidence: "ruleMinConfidence",
  dedup: "ruleDedup",
  unit_normalization: "ruleUnitNormalization",
};

// Reason category used to *group* filtered items, so the audit reads as a few
// labelled buckets instead of one long noisy list.
type ReasonKey = "duplicate" | "ocr" | "confidence" | "boilerplate" | "lowinfo" | "other";
function reasonKey(entry: CleaningAuditEntry): ReasonKey {
  const r = entry.reason.toLowerCase();
  if (entry.action === "deduped" || r.includes("duplicate")) return "duplicate";
  if (r.includes("ocr")) return "ocr";
  if (r.includes("confidence")) return "confidence";
  if (r.includes("page-number") || r.includes("header") || r.includes("boilerplate")) return "boilerplate";
  if (r.includes("low-information")) return "lowinfo";
  return "other";
}
const REASON_META: Record<ReasonKey, { cls: string; zh: string; en: string }> = {
  duplicate: { cls: "gray", zh: "重复（同口径/期间）", en: "Duplicate (same scope/period)" },
  ocr: { cls: "amber", zh: "OCR 噪声", en: "OCR noise" },
  confidence: { cls: "amber", zh: "低置信度", en: "Low confidence" },
  boilerplate: { cls: "gray", zh: "模板 / 页眉页脚 / 页码", en: "Boilerplate / header / page no." },
  lowinfo: { cls: "gray", zh: "低信息量", en: "Low-information" },
  other: { cls: "gray", zh: "其他", en: "Other" },
};

function StatTile({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="card card-pad" style={{ flex: "1 1 130px", minWidth: 120 }}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 650, marginTop: 4, color: accent }}>{value}</div>
    </div>
  );
}

/** One filtered item as evidence: page + snippet + reason + confidence. */
function ExceptionRow({ entry, lang }: { entry: CleaningAuditEntry; lang: Lang }) {
  const snippet = entry.snippet || entry.metric_name || "—";
  return (
    <li style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
      <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 3 }}>
        {entry.page_number != null && (
          <span className="pill blue" style={{ fontSize: 11 }}>{t("onPage", lang, { n: entry.page_number })}</span>
        )}
        {entry.report_section && <span className="muted" style={{ fontSize: 11 }}>{entry.report_section}</span>}
        {entry.confidence != null && (
          <span className="muted" style={{ fontSize: 11 }}>· {Math.round(entry.confidence * 100)}%</span>
        )}
      </div>
      <div className="snippet" style={{ fontSize: 12.5 }} title={snippet}>{snippet}</div>
      {entry.detail && <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{entry.detail}</div>}
    </li>
  );
}

/** Data Quality: an evidence-centric, layered view of the cleaning pass —
 *  which rules ran, the high-level counts, and filtered items grouped by reason
 *  with their page + snippet + reason so users see *what* and *why*. */
export function DataQualityPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const { data, loading, error, reload } = useAsync(() => api.getCleaned(documentId), [documentId]);

  return (
    <PanelStates loading={loading} error={error} onRetry={reload}>
      {data && (() => {
        const { retained, removed, deduped, normalized } = data.stats;
        const filtered = removed + deduped;
        const total = retained + filtered;
        const rate = total > 0 ? Math.round((filtered / total) * 100) : 0;

        const filteredEntries = data.audit.filter((a) => a.action === "removed" || a.action === "deduped");
        const normalizedEntries = data.audit.filter((a) => a.action === "normalized");

        // Group filtered items by reason category (largest group first).
        const groups = new Map<ReasonKey, CleaningAuditEntry[]>();
        for (const e of filteredEntries) {
          const k = reasonKey(e);
          (groups.get(k) ?? groups.set(k, []).get(k)!).push(e);
        }
        const orderedGroups = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);

        return (
          <div className="grid" style={{ gap: 20 }}>
            {/* Layer 1 — high-level counts. */}
            <div className="row" style={{ flexWrap: "wrap", gap: 14 }}>
              <StatTile label={t("totalExtracted", lang)} value={String(total)} />
              <StatTile label={t("retained", lang)} value={String(retained)} accent="var(--up)" />
              <StatTile label={t("filtered", lang)} value={String(filtered)} accent={filtered ? "var(--warn)" : undefined} />
              <StatTile label={t("cleaningRate", lang)} value={`${rate}%`} />
            </div>

            {/* Layer 2 — which rules are in effect. */}
            {data.rules.length > 0 && (
              <div className="card card-pad">
                <p className="section-title" style={{ margin: "0 0 10px" }}>{t("cleaningRules", lang)}</p>
                <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                  {data.rules.map((r) => (
                    <span key={r} className="pill gray" style={{ fontSize: 11.5 }}>
                      {RULE_LABEL[r] ? t(RULE_LABEL[r], lang) : r}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Layer 3 — filtered items grouped by reason (evidence per item). */}
            <div className="card card-pad">
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <p className="section-title" style={{ margin: 0 }}>{t("groupedExceptions", lang)}</p>
                {normalized > 0 && <span className="muted" style={{ fontSize: 12 }}>{normalized} {t("normalized", lang)}</span>}
              </div>

              {filtered === 0 ? (
                <div className="pill green" style={{ whiteSpace: "normal" }}>✓ {t("noNoise", lang)}</div>
              ) : (
                <div className="grid" style={{ gap: 10 }}>
                  {orderedGroups.map(([key, entries], gi) => {
                    const meta = REASON_META[key];
                    return (
                      <Collapsible
                        key={key}
                        title={`${lang === "zh" ? meta.zh : meta.en}`}
                        count={entries.length}
                        defaultOpen={gi === 0}
                      >
                        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                          {entries.map((e, i) => <ExceptionRow key={i} entry={e} lang={lang} />)}
                        </ul>
                      </Collapsible>
                    );
                  })}
                </div>
              )}

              {normalizedEntries.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <Collapsible title={t("ruleUnitNormalization", lang)} count={normalizedEntries.length}>
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

            <div className="muted" style={{ fontSize: 12 }}>{t("cleaningNote", lang)} {t("retainedNote", lang)}</div>
          </div>
        );
      })()}
    </PanelStates>
  );
}
