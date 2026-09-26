"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api";
import { adminUsersApi, type CandidateRow } from "@/lib/adminUsers";

export default function CandidatesView() {
  const [rows, setRows] = useState<CandidateRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    adminUsersApi
      .list()
      .then((r) => !stop && setRows(r))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, []);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!rows) return <p role="status" className="text-sm text-primary/60">Loading candidates…</p>;

  return (
    <div>
      <Link href="/admin" className="text-sm text-accent-cta hover:underline">← Back to admin</Link>
      <h1 className="mt-2 text-2xl">Students</h1>
      <p className="mt-1 text-sm text-primary/60">{rows.length} students, best overall performance first. Click one to see their full report — exams, scores, video interview and CV.</p>
      <div className="mt-6 overflow-x-auto rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)]">
        <table className="w-full text-sm">
          <thead className="bg-primary/[0.03] text-left text-xs uppercase tracking-wide text-primary/60">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2 text-right">Exams done</th>
              <th className="px-4 py-2">Performance</th>
              <th className="px-4 py-2">Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-t border-primary/5 hover:bg-primary/[0.03]">
                <td className="px-4 py-2">
                  <Link href={`/admin/users/${c.id}`} className="font-medium hover:underline">
                    {c.full_name ?? "—"}
                  </Link>
                </td>
                <td className="px-4 py-2 text-primary/70">{c.email}</td>
                <td className="px-4 py-2 text-right tabular-nums">{c.submitted_assessments}</td>
                <td className="px-4 py-2">
                  {c.readiness == null ? (
                    <span className="text-primary/40">—</span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-primary/10">
                        <span className="block h-full rounded-full bg-accent-cta" style={{ width: `${c.readiness}%` }} />
                      </span>
                      <span className="tabular-nums">{Math.round(c.readiness)}</span>
                      <span className="text-xs text-primary/50">{c.readiness_band}</span>
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-primary/60">{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-primary/50">No students yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
