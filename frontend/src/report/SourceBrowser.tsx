import { useEffect, useState } from "react";
import { PagePreview } from "../components/PagePreview";
import { api } from "../api/client";
import { useLang } from "../lib/context";
import type { PageOut } from "../types";

/** Browse the original report page by page — the "highlighted original text" view. */
export function SourceBrowser({ documentId, pages }: { documentId: string; pages: number[] }) {
  const { lang } = useLang();
  const [current, setCurrent] = useState<number>(pages[0] ?? 1);
  const [page, setPage] = useState<PageOut | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getPage(documentId, current).then(setPage).catch(() => setPage(null)).finally(() => setLoading(false));
  }, [documentId, current]);

  return (
    <div className="row" style={{ alignItems: "start", gap: 20, flexWrap: "wrap" }}>
      <div className="card card-pad" style={{ width: 180 }}>
        <p className="section-title">{lang === "zh" ? "页面" : "Pages"}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 460, overflow: "auto" }}>
          {pages.map((p) => (
            <button key={p} className={`btn sm ${p === current ? "primary" : "ghost"}`} onClick={() => setCurrent(p)}>
              {lang === "zh" ? `第 ${p} 页` : `Page ${p}`}
            </button>
          ))}
        </div>
      </div>
      <div className="card card-pad" style={{ flex: 1, minWidth: 320, display: "grid", placeItems: "center" }}>
        {loading ? <div className="spinner" /> : page ? <PagePreview page={page} /> : <div className="empty">—</div>}
      </div>
    </div>
  );
}
