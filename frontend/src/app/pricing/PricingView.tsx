"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { commerceApi, formatPrice, type CommerceConfig, type Product } from "@/lib/commerce";
import { TiltCard } from "@/components/fx/TiltCard";
import { Icon } from "@/components/ui/Icon";

const kindMeta: Record<string, { icon: string; accent: string }> = {
  assessment: { icon: "assessments", accent: "violet" },
  bundle: { icon: "star", accent: "blue" },
  report_upgrade: { icon: "reports", accent: "amber" },
};
const accentSoft: Record<string, string> = { violet: "bg-violet/12 text-violet", blue: "bg-blue/12 text-blue", amber: "bg-amber/20 text-[#c9762f]" };

type Data = { products: Product[]; owned: Set<string>; freeAccess: boolean };

const cta = "inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[linear-gradient(100deg,#7b6ef6,#6a5bf0_45%,#4f9cff)] px-4 text-sm font-semibold text-white shadow-[0_12px_28px_-10px_rgba(123,110,246,0.7)] transition-all hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-50 disabled:bg-none disabled:bg-ink/10 disabled:text-muted disabled:shadow-none";

/** Where an owned product takes the candidate — the whole experience runs from the product. */
const enterHref = (p: Product) => (p.kind === "report_upgrade" ? "/report" : "/assessments");

export default function PricingView() {
  const { state, user } = useAuth();
  const router = useRouter();
  const cancelled = useSearchParams().get("cancelled") === "1";
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [buying, setBuying] = useState<string | null>(null);
  const isCandidate = user?.role === "candidate";

  useEffect(() => {
    if (state.status === "loading") return; // wait until we know who's looking
    let stop = false;
    Promise.all([
      commerceApi.products(),
      commerceApi.config().catch(() => ({ free_access: false, payments_enabled: false }) as CommerceConfig),
      isCandidate ? commerceApi.mine() : Promise.resolve(null),
    ])
      .then(([products, config, mine]) => !stop && setData({ products, owned: new Set(mine?.products.map((p) => p.key) ?? []), freeAccess: config.free_access }))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, [state.status, isCandidate]);

  const buy = async (product: Product) => {
    if (!user) {
      router.push(`/register?next=${encodeURIComponent("/pricing")}`);
      return;
    }
    setBuying(product.key);
    setError("");
    try {
      const { checkout_url, free } = await commerceApi.checkout(product.key);
      if (free || !checkout_url) {
        // Local/dev without Stripe: enrolled for free — go straight to the assessments.
        router.push("/assessments");
        return;
      }
      window.location.assign(checkout_url); // Stripe-hosted checkout (test mode)
    } catch (err) {
      setError(errorMessage(err));
      setBuying(null);
    }
  };

  if (!data) {
    return error ? (
      <p role="alert" className="text-center text-sm text-red-700">
        {error}
      </p>
    ) : (
      <div role="status" aria-label="Loading" className="grid animate-pulse gap-6 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-64 rounded-xl bg-primary/5" />
        ))}
      </div>
    );
  }

  if (data.products.length === 0) {
    return <p className="text-center text-sm text-primary/60">No products are on sale yet.</p>;
  }

  const byKey = new Map(data.products.map((p) => [p.key, p]));
  const { freeAccess } = data;

  return (
    <div className="space-y-6">
      {cancelled && (
        <p role="status" className="rounded-md bg-primary/5 px-4 py-3 text-sm">
          Checkout was cancelled — you haven’t been charged.
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}
      <div className="grid gap-6 md:grid-cols-2">
        {data.products.map((p) => {
          const owned = data.owned.has(p.key);
          const locked = p.requires_product_keys.length > 0 && !p.requires_product_keys.some((k) => data.owned.has(k));
          const bundleOwned = p.kind === "bundle" && p.bundled_product_keys.every((k) => data.owned.has(k));
          const km = kindMeta[p.kind] ?? kindMeta.assessment;
          return (
            <TiltCard key={p.key} className="h-full rounded-3xl" max={5}>
            <article className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-line bg-card p-7 shadow-[var(--shadow-soft)] transition-shadow hover:shadow-[var(--shadow-lift)]">
              {(owned || bundleOwned) && (
                <span className="absolute right-5 top-5 inline-flex items-center gap-1 rounded-full bg-mint-500/15 px-2.5 py-1 text-[11px] font-bold text-[#159c7a]"><Icon name="check" size={12} /> Owned</span>
              )}
              <span className={`grid h-12 w-12 place-items-center rounded-2xl ${accentSoft[km.accent]}`}><Icon name={km.icon} size={22} /></span>
              <h2 className="mt-4 text-lg font-bold text-ink">{p.name}</h2>
              <p className="mt-2 font-heading text-4xl font-extrabold text-gradient">{freeAccess ? "Free" : formatPrice(p.price, p.currency)}</p>
              {p.description && <p className="mt-3 text-sm leading-relaxed text-muted">{p.description}</p>}
              {p.kind === "bundle" && (
                <p className="mt-3 rounded-xl bg-canvas/70 px-3 py-2 text-xs text-muted">
                  Includes: {p.bundled_product_keys.map((k) => byKey.get(k)?.name ?? k).join(" + ")}
                </p>
              )}
              {p.kind !== "bundle" && !!p.assessments?.length && (
                <ul className="mt-5 space-y-2 text-sm">
                  {p.assessments.map((a) => (
                    <li key={a.key} className="flex items-center gap-2.5 text-ink/80">
                      <span aria-hidden className="grid h-5 w-5 place-items-center rounded-full bg-violet/12 text-violet"><Icon name="check" size={12} /></span>
                      {a.name}
                    </li>
                  ))}
                  {/* The AI video interview ships with any product that includes Written Communication
                      (its access gate) — advertise it as part of the experience. */}
                  {p.assessment_keys.includes("written_communication") && (
                    <li className="flex items-center gap-2.5 text-ink/80">
                      <span aria-hidden className="grid h-5 w-5 place-items-center rounded-full bg-violet/12 text-violet"><Icon name="check" size={12} /></span>
                      AI video interview
                    </li>
                  )}
                </ul>
              )}
              <div className="mt-auto pt-6">
                {owned || bundleOwned ? (
                  <Link href={enterHref(p)} className={`${cta} block text-center`}>
                    {p.kind === "report_upgrade" ? "View your report →" : "Start your assessment →"}
                  </Link>
                ) : user && !isCandidate ? (
                  <p className="text-center text-xs text-primary/50">Sign in as a candidate to buy</p>
                ) : locked && user ? (
                  <button className={cta} disabled>
                    Available after you buy an assessment
                  </button>
                ) : (
                  <button className={cta} onClick={() => buy(p)} disabled={buying !== null}>
                    {buying === p.key
                      ? freeAccess ? "Setting up…" : "Opening secure checkout…"
                      : freeAccess
                        ? (user ? "Start for free →" : "Create an account to start")
                        : user ? `Buy — ${formatPrice(p.price, p.currency)}` : "Create an account to buy"}
                  </button>
                )}
              </div>
            </article>
            </TiltCard>
          );
        })}
      </div>
      <p className="text-center text-xs text-muted">
        {freeAccess
          ? "Everything is free right now — no payment required. Just pick an assessment to begin."
          : "Payments are processed securely by Stripe. Prices include everything listed — no subscription."}
      </p>
    </div>
  );
}
