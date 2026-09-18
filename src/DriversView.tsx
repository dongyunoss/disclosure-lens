import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  ExternalLink,
  FileText,
  Info,
  Clock3,
} from "lucide-react";
import { wonToEok, signedEok } from "./format";
import {
  dominantPart,
  monitorLabel,
  safeSource,
  validateDrivers,
  type DriverAnalysis,
  type DriverCatalog,
  type MonitorStatus,
} from "./drivers";
import "./drivers.css";

const base = import.meta.env.BASE_URL;
async function read(path: string) {
  const res = await fetch(base + path, { cache: "no-cache" });
  if (!res.ok) throw new Error("분석 결과를 불러오지 못했습니다.");
  return res.json();
}
export default function DriversView({
  companyId,
  onCompanyChange,
}: {
  companyId: string;
  onCompanyChange: (id: string) => void;
}) {
  const [catalog, setCatalog] = useState<DriverCatalog | null>(null),
    [monitor, setMonitor] = useState<MonitorStatus | null>(null);
  const [analysis, setAnalysis] = useState<DriverAnalysis | null>(null),
    [error, setError] = useState("");
  const [id, setId] = useState(
    new URLSearchParams(location.search).get("analysis") || "",
  );
  const [metricId, setMetricId] = useState(
    new URLSearchParams(location.search).get("metric") || "fcf",
  );
  const currentCompany = companyId,
    setCurrentCompany = onCompanyChange;
  const [tick, setTick] = useState(Date.now());
  useEffect(() => {
    let alive = true;
    async function refresh() {
      const [a, b] = await Promise.allSettled([
        read("drivers/catalog.json"),
        read("drivers/monitor.json"),
      ]);
      if (!alive) return;
      if (
        a.status === "fulfilled" &&
        a.value.schemaVersion === 1 &&
        Array.isArray(a.value.items)
      )
        setCatalog(a.value);
      else setError("분석 목록을 불러오지 못했습니다.");
      if (b.status === "fulfilled") setMonitor(b.value);
      setTick(Date.now());
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 60000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  const entries =
    catalog?.items.filter((x) => x.companyId === currentCompany) || [];
  const entry = entries.find((x) => x.id === id) || entries[0];
  useEffect(() => {
    let alive = true;
    setAnalysis(null);
    setError("");
    if (entry) {
      if (!/^drivers\/[a-z0-9-]+\.json$/.test(entry.path)) {
        setError("분석 경로 오류");
        return;
      }
      read(entry.path)
        .then(validateDrivers)
        .then((d) => {
          if (alive) setAnalysis(d);
        })
        .catch(() => {
          if (alive) setError("분석 데이터 검증에 실패했습니다.");
        });
    }
    return () => {
      alive = false;
    };
  }, [entry?.path]);
  const metric =
    analysis?.metrics.find((m) => m.id === metricId) || analysis?.metrics[0];
  useEffect(() => {
    const u = new URL(location.href);
    u.searchParams.set("view", "drivers");
    u.searchParams.set("company", currentCompany);
    if (entry) u.searchParams.set("analysis", entry.id);
    else u.searchParams.delete("analysis");
    if (metric) u.searchParams.set("metric", metric.id);
    history.replaceState(null, "", u);
  }, [currentCompany, entry?.id, metric?.id]);
  const mainPart = metric && dominantPart(metric);
  const maxImpact =
    metric?.components.reduce((max, p) => {
      const n = BigInt(p.impact),
        v = n < 0n ? -n : n;
      return v > max ? v : max;
    }, 1n) || 1n;
  const evidenceIds = new Set([
    ...(metric?.components.flatMap((p) => p.evidence) || []),
    ...(metric?.evidence || []),
  ]);
  return (
    <section className="drivers-workspace">
      <div className="monitor-banner panel">
        <div className="monitor-icon">
          <Activity size={22} />
        </div>
        <div>
          <strong>{monitorLabel(monitor, tick)}</strong>
          <p>{monitor?.message || "공시 감지 상태를 확인하고 있습니다."}</p>
          {monitor?.checkedAt && (
            <small>
              마지막 확인 {new Date(monitor.checkedAt).toLocaleString("ko-KR")}
            </small>
          )}
        </div>
        <span className="pill">자동 분석 → 근거 확인 → 검수</span>
      </div>
      <div className="driver-controls panel">
        <div>
          <label htmlFor="driver-company">분석 기업</label>
          <select
            id="driver-company"
            value={currentCompany}
            onChange={(e) => {
              setCurrentCompany(e.target.value);
              setId("");
            }}
          >
            <option value="samsung">삼성전자</option>
            <option value="skhynix">SK하이닉스</option>
            <option value="lge">LG전자</option>
          </select>
        </div>
        <div>
          <label htmlFor="driver-report">공시 분석</label>
          <select
            id="driver-report"
            value={entry?.id || ""}
            onChange={(e) => setId(e.target.value)}
            disabled={!entries.length}
          >
            {!entries.length && <option value="">분석 결과 준비 중</option>}
            {entries.map((e) => (
              <option value={e.id} key={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!entry && catalog && (
        <div className="empty panel">
          <Clock3 />
          <h2>이 기업의 원인 분석을 준비하고 있습니다</h2>
          <p>
            공시 수집 연결 후 새 보고서부터 자동으로 분석합니다. 현재 삼성전자의
            실제 FCF·지역별 매출 분석을 확인할 수 있습니다.
          </p>
          <button
            className="button primary"
            onClick={() => setCurrentCompany("samsung")}
          >
            삼성전자 분석 보기
          </button>
        </div>
      )}
      {entry && !analysis && !error && (
        <p className="panel">실제 공시 수치를 불러오고 있습니다…</p>
      )}
      {analysis && metric && (
        <>
          <div className="driver-analysis-header">
            <div>
              <span className="type-badge uncertain">자동 산출 · 미검수</span>
              <h2>{analysis.companyName} · 수치가 달라진 이유</h2>
              <p>
                {analysis.periodBefore} <ArrowRight size={14} />{" "}
                {analysis.periodAfter} · 연결 · 단위 억 원
              </p>
            </div>
            <a
              className="button secondary"
              href={safeSource(analysis.source.url)}
              target="_blank"
              rel="noreferrer"
            >
              보고서 원문 <ExternalLink size={15} />
            </a>
          </div>
          <div className="driver-tabs" role="tablist" aria-label="분석 지표">
            {analysis.metrics.map((m) => (
              <button
                key={m.id}
                role="tab"
                aria-selected={metric.id === m.id}
                onClick={() => setMetricId(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="driver-summary panel">
            <div>
              <span>이전 기간</span>
              <strong>{wonToEok(metric.before)}</strong>
            </div>
            <ArrowRight className="summary-arrow" size={20} />
            <div>
              <span>이번 기간</span>
              <strong>{wonToEok(metric.after)}</strong>
            </div>
            <div className="driver-delta">
              <span>변화</span>
              <strong>{signedEok(metric.delta)}</strong>
              <small>
                {metric.percent === null
                  ? "증감률 미표시 (기준값 확인)"
                  : metric.percent + "%"}
              </small>
            </div>
          </div>
          <div className="driver-explanation panel">
            <span className="eyebrow">숫자로 확인한 기여</span>
            <h3>
              {mainPart
                ? mainPart.label +
                  "가 " +
                  (BigInt(metric.delta) > 0n ? "증가" : "감소") +
                  "에 가장 크게 기여했습니다."
                : "확인된 수치와 원인 근거를 구분합니다."}
            </h3>
            <p>
              {mainPart
                ? "전체 변화 " +
                  signedEok(metric.delta) +
                  "억 원 중 이 항목의 기여는 " +
                  signedEok(mainPart.impact) +
                  "억 원입니다."
                : "전체 증감은 계산할 수 있지만 원인을 설명할 비교 항목은 아직 확보되지 않았습니다."}
            </p>
            {metric.id === "fcf" && (
              <p className="driver-definition">{metric.definition}</p>
            )}
            <div className="driver-bridge" aria-label="증감 기여도">
              {metric.components.map((p) => {
                const n = BigInt(p.impact),
                  abs = n < 0n ? -n : n,
                  width = Number((abs * 10000n) / maxImpact) / 100;
                return (
                  <div className="bridge-row" key={p.label}>
                    <div className="bridge-label">
                      <strong>{p.label}</strong>
                      <span>
                        {wonToEok(p.before)} → {wonToEok(p.after)}
                      </span>
                    </div>
                    <div className="bridge-track">
                      <div
                        className={n < 0n ? "negative" : "positive"}
                        style={{ width: width + "%" }}
                      />
                    </div>
                    <div className="bridge-impact">
                      <strong>{signedEok(p.impact)}</strong>
                      {p.share != null && <small>전체 증감의 {p.share}%</small>}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="driver-caveat">
              <Info size={17} />
              {metric.caveat}
            </p>
          </div>
          <div className="driver-evidence panel">
            <div className="section-heading">
              <h2>계산에 사용한 실제 근거</h2>
              <span>
                {analysis.evidence.filter((e) => evidenceIds.has(e.id)).length}
                개 원문 행
              </span>
            </div>
            {analysis.evidence
              .filter((e) => evidenceIds.has(e.id))
              .map((e) => (
                <details key={e.id}>
                  <summary>
                    <FileText size={16} />
                    {e.section} ·{" "}
                    {e.id === "region-before"
                      ? "전기"
                      : e.id === "region-after"
                        ? "당기"
                        : {
                            cfo: "영업활동현금흐름",
                            ppe: "유형자산 취득",
                            intangibles: "무형자산 취득",
                            revenue: "매출액",
                          }[e.id] || e.id}
                  </summary>
                  <div>
                    <p>
                      원문 단위: {e.unit} · 열 순서: {e.columns.join(" / ")}
                    </p>
                    <blockquote>{e.quote}</blockquote>
                    <a
                      href={safeSource(e.sourceUrl)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      이 근거의 원문 열기 ↗
                    </a>
                  </div>
                </details>
              ))}
          </div>
          <div className="driver-notes panel">
            <h3>설명 가능한 범위</h3>
            <p>{analysis.comparisonNote}</p>
            <p>
              <strong>회사 설명과 추정은 별도입니다.</strong> 투자 목적, 고객
              수요, 수출 물량 같은 경영상 원인은 공시·주석·실적발표의 설명이
              확인되어야 제시합니다.
            </p>
            {analysis.limitations.map((text, i) => (
              <p key={i}>{text}</p>
            ))}
            <small>
              보고서 제출일 {analysis.source.filedAt} · 원본 확인일{" "}
              {analysis.source.checkedAt.slice(0, 10)}
            </small>
          </div>
        </>
      )}
      {!!monitor?.filings?.length && (
        <div className="driver-feed panel">
          <h2>최근 감지한 공시</h2>
          {monitor.filings.map((f) => (
            <article key={f.receipt}>
              <a href={safeSource(f.url)} target="_blank" rel="noreferrer">
                {f.title} ↗
              </a>
              <p>{f.message}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
