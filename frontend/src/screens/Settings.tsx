import { Layout } from "../components/Layout";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";

export function Settings() {
  const { lang, setLang } = useLang();
  return (
    <Layout title={t("settings", lang)}>
      <div className="card card-pad" style={{ maxWidth: 560 }}>
        <div className="row" style={{ justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
          <div>
            <strong>{lang === "zh" ? "界面语言" : "Language"}</strong>
            <div className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "简体中文 / English" : "Chinese / English"}</div>
          </div>
          <select value={lang} onChange={(e) => setLang(e.target.value as "zh" | "en")}>
            <option value="zh">简体中文</option>
            <option value="en">English</option>
          </select>
        </div>
        <div className="row" style={{ justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
          <div>
            <strong>{lang === "zh" ? "数据提取偏好" : "Extraction"}</strong>
            <div className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "规则引擎 · 高可追溯" : "Rule engine · high traceability"}</div>
          </div>
          <span className="pill green">v1</span>
        </div>
        <div className="row" style={{ justifyContent: "space-between", padding: "12px 0" }}>
          <div>
            <strong>{lang === "zh" ? "关于" : "About"}</strong>
            <div className="muted" style={{ fontSize: 12 }}>财报分析助手 · Financial Report Analyzer · MVP v0.1</div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
