"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "@/lib/api";
import { commerceApi, formatPrice, type Payment } from "@/lib/commerce";

type State = { kind: "checking" } | { kind: "done"; payment: Payment } | { kind: "error"; message: string };

const cta = "inline-block rounded-md bg-accent-cta px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-accent-cta/85";

/** Asks the backend to verify the Stripe session (the backend checks with Stripe; the browser is never trusted). */
async function check(sessionId: string | null): Promise<State> {
  if (!sessionId) return { kind: "error", message: "Missing checkout reference." };
  try {
    return { kind: "done", payment: await commerceApi.confirm(sessionId) };
  } catch (err) {
    return { kind: "error", message: errorMessage(err) };
  }
}

export default function SuccessView() {
  const sessionId = useSearchParams().get("session_id");
  const [state, setState] = useState<State>({ kind: "checking" });

  useEffect(() => {
    let stop = false;
    check(sessionId).then((next) => !stop && setState(next));
    return () => {
      stop = true;
    };
  }, [sessionId]);

  const retry = useCallback(async () => {
    setState({ kind: "checking" });
    setState(await check(sessionId));
  }, [sessionId]);

  if (state.kind === "checking") {
    return (
      <p role="status" className="text-center text-sm text-primary/60">
        Confirming your payment with Stripe…
      </p>
    );
  }
  if (state.kind === "error") {
    return (
      <div role="alert" className="text-center">
        <h1 className="text-xl">We couldn’t confirm this payment</h1>
        <p className="mt-2 text-sm text-primary/60">{state.message}</p>
        <Link href="/pricing" className="mt-6 inline-block text-sm underline decoration-accent-cta underline-offset-2">
          Back to pricing
        </Link>
      </div>
    );
  }

  const p = state.payment;
  if (p.status === "paid") {
    return (
      <div role="status" className="text-center">
        <p aria-hidden className="text-4xl text-accent-cta">
          ✓
        </p>
        <h1 className="mt-2 text-2xl">Payment received</h1>
        <p className="mt-2 text-primary/70">
          {formatPrice(p.amount, p.currency)} — your purchase is unlocked and shown on your account.
        </p>
        <Link href="/account" className={`${cta} mt-8`}>
          Go to your account
        </Link>
      </div>
    );
  }
  if (p.status === "pending") {
    return (
      <div role="status" className="text-center">
        <h1 className="text-xl">Your payment is still processing</h1>
        <p className="mt-2 text-sm text-primary/60">This usually takes a few seconds. Nothing is unlocked until Stripe confirms it.</p>
        <button onClick={retry} className="mt-6 rounded-md border border-primary/20 px-5 py-2.5 text-sm hover:border-accent-cta">
          Check again
        </button>
      </div>
    );
  }
  return (
    <div role="alert" className="text-center">
      <h1 className="text-xl">This payment didn’t go through</h1>
      <p className="mt-2 text-sm text-primary/60">Status: {p.status.replace("_", " ")}. You haven’t been given access — please try again.</p>
      <Link href="/pricing" className={`${cta} mt-6`}>
        Back to pricing
      </Link>
    </div>
  );
}
