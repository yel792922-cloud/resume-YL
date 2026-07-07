import { type ReactNode, useState } from "react";
import { useSource } from "../lib/context";
import { useLang } from "../lib/context";
import { useMode, type AnalysisMode } from "../lib/mode";
import { t } from "../lib/i18n";
import { confidenceTier, factValueWithUnit, metricContext } from "../lib/format";
import type { ConfidenceLevel, DocumentStatus, Fact, SourceRef } from "../types";

/** Raw / Clean analysis-mode toggle. Reads the global mode; affects Q&A,
 *  forecasting, comparison and export. */
export function ModeToggle() {
  const { lang } = useLang();
  const { mode, setMode } = useMode();
  const opts: { key: AnalysisMode; zh: string; en: string }[] = [
    { key: "clean", zh: "清洗", en: "Clean" },
    { key: "raw", zh: "原始", en: "Raw" },
  ];
  return (
    <div
      className="mode-toggle"
      role="group"
      aria-label={lang === "zh" ? "数据模式" : "Analysis mode"}
      title={lang === "zh" ? "清洗 = 规范化数据；原始 = 未清洗提取" : "Clean = normalized data; Raw = uncleaned extraction"}
    >
      <span className="muted" style={{ fontSize: 12, marginRight: 2 }}>{lang === "zh" ? "数据" : "Data"}:</span>
      {opts.map((o) => (
        <button
          key={o.key}
          className={`mode-opt ${mode === o.key ? "active" : ""}`}
          aria-pressed={mode === o.key}
          onClick={() => setMode(o.key)}
        >
          {lang === "zh" ? o.zh : o.en}
        </button>
      ))}
    </div>
  );
}

const SCOPE_META: Record<string, { cls: string; key: "scopeConsolidated" | "scopeSegment" | "scopeGeography" | "scopePerShare" }> = {
  consolidated: { cls: "blue", key: "scopeConsolidated" },
  segment: { cls: "green", key: "scopeSegment" },
  geography: { cls: "amber", key: "scopeGeography" },
  per_share: { cls: "gray", key: "scopePerShare" },
};

/** A small pill naming a metric's reporting scope, so same-named rows are
 *  easy to tell apart. Renders nothing for unscoped facts. */
export function ScopeChip({ scopeType, scopeLabel }: { scopeType: string; scopeLabel?: string }) {
  const { lang } = useLang();
  const meta = SCOPE_META[scopeType];
  if (!meta) return null;
  return (
    <span className={`pill ${meta.cls}`} style={{ fontSize: 11 }} title={scopeLabel || t(meta.key, lang)}>
      {t(meta.key, lang)}
    </span>
  );
}

/** A clickable evidence chip → opens the source drawer with highlight. */
export function SourceLink({
  documentId,
  source,
  label,
}: {
  documentId: string;
  source: SourceRef | null;
  label?: string;
}) {
  const { open } = useSource();
  const { lang } = useLang();
  if (!source || !source.page_number) return null;
  const text = label ?? (lang === "zh" ? `第 ${source.page_number} 页` : `p.${source.page_number}`);
  return (
    <button className="srclink" onClick={() => open(documentId, source)} title={source.snippet ?? ""}>
      <span>◎</span>
      {text}
    </button>
  );
}

export function Confidence({ score }: { score: number }) {
  const tier = confidenceTier(score);
  return (
    <span className={`conf ${tier}`} title={`confidence ${(score * 100).toFixed(0)}%`}>
      <span className="dot" />
      {(score * 100).toFixed(0)}%
    </span>
  );
}

const LEVEL_LABEL: Record<ConfidenceLevel, { zh: string; en: string }> = {
  high: { zh: "高", en: "High" },
  medium: { zh: "中", en: "Medium" },
  low: { zh: "低", en: "Low" },
};

/** Confidence badge for qualitative levels (forecast). Reuses the .conf styles. */
export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const { lang } = useLang();
  return (
    <span className={`conf ${level}`} title="confidence" aria-label={`Confidence: ${LEVEL_LABEL[level].en}`}>
      <span className="dot" />
      {LEVEL_LABEL[level][lang]}
    </span>
  );
}

/** Loading / error / empty wrapper so panels handle async states consistently. */
export function PanelStates({
  loading,
  error,
  empty,
  emptyText,
  onRetry,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  emptyText?: string;
  onRetry?: () => void;
  children: ReactNode;
}) {
  const { lang } = useLang();
  if (loading) return <div className="center"><div className="spinner" role="status" aria-label="Loading" /></div>;
  if (error)
    return (
      <div className="card empty">
        <div style={{ marginBottom: 10 }}>⚠ {t("loadFailed", lang)}</div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{error}</div>
        {onRetry && <button className="btn sm" onClick={onRetry}>{t("retry", lang)}</button>}
      </div>
    );
  if (empty) return <div className="card empty">{emptyText ?? t("noData", lang)}</div>;
  return <>{children}</>;
}

/** A small accessible collapsible for long/secondary content. */
export function Collapsible({
  title,
  count,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        className="btn ghost sm"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        style={{ padding: "4px 6px" }}
      >
        <span aria-hidden style={{ display: "inline-block", width: 12 }}>{open ? "▾" : "▸"}</span>
        {title}{count != null ? ` (${count})` : ""}
      </button>
      {open && <div style={{ marginTop: 8 }}>{children}</div>}
    </div>
  );
}

export function MetricCard({ fact }: { fact: Fact }) {
  const { open } = useSource();
  const { lang } = useLang();
  const label = lang === "zh" ? fact.metric_label || fact.metric_name : fact.metric_name;
  return (
    <div className="metric" onClick={() => open(fact.document_id, fact.source, label)}>
      <div className="label" style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        {label}
        <ScopeChip scopeType={fact.scope_type} scopeLabel={fact.scope_label} />
      </div>
      <div className="value">{factValueWithUnit(fact)}</div>
      {/* Layered context line: scope · period · unit. */}
      <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>{metricContext(fact, lang)}</div>
      <div className="foot">
        <Confidence score={fact.confidence_score} />
        <SourceLink documentId={fact.document_id} source={fact.source} />
      </div>
    </div>
  );
}

const STATUS_STYLE: Record<DocumentStatus, { cls: string; zh: string; en: string }> = {
  ready: { cls: "green", zh: "已解析", en: "Ready" },
  parsing: { cls: "amber", zh: "解析中", en: "Parsing" },
  extracting: { cls: "amber", zh: "提取中", en: "Extracting" },
  uploaded: { cls: "gray", zh: "已上传", en: "Uploaded" },
  failed: { cls: "red", zh: "失败", en: "Failed" },
};

export function StatusPill({ status }: { status: DocumentStatus }) {
  const { lang } = useLang();
  const s = STATUS_STYLE[status];
  return <span className={`pill ${s.cls}`}>{lang === "zh" ? s.zh : s.en}</span>;
}
