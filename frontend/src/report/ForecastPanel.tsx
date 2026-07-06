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

const SCENARIOS: ScenarioName[] = ["base", "bull", "bear"];
const SCENARIO_META: Record<ScenarioName, { cls: string; key: "scenarioBase" | "scenarioBull" | "scenarioBear" }> = {
  base: { cls: "blue", key: "scenarioBase" },
  bull: { cls: "green", key: "scenarioBull" },
  bear: { cls: "red", key: "scenarioBear" },
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
  // The backend's second assumption line is the concise scenario tagline.
  const tagline = hs?.assumptions?.[hs.assumptions.length - 1] ?? "";

  return (
    <div className="card card-pad" style={{ flex: "1 1 220px", minWidth: 200 }}>
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

/** Scenario Forecast: base/bull/bear with scannable metrics and source evidence. */
export function ForecastPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const { mode } = useMode();
  const [override, setOverride] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const { data, loading, error, reload } = useAsync(
    () => api.getForecast(documentId, override, mode),
    [documentId, override, mode],
  );

  const empty = useMemo(() => !!data && data.metrics.length === 0, [data]);

  const applyOverride = () => {
    const v = parseFloat(draft);
    setOverride(Number.isFinite(v) ? v : null);
  };
  const resetOverride = () => {
    setDraft("");
    setOverride(null);
  };

  return (
    <PanelStates loading={loading} error={error} onRetry={reload} empty={empty} emptyText={t("noData", lang)}>
      {data && (
        <div className="grid" style={{ gap: 18 }}>
          {/* Disclaimer — make it obvious these are analytical scenarios. */}
          <div className="pill amber" role="note" style={{ whiteSpace: "normal", lineHeight: 1.5, padding: "8px 12px", alignSelf: "start" }}>
            ⚠ {t("forecastDisclaimer", lang)}
          </div>

          {/* Meta + growth override */}
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <span className="pill gray">{data.base_period || "—"} → {data.forecast_period}</span>
              <span className="pill gray">{data.cadence}</span>
              {data.annualized && <span className="pill gray">{t("annualizedView", lang)}</span>}
            </div>
            <div className="row" style={{ gap: 6, alignItems: "center" }}>
              <label htmlFor="growth-override" className="muted" style={{ fontSize: 12 }}>{t("growthOverride", lang)}</label>
              <input
                id="growth-override"
                type="number"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyOverride()}
                style={{ width: 90 }}
                placeholder="—"
              />
              <button className="btn sm" onClick={applyOverride}>{t("apply", lang)}</button>
              {override != null && <button className="btn ghost sm" onClick={resetOverride}>{t("reset", lang)}</button>}
            </div>
          </div>

          {/* Three scenario cards */}
          <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "stretch" }}>
            {SCENARIOS.map((name) => <ScenarioCard key={name} data={data} name={name} />)}
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
                  <th className="num">{t("scenarioBase", lang)}</th>
                  <th className="num">{t("scenarioBull", lang)}</th>
                  <th className="num">{t("scenarioBear", lang)}</th>
                  <th>{t("sourceEvidence", lang)}</th>
                </tr>
              </thead>
              <tbody>
                {data.metrics.map((m) => (
                  <tr key={m.concept_id}>
                    <td><strong>{metricLabel(m, lang)}</strong></td>
                    <td className="num">{fmtValue(m.current_value, m.is_percent)}</td>
                    {SCENARIOS.map((name) => {
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
                  const key = meta.key as "scenarioBase" | "scenarioBull" | "scenarioBear";
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
