import { useEffect, useRef, useState } from "react";
import { ExternalLink, ZoomIn } from "lucide-react";
import { signedEok } from "./format";
import {
  safeSource,
  type DriverMetric,
  type DriverPart,
  type TableOverlay,
} from "./drivers";
import "./source-table.css";

export default function SourceTableViewer({
  table,
  metric,
  selected,
  onSelect,
}: {
  table: TableOverlay;
  metric: DriverMetric;
  selected: DriverPart;
  onSelect: (label: string) => void;
}) {
  const [zoom, setZoom] = useState(100),
    [show, setShow] = useState(true),
    [ready, setReady] = useState(false),
    [failed, setFailed] = useState(false);
  const [side, setSide] = useState<"before" | "after">("after");
  const scroll = useRef<HTMLDivElement>(null),
    canvas = useRef<HTMLDivElement>(null);
  const marks = table.highlights.filter((h) => h.partLabel === selected.label);
  useEffect(() => {
    setReady(false);
    setFailed(false);
    setZoom(100);
    setSide("after");
  }, [table.asset]);
  function focusCell(targetSide: "before" | "after" = side) {
    if (!ready || !scroll.current || !canvas.current) return;
    const mark = marks.find((m) => m.side === targetSide);
    if (!mark) return;
    const area = scroll.current,
      board = canvas.current;
    const x = (mark.rect.x + mark.rect.width / 2) * board.clientWidth,
      y = (mark.rect.y + mark.rect.height / 2) * board.clientHeight;
    area.scrollTo({
      left: Math.max(0, x - area.clientWidth / 2),
      top: Math.max(0, y - area.clientHeight / 2),
      behavior: "instant",
    });
  }
  useEffect(() => {
    focusCell();
    if (!scroll.current || !canvas.current || !ready) return;
    const resize = new ResizeObserver(() => focusCell());
    resize.observe(canvas.current);
    const visible = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) focusCell();
      },
      { threshold: 0.1 },
    );
    visible.observe(scroll.current);
    return () => {
      resize.disconnect();
      visible.disconnect();
    };
  }, [selected.label, side, zoom, ready, table.asset]);
  return (
    <section
      className="source-table-viewer panel"
      aria-label="실제 공시표 위 강조 표시"
    >
      <header>
        <div>
          <span className="eyebrow">ORIGINAL FILING · ANNOTATED</span>
          <h2>실제 공시표에서 확인</h2>
          <p>
            {table.title} · PDF {table.page}쪽 (문서 표기 {table.printedPage}쪽)
          </p>
        </div>
        <a
          className="button secondary"
          href={safeSource(table.sourceUrl)}
          target="_blank"
          rel="noreferrer"
        >
          PDF 원문 열기 <ExternalLink size={14} />
        </a>
      </header>
      <div className="table-part-picker" aria-label="공시표 강조 항목">
        {metric.components.map((part) => (
          <button
            key={part.label}
            aria-pressed={part.label === selected.label}
            onClick={() => onSelect(part.label)}
          >
            {part.label}
          </button>
        ))}
      </div>
      <div className="table-annotation-note" role="status">
        <strong>{selected.label}</strong>
        <span>
          {metric.id === "fcf" ? "FCF" : "매출"} 변화에{" "}
          <b>{signedEok(selected.impact)}억 원</b> 기여
        </span>
      </div>
      <div className="table-tools">
        <label>
          <input
            type="checkbox"
            checked={show}
            onChange={(e) => setShow(e.target.checked)}
          />
          강조 표시
        </label>
        <label>
          <ZoomIn size={15} />
          <span>확대</span>
          <select
            aria-label="공시표 확대"
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          >
            <option value={100}>100%</option>
            <option value={125}>125%</option>
            <option value={150}>150%</option>
            <option value={200}>200%</option>
          </select>
        </label>
        <span>
          원문 단위: <strong>{table.unit}</strong> · 표의 금액은 원문
          그대로입니다.
        </span>
      </div>
      <div className="table-value-links">
        {(["before", "after"] as const).map((s) => {
          const mark = marks.find((m) => m.side === s);
          return (
            mark && (
              <button
                key={s}
                className={s + " " + (side === s ? "active" : "")}
                onClick={() => {
                  setSide(s);
                  focusCell(s);
                }}
                aria-label={
                  (s === "before" ? "이전" : "이후") + " 금액 위치로 이동"
                }
              >
                <span>{s === "before" ? "이전" : "이후"} 금액</span>
                <strong>{mark.rawValue}</strong>
                <small>{table.unit} · 위치 보기</small>
              </button>
            )
          );
        })}
      </div>
      {failed ? (
        <div className="source-image-error" role="alert">
          공시표 이미지를 불러오지 못했습니다. 위의 PDF 원문 열기로 확인해
          주세요.
        </div>
      ) : (
        <div
          ref={scroll}
          className="source-table-scroll"
          tabIndex={0}
          aria-label="확대 가능한 공시 원본 표"
        >
          <div
            ref={canvas}
            className="source-table-canvas"
            style={{
              width: zoom + "%",
              minWidth: (760 * zoom) / 100 + "px",
              aspectRatio: table.width + "/" + table.height,
            }}
          >
            <img
              src={import.meta.env.BASE_URL + table.asset}
              width={table.width}
              height={table.height}
              alt={
                table.title +
                " 실제 PDF 표. 아래 원문 근거에 각 행의 텍스트도 제공됩니다."
              }
              onLoad={() => setReady(true)}
              onError={() => setFailed(true)}
            />
            {show &&
              ready &&
              marks.map((mark) => (
                <button
                  key={mark.side}
                  className={"pdf-cell-highlight " + mark.side}
                  data-side={mark.side}
                  style={{
                    left: mark.rect.x * 100 + "%",
                    top: mark.rect.y * 100 + "%",
                    width: mark.rect.width * 100 + "%",
                    height: mark.rect.height * 100 + "%",
                  }}
                  aria-label={
                    (mark.side === "before" ? "이전" : "이후") +
                    " 원문 셀 " +
                    mark.rawValue +
                    " " +
                    table.unit
                  }
                  title={
                    (mark.side === "before" ? "이전" : "이후") +
                    " 원문 금액: " +
                    mark.rawValue +
                    " " +
                    table.unit
                  }
                  onClick={() => setSide(mark.side)}
                />
              ))}
          </div>
        </div>
      )}
      <footer>
        <span className="before-dot" />
        이전 값 <span className="after-dot" />
        이후 값{" "}
        <span>
          표 이미지는 실제 PDF 발췌이며, 색 테두리만 서비스가 추가했습니다.
        </span>
      </footer>
      {metric.id === "fcf" && (
        <p className="source-table-hint">
          FCF는 강조된 원문 항목으로 계산한 값입니다. 취득 지출은 공시표의 음수
          표기를 유지하고, 계산에서는 지출 규모를 양수로 사용합니다.
        </p>
      )}
      <p className="source-table-hint">
        표를 가로·세로로 움직여 주변 항목을 확인할 수 있습니다. 모바일에서는
        이전·이후 금액 버튼으로 각 셀에 이동하세요.
      </p>
    </section>
  );
}
