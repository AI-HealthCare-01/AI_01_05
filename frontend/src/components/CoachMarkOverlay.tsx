import { useId, useLayoutEffect, useMemo, useRef, useState, type MouseEvent } from "react";

type SpotlightRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const MARGIN = 16;
const TOOLTIP_GAP = 12;

// 툴팁 좌우 위치 보정용 clamp 유틸
function clamp(min: number, value: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function renderDots(total: number, current: number) {
  return Array.from({ length: total }).map((_, index) => (
    <span
      key={`coach-dot-${index}`}
      style={{
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: index === current ? "#FFFFFF" : "rgba(255,255,255,0.4)",
        display: "inline-block",
      }}
    />
  ));
}

export default function CoachMarkOverlay({
  open,
  stepIndex,
  totalSteps,
  message,
  spotlight,
  onTargetClick,
  onPrev,
  onSkip,
}: {
  open: boolean;
  stepIndex: number;
  totalSteps: number;
  message: string;
  spotlight: SpotlightRect | null;
  onTargetClick: () => void;
  onPrev: () => void;
  onSkip: () => void;
}) {
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [tooltipSize, setTooltipSize] = useState({ width: 0, height: 0 });
  const maskId = useId();

  useLayoutEffect(() => {
    if (!open || !tooltipRef.current) return;
    const rect = tooltipRef.current.getBoundingClientRect();
    setTooltipSize({ width: rect.width, height: rect.height });
  }, [message, open, spotlight, stepIndex]);

  const tooltipLayout = useMemo(() => {
    if (!spotlight) return null;
    const centerX = spotlight.left + spotlight.width / 2;
    const desiredLeft = centerX - tooltipSize.width / 2;
    const left = clamp(MARGIN, desiredLeft, window.innerWidth - tooltipSize.width - MARGIN);

    // 요소가 상단에 가까우면 툴팁을 아래쪽에, 아니면 위쪽에 배치한다.
    const placeBelow = spotlight.top < tooltipSize.height + 70;
    const top = placeBelow
      ? spotlight.top + spotlight.height + TOOLTIP_GAP
      : spotlight.top - tooltipSize.height - TOOLTIP_GAP;

    const arrowLeft = clamp(12, centerX - left - 7, tooltipSize.width - 12);
    return { left, top, placeBelow, arrowLeft };
  }, [spotlight, tooltipSize.height, tooltipSize.width]);

  if (!open || !spotlight) return null;

  const radius = Math.min(18, Math.min(spotlight.width, spotlight.height) / 2);

  const handleOverlayClick = (event: MouseEvent<HTMLDivElement>) => {
    const { clientX, clientY } = event;
    const insideX = clientX >= spotlight.left && clientX <= spotlight.left + spotlight.width;
    const insideY = clientY >= spotlight.top && clientY <= spotlight.top + spotlight.height;
    if (insideX && insideY) {
      onTargetClick();
    }
  };

  return (
    <div
      data-coachmark-root
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 4000,
        pointerEvents: "auto",
      }}
    >
      <div
        onClick={handleOverlayClick}
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "auto",
        }}
      />
      {/* 화면 전체 어둡게 + 스포트라이트 구멍(SVG mask) */}
      <svg
        width="100%"
        height="100%"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
        }}
      >
        <defs>
          <mask id={maskId}>
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            <rect
              x={spotlight.left}
              y={spotlight.top}
              width={spotlight.width}
              height={spotlight.height}
              rx={radius}
              ry={radius}
              fill="black"
            />
          </mask>
        </defs>
        <rect x="0" y="0" width="100%" height="100%" fill="rgba(0,0,0,0.62)" mask={`url(#${maskId})`} />
        <rect
          x={spotlight.left}
          y={spotlight.top}
          width={spotlight.width}
          height={spotlight.height}
          rx={radius}
          ry={radius}
          fill="none"
          stroke="white"
          strokeWidth="2.5"
        />
      </svg>

      {/* 툴팁 */}
      <div
        ref={tooltipRef}
        style={{
          position: "fixed",
          left: tooltipLayout?.left ?? MARGIN,
          top: tooltipLayout?.top ?? MARGIN,
          background: "#FFFFFF",
          color: "#2C2C2C",
          borderRadius: 12,
          padding: "12px 14px",
          maxWidth: "min(340px, calc(100vw - 32px))",
          width: "max-content",
          boxShadow: "0 8px 28px rgba(0,0,0,0.24)",
          fontSize: 14,
          lineHeight: 1.45,
          pointerEvents: "auto",
        }}
      >
        {message}
        <span
          style={{
            position: "absolute",
            left: tooltipLayout?.arrowLeft ?? 18,
            width: 12,
            height: 12,
            background: "#FFFFFF",
            transform: "rotate(45deg)",
            ...(tooltipLayout?.placeBelow
              ? { top: -6 }
              : { bottom: -6 }),
          }}
        />
      </div>

      {/* 하단 컨트롤 */}
      <div
        style={{
          position: "fixed",
          left: 0,
          right: 0,
          bottom: 22,
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          alignItems: "center",
          padding: "0 18px",
          pointerEvents: "auto",
          color: "#FFFFFF",
        }}
      >
        <button
          type="button"
          onClick={onPrev}
          disabled={stepIndex === 0}
          style={{
            justifySelf: "start",
            background: "transparent",
            border: "none",
            color: stepIndex === 0 ? "rgba(255,255,255,0.45)" : "#FFFFFF",
            fontSize: 15,
            cursor: stepIndex === 0 ? "default" : "pointer",
            padding: 0,
          }}
        >
          ← 이전
        </button>
        <div style={{ display: "flex", gap: 6 }}>{renderDots(totalSteps, stepIndex)}</div>
        <button
          type="button"
          onClick={onSkip}
          style={{
            justifySelf: "end",
            background: "transparent",
            border: "none",
            color: "#FFFFFF",
            fontSize: 15,
            cursor: "pointer",
            padding: 0,
          }}
        >
          건너뛰기
        </button>
      </div>
    </div>
  );
}
