import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { StatusPill } from "../components/ui";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { reportTypeLabel, t } from "../lib/i18n";
import { formatDate } from "../lib/format";
import type { DocumentSummary } from "../types";

export function MyReports({ favoritesOnly = false }: { favoritesOnly?: boolean }) {
  const { lang } = useLang();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.listDocuments(favoritesOnly).then(setDocs).catch(() => setDocs([])).finally(() => setLoading(false));
  };
  useEffect(() => {
    load();
  }, [favoritesOnly]);

  const remove = async (id: string) => {
    await api.deleteDocument(id);
    load();
  };
  const fav = async (id: string) => {
    await api.toggleFavorite(id);
    load();
  };

  return (
    <Layout
      title={favoritesOnly ? t("favorites", lang) : t("myReports", lang)}
      actions={<Link to="/upload" className="btn primary sm">⬆ {t("upload", lang)}</Link>}
    >
      {loading ? (
        <div className="center"><div className="spinner" /></div>
      ) : docs.length === 0 ? (
        <div className="card empty">{t("noData", lang)}</div>
      ) : (
        <div className="card">
          <table className="fin">
            <thead>
              <tr>
                <th>{lang === "zh" ? "公司 / 文件" : "Company / File"}</th>
                <th>{lang === "zh" ? "类型" : "Type"}</th>
                <th>{lang === "zh" ? "报告期" : "Period"}</th>
                <th className="num">{lang === "zh" ? "数据项" : "Facts"}</th>
                <th>{lang === "zh" ? "状态" : "Status"}</th>
                <th>{lang === "zh" ? "日期" : "Date"}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/reports/${d.id}`}><strong>{d.company_name || d.filename}</strong></Link>
                    <div className="muted" style={{ fontSize: 11.5 }}>
                      {d.language.toUpperCase()}{d.is_scanned ? " · scanned" : ""}
                    </div>
                  </td>
                  <td>{reportTypeLabel(d.report_type, lang)}</td>
                  <td>{d.report_period || "—"}</td>
                  <td className="num">{d.fact_count}</td>
                  <td><StatusPill status={d.status} /></td>
                  <td>{formatDate(d.created_at)}</td>
                  <td className="num" style={{ whiteSpace: "nowrap" }}>
                    <button className="btn ghost sm" title="favorite" onClick={() => fav(d.id)}>{d.is_favorite ? "★" : "☆"}</button>
                    <button className="btn ghost sm" title="delete" onClick={() => remove(d.id)}>🗑</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
