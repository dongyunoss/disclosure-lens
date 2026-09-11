import type { Catalog, Comparison } from "./types";
const fail = (): never => {
  throw new Error(
    "데이터 형식이 올바르지 않습니다. 검수된 버전을 다시 확인해 주세요.",
  );
};
export function checkCatalog(value: Catalog, demo: boolean): Catalog {
  if (
    value?.schemaVersion !== 1 ||
    !Array.isArray(value.companies) ||
    value.companies.length !== 3
  )
    fail();
  const companies = new Set<string>();
  for (const c of value.companies) {
    if (
      !["samsung", "skhynix", "lge"].includes(c.id) ||
      companies.has(c.id) ||
      !Array.isArray(c.comparisons)
    )
      fail();
    companies.add(c.id);
    for (const p of c.comparisons)
      if (
        !p.id ||
        !Array.isArray(p.years) ||
        p.years[0] !== 2024 ||
        p.years[1] !== 2025 ||
        !new RegExp(
          "^" + (demo ? "demo" : "data") + "/[a-zA-Z0-9_/-]+\\.json$",
        ).test(p.path) ||
        p.mode !== (demo ? "demo" : "reviewed")
      )
        fail();
  }
  return value;
}
export function checkComparison(value: Comparison, demo: boolean): Comparison {
  if (
    value?.schemaVersion !== 1 ||
    value.mode !== (demo ? "demo" : "reviewed") ||
    !Array.isArray(value.reports) ||
    value.reports.length !== 2 ||
    !Array.isArray(value.financials) ||
    !Array.isArray(value.changes) ||
    !Array.isArray(value.evidence)
  )
    fail();
  const reports = new Set(value.reports.map((r) => r.id));
  const blocks = new Map(value.evidence.map((b) => [b.id, b]));
  if (
    blocks.size !== value.evidence.length ||
    value.reports[0].year !== 2024 ||
    value.reports[1].year !== 2025 ||
    !Array.isArray(value.coverage)
  )
    fail();
  for (const r of value.reports) {
    if (r.companyId !== value.companyId) fail();
    if (
      !demo &&
      (!/^\d{14}$/.test(r.receipt || "") ||
        r.dartUrl !==
          "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + r.receipt)
    )
      fail();
  }
  for (const b of value.evidence)
    if (
      !reports.has(b.reportId) ||
      typeof b.text !== "string" ||
      (b.kind === "table" &&
        (!Array.isArray(b.rows) || !Array.isArray(b.headers)))
    )
      fail();
  for (const f of value.financials) {
    if (
      ![f.before, f.after, f.delta].every(
        (x) => typeof x === "string" && /^-?\d+$/.test(x),
      ) ||
      f.basis !== "CFS" ||
      f.currency !== "KRW" ||
      (f.percent !== null && !/^-?\d+(\.\d+)?$/.test(f.percent))
    )
      fail();
    if (
      blocks.get(f.beforeBlockId)?.reportId !== value.reports[0].id ||
      blocks.get(f.afterBlockId)?.reportId !== value.reports[1].id
    )
      fail();
  }
  for (const c of value.changes) {
    if (
      !["content", "added", "removed", "wording", "uncertain"].includes(
        c.kind,
      ) ||
      !Array.isArray(c.before) ||
      !Array.isArray(c.after)
    )
      fail();
    for (const [side, report] of [
      [c.before, value.reports[0]],
      [c.after, value.reports[1]],
    ] as const)
      for (const ref of side) {
        const b = blocks.get(ref.blockId);
        if (
          !b ||
          b.reportId !== report.id ||
          typeof ref.quote !== "string" ||
          !ref.quote ||
          !b.text.includes(ref.quote)
        )
          fail();
      }
  }
  return value;
}
