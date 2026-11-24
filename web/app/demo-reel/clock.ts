"use client";

import { useEffect, useState } from "react";

type RecWindow = Window & { __REC__?: boolean; __vt?: number };

export function useClock(): number {
  const [t, setT] = useState(0);
  useEffect(() => {
    const w = window as RecWindow;
    if (w.__REC__) {
      const h = () => setT(w.__vt || 0);
      h();
      window.addEventListener("vt", h);
      return () => window.removeEventListener("vt", h);
    }
    let raf = 0;
    const start = performance.now();
    const tick = (n: number) => {
      setT(n - start);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return t;
}

export function ramp(clock: number, start: number, dur: number, power = 2): number {
  if (clock < start) return 0;
  const x = Math.min(1, (clock - start) / dur);
  return 1 - Math.pow(1 - x, power);
}
