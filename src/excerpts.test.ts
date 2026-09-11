import { describe, it, expect } from "vitest";
import raw from "../public/excerpts/library.json";
import {
  excerptCitation,
  sourcePageURL,
  validateExcerpts,
  type ExcerptLibraryData,
} from "./excerpts";
const library = raw as ExcerptLibraryData,
  source = library.sources[0],
  item = source.excerpts[0];
describe("official source excerpts", () => {
  it("contains four real reports with three passages each", () => {
    expect(validateExcerpts(library).sources).toHaveLength(4);
    expect(library.sources.flatMap((s) => s.excerpts)).toHaveLength(12);
  });
  it("links physical PDF pages, not printed page labels", () =>
    expect(sourcePageURL(source, item)).toBe(source.url + "#page=28"));
  it("includes quote, report, page and source in copied content", () => {
    const result = excerptCitation(source, item);
    expect(result).toContain(item.quote);
    expect(result).toContain("삼성전자 2024 사업보고서");
    expect(result).toContain("문서 표기 25쪽");
    expect(result).toContain(source.url);
  });
  it("allows only verbatim partial excerpts", () => {
    expect(excerptCitation(source, item, item.quote.slice(0, 5))).toContain(
      item.quote.slice(0, 5),
    );
    expect(() => excerptCitation(source, item, "없는 문장")).toThrow();
  });
  it("includes currency unit and fiscal columns for table rows", () => {
    const text = excerptCitation(source, source.excerpts[1]);
    expect(text).toContain("단위: 백만원");
    expect(text).toContain("2024 / 2023 / 2022");
  });
  it("rejects a non-official URL", () => {
    const x = structuredClone(library);
    x.sources[0].url = "https://example.com/report.pdf";
    expect(() => validateExcerpts(x)).toThrow();
  });
  it("rejects out of range pages", () => {
    const x = structuredClone(library);
    x.sources[0].excerpts[0].page = 9999;
    expect(() => validateExcerpts(x)).toThrow();
  });
  it("rejects changed table values", () => {
    const x = structuredClone(library);
    x.sources[0].excerpts[1].values![0] = "999999";
    expect(() => validateExcerpts(x)).toThrow();
  });
});
