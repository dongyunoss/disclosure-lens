import { useEffect, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  FileText,
  Info,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  excerptCitation,
  sourcePageURL,
  validateExcerpts,
  type ExcerptLibraryData,
} from "./excerpts";
export default function ExcerptLibrary({
  requestedCompany,
  onCompanyChange,
}: {
  requestedCompany: string;
  onCompanyChange: (id: string) => void;
}) {
  const [library, setLibrary] = useState<ExcerptLibraryData | null>(null),
    [error, setError] = useState("");
  const [sourceId, setSourceId] = useState(
    new URLSearchParams(location.search).get("source") || "samsung-2025",
  );
  const [excerptId, setExcerptId] = useState(
    new URLSearchParams(location.search).get("excerpt") || "business",
  );
  const [query, setQuery] = useState(""),
    [selection, setSelection] = useState(""),
    [copied, setCopied] = useState(false),
    [fallback, setFallback] = useState("");
  useEffect(() => {
    const c = new AbortController();
    fetch(import.meta.env.BASE_URL + "excerpts/library.json", {
      signal: c.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error("발췌 원문을 불러오지 못했습니다.");
        return r.json();
      })
      .then((d) => setLibrary(validateExcerpts(d)))
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, []);
  useEffect(() => {
    if (requestedCompany) {
      setSourceId(requestedCompany + "-2025");
      setExcerptId("business");
      setSelection("");
      setFallback("");
      setQuery("");
    }
  }, [requestedCompany]);
  const source = library?.sources.find((s) => s.id === sourceId);
  useEffect(() => {
    onCompanyChange(source?.companyId || sourceId.split("-")[0]);
  }, [source?.companyId, sourceId, onCompanyChange]);
  const selected =
    source?.excerpts.find((e) => e.id === excerptId) || source?.excerpts[0];
  useEffect(() => {
    if (!source || !selected) return;
    const u = new URL(location.href);
    u.searchParams.set("view", "excerpts");
    u.searchParams.set("source", source.id);
    u.searchParams.set("excerpt", selected.id);
    history.replaceState(null, "", u);
  }, [source?.id, selected?.id]);
  function reset() {
    setSelection("");
    setCopied(false);
    setFallback("");
  }
  function chooseSource(id: string) {
    setSourceId(id);
    setExcerptId("business");
    setQuery("");
    reset();
  }
  function capture(event: React.SyntheticEvent<HTMLTextAreaElement>) {
    const target = event.currentTarget;
    setSelection(
      target.value.slice(target.selectionStart, target.selectionEnd),
    );
    setCopied(false);
    setFallback("");
  }
  async function copy() {
    if (!source || !selected) return;
    const text = excerptCitation(source, selected, selection);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setFallback("");
    } catch {
      setFallback(text);
    }
  }
  const matching =
    source?.excerpts.filter(
      (e) =>
        !query ||
        [e.title, e.section, e.quote]
          .join(" ")
          .toLowerCase()
          .includes(query.toLowerCase()),
    ) || [];
  return (
    <section className="excerpt-workspace">
      <div className="notice source-real">
        <ShieldCheck size={18} />
        <span>
          <strong>실제 사업보고서 발췌</strong> · 기업 공식 IR의 PDF에서 직접
          추출했습니다. 변경점 분석의 검수 완료를 뜻하지 않습니다.
        </span>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
          <button onClick={() => location.reload()}>다시 시도</button>
        </div>
      )}
      {!library && !error && (
        <div className="empty panel">원문 발췌 목록을 불러오고 있습니다…</div>
      )}
      {library && (
        <>
          <div className="excerpt-controls panel">
            <div>
              <label htmlFor="excerpt-source">공식 사업보고서</label>
              <select
                id="excerpt-source"
                value={sourceId}
                onChange={(e) => chooseSource(e.target.value)}
              >
                {["samsung", "skhynix", "lge"].map((cid) => {
                  const docs = library.sources.filter(
                    (s) => s.companyId === cid,
                  );
                  return docs.length ? (
                    docs.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.companyName} · {s.year} 사업보고서
                      </option>
                    ))
                  ) : (
                    <option key={cid} value={cid + "-2025"} disabled>
                      SK하이닉스 · 원문 연결 준비 중
                    </option>
                  );
                })}
              </select>
            </div>
            <div className="excerpt-search">
              <label htmlFor="excerpt-search">발췌문 검색</label>
              <div>
                <Search size={17} />
                <input
                  id="excerpt-search"
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="사업 개요, 매출액, 영업이익"
                />
              </div>
            </div>
            <span className="pill">실제 보고서 {library.sources.length}개</span>
          </div>
          {!source ? (
            <div className="empty panel">
              <FileText size={30} />
              <h2>공식 원문 연결을 준비하고 있습니다</h2>
              <p>
                현재 삼성전자와 LG전자의 2024·2025 사업보고서를 확인할 수
                있습니다.
              </p>
              <button
                className="button primary"
                onClick={() => chooseSource("samsung-2025")}
              >
                삼성전자 원문 보기
              </button>
            </div>
          ) : (
            <>
              <div className="excerpt-grid">
                <aside className="excerpt-list" aria-label="발췌 항목">
                  <div className="section-heading">
                    <h2>발췌할 내용</h2>
                    <span>{matching.length}개 항목</span>
                  </div>
                  {matching.map((item) => (
                    <button
                      key={item.id}
                      className={
                        "change-card " +
                        (selected?.id === item.id ? "selected" : "")
                      }
                      onClick={() => {
                        setExcerptId(item.id);
                        reset();
                      }}
                    >
                      <span
                        className={
                          "type-badge " +
                          (item.kind === "table" ? "content" : "added")
                        }
                      >
                        {item.kind === "table" ? "재무표 행" : "사업 설명"}
                      </span>
                      <h3>{item.title}</h3>
                      <p>
                        PDF {item.page}쪽 · 문서 표기 {item.printedPage || "—"}
                        쪽
                      </p>
                      <div className="card-bottom">
                        <FileText size={13} />
                        실제 PDF에서 추출
                      </div>
                    </button>
                  ))}
                  {!matching.length && (
                    <p className="no-changes">
                      검색어에 해당하는 발췌문이 없습니다.
                    </p>
                  )}
                </aside>
                {selected && (
                  <article className="excerpt-detail panel">
                    <header>
                      <div>
                        <span className="eyebrow">OFFICIAL FILING EXCERPT</span>
                        <h2>
                          {source.companyName} {source.year} 사업보고서
                        </h2>
                        <p>{selected.section}</p>
                      </div>
                      <a
                        className="button secondary"
                        href={sourcePageURL(source, selected)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        해당 페이지 열기 <ExternalLink size={15} />
                      </a>
                    </header>
                    <div className="excerpt-body">
                      <div className="excerpt-provenance">
                        <span>
                          PDF {selected.page} / {source.pageCount}쪽
                        </span>
                        <span>문서 표기 {selected.printedPage || "—"}쪽</span>
                        <span>제출일 {source.filedAt}</span>
                      </div>
                      {selected.kind === "table" && (
                        <>
                          <div className="table-scroll">
                            <table className="excerpt-table">
                              <caption>
                                연결 손익계산서의 선택 행 · 단위:{" "}
                                {selected.unit}
                              </caption>
                              <thead>
                                <tr>
                                  <th>계정</th>
                                  {selected.headers?.map((h) => (
                                    <th key={h}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                <tr>
                                  <th>
                                    {selected.id === "revenue"
                                      ? "매출액"
                                      : "영업이익"}
                                  </th>
                                  {selected.values?.map((v, i) => (
                                    <td key={i}>{v}</td>
                                  ))}
                                </tr>
                              </tbody>
                            </table>
                          </div>
                          <p className="excerpt-small">
                            원문 열의 순서를 유지했습니다.{" "}
                            <a
                              href={
                                source.url + "#page=" + selected.statementPage
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              기간·단위가 기재된 표 머리말 확인 ↗
                            </a>
                          </p>
                        </>
                      )}
                      <label className="excerpt-label" htmlFor="excerpt-text">
                        {selected.kind === "table"
                          ? "원문 표 행 발췌"
                          : "원문 문장 발췌"}
                      </label>
                      <textarea
                        id="excerpt-text"
                        className="excerpt-quote"
                        readOnly
                        value={selected.quote}
                        onSelect={capture}
                        rows={selected.kind === "table" ? 3 : 5}
                      />
                      <p className="excerpt-small">
                        필요한 부분만 드래그하거나 키보드로 선택할 수 있습니다.
                        선택하지 않으면 발췌문 전체를 복사합니다.
                      </p>
                      <div className="excerpt-copy-row">
                        <span>
                          {selection
                            ? "선택한 부분 " + selection.length + "자"
                            : "발췌문 전체"}{" "}
                          · 출처 자동 포함
                        </span>
                        <button className="button primary" onClick={copy}>
                          {copied ? <Check size={17} /> : <Copy size={17} />}{" "}
                          {copied ? "출처와 함께 복사했어요" : "출처 포함 복사"}
                        </button>
                      </div>
                      {fallback && (
                        <div role="status" className="copy-fallback">
                          <p>
                            자동 복사가 허용되지 않았습니다. 아래 내용을 선택해
                            복사하세요.
                          </p>
                          <textarea
                            aria-label="직접 복사할 발췌문"
                            readOnly
                            value={fallback}
                            rows={8}
                            onFocus={(e) => e.target.select()}
                          />
                        </div>
                      )}
                      <div className="excerpt-source-note">
                        <Info size={16} />
                        <div>
                          기업 공식 IR 게시본 기준입니다. 최종 정정 여부는
                          확인되지 않았습니다.
                          <br />
                          확인일 {source.retrievedAt.slice(0, 10)} ·{" "}
                          <a
                            href={source.listingUrl}
                            target="_blank"
                            rel="noreferrer"
                          >
                            기업 공식 보고서 목록 ↗
                          </a>
                        </div>
                      </div>
                    </div>
                  </article>
                )}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
