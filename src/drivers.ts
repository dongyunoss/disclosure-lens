export type DriverEvidence = {
  id: string;
  quote: string;
  sourceUrl: string;
  section: string;
  unit: string;
  columns: string[];
};
export type DriverPart = {
  label: string;
  before: string;
  after: string;
  delta: string;
  impact: string;
  evidence: string[];
  share?: string | null;
};
export type DriverMetric = {
  id: string;
  label: string;
  before: string;
  after: string;
  delta: string;
  percent: string | null;
  definition: string;
  caveat: string;
  components: DriverPart[];
  evidence?: string[];
};
export type DriverAnalysis = {
  schemaVersion: 1;
  id: string;
  companyId: string;
  companyName: string;
  title: string;
  status: "automatic" | "source_pending";
  generatedAt: string;
  periodBefore: string;
  periodAfter: string;
  basis: string;
  currency: string;
  source: {
    title: string;
    url: string;
    filedAt: string;
    checkedAt: string;
    latestCorrectionVerified: boolean;
  };
  comparisonNote: string;
  metrics: DriverMetric[];
  evidence: DriverEvidence[];
  limitations: string[];
};
export type DriverCatalog = {
  schemaVersion: 1;
  items: {
    id: string;
    companyId: string;
    companyName: string;
    title: string;
    path: string;
    status: string;
  }[];
};
export type MonitorStatus = {
  state: string;
  checkedAt: string | null;
  intervalSeconds: number;
  message: string;
  filings: {
    receipt: string;
    title: string;
    url: string;
    status: string;
    message: string;
  }[];
};
export function safeSource(value: string) {
  const url = new URL(value);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    !["images.samsung.com", "www.lge.co.kr", "dart.fss.or.kr"].includes(
      url.hostname,
    )
  )
    throw new Error("공식 근거 주소가 아닙니다.");
  return value;
}
export function validateDrivers(data: DriverAnalysis): DriverAnalysis {
  if (
    data.schemaVersion !== 1 ||
    !["automatic", "source_pending"].includes(data.status) ||
    data.basis !== "연결" ||
    data.currency !== "KRW" ||
    !data.metrics?.length
  )
    throw new Error("분석 데이터 형식 오류");
  safeSource(data.source.url);
  const ids = new Set(
    data.evidence.map((e) => {
      safeSource(e.sourceUrl);
      if (!e.quote) throw new Error("원문 누락");
      return e.id;
    }),
  );
  if (ids.size !== data.evidence.length) throw new Error("중복 근거");
  for (const m of data.metrics) {
    for (const value of [
      m.before,
      m.after,
      m.delta,
      ...m.components.flatMap((p) => [p.before, p.after, p.delta, p.impact]),
    ])
      if (!/^-?\d+$/.test(value)) throw new Error("정수 금액 오류");
    if (BigInt(m.after) - BigInt(m.before) !== BigInt(m.delta))
      throw new Error("증감액 검증 실패");
    if (
      m.components.length &&
      m.components.reduce((sum, p) => sum + BigInt(p.impact), 0n) !==
        BigInt(m.delta)
    )
      throw new Error("기여도 합계 검증 실패");
    for (const p of m.components) {
      if (BigInt(p.after) - BigInt(p.before) !== BigInt(p.delta))
        throw new Error("항목 증감액 검증 실패");
      if (p.evidence.some((id) => !ids.has(id)))
        throw new Error("근거 연결 오류");
    }
    if (m.id === "fcf") {
      if (m.components.length !== 3) throw new Error("FCF 항목 누락");
      const [cfo, ppe, intangible] = m.components;
      for (const key of ["before", "after"] as const)
        if (
          BigInt(m[key]) !==
          BigInt(cfo[key]) - BigInt(ppe[key]) - BigInt(intangible[key])
        )
          throw new Error("FCF 정의 검증 실패");
    }
  }
  return data;
}
export function monitorLabel(status: MonitorStatus | null, time = Date.now()) {
  if (!status || status.state === "not_configured")
    return "실시간 감지 연결 전";
  const checked = Date.parse(status.checkedAt || "");
  if (!Number.isFinite(checked) || time - checked > 15 * 60 * 1000)
    return "감지 상태 확인 필요";
  return status.state === "degraded"
    ? "일부 공시 확인 지연"
    : "5분 간격 확인 중";
}
export function dominantPart(metric: DriverMetric) {
  const direction = BigInt(metric.delta);
  if (direction === 0n) return null;
  return (
    metric.components
      .filter((p) =>
        direction > 0n ? BigInt(p.impact) > 0n : BigInt(p.impact) < 0n,
      )
      .sort((a, b) => {
        const x = BigInt(a.impact),
          y = BigInt(b.impact);
        const ax = x < 0n ? -x : x,
          ay = y < 0n ? -y : y;
        return ax > ay ? -1 : ax < ay ? 1 : 0;
      })[0] || null
  );
}
