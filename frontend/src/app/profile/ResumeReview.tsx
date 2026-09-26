"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { errorMessage } from "@/lib/api";
import { EMPTY_PROFILE, profileApi, type Education, type ResumeClaim, type ResumeProfile, type Role } from "@/lib/profile";

const POLL_MS = 2500;
const input = "w-full rounded-md border border-primary/15 bg-surface-card px-3 py-1.5 text-sm outline-none focus:border-accent-cta";
const primary = "rounded-md bg-accent-cta px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-accent-cta/85 disabled:opacity-50";
const secondary = "rounded-md border border-primary/20 px-4 py-2 text-sm transition-colors hover:border-accent-cta disabled:opacity-50";

const toList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function ResumeReview() {
  const [claim, setClaim] = useState<ResumeClaim | null | undefined>(undefined);
  const [form, setForm] = useState<ResumeProfile>(EMPTY_PROFILE);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Load, then keep polling while the AI is reading the CV.
  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = () =>
      profileApi
        .get()
        .then(({ claim: c }) => {
          if (stop) return;
          setClaim(c);
          if (c && c.status !== "processing") setForm(c.confirmed ?? c.parsed ?? EMPTY_PROFILE);
          if (c?.status === "processing") timer = setTimeout(load, POLL_MS);
        })
        .catch((err) => !stop && setError(errorMessage(err)));
    load();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [claim?.id, claim?.status]);

  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      setClaim(await profileApi.upload(file));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const confirm = async (e: FormEvent) => {
    e.preventDefault();
    if (!claim) return;
    setBusy(true);
    setError("");
    try {
      const cleaned: ResumeProfile = {
        ...form,
        summary: form.summary?.trim() || null,
        roles: form.roles.filter((r) => r.title.trim()).map((r) => ({ ...r, highlights: r.highlights.filter((h) => h.trim()) })),
        education: form.education.filter((ed) => ed.qualification.trim()),
      };
      const saved = await profileApi.confirm(claim.id, cleaned);
      setClaim(saved);
      setForm(saved.confirmed ?? cleaned);
      setNotice("Thanks — your profile is confirmed.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const retry = async () => {
    if (!claim) return;
    setBusy(true);
    try {
      setClaim(await profileApi.retry(claim.id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const hiddenFile = (
    <input ref={fileInput} type="file" accept=".pdf,.docx" className="sr-only" aria-label="Upload your CV" onChange={(e) => upload(e.target.files?.[0])} />
  );

  if (claim === undefined) {
    return error ? <p role="alert" className="text-sm text-red-700">{error}</p> : <p role="status" className="text-sm text-primary/60">Loading…</p>;
  }

  if (claim === null) {
    return (
      <div className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-8 text-center">
        <h1 className="text-2xl">Your CV profile</h1>
        <p className="mx-auto mt-2 max-w-md text-primary/70">Upload your CV and we’ll read it to understand your background. You’ll check and correct what we found.</p>
        {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
        <button className={`${primary} mt-6`} onClick={() => fileInput.current?.click()} disabled={busy}>
          {busy ? "Uploading…" : "Upload CV (PDF or Word, up to 5 MB)"}
        </button>
        {hiddenFile}
      </div>
    );
  }

  if (claim.status === "processing") {
    return (
      <div role="status" className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-10 text-center">
        <div aria-hidden className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary/15 border-t-accent-cta" />
        <h1 className="mt-4 text-xl">Reading your CV…</h1>
        <p className="mt-1 text-sm text-primary/60">{claim.file?.filename} · this usually takes under a minute.</p>
      </div>
    );
  }

  const setRole = (i: number, patch: Partial<Role>) => setForm((f) => ({ ...f, roles: f.roles.map((r, j) => (j === i ? { ...r, ...patch } : r)) }));
  const setEdu = (i: number, patch: Partial<Education>) =>
    setForm((f) => ({ ...f, education: f.education.map((ed, j) => (j === i ? { ...ed, ...patch } : ed)) }));

  return (
    <form onSubmit={confirm} className="space-y-6">
      <div>
        <h1 className="text-2xl">{claim.parsed ? "Here’s what we found in your CV" : "Your background"}</h1>
        <p className="mt-1 text-sm text-primary/60">
          {claim.file?.filename} · Check it and correct anything that’s wrong. This is treated as <strong>self-reported</strong> context — it never raises
          a score on its own; your assessment answers do that.
        </p>
      </div>

      {claim.status === "confirmed" && (
        <p role="status" className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-800">
          ✓ Confirmed {claim.confirmed_at ? new Date(claim.confirmed_at).toLocaleString() : ""}. You can still edit and confirm again.
        </p>
      )}
      {notice && claim.status !== "confirmed" && <p role="status" className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-800">{notice}</p>}
      {claim.message && claim.status !== "confirmed" && (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-primary/5 px-4 py-3 text-sm">
          <span>{claim.message}</span>
          {(claim.status === "unavailable" || claim.status === "needs_review") && (
            <button type="button" className={secondary} onClick={retry} disabled={busy}>
              Try reading again
            </button>
          )}
        </div>
      )}
      {error && <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}

      <section className="space-y-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
        <h2 className="text-lg">Summary</h2>
        <textarea className={input} rows={3} value={form.summary ?? ""} maxLength={600} onChange={(e) => setForm({ ...form, summary: e.target.value })} aria-label="Summary" />
        <label className="block max-w-xs text-sm font-medium">
          Years of professional experience
          <input
            className={`${input} mt-1`}
            type="number"
            min={0}
            max={60}
            step={0.5}
            value={form.total_years_experience ?? ""}
            onChange={(e) => setForm({ ...form, total_years_experience: e.target.value === "" ? null : Number(e.target.value) })}
          />
        </label>
      </section>

      <section className="space-y-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg">Roles</h2>
          <button type="button" className={secondary} onClick={() => setForm({ ...form, roles: [...form.roles, { title: "", organisation: "", start: "", end: "", highlights: [] }] })}>
            + Add role
          </button>
        </div>
        {form.roles.length === 0 && <p className="text-sm text-primary/60">No roles yet.</p>}
        {form.roles.map((r, i) => (
          <div key={i} className="grid gap-2 rounded-md border border-primary/10 p-4 sm:grid-cols-2">
            <input className={input} placeholder="Job title" aria-label={`Role ${i + 1} title`} value={r.title} onChange={(e) => setRole(i, { title: e.target.value })} />
            <input className={input} placeholder="Organisation" aria-label={`Role ${i + 1} organisation`} value={r.organisation ?? ""} onChange={(e) => setRole(i, { organisation: e.target.value })} />
            <input className={input} placeholder="Start (e.g. 2021)" aria-label={`Role ${i + 1} start`} value={r.start ?? ""} maxLength={20} onChange={(e) => setRole(i, { start: e.target.value })} />
            <input className={input} placeholder="End (or Present)" aria-label={`Role ${i + 1} end`} value={r.end ?? ""} maxLength={20} onChange={(e) => setRole(i, { end: e.target.value })} />
            <textarea
              className={`${input} sm:col-span-2`}
              rows={2}
              placeholder="Key achievements — one per line"
              aria-label={`Role ${i + 1} highlights`}
              value={r.highlights.join("\n")}
              onChange={(e) => setRole(i, { highlights: e.target.value.split("\n").slice(0, 6) })}
            />
            <button type="button" className="justify-self-start text-xs text-primary/60 underline" onClick={() => setForm({ ...form, roles: form.roles.filter((_, j) => j !== i) })}>
              Remove role
            </button>
          </div>
        ))}
      </section>

      <section className="grid gap-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6 sm:grid-cols-2">
        <label className="text-sm font-medium">
          Industries <span className="font-normal text-primary/50">(comma-separated)</span>
          <input className={`${input} mt-1`} defaultValue={form.industries.join(", ")} key={`ind-${claim.id}-${claim.status}`} onBlur={(e) => setForm({ ...form, industries: toList(e.target.value) })} />
        </label>
        <label className="text-sm font-medium">
          Skills <span className="font-normal text-primary/50">(comma-separated)</span>
          <input className={`${input} mt-1`} defaultValue={form.skills.join(", ")} key={`sk-${claim.id}-${claim.status}`} onBlur={(e) => setForm({ ...form, skills: toList(e.target.value) })} />
        </label>
      </section>

      <section className="space-y-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg">Education</h2>
          <button type="button" className={secondary} onClick={() => setForm({ ...form, education: [...form.education, { qualification: "", institution: "", year: null }] })}>
            + Add
          </button>
        </div>
        {form.education.map((ed, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_1fr_7rem_auto]">
            <input className={input} placeholder="Qualification" aria-label={`Education ${i + 1} qualification`} value={ed.qualification} onChange={(e) => setEdu(i, { qualification: e.target.value })} />
            <input className={input} placeholder="Institution" aria-label={`Education ${i + 1} institution`} value={ed.institution ?? ""} onChange={(e) => setEdu(i, { institution: e.target.value })} />
            <input
              className={input}
              placeholder="Year"
              type="number"
              aria-label={`Education ${i + 1} year`}
              value={ed.year ?? ""}
              onChange={(e) => setEdu(i, { year: e.target.value === "" ? null : Number(e.target.value) })}
            />
            <button type="button" className="text-xs text-primary/60 underline" onClick={() => setForm({ ...form, education: form.education.filter((_, j) => j !== i) })}>
              Remove
            </button>
          </div>
        ))}
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-3">
          <button type="button" className={secondary} onClick={() => fileInput.current?.click()} disabled={busy}>
            Upload a different CV
          </button>
          <Link href="/assessments" className={secondary}>
            Back to assessments
          </Link>
        </div>
        <button type="submit" className={primary} disabled={busy}>
          {busy ? "Saving…" : claim.status === "confirmed" ? "Confirm changes" : "Confirm my profile"}
        </button>
      </div>
      {hiddenFile}
    </form>
  );
}
