import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";
import { BUSINESS_STRUCTURE, GEO_SCOPE, INDUSTRY, REPORT_TYPE } from "../lib/profileLabels";

export function Upload() {
  const { lang } = useLang();
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [period, setPeriod] = useState("");
  // Report-profile hints (default "auto" → inferred from the report).
  const [biz, setBiz] = useState("auto");
  const [geo, setGeo] = useState("auto");
  const [industry, setIndustry] = useState("auto");
  const [rtype, setRtype] = useState("auto");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [maxMb, setMaxMb] = useState<number | null>(null);

  useEffect(() => {
    api.health().then((h) => setMaxMb(h.max_upload_mb)).catch(() => {});
  }, []);

  // Client-side guard so oversized files fail fast with a clear message.
  const tooBig = !!(file && maxMb && file.size > maxMb * 1024 * 1024);

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file, company || undefined, period || undefined, {
        business_structure: biz, geo_scope: geo, industry, report_type: rtype,
      });
      nav(`/reports/${doc.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title={t("upload", lang)}>
      <div className="card card-pad" style={{ maxWidth: 640 }}>
        <p className="section-title">{lang === "zh" ? "上传财报 PDF" : "Upload report PDF"}</p>

        <label
          className="card"
          style={{
            display: "block", border: "1.5px dashed var(--line)", padding: 32, textAlign: "center",
            cursor: "pointer", boxShadow: "none", marginBottom: 18,
          }}
        >
          <input
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div style={{ fontSize: 28 }}>📄</div>
          <div style={{ marginTop: 8 }}>
            {file ? <strong>{file.name}</strong> : lang === "zh" ? "点击选择 PDF 文件（支持中英文 / 扫描件）" : "Choose a PDF (Chinese / English / scanned)"}
          </div>
          {file && (
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{(file.size / 1_048_576).toFixed(1)} MB</div>
          )}
          {maxMb && (
            <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
              {lang === "zh" ? `单文件上限 ${maxMb} MB` : `Max file size ${maxMb} MB`}
            </div>
          )}
        </label>
        {tooBig && (
          <div className="pill red" style={{ marginBottom: 12, whiteSpace: "normal" }}>
            {lang === "zh" ? `文件超过 ${maxMb} MB 上限` : `File exceeds the ${maxMb} MB limit`}
          </div>
        )}

        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 16 }}>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "公司名称（可选）" : "Company (optional)"}</label>
            <input value={company} onChange={(e) => setCompany(e.target.value)} style={{ width: "100%", marginTop: 4 }} placeholder="e.g. Skylark Technologies" />
          </div>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "报告期（可选）" : "Period (optional)"}</label>
            <input value={period} onChange={(e) => setPeriod(e.target.value)} style={{ width: "100%", marginTop: 4 }} placeholder="e.g. 2024 FY" />
          </div>
        </div>

        {/* Report profile (optional hint) — defaults to auto-detect. */}
        <div style={{ marginBottom: 16 }}>
          <p className="section-title" style={{ marginBottom: 4 }}>{lang === "zh" ? "报告结构（可选，默认自动检测）" : "Report profile (optional — defaults to auto-detect)"}</p>
          <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
            {lang === "zh"
              ? "这些只是提示，用于调整提取与分组方式；系统仍会自动推断。"
              : "These are hints that tune extraction & grouping; the system still auto-infers."}
          </div>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
            {([
              [lang === "zh" ? "业务结构" : "Business structure", biz, setBiz, BUSINESS_STRUCTURE],
              [lang === "zh" ? "地区范围" : "Geographic scope", geo, setGeo, GEO_SCOPE],
              [lang === "zh" ? "行业 / 类型" : "Industry / style", industry, setIndustry, INDUSTRY],
              [lang === "zh" ? "报告类型" : "Report type", rtype, setRtype, REPORT_TYPE],
            ] as [string, string, (v: string) => void, Record<string, { zh: string; en: string }>][]).map(
              ([label, val, set, map]) => (
                <div key={label}>
                  <label className="muted" style={{ fontSize: 12 }}>{label}</label>
                  <select value={val} onChange={(e) => set(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                    {Object.keys(map).map((id) => (
                      <option key={id} value={id}>{lang === "zh" ? map[id].zh : map[id].en}</option>
                    ))}
                  </select>
                </div>
              ),
            )}
          </div>
        </div>

        {error && <div className="pill red" style={{ marginBottom: 12 }}>{error}</div>}

        <button className="btn primary" disabled={!file || busy || tooBig} onClick={submit}>
          {busy ? (lang === "zh" ? "解析中…" : "Analyzing…") : lang === "zh" ? "开始解析" : "Analyze"}
        </button>
        <div className="muted" style={{ fontSize: 12, marginTop: 14 }}>
          {lang === "zh"
            ? "上传后将自动完成：解析版面 → 提取指标 → 建立原文定位 → 生成摘要。"
            : "On upload: layout parse → metric extraction → source mapping → summary."}
        </div>
      </div>
    </Layout>
  );
}
