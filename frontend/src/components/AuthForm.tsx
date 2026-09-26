"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { errorMessage } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { forgetWatched, watchedVideo } from "@/lib/orientation";
import { Icon } from "@/components/ui/Icon";

const input =
  "h-12 w-full rounded-2xl border border-line bg-white/80 px-4 text-[15px] text-ink placeholder:text-faint outline-none transition-colors focus:border-violet/50 focus:bg-white";
const primary =
  "inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-[linear-gradient(100deg,#7b6ef6,#6a5bf0_45%,#4f9cff)] px-4 text-sm font-semibold text-white shadow-[0_12px_28px_-10px_rgba(123,110,246,0.7)] transition-all hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-50";

/** Email + password form shared by /register and /login. */
export default function AuthForm({ mode }: { mode: "register" | "login" }) {
  const { register, login } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next");

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user =
        mode === "register"
          ? await register({ email, fullName, password, consent, orientation: watchedVideo() })
          : await login(email, password);
      if (mode === "register") forgetWatched(); // now stored on the account
      // Only follow same-site relative paths.
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : homeFor(user));
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md rounded-3xl border border-line bg-card p-8 shadow-[var(--shadow-lift)]">
      <span className="inline-flex items-center gap-2 rounded-full bg-violet/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-violet-ink">
        <Icon name="spark" size={13} /> {mode === "register" ? "Get started" : "Welcome back"}
      </span>
      <h1 className="mt-3 font-heading text-2xl font-extrabold text-ink">{mode === "register" ? "Create your account" : "Sign in"}</h1>
      <p className="mt-1 text-sm text-muted">
        {mode === "register" ? "Start your consulting assessment." : "Continue to your MODUS workspace."}
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded-2xl bg-red-50 px-4 py-2.5 text-sm text-red-800">
          {error}
        </p>
      )}

      <form onSubmit={submit} className="mt-6 space-y-4">
        {mode === "register" && (
          <div>
            <label htmlFor="full_name" className="mb-1 block text-sm font-medium">
              Full name
            </label>
            <input id="full_name" className={input} value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" required minLength={2} maxLength={120} />
          </div>
        )}
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            Email
          </label>
          <input id="email" type="email" className={input} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            className={input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            minLength={mode === "register" ? 8 : 1}
            maxLength={128}
            required
            aria-describedby={mode === "register" ? "password-help" : undefined}
          />
          {mode === "register" && (
            <p id="password-help" className="mt-1 text-xs text-primary/50">
              At least 8 characters, with a letter and a number.
            </p>
          )}
        </div>
        {mode === "register" && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5 h-4 w-4 accent-accent-cta" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
            <span>
              I agree to the processing of my data to run my assessments and reports, and to AI-assisted scoring of my answers (reviewable by a person).
            </span>
          </label>
        )}
        <button type="submit" className={primary} disabled={busy || (mode === "register" && !consent)}>
          {busy ? (mode === "register" ? "Creating account…" : "Signing in…") : mode === "register" ? "Create account" : "Sign in"}
          {!busy && <Icon name="arrow" size={17} />}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-muted">
        {mode === "register" ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-violet-ink hover:underline">
              Sign in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href="/register" className="font-semibold text-violet-ink hover:underline">
              Create an account
            </Link>
          </>
        )}
      </p>
    </div>
  );
}
