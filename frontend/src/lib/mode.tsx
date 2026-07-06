import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type AnalysisMode = "raw" | "clean";

interface ModeCtx {
  mode: AnalysisMode;
  setMode: (m: AnalysisMode) => void;
}

const ModeContext = createContext<ModeCtx>({ mode: "clean", setMode: () => {} });
export const useMode = () => useContext(ModeContext);

/**
 * Global analysis mode — "clean" uses cleaned/normalized data, "raw" uses the
 * original extraction. Read by Q&A, forecasting, comparison and export so the
 * whole app analyzes one consistent view. Persisted; defaults to clean.
 */
export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<AnalysisMode>(
    () => ((localStorage.getItem("fra_mode") as AnalysisMode) === "raw" ? "raw" : "clean"),
  );
  useEffect(() => localStorage.setItem("fra_mode", mode), [mode]);
  return <ModeContext.Provider value={{ mode, setMode }}>{children}</ModeContext.Provider>;
}
