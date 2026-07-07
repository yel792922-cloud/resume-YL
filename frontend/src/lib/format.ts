import type { Fact } from "../types";
import { t, type Lang } from "./i18n";

/** Display a fact's value, preferring the printed text (keeps traceability). */
export function factValue(f: Fact): string {
  if (f.value_text) return f.value_text;
  if (f.metric_value !== null && f.metric_value !== undefined) {
    return f.metric_value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return "—";
}

const SCOPE_BASIS: Record<string, "scopeConsolidated" | "scopeSegment" | "scopeGeography" | "scopePerShare"> = {
  consolidated: "scopeConsolidated",
  segment: "scopeSegment",
  geography: "scopeGeography",
  per_share: "scopePerShare",
};

/** Unit shown as *evidence*: the source unit when known, else an explicit
 *  "unidentified" placeholder — never a silent blank. A percent's unit lives in
 *  the value itself, so it reads as "—" in a dedicated unit slot. */
export function unitDisplay(f: Fact, lang: Lang): string {
  if (f.unit === "%") return "—";
  if (f.unit) return f.unit;
  // A numeric fact with no unit is a genuine gap → flag it, don't hide it.
  if (f.metric_value !== null && f.metric_value !== undefined) return t("unitUnknown", lang);
  return "—";
}

/** The layered context line under a metric name: scope · period · unit.
 *  e.g. "合并口径 · 2024 FY · 人民币（亿元）". Omits parts that are absent. */
export function metricContext(f: Fact, lang: Lang): string {
  const parts: string[] = [];
  const basisKey = SCOPE_BASIS[f.scope_type];
  if (basisKey) parts.push(`${t(basisKey, lang)}${t("basisSuffix", lang)}`);
  if (f.report_period) parts.push(f.report_period);
  parts.push(unitDisplay(f, lang));
  return parts.join(" · ");
}

/** A compact value + unit for cards, avoiding duplicated "%" and unit noise. */
export function factValueWithUnit(f: Fact): string {
  const val = factValue(f);
  if (!f.unit || f.unit === "%" || (f.value_text && f.value_text.includes(f.unit))) return val;
  return `${val} ${f.unit}`;
}

export function confidenceTier(score: number): "high" | "medium" | "low" {
  if (score >= 0.8) return "high";
  if (score >= 0.55) return "medium";
  return "low";
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}
