import { useMemo, useState } from "react";
import { ConfidenceBadge, Collapsible, PanelStates, SourceLink } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { useMode } from "../lib/mode";
import { useAsync } from "../lib/async";
import { t, type Lang } from "../lib/i18n";
import type {
  ConfidenceLevel,
  ForecastMetric,
  ForecastResponse,
  ScenarioForecast,
  ScenarioName,
} from "../types";

const BASE_SCENARIOS: ScenarioName[] = ["base", "bull", "bear"];
const SCENARIO_META: Record<ScenarioName, { cls: string; key: "scenarioBase" | "scenarioBull" | "scenarioBear" | "scenarioCustom" }> = {
  base: { cls: "blue", key: "scenarioBase" },
  bull: { cls: "green", key: "scenarioBull" },
  bear: { cls: "red", key: "scenarioBear" },
  custom: { cls: "amber", key: "scenarioCustom" },
};
const LEVEL_ORDER: Record<ConfidenceLevel, number> = { low: 0, medium: 1, high: 2 };

const ARROW: Record<string, { sym: string; color: string }> = {
  up: { sym: "▲", color: "var(--up)" },
  down: { sym: "▼", color: "var(--down)" },
  flat: { sym: "▬", color: "var(--ink-soft)" },
};

function metricLabel(m: ForecastMetric, lang: Lang): string {
  const name = lang === "zh" ? m.metric_label || m.metric_name : m.metric_name;
  return m.unit && m.unit !== "%" ? `${name} (${m.unit})` : name;
}

function fmtValue(v: number, isPercent: boolean): string {
  if (isPercent) return `${v.toFixed(1)}%`;
  return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function fmtGrowth(s: ScenarioForecast, isPercent: boolean): string {
  if (s.growth_pct == null) return "—";
  const sign = s.growth_pct >= 0 ? "+" : "";
  return isPercent ? `${sign}${s.growth_pct.toFixed(1)}pp` : `${sign}${s.growth_pct.toFixed(1)}%`;
}

function scenarioOf(m: ForecastMetric, name: ScenarioName): ScenarioForecast | undefined {
  return m.scenarios.find((s) => s.scenario === name);
}

function scenarioConfidence(metrics: ForecastMetric[], name: ScenarioName): ConfidenceLevel {
  const levels = metrics.map((m) => scenarioOf(m, name)?.confidence).filter(Boolean) as ConfidenceLevel[];
  if (!levels.length) return "low";
  return levels.reduce((min, l) => (LEVEL_ORDER[l] < LEVEL_ORDER[min] ? l : min), "high" as ConfidenceLevel);
}

function ScenarioCard({ data, name }: { data: ForecastResponse; name: ScenarioName }) {
  const { lang } = useLang();
  const meta = SCENARIO_META[name];
  const headline = data.metrics.find((m) => m.concept_id === "revenue") ?? data.metrics[0];
  const hs = headline ? scenarioOf(headline, name) : undefined;
  const tagline = hs?.assumptions?.[hs.assumptions.length - 1] ?? "";

  return (
    <div className="card card-pad" style={{ flex: "1 1 200px", minWidth: 190 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span className={`pill ${meta.cls}`}>{t(meta.key, lang)}</span>
        <ConfidenceBadge level={scenarioConfidence(data.metrics, name)} />
      </div>
      <div className="muted" style={{ fontSize: 12 }}>{t("horizon", lang)}: {data.forecast_period}</div>
      {headline && hs && (
        <div style={{ marginTop: 8 }}>
          <div className="muted" style={{ fontSize: 11 }}>{t("expectedTrend", lang)}</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>
            {lang === "zh" ? headline.metric_label || headline.metric_name : headline.metric_name}{" "}
            <span style={{ color: ARROW[hs.direction].color }}>{ARROW[hs.direction].sym} {fmtGrowth(hs, headline.is_percent)}</span>
          </div>
        </div>
      )}
      {tagline && (
        <div style={{ marginTop: 8 }}>
          <div className="muted" style={{ fontSize: 11 }}>{t("assumptions", lang)}</div>
          <div style={{ fontSize: 12.5 }}>{tagline}</div>
        </div>
      )}
    </div>
  );
}

/** Scenario Forecast: report-period-aware base/bull/bear + a configurable
 *  Custom scenario, with an evidence-linked impact summary. */
export function ForecastPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const { mode } = useMode();
  const [override, setOverride] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState("");
  const [notesApplied, setNotesApplied] = useState("");

  const weightsKey = JSON.stringify(weights);
  const hasCustom = override != null || Object.keys(weights).length > 0 || notesApplied.trim() !== "";

  const { data, loading, error, reload } = useAsync(
    () =>
      hasCustom
        ? api.customForecast(documentId, {
            growth_override_pct: override,
            factor_weights: weights,
            notes: notesApplied.trim() || null,
            mode,
          })
        : api.getForecast(documentId, null, mode),
    [documentId, mode, override, weightsKey, notesApplied],
  );

  const empty = useMemo(() => !!data && data.metrics.length === 0, [data]);

  // Which scenarios the current response actually contains (adds "custom").
  const scenarios: ScenarioName[] = useMemo(() => {
    const has = new Set<string>();
    data?.metrics.forEach((m) => m.scenarios.forEach((s) => has.add(s.scenario)));
    return [...BASE_SCENARIOS, ...(has.has("custom") ? (["custom"] as ScenarioName[]) : [])];
  }, [data]);

  const applyOverride = () => {
    const v = parseFloat(draft);
    setOverride(Number.isFinite(v) ? v : null);
  };
  const setWeight = (id: string, w: number) =>
    setWeights((prev) => {
      const next = { ...prev };
      if (w === 0) delete next[id];
      else next[id] = w;
      return next;
    });
  const resetCustom = () => {
    setDraft("");
    setOverride(null);
    setWeights({});
    setNotes("");
    setNotesApplied("");
  };

  return (
    <PanelStates loading={loading} error={error} onRetry={reload} empty={empty} emptyText={t("noData", lang)}>
      {data && (
        <div className="grid" style={{ gap: 18 }}>
          <div className="pill amber" role="note" style={{ whiteSpace: "normal", lineHeight: 1.5, padding: "8px 12px", alignSelf: "start" }}>
            ⚠ {t("forecastDisclaimer", lang)}
          </div>

          {/* Meta + growth override (negative / zero / positive all allowed) */}
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <span className="pill gray">{data.base_period || "—"} → {data.forecast_period}</span>
              <span className="pill gray">{data.cadence}</span>
              {data.annualized && <span className="pill gray" title={data.annualized_note ?? ""}>{t("annualizedOptional", lang)}</span>}
            </div>
            <div className="row" style={{ gap: 6, alignItems: "center" }}>
              <label htmlFor="growth-override" className="muted" style={{ fontSize: 12 }}>{t("growthOverride", lang)}</label>
              <input
                id="growth-override"
                type="number"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyOverride()}
                style={{ width: 96 }}
                placeholder="−10 / 0 / +15"
              />
              <button className="btn sm" onClick={applyOverride}>{t("apply", lang)}</button>
              {hasCustom && <button className="btn ghost sm" onClick={resetCustom}>{t("resetCustom", lang)}</button>}
            </div>
          </div>

          {/* Custom scenario builder — configurable external factor weights + notes */}
          <div className="card card-pad" style={{ display: "grid", gap: 12 }}>
            <div>
              <p className="section-title" style={{ margin: "0 0 2px" }}>{t("customScenario", lang)}</p>
              <div className="muted" style={{ fontSize: 12 }}>{t("customHint", lang)}</div>
            </div>
            <div>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <span className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{t("factorWeightsTitle", lang)}</span>
                <span className="muted" style={{ fontSize: 11 }}>{t("headwindTailwind", lang)}</span>
              </div>
              <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "6px 18px", marginTop: 8 }}>
                {data.factors.map((f) => {
                  const w = weights[f.id] ?? 0;
                  return (
                    <label key={f.id} className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 12.5 }}>{lang === "zh" ? f.label_zh : f.label_en}</span>
                      <span className="row" style={{ gap: 6, alignItems: "center" }}>
                        <input
                          type="range" min={-2} max={2} step={1} value={w}
                          onChange={(e) => setWeight(f.id, Number(e.target.value))}
                          style={{ width: 84 }}
                          aria-label={lang === "zh" ? f.label_zh : f.label_en}
                        />
                        <span style={{ fontSize: 12, width: 22, textAlign: "right", fontVariantNumeric: "tabular-nums", color: w > 0 ? "var(--up)" : w < 0 ? "var(--down)" : "var(--ink-soft)" }}>
                          {w > 0 ? `+${w}` : w}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
            <div>
              <label htmlFor="custom-notes" className="muted" style={{ fontSize: 12 }}>{t("customNotes", lang)}</label>
              <input
                id="custom-notes"
                style={{ width: "100%", marginTop: 4 }}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={() => setNotesApplied(notes)}
                onKeyDown={(e) => e.key === "Enter" && setNotesApplied(notes)}
                placeholder={lang === "zh" ? "记录你的判断依据…" : "Record your rationale…"}
              />
            </div>
          </div>

          {/* Impact summary — explain WHY the numbers move */}
          {data.impact_summary && (
            <div className="card card-pad" style={{ display: "grid", gap: 12 }}>
              <p className="section-title" style={{ margin: 0 }}>{t("impactSummaryTitle", lang)}</p>
              <div style={{ fontSize: 13.5 }}>{data.impact_summary.headline}</div>
              <div className="row" style={{ gap: 18, flexWrap: "wrap", alignItems: "start" }}>
                {data.impact_summary.internal_drivers.length > 0 && (
                  <div style={{ flex: "1 1 280px", minWidth: 240 }}>
                    <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>{t("internalDrivers", lang)}</div>
                    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                      {data.impact_summary.internal_drivers.map((d, i) => (
                        <li key={i} style={{ padding: "5px 0", borderBottom: "1px solid var(--line)", fontSize: 12.5 }}>{d.detail}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.impact_summary.external_drivers.length > 0 && (
                  <div style={{ flex: "1 1 240px", minWidth: 220 }}>
                    <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>{t("externalDrivers", lang)}</div>
                    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                      {data.impact_summary.external_drivers.map((d) => (
                        <li key={d.id} className="row" style={{ justifyContent: "space-between", gap: 10, padding: "5px 0", borderBottom: "1px solid var(--line)", fontSize: 12.5 }}>
                          <span>{lang === "zh" ? d.label_zh : d.label_en} <span className="muted">({d.weight > 0 ? `+${d.weight}` : d.weight})</span></span>
                          <span style={{ color: d.contribution_pp >= 0 ? "var(--up)" : "var(--down)", fontVariantNumeric: "tabular-nums" }}>
                            {d.contribution_pp >= 0 ? "+" : ""}{d.contribution_pp.toFixed(1)}pp
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              {data.impact_summary.notes && (
                <div className="muted" style={{ fontSize: 12 }}>“{data.impact_summary.notes}”</div>
              )}
            </div>
          )}

          {/* Scenario cards (base/bull/bear + custom when present) */}
          <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "stretch" }}>
            {scenarios.map((name) => <ScenarioCard key={name} data={data} name={name} />)}
          </div>

          {/* Supporting metrics — scannable comparison + source evidence */}
          <div className="card" style={{ overflowX: "auto" }}>
            <div className="card-pad" style={{ paddingBottom: 0 }}>
              <p className="section-title" style={{ margin: 0 }}>{t("supportingMetrics", lang)}</p>
            </div>
            <table className="fin">
              <thead>
                <tr>
                  <th>{lang === "zh" ? "指标" : "Metric"}</th>
                  <th className="num">{t("current", lang)}</th>
                  {scenarios.map((name) => (
                    <th key={name} className="num">{t(SCENARIO_META[name].key, lang)}</th>
                  ))}
                  <th>{t("sourceEvidence", lang)}</th>
                </tr>
              </thead>
              <tbody>
                {data.metrics.map((m) => (
                  <tr key={m.concept_id}>
                    <td><strong>{metricLabel(m, lang)}</strong></td>
                    <td className="num">{fmtValue(m.current_value, m.is_percent)}</td>
                    {scenarios.map((name) => {
                      const s = scenarioOf(m, name);
                      return (
                        <td key={name} className="num" title={s?.explanation}>
                          {s ? (
                            <>
                              <div style={{ fontWeight: 600 }}>{fmtValue(s.predicted_value, m.is_percent)}</div>
                              <div style={{ fontSize: 11, color: ARROW[s.direction].color }}>{fmtGrowth(s, m.is_percent)}</div>
                            </>
                          ) : "—"}
                        </td>
                      );
                    })}
                    <td><SourceLink documentId={documentId} source={m.source} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.annualized && data.annualized_note && (
            <div className="muted" style={{ fontSize: 12 }}>ℹ {data.annualized_note}</div>
          )}

          {/* Key risks + guidance considered (source-linked, collapsible) */}
          {(data.key_risks.length > 0 || data.guidance.length > 0) && (
            <div className="card card-pad" style={{ display: "grid", gap: 12 }}>
              {data.key_risks.length > 0 && (
                <Collapsible title={t("keyRisks", lang)} count={data.key_risks.length} defaultOpen>
                  <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                    {data.key_risks.map((r, i) => (
                      <li key={i} className="row" style={{ justifyContent: "space-between", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
                        <span style={{ color: "var(--down)", flex: 1, minWidth: 0 }}>⚠ {r.text}</span>
                        {r.source && <SourceLink documentId={documentId} source={r.source} />}
                      </li>
                    ))}
                  </ul>
                </Collapsible>
              )}
              {data.guidance.length > 0 && (
                <Collapsible title={t("managementGuidance", lang)} count={data.guidance.length}>
                  <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                    {data.guidance.map((g, i) => (
                      <li key={i} className="row" style={{ justifyContent: "space-between", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
                        <span style={{ flex: 1, minWidth: 0 }}>{g.text}</span>
                        {g.source && <SourceLink documentId={documentId} source={g.source} />}
                      </li>
                    ))}
                  </ul>
                </Collapsible>
              )}
            </div>
          )}

          {/* External scenario assumptions — clearly labelled as assumptions, not facts. */}
          {data.external_assumptions.length > 0 && (
            <div className="card card-pad" style={{ display: "grid", gap: 10 }}>
              <p className="section-title" style={{ margin: 0 }}>{t("externalFactors", lang)}</p>
              <div className="pill amber" role="note" style={{ whiteSpace: "normal", lineHeight: 1.5, padding: "8px 12px", alignSelf: "start" }}>
                ⚠ {data.external_note || t("externalFactorsNote", lang)}
              </div>
              <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "stretch" }}>
                {data.external_assumptions.map((ea) => {
                  const meta = SCENARIO_META[ea.scenario as ScenarioName] ?? SCENARIO_META.base;
                  const key = meta.key;
                  return (
                    <div key={ea.scenario} className="card card-pad" style={{ flex: "1 1 220px", minWidth: 200, boxShadow: "none" }}>
                      <span className={`pill ${meta.cls}`}>{t(key, lang)}</span>
                      <ul style={{ margin: "10px 0 0", paddingLeft: 18, fontSize: 12.5 }}>
                        {ea.external_factors.map((f, i) => (
                          <li key={i} style={{ marginBottom: 4 }}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </PanelStates>
  );
}
