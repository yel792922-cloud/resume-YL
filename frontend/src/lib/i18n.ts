// Minimal bilingual label layer. The app is CN-first with an EN toggle.
import type { FactCategory, ReportType } from "../types";

export type Lang = "zh" | "en";

type Pair = { zh: string; en: string };

export const CATEGORY_LABELS: Record<FactCategory, Pair> = {
  income_statement: { zh: "利润表", en: "Income Statement" },
  balance_sheet: { zh: "资产负债表", en: "Balance Sheet" },
  cash_flow: { zh: "现金流量表", en: "Cash Flow" },
  business: { zh: "业务数据", en: "Business" },
  guidance: { zh: "业绩指引", en: "Guidance" },
  management: { zh: "管理层讨论", en: "Management" },
  risk: { zh: "风险提示", en: "Risk Factors" },
};

export const REPORT_TYPE_LABELS: Record<ReportType, Pair> = {
  annual: { zh: "年报", en: "Annual" },
  interim: { zh: "中报", en: "Interim" },
  quarterly: { zh: "季报", en: "Quarterly" },
  prospectus: { zh: "招股书", en: "Prospectus" },
  other: { zh: "其他", en: "Other" },
};

export const UI: Record<string, Pair> = {
  appName: { zh: "财报分析助手", en: "Report Analyzer" },
  home: { zh: "首页", en: "Home" },
  upload: { zh: "上传财报", en: "Upload" },
  myReports: { zh: "我的财报", en: "My Reports" },
  search: { zh: "搜索", en: "Search" },
  comparison: { zh: "对比分析", en: "Comparison" },
  favorites: { zh: "关注列表", en: "Favorites" },
  settings: { zh: "设置", en: "Settings" },
  overview: { zh: "总览", en: "Overview" },
  metrics: { zh: "财务指标", en: "Metrics" },
  management: { zh: "管理层讨论", en: "Management" },
  risks: { zh: "风险提示", en: "Risks" },
  sourceView: { zh: "原文定位", en: "Source" },
  confidence: { zh: "置信度", en: "Confidence" },
  page: { zh: "第 {n} 页", en: "Page {n}" },
  viewSource: { zh: "查看原文", en: "View source" },
  headlineMetrics: { zh: "核心速览", en: "Headline Metrics" },
  smartSummary: { zh: "智能摘要", en: "Smart Summary" },
  noData: { zh: "暂无数据", en: "No data yet" },
  export: { zh: "导出", en: "Export" },
  loadSample: { zh: "载入示例财报", en: "Load sample report" },
  traceEvery: {
    zh: "每一个数据都可追溯到原文位置",
    en: "Every number traces back to its source",
  },
};

export function t(key: keyof typeof UI, lang: Lang, vars?: Record<string, string | number>): string {
  const raw = UI[key]?.[lang] ?? key;
  if (!vars) return raw;
  return Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), raw);
}

export function categoryLabel(cat: FactCategory, lang: Lang): string {
  return CATEGORY_LABELS[cat][lang];
}

export function reportTypeLabel(rt: ReportType, lang: Lang): string {
  return REPORT_TYPE_LABELS[rt][lang];
}
