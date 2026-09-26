"use client";

import { useEffect, useState } from "react";

import { ApiError, apiFetch, type HealthResponse } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";

type State =
  | { kind: "loading" }
  | { kind: "ready"; data: HealthResponse }
  | { kind: "error"; message: string; data?: HealthResponse };

async function checkHealth(): Promise<State> {
  try {
    return { kind: "ready", data: await apiFetch<HealthResponse>("/health") };
  } catch (err) {
    if (err instanceof ApiError && err.body && typeof err.body === "object") {
      // 503 still carries per-dependency detail.
      return { kind: "error", message: `Backend degraded (HTTP ${err.status})`, data: err.body as HealthResponse };
    }
    return { kind: "error", message: `Cannot reach backend at ${API_BASE_URL || "(NEXT_PUBLIC_API_URL not set)"}` };
  }
}

export default function SystemStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    checkHealth().then((next) => !cancelled && setState(next));
    return () => {
      cancelled = true;
    };
  }, []);

  const load = async () => {
    setState({ kind: "loading" });
    setState(await checkHealth());
  };

  const data = state.kind === "loading" ? undefined : state.data;

  return (
    <section className="w-full max-w-md rounded-xl border border-primary/10 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">System status</h2>
        <button
          onClick={load}
          disabled={state.kind === "loading"}
          className="rounded-md border border-primary/15 px-3 py-1 text-sm hover:bg-primary/5 disabled:opacity-50"
        >
          {state.kind === "loading" ? "Checking…" : "Refresh"}
        </button>
      </div>

      {state.kind === "error" && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          {state.message}
        </p>
      )}

      {data && (
        <dl className="mt-4 space-y-2 text-sm">
          <Row label="API" value={data.status === "ok" ? "up" : "degraded"} good={data.status === "ok"} />
          {Object.entries(data.checks).map(([name, value]) => (
            <Row key={name} label={name} value={value} good={value === "up"} />
          ))}
          <div className="flex justify-between pt-2 text-primary/60">
            <dt>Environment</dt>
            <dd>{data.environment}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}

function Row({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="flex justify-between">
      <dt className="capitalize">{label}</dt>
      <dd className={good ? "text-green-700" : "text-red-700"}>
        {good ? "✓ " : "✗ "}
        {value}
      </dd>
    </div>
  );
}
