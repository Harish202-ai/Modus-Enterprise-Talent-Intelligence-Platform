"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

function NavLink({ href, active, children }: { href: string; active?: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-violet/12 text-violet-ink" : "text-muted hover:text-ink hover:bg-ink/5",
      )}
    >
      {children}
    </Link>
  );
}

export default function SiteHeader() {
  const { state, hasRole, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const onAdmin = pathname.startsWith("/admin");
  const [busy, setBusy] = useState(false);

  const signOut = async () => {
    setBusy(true);
    try {
      await logout();
    } finally {
      setBusy(false);
      router.push("/login");
    }
  };

  return (
    <header className="sticky top-0 z-50 px-4 pt-4">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2 rounded-full border border-white/60 bg-white/60 px-3 py-2 shadow-[var(--shadow-soft)] backdrop-blur-xl md:px-4">
        <Link href="/" className="group inline-flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-[linear-gradient(135deg,#7b6ef6,#4f9cff)] shadow-[0_8px_18px_-6px_rgba(123,110,246,0.7)]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M4 18V7l6 6 6-6v11" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="20" cy="6" r="2" fill="white" />
            </svg>
          </span>
          <span className="font-heading text-lg font-extrabold tracking-tight text-ink">METI-MC</span>
        </Link>

        <nav aria-label="Account" className="ml-auto flex flex-wrap items-center gap-1 text-sm">
          {!hasRole(["admin"]) && <NavLink href="/pricing" active={pathname === "/pricing"}>Pricing</NavLink>}
          {state.status === "signed_in" ? (
            <>
              {hasRole(["candidate"]) && (
                <>
                  {/* No "Assessments" link: the exam is entered through the product on /pricing. */}
                  <NavLink href="/results" active={pathname.startsWith("/results")}>Results</NavLink>
                  <NavLink href="/report" active={pathname.startsWith("/report")}>Report</NavLink>
                  <NavLink href="/roadmap" active={pathname.startsWith("/roadmap")}>Roadmap</NavLink>
                  <NavLink href="/progress" active={pathname.startsWith("/progress")}>Progress</NavLink>
                </>
              )}
              {hasRole(["admin"]) && <NavLink href="/admin" active={onAdmin}>Admin</NavLink>}
              <Link href="/account" title={state.user.email} className="ml-1 inline-flex items-center gap-2 rounded-full border border-line bg-card px-2.5 py-1 text-sm font-medium text-ink transition-colors hover:border-violet/40">
                <span className="grid h-6 w-6 place-items-center rounded-lg bg-[linear-gradient(135deg,#7b6ef6,#4f9cff)] text-[11px] font-bold text-white">
                  {state.user.full_name.slice(0, 1).toUpperCase()}
                </span>
                <span className="hidden max-w-[8rem] truncate sm:inline">{state.user.full_name}</span>
              </Link>
              <button
                onClick={signOut}
                disabled={busy}
                className="grid h-9 w-9 place-items-center rounded-full border border-line text-muted transition-colors hover:text-ink disabled:opacity-50"
                title="Sign out"
                aria-label="Sign out"
              >
                <Icon name="logout" size={16} />
              </button>
            </>
          ) : state.status === "signed_out" ? (
            <>
              <NavLink href="/login" active={pathname === "/login"}>Sign in</NavLink>
              <Link
                href="/register"
                className="inline-flex h-9 items-center rounded-full bg-[linear-gradient(100deg,#7b6ef6,#6a5bf0_45%,#4f9cff)] px-4 text-sm font-semibold text-white shadow-[0_10px_24px_-10px_rgba(123,110,246,0.8)] transition-transform hover:-translate-y-0.5"
              >
                Create account
              </Link>
            </>
          ) : null}
        </nav>
      </div>
    </header>
  );
}
