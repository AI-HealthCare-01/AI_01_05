import { useCallback, useEffect, useMemo, useState } from "react";

export type CoachMarkStep = {
  id: string;
  message: string;
};

type SpotlightRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const DEFAULT_STORAGE_KEY = "home_coachmark_seen";
const SPOTLIGHT_PADDING = 10;

function toSpotlightRect(rect: DOMRect): SpotlightRect {
  return {
    left: rect.left - SPOTLIGHT_PADDING,
    top: rect.top - SPOTLIGHT_PADDING,
    width: rect.width + SPOTLIGHT_PADDING * 2,
    height: rect.height + SPOTLIGHT_PADDING * 2,
  };
}

export function useCoachMark({
  steps,
  enabled,
  storageKey = DEFAULT_STORAGE_KEY,
}: {
  steps: CoachMarkStep[];
  enabled: boolean;
  storageKey?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [seen, setSeen] = useState<boolean>(false);
  const [rectMap, setRectMap] = useState<Record<string, SpotlightRect>>({});

  // 사용자별 storageKey가 바뀌면 해당 계정 기준으로 최초 노출 여부를 다시 읽는다.
  useEffect(() => {
    setSeen(localStorage.getItem(storageKey) === "true");
    setCurrentIndex(0);
    setIsOpen(false);
  }, [storageKey]);

  // 각 스텝 대상 요소 위치를 getBoundingClientRect로 측정한다.
  const measure = useCallback(() => {
    const nextMap: Record<string, SpotlightRect> = {};
    for (const step of steps) {
      const element = document.getElementById(step.id);
      if (!element) continue;
      nextMap[step.id] = toSpotlightRect(element.getBoundingClientRect());
    }
    setRectMap(nextMap);
  }, [steps]);

  const ready = useMemo(
    () => steps.every((step) => Boolean(rectMap[step.id])),
    [rectMap, steps],
  );

  useEffect(() => {
    if (!enabled) return;
    // rAF 2회로 레이아웃 완료 후 측정
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(() => measure());
    });
    return () => cancelAnimationFrame(id);
  }, [enabled, measure, currentIndex]);

  // 화면 크기/스크롤이 바뀌면 대상 위치를 재측정한다.
  useEffect(() => {
    if (!enabled) return;
    const onResizeOrScroll = () => measure();
    window.addEventListener("resize", onResizeOrScroll);
    window.addEventListener("scroll", onResizeOrScroll, true);
    return () => {
      window.removeEventListener("resize", onResizeOrScroll);
      window.removeEventListener("scroll", onResizeOrScroll, true);
    };
  }, [enabled, measure]);

  useEffect(() => {
    if (!enabled || seen || !ready) return;
    // 레이아웃 안정화 후 오픈
    const id = requestAnimationFrame(() => {
      measure();
      setIsOpen(true);
    });
    return () => cancelAnimationFrame(id);
  }, [enabled, ready, seen, measure]);

  const closeAndPersist = useCallback(() => {
    localStorage.setItem(storageKey, "true");
    setSeen(true);
    setIsOpen(false);
  }, [storageKey]);

  const goPrev = useCallback(() => {
    setCurrentIndex((prev) => (prev <= 0 ? 0 : prev - 1));
  }, []);

  const goNext = useCallback(() => {
    setCurrentIndex((prev) => {
      if (prev >= steps.length - 1) {
        closeAndPersist();
        return prev;
      }
      return prev + 1;
    });
  }, [closeAndPersist, steps.length]);

  const skip = useCallback(() => {
    closeAndPersist();
  }, [closeAndPersist]);

  // ESC 키를 누르면 건너뛰기와 동일하게 종료한다.
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        skip();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, skip]);

  const currentStep = steps[currentIndex] ?? null;
  const spotlightRect = currentStep ? rectMap[currentStep.id] : null;

  return {
    isOpen,
    currentIndex,
    totalSteps: steps.length,
    currentStep,
    spotlightRect,
    goNext,
    goPrev,
    skip,
  };
}
