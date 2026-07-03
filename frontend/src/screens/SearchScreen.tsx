import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { SearchPanel } from "../report/SearchPanel";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import { t } from "../lib/i18n";
import type { DocumentSummary } from "../types";

export function SearchScreen() {
  const { lang } = useLang();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [docId, setDocId] = useState<string>("");

  useEffect(() => {
    api.listDocuments().then((d) => {
      const ready = d.filter((x) => x.status === "ready");
      setDocs(ready);
      if (ready[0]) setDocId(ready[0].id);
    });
  }, []);

  return (
    <Layout title={t("search", lang)}>
      {docs.length === 0 ? (
        <div className="card empty">{lang === "zh" ? "请先上传或载入一份财报" : "Upload or load a report first"}</div>
      ) : (
        <div className="card card-pad">
          <div className="row" style={{ marginBottom: 16, alignItems: "center" }}>
            <span className="muted">{lang === "zh" ? "在报告中搜索：" : "Search within:"}</span>
            <select value={docId} onChange={(e) => setDocId(e.target.value)}>
              {docs.map((d) => (
                <option key={d.id} value={d.id}>{d.company_name || d.filename} · {d.report_period}</option>
              ))}
            </select>
          </div>
          {docId && <SearchPanel documentId={docId} />}
        </div>
      )}
    </Layout>
  );
}
