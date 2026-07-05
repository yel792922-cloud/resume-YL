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
  retry: { zh: "重试", en: "Retry" },
  loadFailed: { zh: "加载失败", en: "Failed to load" },

  // Data quality (cleaning)
  dataQuality: { zh: "数据质量", en: "Data Quality" },
  totalExtracted: { zh: "提取总数", en: "Total extracted" },
  retained: { zh: "保留", en: "Retained" },
  filtered: { zh: "已过滤", en: "Filtered" },
  cleaningRate: { zh: "清洗比例", en: "Cleaning rate" },
  normalized: { zh: "已规范化", en: "Normalized" },
  filteredItems: { zh: "被过滤的条目", en: "Filtered items" },
  reason: { zh: "原因", en: "Reason" },
  showAll: { zh: "展开全部", en: "Show all" },
  showLess: { zh: "收起", en: "Show less" },
  noNoise: { zh: "未发现噪声，所有事实均已保留", en: "No noise filtered — all facts retained" },
  cleaningNote: {
    zh: "清洗为只读操作，不会删除已存储数据；保留项均可追溯原文。",
    en: "Cleaning is read-only — it never deletes stored data; every retained fact stays source-traceable.",
  },

  // Scenario forecast
  forecast: { zh: "情景预测", en: "Scenario Forecast" },
  scenarioBase: { zh: "基准", en: "Base" },
  scenarioBull: { zh: "乐观", en: "Bull" },
  scenarioBear: { zh: "悲观", en: "Bear" },
  horizon: { zh: "预测区间", en: "Horizon" },
  expectedTrend: { zh: "预期趋势", en: "Expected trend" },
  assumptions: { zh: "关键假设", en: "Key assumptions" },
  supportingMetrics: { zh: "支撑指标", en: "Supporting metrics" },
  sourceEvidence: { zh: "原文依据", en: "Source evidence" },
  keyRisks: { zh: "关键风险", en: "Key risks" },
  managementGuidance: { zh: "管理层指引", en: "Management guidance" },
  current: { zh: "当前", en: "Current" },
  annualizedView: { zh: "年化", en: "Annualized" },
  growthOverride: { zh: "自定义增长率 (%)", en: "Growth override (%)" },
  apply: { zh: "应用", en: "Apply" },
  reset: { zh: "重置", en: "Reset" },
  forecastDisclaimer: {
    zh: "这些是基于历史趋势的情景分析估算，并非保证性预测，不构成投资建议。",
    en: "These are scenario-based analytical estimates from historical trends — not guaranteed predictions or investment advice.",
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
