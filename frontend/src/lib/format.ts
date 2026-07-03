import type { Fact } from "../types";

/** Display a fact's value, preferring the printed text (keeps traceability). */
export function factValue(f: Fact): string {
  if (f.value_text) return f.value_text;
  if (f.metric_value !== null && f.metric_value !== undefined) {
    return f.metric_value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return "—";
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
