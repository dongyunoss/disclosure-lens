import { describe, it, expect } from "vitest";
import sample from "../public/demo/samsung-2024-2025-demo.json";
import catalog from "../public/demo/catalog.json";
import { checkCatalog, checkComparison } from "./data";
import type { Catalog, Comparison } from "./types";
describe("data boundary", () => {
  it("accepts valid demo data", () =>
    expect(checkComparison(sample as Comparison, true).mode).toBe("demo"));
  it("rejects demo in reviewed mode", () =>
    expect(() => checkComparison(sample as Comparison, false)).toThrow());
  it("accepts the three supported companies", () =>
    expect(checkCatalog(catalog as Catalog, true).companies).toHaveLength(3));
  it("rejects arbitrary catalog paths", () => {
    const c = structuredClone(catalog) as Catalog;
    c.companies[0].comparisons[0].path = "../private/draft.json";
    expect(() => checkCatalog(c, true)).toThrow();
  });
  it("rejects invalid amounts before rendering", () => {
    const c = structuredClone(sample) as Comparison;
    c.financials[0].before = "NaN";
    expect(() => checkComparison(c, true)).toThrow();
  });
  it("rejects cross-report evidence", () => {
    const c = structuredClone(sample) as Comparison;
    c.changes[0].before[0].blockId = c.changes[0].after[0].blockId;
    expect(() => checkComparison(c, true)).toThrow();
  });
  it("rejects invented quotes", () => {
    const c = structuredClone(sample) as Comparison;
    c.changes[0].after[0].quote = "원문에 없는 설명";
    expect(() => checkComparison(c, true)).toThrow();
  });
});
