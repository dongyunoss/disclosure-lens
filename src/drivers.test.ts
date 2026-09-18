import { describe, it, expect } from "vitest";
import raw from "../public/drivers/samsung-2025-drivers-v1.json";
import {
  dominantPart,
  monitorLabel,
  validateDrivers,
  type DriverAnalysis,
} from "./drivers";
const data = () => structuredClone(raw) as DriverAnalysis;
describe("financial driver analysis", () => {
  it("rejects a mismatched original PDF cell", () => {
    const d = data();
    d.tableOverlays![0].highlights[0].rawValue = "1";
    expect(() => validateDrivers(d)).toThrow();
  });
  it("rejects highlights outside the original table", () => {
    const d = data();
    d.tableOverlays![0].highlights[0].rect.x = 1;
    expect(() => validateDrivers(d)).toThrow();
  });
  it("validates actual PDF arithmetic without floating point", () => {
    const d = validateDrivers(data());
    expect(d.metrics[0].delta).toBe("13921017000000");
    expect(dominantPart(d.metrics[0])?.label).toBe("영업현금흐름 변화");
    expect(dominantPart(d.metrics[1])?.label).toBe("미주");
  });
  it("rejects changed totals", () => {
    const d = data();
    d.metrics[0].after = "1";
    expect(() => validateDrivers(d)).toThrow();
  });
  it("rejects invented component contributions", () => {
    const d = data();
    d.metrics[0].components[0].impact = "0";
    expect(() => validateDrivers(d)).toThrow();
  });
  it("rejects missing evidence references", () => {
    const d = data();
    d.evidence = [];
    expect(() => validateDrivers(d)).toThrow();
  });
  it("rejects nonofficial links", () => {
    const d = data();
    d.source.url = "javascript:alert(1)";
    expect(() => validateDrivers(d)).toThrow();
  });
  it("does not display live status for a stale worker", () => {
    const t = Date.parse("2026-09-18T00:00:00Z"),
      s = {
        state: "polling",
        checkedAt: new Date(t).toISOString(),
        intervalSeconds: 300,
        message: "",
        filings: [],
      };
    expect(monitorLabel(s, t + 60000)).toBe("5분 간격 확인 중");
    expect(monitorLabel(s, t + 16 * 60000)).toBe("감지 상태 확인 필요");
    expect(monitorLabel(null)).toBe("실시간 감지 연결 전");
  });
});
