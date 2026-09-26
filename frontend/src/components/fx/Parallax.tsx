"use client";

import { createContext, useContext, useEffect, useRef } from "react";
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion, type MotionValue } from "framer-motion";

type Ctx = { mx: MotionValue<number>; my: MotionValue<number> };
const ParallaxCtx = createContext<Ctx | null>(null);

export function ParallaxScene({ children, className }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const rawx = useMotionValue(0);
  const rawy = useMotionValue(0);
  const mx = useSpring(rawx, { stiffness: 55, damping: 18, mass: 0.7 });
  const my = useSpring(rawy, { stiffness: 55, damping: 18, mass: 0.7 });
  const reduce = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el || reduce) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      rawx.set((e.clientX - r.left) / r.width - 0.5);
      rawy.set((e.clientY - r.top) / r.height - 0.5);
    };
    const reset = () => {
      rawx.set(0);
      rawy.set(0);
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", reset);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", reset);
    };
  }, [rawx, rawy, reduce]);

  return (
    <div ref={ref} className={className}>
      <ParallaxCtx.Provider value={{ mx, my }}>{children}</ParallaxCtx.Provider>
    </div>
  );
}

export function ParallaxLayer({ depth = 0.5, children, className, invert = false }: { depth?: number; children: React.ReactNode; className?: string; invert?: boolean }) {
  const ctx = useContext(ParallaxCtx);
  const fallback = useMotionValue(0);
  const mx = ctx?.mx ?? fallback;
  const my = ctx?.my ?? fallback;
  const amp = depth * 46 * (invert ? 1 : -1);
  const x = useTransform(mx, (v) => v * amp);
  const y = useTransform(my, (v) => v * amp);
  return (
    <motion.div style={{ x, y }} className={className}>
      {children}
    </motion.div>
  );
}
