import {
  safeSource,
  validateDrivers,
  type DriverAnalysis,
  type TableOverlay,
  type DriverMetric,
} from "./drivers";

export type ReviewFact = {
  id: string;
  label: string;
  before: string;
  after: string;
  tableId: string;
  quote: string;
  kind: "instant" | "duration";
  cashOutflow: boolean;
};
export type ReviewStatus =
  | "attention"
  | "movement"
  | "not_triggered"
  | "unavailable";
export type Finding = {
  id: string;
  category: string;
  title: string;
  status: ReviewStatus;
  factIds: string[];
  criterion: string;
  why: string;
  nextCheck: string;
  caveat: string;
  unavailableReason?: string;
  stats: { label: string; value: string; unit: string }[];
};
export type Review = {
  schemaVersion: 1;
  ruleVersion: string;
  id: string;
  companyId: string;
  companyName: string;
  beforeYear: number;
  afterYear: number;
  basis: string;
  currency: string;
  periodType: string;
  source: DriverAnalysis["source"];
  facts: ReviewFact[];
  tables: TableOverlay[];
  findings: Finding[];
  coverageGaps: string[];
};
export const statusLabels: Record<ReviewStatus, string> = {
  attention: "확인 우선",
  movement: "주요 변화",
  not_triggered: "설정 기준 미해당",
  unavailable: "판단 보류",
};
export function tableMetric(facts: ReviewFact[], id: string): DriverMetric {
  const components = facts
    .filter((f) => f.tableId === id)
    .map((f) => ({
      label: f.label,
      before: f.before,
      after: f.after,
      delta: String(BigInt(f.after) - BigInt(f.before)),
      impact: "0",
      evidence: [],
    }));
  return {
    id,
    label: "원문 재무 항목",
    before: "0",
    after: "0",
    delta: "0",
    percent: null,
    definition: "",
    caveat: "",
    components,
  };
}
export function validateReview(data: Review): Review {
  if (
    data.schemaVersion !== 1 ||
    data.ruleVersion !== "review-rules-1" ||
    data.basis !== "연결" ||
    data.currency !== "KRW" ||
    data.periodType !== "annual" ||
    !data.facts?.length ||
    !data.findings?.length
  )
    throw new Error("투자 검토 데이터 형식 오류");
  safeSource(data.source.url);
  const ids = new Set(data.facts.map((f) => f.id));
  if (
    ids.size !== data.facts.length ||
    new Set(data.tables.map((t) => t.id)).size !== data.tables.length ||
    new Set(data.findings.map((f) => f.id)).size !== data.findings.length
  )
    throw new Error("중복 검토 항목");
  for (const f of data.facts) {
    if (
      !f.quote ||
      ![f.before, f.after].every((v) => /^-?\d+$/.test(v)) ||
      !data.tables.some((t) => t.id === f.tableId)
    )
      throw new Error("재무 항목 근거 누락");
  }
  for (const item of data.findings) {
    if (
      !Object.hasOwn(statusLabels, item.status) ||
      item.factIds.some((id) => !ids.has(id)) ||
      !item.criterion ||
      !item.nextCheck ||
      (item.status !== "unavailable" && !item.factIds.length)
    )
      throw new Error("검토 기준 또는 근거 연결 오류");
    if (item.stats.some((s) => !/^[-]?\d+(\.\d+)?$/.test(s.value)))
      throw new Error("검토 비율 오류");
  }
  // Reuse the exact KRW-to-source-cell checks used by the financial bridges.
  for (const t of data.tables) {
    if (t.metricId !== t.id) throw new Error("원문 표 식별자 오류");
    validateDrivers({
      schemaVersion: 1,
      status: "automatic",
      basis: "연결",
      currency: "KRW",
      source: data.source,
      metrics: [tableMetric(data.facts, t.id)],
      evidence: [],
      tableOverlays: [t],
    } as unknown as DriverAnalysis);
  }
  return data;
}
