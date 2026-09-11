import { describe, it, expect } from "vitest";
import { wonToEok, signedEok, decodeSelection, selectionHash } from "./format";
describe("exact money presentation", () => {
  it("retains large integer precision", () =>
    expect(wonToEok("900719925474099300000")).toBe("9,007,199,254,740.99"));
  it("rounds after unit conversion", () =>
    expect(wonToEok("123456789")).toBe("1.23"));
  it("handles losses", () => expect(signedEok("-123456789")).toBe("−1.23"));
  it("shows zero", () => expect(wonToEok("0")).toBe("0.00"));
});
describe("share links", () => {
  it("round trips selected evidence", () =>
    expect(
      decodeSelection(selectionHash("samsung", "2024-2025", "내용 변경 1")),
    ).toEqual({
      company: "samsung",
      pair: "2024-2025",
      change: "내용 변경 1",
    }));
  it("handles empty locations", () =>
    expect(decodeSelection("")).toEqual({ company: "", pair: "", change: "" }));
});
