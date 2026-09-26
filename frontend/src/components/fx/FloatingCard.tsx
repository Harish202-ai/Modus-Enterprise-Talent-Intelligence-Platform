"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

export function FloatingCard({ children, className, delay = 0, float = true }: { children: React.ReactNode; className?: string; delay?: number; float?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
      className={cn("glass rounded-2xl px-4 py-3 shadow-[var(--shadow-float)]", float && "animate-float-sm", className)}
      style={{ animationDelay: `${delay}s` }}
    >
      {children}
    </motion.div>
  );
}
