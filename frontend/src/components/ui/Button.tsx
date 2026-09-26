"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "soft";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200 focus-visible:outline-none disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap";

const variants: Record<Variant, string> = {
  primary: "text-white shadow-[0_12px_28px_-10px_rgba(123,110,246,0.7)] bg-[linear-gradient(100deg,#7b6ef6,#6a5bf0_45%,#4f9cff)] hover:shadow-[0_18px_36px_-10px_rgba(123,110,246,0.85)]",
  secondary: "bg-card text-ink border border-line shadow-[var(--shadow-soft)] hover:border-violet/40",
  soft: "bg-violet/10 text-violet-ink hover:bg-violet/15",
  ghost: "text-ink/70 hover:text-ink hover:bg-ink/5",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-sm",
  md: "h-11 px-5 text-[15px]",
  lg: "h-13 px-7 text-base py-3.5",
};

type Common = { variant?: Variant; size?: Size; className?: string; children: React.ReactNode };

export function Button({ variant = "primary", size = "md", className, children, ...rest }: Common & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <motion.button whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }} transition={{ type: "spring", stiffness: 400, damping: 20 }} className={cn(base, variants[variant], sizes[size], className)} {...(rest as any)}>
      {children}
    </motion.button>
  );
}

export function ButtonLink({ href, variant = "primary", size = "md", className, children }: Common & { href: string }) {
  return (
    <Link href={href} className="inline-flex">
      <motion.span whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }} transition={{ type: "spring", stiffness: 400, damping: 20 }} className={cn(base, variants[variant], sizes[size], className)}>
        {children}
      </motion.span>
    </Link>
  );
}
