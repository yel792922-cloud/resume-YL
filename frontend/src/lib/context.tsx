import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { PagePreview } from "../components/PagePreview";
import type { PageOut, SourceRef } from "../types";
import type { Lang } from "./i18n";

// ---------- Language ----------
interface LangCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
}
const LangContext = createContext<LangCtx>({ lang: "zh", setLang: () => {} });
export const useLang = () => useContext(LangContext);

// ---------- Source drawer ----------
interface SourceCtx {
  open: (documentId: string, source: SourceRef, title?: string) => void;
}
const SourceContext = createContext<SourceCtx>({ open: () => {} });
export const useSource = () => useContext(SourceContext);

interface DrawerState {
  documentId: string;
  source: SourceRef;
  title?: string;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("lang") as Lang) || "zh");
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const [page, setPage] = useState<PageOut | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => localStorage.setItem("lang", lang), [lang]);

  const open = useCallback((documentId: string, source: SourceRef, title?: string) => {
    setDrawer({ documentId, source, title });
  }, []);

  useEffect(() => {
    if (!drawer?.source.page_number) {
      setPage(null);
      return;
    }
    setLoading(true);
    api
      .getPage(drawer.documentId, drawer.source.page_number)
      .then(setPage)
      .catch(() => setPage(null))
      .finally(() => setLoading(false));
  }, [drawer]);

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      <SourceContext.Provider value={{ open }}>
        {children}
        {drawer && (
          <div className="drawer-backdrop" onClick={() => setDrawer(null)}>
            <div className="drawer" onClick={(e) => e.stopPropagation()}>
              <div className="drawer-head">
                <div>
                  <strong>{drawer.title || (lang === "zh" ? "原文定位" : "Source location")}</strong>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {lang === "zh" ? `第 ${drawer.source.page_number} 页` : `Page ${drawer.source.page_number}`}
                    {drawer.source.table_cell ? ` · ${drawer.source.table_cell}` : ""}
                    {drawer.source.section ? ` · ${drawer.source.section}` : ""}
                  </div>
                </div>
                <button className="btn ghost sm" onClick={() => setDrawer(null)}>
                  ✕
                </button>
              </div>
              <div className="drawer-body">
                {drawer.source.snippet && (
                  <div className="snippet" style={{ marginBottom: 16 }}>
                    {drawer.source.snippet}
                  </div>
                )}
                {loading && (
                  <div className="center">
                    <div className="spinner" />
                  </div>
                )}
                {page && <PagePreview page={page} highlight={drawer.source.bbox} />}
                {!loading && !page && (
                  <div className="empty">{lang === "zh" ? "无法加载原文页" : "Could not load source page"}</div>
                )}
              </div>
            </div>
          </div>
        )}
      </SourceContext.Provider>
    </LangContext.Provider>
  );
}
