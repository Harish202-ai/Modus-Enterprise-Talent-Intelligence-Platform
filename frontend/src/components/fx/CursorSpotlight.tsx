"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";

export function CursorSpotlight({ color = "rgba(123,110,246,0.16)", size = 460 }: { color?: string; size?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    const parent = el?.parentElement;
    if (!el || !parent || reduce) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      const r = parent.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.opacity = "1";
        el.style.background = `radial-gradient(${size}px circle at ${x}px ${y}px, ${color}, transparent 65%)`;
      });
    };
    const leave = () => (el.style.opacity = "0");
    parent.addEventListener("pointermove", onMove);
    parent.addEventListener("pointerleave", leave);
    return () => {
      parent.removeEventListener("pointermove", onMove);
      parent.removeEventListener("pointerleave", leave);
      cancelAnimationFrame(raf);
    };
  }, [color, size, reduce]);

  return <div ref={ref} aria-hidden className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300" />;
}
