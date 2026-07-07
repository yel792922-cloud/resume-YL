// Bilingual labels for report-profile options and metric kinds.
import type { Lang } from "./i18n";

type Pair = { zh: string; en: string };

export const BUSINESS_STRUCTURE: Record<string, Pair> = {
  auto: { zh: "自动检测", en: "Auto-detect" },
  single: { zh: "单一业务", en: "Single business" },
  multi: { zh: "多业务", en: "Multi-business" },
  conglomerate: { zh: "高度多元 / 集团", en: "Conglomerate" },
  unknown: { zh: "不确定", en: "Not sure" },
};

export const GEO_SCOPE: Record<string, Pair> = {
  auto: { zh: "自动检测", en: "Auto-detect" },
  single_region: { zh: "单一地区", en: "Single region" },
  multi_region: { zh: "多地区 / 跨境", en: "Multi-region" },
  global: { zh: "全球", en: "Global" },
  unknown: { zh: "不确定", en: "Not sure" },
};

export const INDUSTRY: Record<string, Pair> = {
  auto: { zh: "自动检测", en: "Auto-detect" },
  bank: { zh: "银行 / 金融", en: "Bank / financial" },
  insurance: { zh: "保险", en: "Insurance" },
  hospitality: { zh: "酒店 / 旅游", en: "Hotel / travel" },
  internet: { zh: "互联网 / 媒体", en: "Internet / media" },
  saas: { zh: "SaaS / 云 / 软件", en: "SaaS / cloud" },
  retail: { zh: "零售 / 消费", en: "Retail / consumer" },
  manufacturing: { zh: "制造 / 工业", en: "Manufacturing" },
  other: { zh: "其他", en: "Other" },
  unknown: { zh: "不确定", en: "Not sure" },
};

export const REPORT_TYPE: Record<string, Pair> = {
  auto: { zh: "自动检测", en: "Auto-detect" },
  annual: { zh: "年报", en: "Annual" },
  interim: { zh: "半年报", en: "Half-year" },
  quarterly: { zh: "季报", en: "Quarterly" },
  other: { zh: "其他", en: "Other" },
  unknown: { zh: "不确定", en: "Not sure" },
};

export const COMPLEXITY: Record<string, Pair> = {
  simple: { zh: "简单报告", en: "Simple report" },
  complex: { zh: "复杂报告", en: "Complex report" },
};

// Metric-kind chips. Only kinds worth flagging get a visible chip (amount is the
// default and stays unlabeled to reduce noise).
export const METRIC_KIND: Record<string, { zh: string; en: string; cls: string } | undefined> = {
  ratio: { zh: "比率", en: "Ratio", cls: "amber" },
  growth: { zh: "增长率", en: "Growth", cls: "green" },
  per_share: { zh: "每股", en: "Per share", cls: "gray" },
  count: { zh: "数量", en: "Count", cls: "gray" },
  segment_total: { zh: "分部合计", en: "Segment total", cls: "green" },
  geography_total: { zh: "地区合计", en: "Geography total", cls: "amber" },
  regulatory: { zh: "监管 / 资本", en: "Regulatory", cls: "blue" },
  user: { zh: "运营 / 用户", en: "Operational", cls: "gray" },
  uncertain: { zh: "待确认", en: "Uncertain", cls: "red" },
};

export function plabel(map: Record<string, Pair>, id: string, lang: Lang): string {
  return map[id]?.[lang] ?? id;
}
