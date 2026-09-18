import { useEffect, useRef, useState } from "react";
import { ArrowRight, ExternalLink, ScanSearch } from "lucide-react";
import SourceTableViewer from "./SourceTableViewer";
import {
  statusLabels,
  tableMetric,
  validateReview,
  type Review,
  type ReviewStatus,
} from "./review";
import { signedEok, wonToEok } from "./format";
import "./review.css";

const order: ReviewStatus[] = [
  "attention",
  "movement",
  "not_triggered",
  "unavailable",
];
export default function ReviewView({
  companyId,
  onCompanyChange,
}: {
  companyId: string;
  onCompanyChange: (id: string) => void;
}) {
  const [data, setData] = useState<Review | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(
    new URLSearchParams(location.search).get("finding") || "",
  );
  const [factId, setFactId] = useState(
    new URLSearchParams(location.search).get("fact") || "",
  );
  const [category, setCategory] = useState("전체"),
    [filter, setFilter] = useState("all");
  const detail = useRef<HTMLDivElement>(null);
  const requestedVersion = useRef({
    companyId,
    id: new URLSearchParams(location.search).get("review"),
  });
  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setData(null);
    setError("");
    setCategory("전체");
    setFilter("all");
    async function read(path: string) {
      const r = await fetch(import.meta.env.BASE_URL + path, {
        signal: c.signal,
      });
      if (!r.ok) throw new Error("검토 결과를 불러오지 못했습니다.");
      return r.json();
    }
    (async () => {
      try {
        const catalog = await read("review/catalog.json");
        const requested =
          requestedVersion.current.companyId === companyId
            ? requestedVersion.current.id
            : null;
        const companyItems = catalog.items.filter(
          (x: { companyId: string }) => x.companyId === companyId,
        );
        const item = requested
          ? companyItems.find((x: { id: string }) => x.id === requested)
          : companyItems[0];
        if (!item && companyItems.length && requested)
          throw new Error(
            "공유된 검토 버전을 찾을 수 없습니다. 투자 검토 포인트 메뉴에서 다시 선택해 주세요.",
          );
        if (!item) return;
        if (!/^review\/[a-z0-9-]+\.json$/.test(item.path))
          throw new Error("검토 데이터 주소 오류");
        const result = validateReview(await read(item.path));
        if (result.companyId !== companyId || result.id !== item.id)
          throw new Error("검토 기업 불일치");
        setData(result);
      } catch (e) {
        if (!c.signal.aborted)
          setError(e instanceof Error ? e.message : "데이터 오류");
      } finally {
        if (!c.signal.aborted) setLoading(false);
      }
    })();
    return () => c.abort();
  }, [companyId]);
  const visible =
    data?.findings
      .filter(
        (f) =>
          (category === "전체" || f.category === category) &&
          (filter === "all" || filter === f.status),
      )
      .sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status)) || [];
  const finding = visible.find((f) => f.id === selected) || visible[0];
  const facts =
    data?.facts.filter((f) => finding?.factIds.includes(f.id)) || [];
  const fact = facts.find((f) => f.id === factId) || facts[0];
  const table = data?.tables.find((t) => t.id === fact?.tableId);
  const metric =
    table && data
      ? tableMetric(
          data.facts.filter((f) => finding?.factIds.includes(f.id)),
          table.id,
        )
      : null;
  useEffect(() => {
    const u = new URL(location.href);
    u.searchParams.set("view", "review");
    u.searchParams.set("company", companyId);
    for (const key of [
      "analysis",
      "metric",
      "part",
      "finding",
      "fact",
      "review",
    ])
      u.searchParams.delete(key);
    if (data) u.searchParams.set("review", data.id);
    if (finding) u.searchParams.set("finding", finding.id);
    if (fact) u.searchParams.set("fact", fact.id);
    history.replaceState(null, "", u);
  }, [data?.id, companyId, finding?.id, fact?.id]);
  function choose(id: string) {
    setSelected(id);
    setFactId("");
    if (innerWidth < 900)
      setTimeout(
        () =>
          detail.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          }),
        20,
      );
  }
  return (
    <div className="review-view">
      <div className="review-company panel">
        <label>
          분석 기업{" "}
          <select
            aria-label="투자 검토 기업"
            value={companyId}
            onChange={(e) => onCompanyChange(e.target.value)}
          >
            <option value="samsung">삼성전자</option>
            <option value="skhynix">SK하이닉스 · 준비 중</option>
            <option value="lge">LG전자 · 준비 중</option>
          </select>
        </label>
        <span>재무제표에서 찾는 투자 검토 질문</span>
      </div>
      {error ? (
        <div className="error" role="alert">
          {error} <button onClick={() => location.reload()}>다시 시도</button>
        </div>
      ) : loading ? (
        <p role="status">재무제표 검토 결과를 불러오는 중입니다.</p>
      ) : !data ? (
        <div className="panel review-empty">
          <h2>이 기업의 재무 검토 결과는 준비 중입니다.</h2>
          <p>
            삼성전자 실제 사업보고서에서 검토 항목과 원문 표시를 확인할 수
            있습니다.
          </p>
          <button className="button" onClick={() => onCompanyChange("samsung")}>
            삼성전자 보기
          </button>
        </div>
      ) : (
        <>
          <section className="review-intro panel">
            <div>
              <span className="eyebrow">FINANCIAL STATEMENT REVIEW</span>
              <h2>{data.companyName} · 무엇을 더 살펴봐야 할까요?</h2>
              <p>
                {data.afterYear} 사업보고서의 {data.beforeYear}·{data.afterYear}{" "}
                비교열 · 연결 · 원화 · {data.facts.length}개 재무 항목 /{" "}
                {data.findings.length}개 검토 기준
              </p>
            </div>
            <span className="review-auto">자동 계산 · 해석 검토 전</span>
            <p className="review-intro-note">
              숫자 변화로 검토 순서를 제안합니다. 원인은 주석과 회사 설명으로
              추가 확인해야 합니다. 전체 위험 평가나 매매 판단을 제공하지
              않습니다.
            </p>
            <small>
              접수일 {data.source.filedAt} · 원본 확인일{" "}
              {data.source.checkedAt.slice(0, 10)} · 최종 정정 여부 미확인 ·
              신규 공시 자동 감지 연결 전
            </small>
          </section>
          <div className="review-summary" aria-label="검토 결과 상태 필터">
            {order.map((status) => (
              <button
                key={status}
                className={"review-count " + status}
                aria-pressed={filter === status}
                onClick={() => setFilter(filter === status ? "all" : status)}
              >
                <strong>
                  {data.findings.filter((f) => f.status === status).length}
                </strong>
                <span>{statusLabels[status]}</span>
              </button>
            ))}
          </div>
          <div className="review-filters" aria-label="검토 영역">
            {["전체", ...new Set(data.findings.map((f) => f.category))].map(
              (c) => (
                <button
                  key={c}
                  aria-pressed={category === c}
                  onClick={() => {
                    setCategory(c);
                    setFilter("all");
                  }}
                >
                  {c}
                </button>
              ),
            )}
            <button
              className="review-reset"
              onClick={() => {
                setCategory("전체");
                setFilter("all");
              }}
            >
              필터 초기화
            </button>
          </div>
          <div className="review-layout">
            <section className="review-list" aria-label="투자 검토 포인트 목록">
              {visible.map((f) => (
                <button
                  key={f.id}
                  className={
                    "review-card panel " +
                    (finding?.id === f.id ? "selected" : "")
                  }
                  aria-pressed={finding?.id === f.id}
                  onClick={() => choose(f.id)}
                >
                  <span className={"review-badge " + f.status}>
                    {statusLabels[f.status]}
                  </span>
                  <small>{f.category}</small>
                  <h3>{f.title}</h3>
                  <p>
                    {f.stats
                      .map((s) => s.label + " " + s.value + s.unit)
                      .join(" · ") || f.unavailableReason}
                  </p>
                  <span className="review-link">
                    판단 기준과 원문 보기 <ArrowRight size={14} />
                  </span>
                </button>
              ))}
              {!visible.length && (
                <p className="panel review-empty">
                  선택한 조건에 해당하는 항목이 없습니다. 미해당이 모든 위험의
                  부재를 뜻하지는 않습니다.
                </p>
              )}
            </section>
            <div className="review-detail" ref={detail}>
              {finding && (
                <>
                  <section className="panel review-explanation">
                    <span className={"review-badge " + finding.status}>
                      {statusLabels[finding.status]}
                    </span>
                    <h2>{finding.title}</h2>
                    <h3>왜 살펴보나요?</h3>
                    <p>{finding.why}</p>
                    <div className="review-next">
                      <ScanSearch size={19} />
                      <div>
                        <h3>다음으로 확인할 것</h3>
                        <p>{finding.nextCheck}</p>
                      </div>
                    </div>
                    <details>
                      <summary>계산 기준과 해석 한계</summary>
                      <p>{finding.criterion}</p>
                      <p>{finding.caveat}</p>
                      <small>
                        고정 탐색 기준 {data.ruleVersion} · 업종별로 보정하지
                        않은 초기 기준이며 위험 확률이나 검증된 예측 모델이
                        아닙니다.
                      </small>
                    </details>
                    {finding.status === "not_triggered" && (
                      <p className="review-footnote">
                        이 항목의 설정 기준에 해당하지 않았습니다. 안전하다는
                        판단은 아닙니다.
                      </p>
                    )}
                    {finding.unavailableReason && (
                      <p>{finding.unavailableReason}</p>
                    )}
                    <div className="review-fact-table">
                      <table>
                        <caption>
                          연결 재무 항목 · 억 원 (원 단위로 계산)
                        </caption>
                        <thead>
                          <tr>
                            <th>원문 항목</th>
                            <th>{data.beforeYear}</th>
                            <th>{data.afterYear}</th>
                            <th>차액</th>
                          </tr>
                        </thead>
                        <tbody>
                          {facts.map((f) => (
                            <tr
                              key={f.id}
                              className={f.id === fact?.id ? "selected" : ""}
                            >
                              <th>
                                <button
                                  aria-pressed={f.id === fact?.id}
                                  onClick={() => setFactId(f.id)}
                                >
                                  {f.label}{" "}
                                  <small>
                                    {f.kind === "instant"
                                      ? "기말 잔액"
                                      : "연간 누적"}
                                    {f.cashOutflow ? " · 지출 규모" : ""}
                                  </small>
                                </button>
                              </th>
                              <td>{wonToEok(f.before)}</td>
                              <td>{wonToEok(f.after)}</td>
                              <td>
                                {signedEok(
                                  String(BigInt(f.after) - BigInt(f.before)),
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="review-footnote">
                      행을 누르면 해당 공시표로 이동합니다. 지출은 위 표에서
                      양의 규모로, 아래 원문에서는 공시 부호 그대로 표시합니다.
                    </p>
                  </section>
                  {table && metric && fact && (
                    <SourceTableViewer
                      review
                      table={table}
                      metric={metric}
                      selected={
                        metric.components.find((p) => p.label === fact.label)!
                      }
                      onSelect={(label) =>
                        setFactId(facts.find((f) => f.label === label)!.id)
                      }
                    />
                  )}
                  {fact && (
                    <details className="panel review-text">
                      <summary>선택한 행의 원문 텍스트</summary>
                      <p>{fact.quote}</p>
                      <small>열 순서: 2025 · 2024 · 2023 / 백만원</small>
                    </details>
                  )}
                </>
              )}
            </div>
          </div>
          <section className="panel review-coverage">
            <h2>아직 판단에 포함하지 못한 부분</h2>
            <p>
              현재는 재무제표 본문의 숫자에서 출발합니다. 아래 영역은 별도
              검토가 필요하며, 결과에 없다고 문제가 없는 것은 아닙니다.
            </p>
            <ul>
              {data.coverageGaps.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
            <p>
              공시가 밝힌 원인, 계산으로 확인한 변화, 추가 확인할 가설은
              구분합니다. 예를 들어 지역 매출 증가는 수출 증가로 단정하지
              않습니다.
            </p>
            <a href="?view=drivers&company=samsung&metric=revenue">
              지역별 매출·FCF 변화 분해 보기 <ArrowRight size={14} />
            </a>
            <a
              href="https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide"
              target="_blank"
              rel="noreferrer"
            >
              재무제표 읽기 참고 · SEC <ExternalLink size={13} />
            </a>
          </section>
        </>
      )}
    </div>
  );
}
