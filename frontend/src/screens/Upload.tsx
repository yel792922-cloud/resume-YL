import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";

export function Upload() {
  const { lang } = useLang();
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [period, setPeriod] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file, company || undefined, period || undefined);
      nav(`/reports/${doc.id}`);
    } catch (e) {
      setError(String(e));
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
        </label>

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

        {error && <div className="pill red" style={{ marginBottom: 12 }}>{error}</div>}

        <button className="btn primary" disabled={!file || busy} onClick={submit}>
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
