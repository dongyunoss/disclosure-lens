export type SourceExcerpt = {
  id: string;
  kind: "paragraph" | "table";
  title: string;
  section: string;
  quote: string;
  page: number;
  printedPage: string | null;
  values?: string[];
  headers?: string[];
  unit?: string;
  basis?: string;
  statementPage?: number;
};
export type OfficialSource = {
  id: string;
  companyId: string;
  companyName: string;
  year: number;
  url: string;
  listingUrl: string;
  filedAt: string;
  retrievedAt: string;
  sha256: string;
  pageCount: number;
  latestCorrectionVerified: false;
  excerpts: SourceExcerpt[];
};
export type ExcerptLibraryData = {
  schemaVersion: 1;
  sources: OfficialSource[];
  unavailable: { companyId: string; companyName: string; reason: string }[];
};
export function sourcePageURL(source: OfficialSource, item: SourceExcerpt) {
  return source.url + "#page=" + item.page;
}
export function excerptCitation(
  source: OfficialSource,
  item: SourceExcerpt,
  selection = "",
) {
  const selected = selection.trim();
  if (selected && !item.quote.includes(selected))
    throw new Error("선택한 문장이 발췌 원문에 없습니다.");
  const quote = selected || item.quote;
  const unit =
    item.kind === "table"
      ? "\n기준: 연결 · 단위: " +
        item.unit +
        "\n열 순서: " +
        item.headers!.join(" / ")
      : "";
  return (
    quote +
    unit +
    "\n\n출처: " +
    source.companyName +
    " " +
    source.year +
    " 사업보고서\n" +
    item.section +
    "\nPDF " +
    item.page +
    "쪽" +
    (item.printedPage ? " (문서 표기 " + item.printedPage + "쪽)" : "") +
    "\n보고서 제출일: " +
    source.filedAt +
    "\n" +
    sourcePageURL(source, item) +
    "\n기업 공식 IR 게시본 · 최종 정정 여부 미확인"
  );
}
export function validateExcerpts(data: ExcerptLibraryData) {
  if (
    data?.schemaVersion !== 1 ||
    !Array.isArray(data.sources) ||
    !Array.isArray(data.unavailable)
  )
    throw new Error("발췌 데이터 형식이 올바르지 않습니다.");
  for (const source of data.sources) {
    const url = new URL(source.url);
    if (
      url.protocol !== "https:" ||
      !["images.samsung.com", "www.lge.co.kr"].includes(url.hostname) ||
      !/^[a-f0-9]{64}$/.test(source.sha256) ||
      source.latestCorrectionVerified !== false ||
      !Array.isArray(source.excerpts)
    )
      throw new Error("공식 원문 출처를 확인할 수 없습니다.");
    for (const item of source.excerpts) {
      if (
        !item.quote ||
        !Number.isInteger(item.page) ||
        item.page < 1 ||
        item.page > source.pageCount ||
        !["paragraph", "table"].includes(item.kind)
      )
        throw new Error("발췌문 또는 페이지가 올바르지 않습니다.");
      if (
        item.kind === "table" &&
        (!item.values ||
          item.values.length !== 3 ||
          !item.headers ||
          item.headers.length !== 3 ||
          !item.values.every((v) => item.quote.includes(v)))
      )
        throw new Error("표 행을 확인할 수 없습니다.");
    }
  }
  return data;
}
