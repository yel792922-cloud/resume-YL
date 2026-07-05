import { useState } from "react";
import { useAuth } from "../lib/auth";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";

export function Login() {
  const { lang, setLang } = useLang();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card card">
        <div className="brand" style={{ padding: "0 0 18px" }}>
          <div className="logo">财</div>
          <div>
            <h1 style={{ color: "var(--ink)" }}>{t("appName", lang)}</h1>
            <small className="muted">Financial Report Analyzer</small>
          </div>
        </div>

        <div className="tabs" style={{ marginBottom: 18 }}>
          <button className={`tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>
            {lang === "zh" ? "登录" : "Sign in"}
          </button>
          <button className={`tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>
            {lang === "zh" ? "注册" : "Create account"}
          </button>
        </div>

        <form onSubmit={submit}>
          <label className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "邮箱" : "Email"}</label>
          <input
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", margin: "4px 0 14px" }} placeholder="you@example.com" autoComplete="email"
          />
          <label className="muted" style={{ fontSize: 12 }}>{lang === "zh" ? "密码" : "Password"}</label>
          <input
            type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", margin: "4px 0 14px" }}
            placeholder={lang === "zh" ? "至少 8 位" : "At least 8 characters"}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          {error && <div className="pill red" style={{ marginBottom: 12, whiteSpace: "normal" }}>{error}</div>}
          <button className="btn primary" type="submit" disabled={busy} style={{ width: "100%", justifyContent: "center" }}>
            {busy ? "…" : mode === "login" ? (lang === "zh" ? "登录" : "Sign in") : lang === "zh" ? "创建账户" : "Create account"}
          </button>
        </form>

        <div className="muted" style={{ fontSize: 12, marginTop: 16, textAlign: "center" }}>
          {t("traceEvery", lang)}
        </div>
        <div style={{ textAlign: "center", marginTop: 10 }}>
          <button className="btn ghost sm" onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
            {lang === "zh" ? "中 / EN" : "EN / 中"}
          </button>
        </div>
      </div>
    </div>
  );
}
