import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ExternalLink,
  FileText,
  Info,
  Layers3,
  Link2,
  Search,
  ShieldCheck,
} from "lucide-react";
import type { Catalog, Change, Comparison, EvidenceBlock, Kind } from "./types";
import { decodeSelection, selectionHash, signedEok, wonToEok } from "./format";
import { useEvidenceTools } from "./webmcp";
import { checkCatalog, checkComparison } from "./data";
import ExcerptLibrary from "./ExcerptLibrary";
import DriversView from "./DriversView";
import "./excerpts.css";

const kinds: Record<Kind, string> = {
  content: "내용 변경",
  added: "추가",
  removed: "삭제",
  wording: "표현 변경",
  uncertain: "확인 필요",
};
const base = import.meta.env.BASE_URL;
async function readJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(base + path, { signal });
  if (!res.ok)
    throw new Error(
      "데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
    );
  return res.json();
}
function Marked({ text, quotes }: { text: string; quotes: string[] }) {
  const ranges = quotes
    .filter(Boolean)
    .flatMap((q) => {
      const at = text.indexOf(q);
      return at < 0 ? [] : [{ start: at, end: at + q.length }];
    })
    .sort((a, b) => a.start - b.start);
  const output: React.ReactNode[] = [];
  let end = 0;
  for (const r of ranges) {
    if (r.start < end) continue;
    output.push(
      text.slice(end, r.start),
      <mark key={r.start}>{text.slice(r.start, r.end)}</mark>,
    );
    end = r.end;
  }
  output.push(text.slice(end));
  return <>{output}</>;
}
function Evidence({
  block,
  quotes,
  selectedRow,
}: {
  block: EvidenceBlock;
  quotes: string[];
  selectedRow?: number;
}) {
  return (
    <article className="source-block" id={block.id}>
      <div className="section-path">{block.section}</div>
      {block.contextBefore && <p className="context">{block.contextBefore}</p>}
      {block.kind === "table" ? (
        <>
          <div className="table-scroll">
            <table className="source-table">
              <thead>
                <tr>
                  {block.headers?.map((h, i) => (
                    <th key={i}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {block.rows?.map((r, i) => (
                  <tr
                    key={i}
                    className={selectedRow === i ? "highlight-row" : ""}
                  >
                    {r.map((cell, j) => (
                      <td key={j}>
                        <Marked text={cell} quotes={quotes} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <small>{block.unit}</small>
        </>
      ) : (
        <p className="source-text">
          <Marked text={block.text} quotes={quotes} />
        </p>
      )}
      {block.contextAfter && <p className="context">{block.contextAfter}</p>}
    </article>
  );
}
export default function App() {
  const [driversCompany, setDriversCompany] = useState(
    new URLSearchParams(location.search).get("company") || "samsung",
  );
  const [driversMode, setDriversMode] = useState(
    new URLSearchParams(location.search).get("view") === "drivers",
  );
  const [excerptCompany, setExcerptCompany] = useState(
    new URLSearchParams(location.search).get("source")?.split("-")[0] ||
      "samsung",
  );
  const [excerptMode, setExcerptMode] = useState(
    new URLSearchParams(location.search).get("view") === "excerpts",
  );
  function navigateView(view: "compare" | "excerpts" | "help" | "drivers") {
    setDriversMode(view === "drivers");
    setExcerptMode(view === "excerpts");
    setHelp(view === "help");
    const u = new URL(location.href);
    u.searchParams.delete("source");
    u.searchParams.delete("excerpt");
    for (const key of ["analysis", "metric", "company", "part"])
      u.searchParams.delete(key);
    if (view === "excerpts" || view === "drivers") {
      u.searchParams.set("view", view);
      u.searchParams.delete("demo");
      u.hash = "";
      setDemo(false);
      setSelection(decodeSelection(""));
    } else u.searchParams.delete("view");
    history.replaceState(null, "", u);
  }
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [data, setData] = useState<Comparison | null>(null),
    [error, setError] = useState("");
  const [demo, setDemo] = useState(
    new URLSearchParams(location.search).get("demo") === "1",
  );
  const [selection, setSelection] = useState(decodeSelection(location.hash)),
    [filter, setFilter] = useState("all"),
    [wording, setWording] = useState(false),
    [side, setSide] = useState(1),
    [copied, setCopied] = useState(false),
    [help, setHelp] = useState(false);
  const viewer = useRef<HTMLElement>(null);
  useEffect(() => {
    const handler = () => setSelection(decodeSelection(location.hash));
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);
  useEffect(() => {
    const c = new AbortController();
    setError("");
    setCatalog(null);
    setData(null);
    readJSON<Catalog>(
      demo ? "demo/catalog.json" : "data/catalog.json",
      c.signal,
    )
      .then((v) => setCatalog(checkCatalog(v, demo)))
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [demo]);
  const company =
    catalog?.companies.find((c) => c.id === selection.company) ||
    catalog?.companies[0];
  const pair =
    company?.comparisons.find((p) => p.id === selection.pair) ||
    company?.comparisons[0];
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    if (pair)
      readJSON<Comparison>(pair.path, c.signal)
        .then((d) => {
          setData(checkComparison(d, demo));
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    return () => c.abort();
  }, [pair?.path, demo]);
  const change = data?.changes.find((c) => c.id === selection.change);
  const finance = data?.financials.find((c) => c.id === selection.change);
  const selected = change || finance;
  const visible =
    data?.changes.filter(
      (c) =>
        (filter === "all" || c.kind === filter) &&
        (wording || c.kind !== "wording"),
    ) || [];
  function choose(id: string, pairId = "", changeId = "") {
    location.hash = selectionHash(id, pairId, changeId);
    setFilter("all");
  }
  function selectChange(id: string) {
    if (company && pair) location.hash = selectionHash(company.id, pair.id, id);
    setTimeout(() => {
      viewer.current?.focus({ preventScroll: true });
      if (window.innerWidth <= 620)
        viewer.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 20);
  }
  function toggleDemo(value: boolean) {
    const u = new URL(location.href);
    if (value) u.searchParams.set("demo", "1");
    else u.searchParams.delete("demo");
    u.hash = "";
    history.replaceState(null, "", u);
    setSelection(decodeSelection(""));
    setDemo(value);
    setFilter("all");
  }
  async function share() {
    try {
      await navigator.clipboard.writeText(location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError(
        "주소 복사 권한이 없습니다. 브라우저 주소창의 URL을 복사해 주세요.",
      );
    }
  }
  const title = change?.title || finance?.label || "변경점을 선택해 주세요";
  useEvidenceTools(data, selectChange);
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="공시렌즈 처음으로">
          <span className="brand-icon">
            <Layers3 size={23} />
          </span>
          공시렌즈<span className="beta">BETA</span>
        </a>
        <div className="side-caption">DISCLOSURE RESEARCH</div>
        <button
          className={
            "nav-item " +
            (!help && !excerptMode && !driversMode ? "active" : "")
          }
          onClick={() => navigateView("compare")}
        >
          <Search size={18} />
          공시 비교
          <ArrowRight size={15} />
        </button>
        <button
          className={"nav-item " + (driversMode ? "active" : "")}
          onClick={() => navigateView("drivers")}
        >
          <Layers3 size={18} /> 수치 변화 원인
        </button>
        <button
          className={"nav-item " + (help && !excerptMode ? "active" : "")}
          onClick={() => navigateView("help")}
        >
          <BookOpen size={18} />
          분석 기준 안내
        </button>
        <button
          className={"nav-item " + (excerptMode ? "active" : "")}
          onClick={() => navigateView("excerpts")}
        >
          <FileText size={18} />
          원문 발췌
        </button>
        <div className="side-label">
          분석 대상 기업 <span>03</span>
        </div>
        {catalog?.companies.map((c) => (
          <button
            key={c.id}
            className={
              "company " +
              ((driversMode
                ? driversCompany
                : excerptMode
                  ? excerptCompany
                  : company?.id) === c.id
                ? "selected"
                : "")
            }
            onClick={() => {
              if (driversMode) {
                setDriversCompany(c.id);
                return;
              }
              choose(c.id, c.comparisons[0]?.id);
              setHelp(false);
            }}
          >
            <span className={"company-mark " + c.id}>
              {c.id === "samsung" ? "S" : c.id === "skhynix" ? "sk" : "LG"}
            </span>
            <span>
              {c.name}
              <small>{c.stockCode} · KOSPI</small>
            </span>
            {(driversMode
              ? driversCompany
              : excerptMode
                ? excerptCompany
                : company?.id) === c.id && <span className="selected-line" />}
          </button>
        ))}
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <strong>근거에서 시작하는 리서치</strong>
          <p>
            변화 설명과 원문을
            <br />한 화면에서 확인하세요.
          </p>
          <div>사업보고서 · 연결 기준</div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            리서치 워크스페이스 <span className="slash">/</span>{" "}
            <strong>
              {driversMode
                ? "수치 변화 원인"
                : excerptMode
                  ? "원문 발췌"
                  : help
                    ? "분석 기준"
                    : "사업보고서 비교"}
            </strong>
          </span>
          <span className="top-note">
            <Layers3 size={15} />
            {driversMode ? "공시 기반 원인 분석" : "2024 — 2025"}
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {driversMode
                  ? "WHAT MOVED THE NUMBERS"
                  : excerptMode
                    ? "OFFICIAL FILING EXCERPTS"
                    : "ANNUAL REPORT COMPARISON"}
              </div>
              <h1>
                {driversMode
                  ? "숫자 뒤의 이유를 확인하세요"
                  : excerptMode
                    ? "실제 공시에서 근거를 발췌하세요"
                    : help
                      ? "분석 기준 안내"
                      : "무엇이 달라졌을까요?"}
              </h1>
              <p>
                {driversMode
                  ? "현금흐름과 매출 변화를 분해하고, 실제 공시 근거로 확인합니다."
                  : excerptMode
                    ? "사업 설명과 재무표를 선택하고, 출처와 함께 복사하세요."
                    : "두 사업보고서의 변화와 그 근거를 함께 읽어보세요."}
              </p>
            </div>
            <button className="button secondary" onClick={share}>
              {copied ? <Check size={16} /> : <Link2 size={16} />}{" "}
              {copied
                ? "주소를 복사했어요"
                : driversMode
                  ? "분석 링크 복사"
                  : excerptMode
                    ? "발췌 링크 복사"
                    : "비교 링크 복사"}
            </button>
          </div>
          {!excerptMode && !driversMode && (
            <div className={"notice " + (demo ? "demo" : "")} role="status">
              <Info size={18} />
              <span>
                {demo ? (
                  <>
                    <strong>기능 미리보기</strong> · 모든 수치와 문장은 가상
                    예시이며 실제 기업 공시가 아닙니다.
                  </>
                ) : (
                  <>
                    <strong>자동 비교 검수 준비 중</strong> · 원문 발췌에서 실제
                    사업보고서를 확인할 수 있습니다.
                  </>
                )}
              </span>
              <button onClick={() => toggleDemo(!demo)}>
                {demo ? "실제 공시 보기" : "가상 예시로 둘러보기"}
                <ArrowRight size={15} />
              </button>
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => location.reload()}>다시 시도</button>
            </div>
          )}
          {driversMode ? (
            <DriversView
              companyId={driversCompany}
              onCompanyChange={setDriversCompany}
            />
          ) : excerptMode ? (
            <ExcerptLibrary
              requestedCompany={selection.company}
              onCompanyChange={setExcerptCompany}
            />
          ) : help ? (
            <section className="help panel">
              <h2>비교의 기준을 먼저 확인하세요</h2>
              <h3>분석 범위</h3>
              <p>
                동일 기업의 2024·2025 회계연도 사업보고서에서 연결 매출,
                영업이익, 사업 개요와 주요 제품·서비스를 비교합니다. 범위 밖의
                변화를 모두 찾았다는 의미는 아닙니다.
              </p>
              <h3>숫자와 증감률</h3>
              <p>
                양쪽 원문과 일치하는 값을 원 단위로 계산하고, 화면에서는 억
                원으로 표시합니다. 이전 값이 0 또는 음수이면 증감률을
                생략합니다. 재작성이나 비교 기준 차이가 있으면 증감률을
                보류합니다.
              </p>
              <h3>서술 변화</h3>
              <p>
                내용 변경, 추가, 삭제, 표현 변경을 구분합니다. 문서의 문구가
                추가되었다는 사실만으로 실제 사업이 시작되었다고 판단하지
                않습니다. 표현 변경은 기본적으로 접혀 있습니다.
              </p>
              <h3>근거와 검수</h3>
              <p>
                원문에서 추출한 문단·표와 주변 문맥을 제공합니다. 실제 데이터는
                출처와 검수 상태를 확인한 후 공개합니다. 가상 예시에는 실제
                접수번호나 원문 링크를 붙이지 않습니다.
              </p>
              <a
                href="https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS001"
                target="_blank"
                rel="noreferrer"
              >
                OpenDART 데이터 안내 ↗
              </a>
            </section>
          ) : (
            <>
              <section
                className="selection-panel panel"
                aria-label="비교 보고서 선택"
              >
                <div className="select-company">
                  <label htmlFor="company">분석 기업</label>
                  <select
                    id="company"
                    value={company?.id || ""}
                    onChange={(e) => choose(e.target.value)}
                  >
                    {catalog?.companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.stockCode})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="select-report">
                  <span className="field-label">이전 보고서</span>
                  <strong>
                    <FileText size={17} />
                    2024 사업보고서
                  </strong>
                  <small>
                    {data?.reports[0].filedAt || "접수일 미확인"} ·{" "}
                    {data?.reports[0].corrected ? "정정본" : "사업연도 기준"}
                  </small>
                </div>
                <span className="compare-arrow">
                  <ArrowRight size={19} />
                </span>
                <div className="select-report">
                  <span className="field-label">이후 보고서</span>
                  <strong>
                    <FileText size={17} />
                    2025 사업보고서
                  </strong>
                  <small>
                    {data?.reports[1].filedAt || "접수일 미확인"} ·{" "}
                    {data?.reports[1].corrected ? "정정본" : "사업연도 기준"}
                  </small>
                </div>
                <div className="comparison-state">
                  <span className="pill">
                    {demo
                      ? "예시 보고서 쌍"
                      : data
                        ? "검수 완료"
                        : "수집 준비 중"}
                  </span>
                  <small>
                    {data?.checkedAt
                      ? `확인일 ${data.checkedAt.slice(0, 10)}`
                      : "확인일 —"}
                  </small>
                </div>
              </section>
              {!catalog && !error && (
                <div className="empty panel" aria-live="polite">
                  보고서 목록을 불러오고 있습니다…
                </div>
              )}
              {catalog && !pair && (
                <section className="empty panel">
                  <div className="empty-icon">
                    <FileText size={32} />
                  </div>
                  <h2>{company?.name}의 비교 결과를 준비하고 있습니다</h2>
                  <p>
                    공시 원문을 수집하고 숫자와 근거를 검수하면
                    <br />
                    이곳에서 2024·2025 사업보고서를 비교할 수 있습니다.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => navigateView("excerpts")}
                  >
                    실제 공시에서 발췌하기 <FileText size={16} />
                  </button>
                  <button
                    className="button secondary"
                    onClick={() => toggleDemo(true)}
                  >
                    가상 예시로 기능 둘러보기 <ArrowRight size={16} />
                  </button>
                  <small>
                    예시 데이터는 실제 기업 분석에 사용할 수 없습니다.
                  </small>
                </section>
              )}
              {pair && !data && !error && (
                <div className="empty panel" aria-live="polite">
                  비교 결과를 불러오고 있습니다…
                </div>
              )}
              {data && (
                <>
                  <section className="financial panel">
                    <div className="section-heading">
                      <h2>
                        <span className="heading-icon">
                          <Layers3 size={18} />
                        </span>
                        재무 변화<span className="count">02</span>
                      </h2>
                      <span>연결 · KRW · 단위: 억 원</span>
                    </div>
                    <div className="table-scroll">
                      <table className="financial-table">
                        <thead>
                          <tr>
                            <th>주요 계정</th>
                            <th>2024</th>
                            <th>2025</th>
                            <th>차액</th>
                            <th>증감률 / 상태</th>
                            <th>근거</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.financials.map((f) => (
                            <tr key={f.id}>
                              <th>{f.label}</th>
                              <td>{wonToEok(f.before)}</td>
                              <td className="current-value">
                                {wonToEok(f.after)}
                              </td>
                              <td
                                className={
                                  BigInt(f.delta) >= 0n
                                    ? "positive"
                                    : "negative"
                                }
                              >
                                {signedEok(f.delta)}
                              </td>
                              <td>
                                <span
                                  className={
                                    "trend " +
                                    (BigInt(f.delta) >= 0n
                                      ? "positive"
                                      : "negative")
                                  }
                                >
                                  {f.percent !== null ? (
                                    <>
                                      {Number(f.percent) >= 0 ? (
                                        <ArrowUp size={13} />
                                      ) : (
                                        <ArrowDown size={13} />
                                      )}{" "}
                                      {Math.abs(Number(f.percent)).toFixed(2)}%
                                    </>
                                  ) : (
                                    f.status
                                  )}
                                </span>
                                {f.reason && (
                                  <small className="reason">{f.reason}</small>
                                )}
                              </td>
                              <td>
                                <button
                                  className={
                                    "evidence-button " +
                                    (finance?.id === f.id ? "chosen" : "")
                                  }
                                  aria-label={`${f.label} 원문 근거 보기`}
                                  onClick={() => selectChange(f.id)}
                                >
                                  <FileText size={16} />
                                  <span>보기</span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="scroll-hint">
                      표를 좌우로 밀어 증감률과 근거를 확인하세요.
                    </p>
                  </section>
                  <section className="narrative">
                    <div className="section-heading">
                      <h2>
                        <span className="heading-icon">
                          <FileText size={18} />
                        </span>
                        서술 변화
                        <span className="count">
                          {String(
                            data.changes.filter((c) => c.kind !== "wording")
                              .length,
                          ).padStart(2, "0")}
                        </span>
                      </h2>
                      <span>사업 개요 · 주요 제품 및 서비스</span>
                    </div>
                    <div className="analysis-grid">
                      <div className="changes-column">
                        <div className="filters" aria-label="변화 유형 필터">
                          {[
                            ["all", "전체"],
                            ["content", "내용 변경"],
                            ["added", "추가"],
                            ["removed", "삭제"],
                          ].map(([id, label]) => (
                            <button
                              key={id}
                              aria-pressed={filter === id}
                              className={filter === id ? "active" : ""}
                              onClick={() => setFilter(id)}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                        <label className="wording-toggle">
                          <input
                            type="checkbox"
                            checked={wording}
                            onChange={(e) => setWording(e.target.checked)}
                          />
                          표현만 바뀐 항목 포함{" "}
                          <span>
                            {
                              data.changes.filter((c) => c.kind === "wording")
                                .length
                            }
                          </span>
                        </label>
                        <div className="changes-list">
                          {visible.map((c: Change, index) => (
                            <button
                              className={
                                "change-card " +
                                (change?.id === c.id ? "selected" : "")
                              }
                              onClick={() => selectChange(c.id)}
                              key={c.id}
                            >
                              <div className="change-meta">
                                <span className={"type-badge " + c.kind}>
                                  {kinds[c.kind]}
                                </span>
                                <span>{c.section}</span>
                                <small>
                                  {String(index + 1).padStart(2, "0")}
                                </small>
                              </div>
                              <h3>
                                {c.title}
                                <ArrowRight size={17} />
                              </h3>
                              <p>{c.explanation}</p>
                              <div className="card-bottom">
                                <FileText size={13} />
                                {c.before.length + c.after.length}개 근거
                                <span>
                                  {demo
                                    ? "가상 예시"
                                    : c.reviewStatus === "approved"
                                      ? "검수 완료"
                                      : "확인 필요"}
                                </span>
                              </div>
                            </button>
                          ))}
                          {visible.length === 0 && (
                            <p className="no-changes">
                              선택한 유형의 변경점이 없습니다.
                            </p>
                          )}
                        </div>
                      </div>
                      <section
                        className="evidence-panel panel"
                        ref={viewer}
                        tabIndex={-1}
                        aria-label="양쪽 원문 근거"
                      >
                        <div className="viewer-heading">
                          <div>
                            <span className="eyebrow">SOURCE EVIDENCE</span>
                            <h3>{title}</h3>
                          </div>
                          <span className="source-badge">
                            <BookOpen size={14} />
                            원문 대조
                          </span>
                        </div>
                        {!selected ? (
                          <div className="viewer-empty">
                            <BookOpen size={35} />
                            <h3>변화의 근거를 직접 확인하세요</h3>
                            <p>
                              왼쪽 변경점이나 재무표의 ‘보기’를 선택하면
                              <br />
                              이전·이후 문단과 표가 나란히 열립니다.
                            </p>
                          </div>
                        ) : (
                          <>
                            <div
                              className="mobile-tabs"
                              role="tablist"
                              aria-label="근거 연도"
                            >
                              <button
                                role="tab"
                                aria-selected={side === 0}
                                onClick={() => setSide(0)}
                              >
                                2024 이전
                              </button>
                              <button
                                role="tab"
                                aria-selected={side === 1}
                                onClick={() => setSide(1)}
                              >
                                2025 이후
                              </button>
                            </div>
                            <div className="sources">
                              {data.reports.map((r, i) => {
                                const citations = change
                                  ? i === 0
                                    ? change.before
                                    : change.after
                                  : [
                                      {
                                        blockId:
                                          i === 0
                                            ? finance!.beforeBlockId
                                            : finance!.afterBlockId,
                                        quote: "",
                                      },
                                    ];
                                return (
                                  <div
                                    key={r.id}
                                    className={
                                      "source-column " +
                                      (side === i ? "mobile-active" : "")
                                    }
                                  >
                                    <div className="report-strip">
                                      <span>
                                        <span className={"year-tag y" + i}>
                                          {r.year}
                                        </span>
                                        {i === 0
                                          ? "이전 보고서"
                                          : "이후 보고서"}
                                      </span>
                                      {r.dartUrl ? (
                                        <a
                                          href={r.dartUrl}
                                          target="_blank"
                                          rel="noreferrer"
                                          aria-label={`${r.year} DART 원문 열기`}
                                        >
                                          <ExternalLink size={15} />
                                        </a>
                                      ) : (
                                        <small>가상 예시</small>
                                      )}
                                    </div>
                                    {citations.length ? (
                                      Array.from(
                                        new Set(
                                          citations.map((c) => c.blockId),
                                        ),
                                      ).map((id) => {
                                        const b = data.evidence.find(
                                          (b) => b.id === id,
                                        );
                                        return b ? (
                                          <Evidence
                                            key={id}
                                            block={b}
                                            selectedRow={
                                              finance
                                                ? i === 0
                                                  ? finance.beforeRow
                                                  : finance.afterRow
                                                : undefined
                                            }
                                            quotes={citations
                                              .filter((c) => c.blockId === id)
                                              .map((c) => c.quote)}
                                          />
                                        ) : (
                                          <p key={id} className="error">
                                            근거를 찾을 수 없습니다.
                                          </p>
                                        );
                                      })
                                    ) : (
                                      <div className="missing-source">
                                        {i === 0
                                          ? "이전 보고서에 대응 문단이 없습니다."
                                          : "이후 보고서에 대응 문단이 없습니다."}
                                        <small>
                                          분석 대상 절 내에서 확인한 결과입니다.
                                        </small>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            <div className="evidence-foot">
                              <Info size={14} />
                              {demo
                                ? "가상 예시입니다. 실제 기업의 공시 내용이 아닙니다."
                                : "강조된 문장과 주변 문맥을 함께 확인하세요."}
                            </div>
                          </>
                        )}
                      </section>
                    </div>
                  </section>
                  <div className="scope-note">
                    <ShieldCheck size={17} />
                    <span>
                      분석 범위: {data.coverage.join(" · ")}{" "}
                      <span className="muted">
                        | 전체 공시의 모든 변화를 포함하지 않습니다.
                      </span>
                    </span>
                  </div>
                </>
              )}
            </>
          )}
          <footer>
            <span>
              공시렌즈 <span className="muted">/</span> 근거를 따라 읽는
              기업공시
            </span>
            {excerptMode || driversMode ? (
              <span>
                {driversMode
                  ? "원문 출처 · 기업 IR / DART"
                  : "원문 출처 · 기업 공식 IR"}
              </span>
            ) : (
              <a
                href="https://opendart.fss.or.kr/"
                target="_blank"
                rel="noreferrer"
              >
                데이터 제공 OpenDART <ExternalLink size={12} />
              </a>
            )}
          </footer>
        </main>
      </div>
    </div>
  );
}
