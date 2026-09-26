import type { Metadata } from "next";
import Link from "next/link";

import RequireAuth from "@/components/RequireAuth";
import SiteHeader from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Admin · METI-MC" };

const cards = [
  {
    href: "/admin/users",
    title: "Students & reports",
    body: "See every student and open their full report — exam results, scores, written & case answers, and their video interview.",
    emoji: "👥",
  },
  {
    href: "/admin/scores",
    title: "Check AI marks",
    body: "Review the marks the AI gave to written and case answers. Change a mark (with a reason) or approve it.",
    emoji: "✅",
  },
  {
    href: "/admin/content",
    title: "Edit the content",
    body: "Change the questions, prices, help articles, interview questions and page text — type it, generate it with AI, or upload a file. Nothing is code.",
    emoji: "✍️",
  },
];

export default function AdminHome() {
  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-3xl px-6 py-10">
        <RequireAuth roles={["admin"]}>
          <h1 className="text-2xl">Admin</h1>
          <p className="mt-1 text-sm text-primary/60">Pick what you want to do. Each area is explained below.</p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {cards.map((c) => (
              <Link
                key={c.href}
                href={c.href}
                className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6 transition-colors hover:border-accent-cta"
              >
                <div aria-hidden className="text-2xl">{c.emoji}</div>
                <h2 className="mt-3 text-lg">{c.title}</h2>
                <p className="mt-1 text-sm text-primary/65">{c.body}</p>
                <span className="mt-3 inline-block text-sm font-medium text-accent-cta">Open →</span>
              </Link>
            ))}
          </div>
        </RequireAuth>
      </div>
    </main>
  );
}
