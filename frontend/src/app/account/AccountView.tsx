"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth, type AuthUser } from "@/lib/auth";
import { commerceApi, formatPrice, type MyEntitlements } from "@/lib/commerce";

type Me = AuthUser & { tenant?: { slug: string; name: string } };

const primary = "rounded-md bg-accent-cta px-3 py-1.5 text-sm text-primary transition-colors hover:bg-accent-cta/85 disabled:opacity-50";

export default function AccountView() {
  const { user, setUser } = useAuth();
  const isCandidate = user?.role === "candidate";
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [purchases, setPurchases] = useState<MyEntitlements | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<Me>(isCandidate ? "/v1/candidates/me" : "/v1/auth/me")
      .then((data) => {
        if (cancelled) return;
        setMe(data);
        setName(data.full_name);
      })
      .catch((err) => !cancelled && setError(errorMessage(err)));
    if (isCandidate) {
      commerceApi
        .mine()
        .then((data) => !cancelled && setPurchases(data))
        .catch((err) => !cancelled && setError(errorMessage(err)));
    }
    return () => {
      cancelled = true;
    };
  }, [isCandidate]);

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await apiFetch<Me>("/v1/candidates/me", { method: "PUT", body: JSON.stringify({ full_name: name }) });
      setMe(updated);
      setName(updated.full_name);
      setUser({ ...user!, full_name: updated.full_name });
      setNotice("Profile saved");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!me) {
    return error ? (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    ) : (
      <p role="status" className="text-sm text-primary/60">
        Loading your account…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl">Your account</h1>
        <p className="mt-1 text-sm text-primary/60">
          {me.email} · {me.role}
          {me.tenant ? ` · ${me.tenant.name}` : ""}
        </p>
      </div>

      {(error || notice) && (
        <p role={error ? "alert" : "status"} className={`rounded-md px-3 py-2 text-sm ${error ? "bg-red-50 text-red-800" : "bg-green-50 text-green-800"}`}>
          {error || notice}
        </p>
      )}

      {isCandidate && (
        <section className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
          <h2 className="text-lg">Profile</h2>
          <form onSubmit={saveName} className="mt-4 flex flex-wrap items-end gap-3">
            <div className="min-w-60 flex-1">
              <label htmlFor="full_name" className="mb-1 block text-sm font-medium">
                Full name
              </label>
              <input
                id="full_name"
                className="w-full rounded-md border border-primary/15 bg-surface-card px-3 py-1.5 text-sm outline-none focus:border-accent-cta"
                value={name}
                onChange={(e) => setName(e.target.value)}
                minLength={2}
                maxLength={120}
                required
              />
            </div>
            <button className={primary} disabled={busy || name.trim() === me.full_name}>
              {busy ? "Saving…" : "Save"}
            </button>
          </form>
        </section>
      )}

      {isCandidate && (
        <section className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg">Your purchases</h2>
            <Link href="/pricing" className="text-sm underline decoration-accent-cta underline-offset-2">
              {purchases?.products.length ? "See all products" : "Choose an assessment"}
            </Link>
          </div>
          {!purchases ? (
            <p className="mt-2 text-sm text-primary/60">Loading…</p>
          ) : purchases.products.length === 0 ? (
            <p className="mt-2 text-sm text-primary/70">You haven’t bought an assessment yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-primary/10 text-sm">
              {purchases.products.map((p) => (
                <li key={p.key} className="flex flex-wrap justify-between gap-2 py-2">
                  <span>
                    <span aria-hidden className="mr-1 text-accent-cta">
                      ✓
                    </span>
                    {p.name}
                    {p.source.startsWith("bundle:") && <span className="text-primary/50"> (in your bundle)</span>}
                  </span>
                  <span className="text-primary/60">
                    {p.source === "stripe" ? `${formatPrice(p.price, p.currency)} · ` : ""}
                    {new Date(p.granted_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {isCandidate && (
        <section className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
          <h2 className="text-lg">Orientation</h2>
          {me.orientation ? (
            <p className="mt-2 text-sm text-primary/70">
              <span aria-hidden className="mr-1 text-accent-cta">
                ✓
              </span>
              You marked the explainer video as watched on {new Date(me.orientation.watched_at).toLocaleString()}.
            </p>
          ) : (
            <p className="mt-2 text-sm text-primary/70">
              You haven’t watched the explainer video yet.{" "}
              <Link href="/#explainer" className="text-primary underline decoration-accent-cta underline-offset-2">
                Watch it now
              </Link>
            </p>
          )}
        </section>
      )}

      {isCandidate && (
        <section className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
          <h2 className="text-lg">Privacy &amp; consent</h2>
          <p className="mt-2 text-sm text-primary/70">
            {me.consent_accepted_at
              ? `You accepted data processing and AI-assisted scoring on ${new Date(me.consent_accepted_at).toLocaleString()}.`
              : "No consent is recorded for this account."}
          </p>
        </section>
      )}

      {!isCandidate && (
        <section className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
          <h2 className="text-lg">Administrator</h2>
          <p className="mt-2 text-sm text-primary/70">You&apos;re signed in as an administrator. Manage the platform from the admin area.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/admin" className={primary}>Go to Admin</Link>
            <Link href="/admin/users" className="rounded-md border border-primary/15 px-3 py-1.5 text-sm hover:bg-primary/5">Students</Link>
            <Link href="/admin/content" className="rounded-md border border-primary/15 px-3 py-1.5 text-sm hover:bg-primary/5">Content</Link>
          </div>
        </section>
      )}
    </div>
  );
}
