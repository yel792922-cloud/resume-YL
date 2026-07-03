import { useSource } from "../lib/context";
import { useLang } from "../lib/context";
import { confidenceTier, factValueWithUnit } from "../lib/format";
import type { DocumentStatus, Fact, SourceRef } from "../types";

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

export function MetricCard({ fact }: { fact: Fact }) {
  const { open } = useSource();
  const { lang } = useLang();
  const label = lang === "zh" ? fact.metric_label || fact.metric_name : fact.metric_name;
  return (
    <div className="metric" onClick={() => open(fact.document_id, fact.source, label)}>
      <div className="label">{label}</div>
      <div className="value">{factValueWithUnit(fact)}</div>
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
