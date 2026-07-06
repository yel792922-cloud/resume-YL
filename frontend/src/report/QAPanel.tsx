import { useState } from "react";
import { api, ApiError } from "../api/client";
import { SourceLink, ConfidenceBadge } from "../components/ui";
import { useLang } from "../lib/context";
import { useMode } from "../lib/mode";
import { t, type Lang } from "../lib/i18n";
import type { AnswerResponse, EvidenceItem } from "../types";

const EXAMPLES = [
  { zh: "营业收入为什么增长？", en: "Why did revenue increase?" },
  { zh: "毛利率为什么变化？", en: "Why did gross margin change?" },
  { zh: "管理层提示了哪些主要风险？", en: "What are the main risks?" },
  { zh: "现金流是否健康？", en: "How healthy is cash flow?" },
  { zh: "较上期有哪些变化？", en: "What changed versus last period?" },
];

const EVIDENCE_TAG: Record<EvidenceItem["kind"], { cls: string; zh: string; en: string }> = {
  fact: { cls: "blue", zh: "数据", en: "Fact" },
  management: { cls: "gray", zh: "管理层", en: "Management" },
  guidance: { cls: "gray", zh: "指引", en: "Guidance" },
  risk: { cls: "red", zh: "风险", en: "Risk" },
  text: { cls: "gray", zh: "原文", en: "Text" },
};

function EvidenceRow({ documentId, item, lang }: { documentId: string; item: EvidenceItem; lang: Lang }) {
  const tag = EVIDENCE_TAG[item.kind] ?? EVIDENCE_TAG.text;
  return (
    <div className="card card-pad" style={{ padding: "10px 14px" }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "start", gap: 10 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <span className={`pill ${tag.cls}`}>{lang === "zh" ? tag.zh : tag.en}</span>
          <div className="snippet" style={{ marginTop: 8 }}>{item.text}</div>
        </div>
        {item.source && (
          <div style={{ flexShrink: 0 }}>
            <SourceLink documentId={documentId} source={item.source} />
          </div>
        )}
      </div>
    </div>
  );
}

/** Evidence-based Q&A for a single report: grounded answer + cited evidence. */
export function QAPanel({ documentId }: { documentId: string }) {
  const { lang } = useLang();
  const { mode } = useMode();
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnswerResponse | null>(null);

  const run = async (question: string) => {
    const text = question.trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.ask(documentId, text, mode));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="row" style={{ marginBottom: 12 }}>
        <input
          style={{ flex: 1 }}
          value={q}
          placeholder={t("askPlaceholder", lang)}
          aria-label={t("askButton", lang)}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(q)}
        />
        <button className="btn primary" onClick={() => run(q)} disabled={loading || !q.trim()}>
          {loading ? "…" : t("askButton", lang)}
        </button>
      </div>

      <div className="row" style={{ flexWrap: "wrap", marginBottom: 16, gap: 6 }}>
        <span className="muted" style={{ fontSize: 12, alignSelf: "center" }}>{t("tryExample", lang)}:</span>
        {EXAMPLES.map((ex) => {
          const text = lang === "zh" ? ex.zh : ex.en;
          return (
            <button key={ex.en} className="pill gray" style={{ border: "none" }} onClick={() => { setQ(text); run(text); }}>
              {text}
            </button>
          );
        })}
      </div>

      {loading && <div className="center"><div className="spinner" role="status" aria-label="Loading" /></div>}

      {error && !loading && (
        <div className="card empty">
          <div style={{ marginBottom: 10 }}>⚠ {t("loadFailed", lang)}</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{error}</div>
          <button className="btn sm" onClick={() => run(q)}>{t("retry", lang)}</button>
        </div>
      )}

      {!loading && !error && !data && (
        <div className="card empty">{t("askEmpty", lang)}</div>
      )}

      {!loading && !error && data && (
        <div className="grid" style={{ gap: 16 }}>
          {/* Answer */}
          <div className="card card-pad">
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <p className="section-title" style={{ margin: 0 }}>{t("answer", lang)}</p>
              {data.insufficient
                ? <span className="pill amber">{t("insufficientEvidence", lang)}</span>
                : <ConfidenceBadge level={data.confidence} />}
            </div>
            <div style={{ fontSize: 14.5, lineHeight: 1.6 }}>{data.answer}</div>
            {data.note && <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>{data.note}</div>}
          </div>

          {/* Evidence */}
          {data.evidence.length > 0 && (
            <div>
              <p className="section-title">{t("evidence", lang)} ({data.evidence.length})</p>
              <div className="grid" style={{ gap: 10 }}>
                {data.evidence.map((item, i) => (
                  <EvidenceRow key={i} documentId={documentId} item={item} lang={lang} />
                ))}
              </div>
            </div>
          )}

          <div className="muted" style={{ fontSize: 12 }}>{t("groundedNote", lang)}</div>
        </div>
      )}
    </div>
  );
}
