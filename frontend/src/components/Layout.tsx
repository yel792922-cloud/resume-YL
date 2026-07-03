import { NavLink } from "react-router-dom";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";
import type { ReactNode } from "react";

const NAV: { to: string; key: Parameters<typeof t>[0]; ico: string }[] = [
  { to: "/", key: "home", ico: "⌂" },
  { to: "/upload", key: "upload", ico: "⬆" },
  { to: "/reports", key: "myReports", ico: "🗂" },
  { to: "/search", key: "search", ico: "🔍" },
  { to: "/compare", key: "comparison", ico: "📊" },
  { to: "/favorites", key: "favorites", ico: "★" },
  { to: "/settings", key: "settings", ico: "⚙" },
];

export function Layout({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  const { lang, setLang } = useLang();
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">财</div>
          <div>
            <h1>{t("appName", lang)}</h1>
            <small>Report Analyzer</small>
          </div>
        </div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            <span className="ico">{n.ico}</span>
            {t(n.key, lang)}
          </NavLink>
        ))}
        <div className="spacer" />
        <div className="foot">
          {t("traceEvery", lang)}
          <br />
          v0.1 · MVP
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <h2>{title}</h2>
          <div className="row" style={{ alignItems: "center" }}>
            {actions}
            <button className="btn sm" onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
              {lang === "zh" ? "中 / EN" : "EN / 中"}
            </button>
          </div>
        </div>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
