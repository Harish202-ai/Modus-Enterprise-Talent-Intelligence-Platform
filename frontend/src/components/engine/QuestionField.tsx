"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { errorMessage } from "@/lib/api";
import { isFileAnswer, wordCount, type Answer, type Question } from "@/lib/engine";

type Props = {
  question: Question;
  number: number;
  value: Answer | undefined;
  onChange: (value: Answer | null) => void;
  error?: string | null;
  disabled?: boolean;
  /** Uploads a file as this question's answer (resume, video, case document). */
  onUpload?: (file: File) => Promise<void>;
};

/** One question, rendered from its data: single_choice, multi_select, likert, rank, free_text (optionally "or upload"), file_upload. */
export default function QuestionField({ question: q, number, value, onChange, error, disabled, onUpload }: Props) {
  const id = `q-${q.key}`;
  return (
    <fieldset className="rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-5" aria-describedby={error ? `${id}-err` : undefined} disabled={disabled}>
      <legend className="sr-only">Question {number}</legend>
      <p className="font-heading text-base font-semibold leading-snug">
        <span className="mr-2 text-accent-cta">{number}.</span>
        {q.prompt}
      </p>
      <div className="mt-4">
        {q.type === "single_choice" && <Choice q={q} value={value} onChange={onChange} />}
        {q.type === "likert" && <Likert q={q} value={value} onChange={onChange} />}
        {q.type === "multi_select" && <Multi q={q} value={value} onChange={onChange} />}
        {q.type === "rank" && <Rank q={q} value={value} onChange={onChange} disabled={disabled} />}
        {q.type === "free_text" && !q.upload_kinds?.length && <FreeText q={q} value={value} onChange={onChange} />}
        {q.type === "free_text" && !!q.upload_kinds?.length && <TextOrUpload q={q} value={value} onChange={onChange} onUpload={onUpload} />}
        {q.type === "file_upload" && <FileInput q={q} value={value} onChange={onChange} onUpload={onUpload} />}
      </div>
      {error && (
        <p id={`${id}-err`} role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
    </fieldset>
  );
}

type InputProps = { q: Question; value: Answer | undefined; onChange: (v: Answer | null) => void };

const optionCls = (selected: boolean) =>
  `flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 text-sm transition-colors ${
    selected ? "border-accent-cta bg-accent-cta/10" : "border-primary/15 hover:border-primary/40"
  }`;

function Choice({ q, value, onChange }: InputProps) {
  return (
    <div className="space-y-2" role="radiogroup">
      {q.options?.map((o) => (
        <label key={o.key} className={optionCls(value === o.key)}>
          <input type="radio" name={q.key} className="mt-0.5 accent-accent-cta" checked={value === o.key} onChange={() => onChange(o.key)} />
          <span>{o.label}</span>
        </label>
      ))}
    </div>
  );
}

function Likert({ q, value, onChange }: InputProps) {
  return (
    <div role="radiogroup" className="grid gap-2" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(7rem, 1fr))` }}>
      {q.options?.map((o) => (
        <label key={o.key} className={`${optionCls(value === o.key)} flex-col items-center text-center`}>
          <input type="radio" name={q.key} className="accent-accent-cta" checked={value === o.key} onChange={() => onChange(o.key)} />
          <span className="text-xs leading-tight">{o.label}</span>
        </label>
      ))}
    </div>
  );
}

function Multi({ q, value, onChange }: InputProps) {
  const selected = Array.isArray(value) ? value : [];
  const max = q.max_selections ?? q.options?.length ?? 0;
  const toggle = (key: string) => {
    const next = selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key];
    onChange(next.length ? next : null);
  };
  return (
    <div>
      <p className="mb-2 text-xs text-primary/60">
        {q.min_selections && q.min_selections > 1 ? `Choose ${q.min_selections}–${max}` : `Choose up to ${max}`} · {selected.length} selected
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {q.options?.map((o) => {
          const on = selected.includes(o.key);
          return (
            <label key={o.key} className={optionCls(on)}>
              <input type="checkbox" className="mt-0.5 accent-accent-cta" checked={on} disabled={!on && selected.length >= max} onChange={() => toggle(o.key)} />
              <span>{o.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

/** Rank all statements: drag and drop, arrow buttons, or Alt+↑/↓ on a focused item. */
function Rank({ q, value, onChange, disabled }: InputProps & { disabled?: boolean }) {
  const labels = new Map((q.options ?? []).map((o) => [o.key, o.label]));
  const confirmed = Array.isArray(value) && value.length === labels.size;
  const order = confirmed ? (value as string[]) : (q.options ?? []).map((o) => o.key);
  const [dragging, setDragging] = useState<number | null>(null);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length || from === to) return;
    const next = [...order];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };

  return (
    <div>
      <p className="mb-2 text-xs text-primary/60">Most like you at the top · drag, use the arrows, or Alt + ↑/↓</p>
      <ol className="space-y-2">
        {order.map((key, i) => (
          <li
            key={key}
            draggable={!disabled}
            onDragStart={() => setDragging(i)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => {
              if (dragging !== null) move(dragging, i);
              setDragging(null);
            }}
            onDragEnd={() => setDragging(null)}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.altKey && e.key === "ArrowUp") {
                e.preventDefault();
                move(i, i - 1);
              }
              if (e.altKey && e.key === "ArrowDown") {
                e.preventDefault();
                move(i, i + 1);
              }
            }}
            aria-label={`${i + 1}: ${labels.get(key)}`}
            className={`flex items-center gap-3 rounded-md border bg-surface-card px-3 py-2.5 text-sm ${
              dragging === i ? "border-accent-cta opacity-60" : confirmed ? "border-primary/25" : "border-dashed border-primary/25"
            } cursor-grab active:cursor-grabbing`}
          >
            <span className="w-5 font-heading font-bold text-accent-cta">{i + 1}</span>
            <span className="flex-1">{labels.get(key)}</span>
            <span className="flex gap-1">
              <button type="button" aria-label={`Move “${labels.get(key)}” up`} disabled={i === 0} onClick={() => move(i, i - 1)} className="rounded px-2 py-1 hover:bg-primary/5 disabled:opacity-25">
                ↑
              </button>
              <button
                type="button"
                aria-label={`Move “${labels.get(key)}” down`}
                disabled={i === order.length - 1}
                onClick={() => move(i, i + 1)}
                className="rounded px-2 py-1 hover:bg-primary/5 disabled:opacity-25"
              >
                ↓
              </button>
            </span>
          </li>
        ))}
      </ol>
      {!confirmed && (
        <button type="button" onClick={() => onChange(order)} className="mt-3 text-sm underline decoration-accent-cta underline-offset-2">
          This order is right
        </button>
      )}
    </div>
  );
}

function FreeText({ q, value, onChange }: InputProps) {
  const text = typeof value === "string" ? value : "";
  const words = wordCount(text);
  const limit = q.max_length ?? 5000;
  return (
    <div>
      <textarea
        className="min-h-40 w-full rounded-md border border-primary/15 bg-surface-card px-3 py-2 text-sm leading-relaxed outline-none focus:border-accent-cta"
        value={text}
        maxLength={limit}
        rows={q.min_words && q.min_words >= 120 ? 14 : 6}
        onChange={(e) => onChange(e.target.value ? e.target.value : null)}
        aria-label={q.prompt}
      />
      <p className="mt-1 flex justify-between text-xs text-primary/55">
        <span>
          {words} words{q.min_words ? ` · at least ${q.min_words}` : ""}
        </span>
        <span>
          {text.length}/{limit} characters
        </span>
      </p>
    </div>
  );
}

const VIDEO = ["mp4", "mov", "webm"];
const humanSize = (bytes: number) => (bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/** Written answer, or upload instead (a video for communication, a document for the case). */
function TextOrUpload({ q, value, onChange, onUpload }: InputProps & { onUpload?: (file: File) => Promise<void> }) {
  const [mode, setMode] = useState<"text" | "file">(isFileAnswer(value) ? "file" : "text");
  const isVideo = (q.upload_kinds ?? []).every((k) => VIDEO.includes(k));
  const tab = (active: boolean) =>
    `rounded-md px-3 py-1.5 text-sm transition-colors ${active ? "bg-accent-cta text-primary" : "text-primary/70 hover:bg-primary/5"}`;
  return (
    <div>
      <div role="tablist" aria-label="Answer format" className="mb-3 inline-flex gap-1 rounded-lg border border-primary/15 p-1">
        <button type="button" role="tab" aria-selected={mode === "text"} className={tab(mode === "text")} onClick={() => setMode("text")}>
          Write it
        </button>
        <button type="button" role="tab" aria-selected={mode === "file"} className={tab(mode === "file")} onClick={() => setMode("file")}>
          {isVideo ? "Upload a video" : "Upload a document"}
        </button>
      </div>
      {mode === "text" ? (
        <>
          {isFileAnswer(value) && <p className="mb-2 text-xs text-primary/60">Typing an answer will replace your uploaded file ({value.filename}).</p>}
          <FreeText q={q} value={isFileAnswer(value) ? undefined : value} onChange={onChange} />
        </>
      ) : (
        <FileInput q={q} value={value} onChange={onChange} onUpload={onUpload} />
      )}
    </div>
  );
}

function FileInput({ q, value, onChange, onUpload }: InputProps & { onUpload?: (file: File) => Promise<void> }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const kinds = q.upload_kinds ?? [];
  const accept = kinds.map((k) => `.${k}`).join(",");

  const pick = async (file: File | undefined) => {
    if (!file || !onUpload) return;
    setError("");
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!kinds.includes(ext)) {
      setError(`Please choose a ${kinds.map((k) => k.toUpperCase()).join(" / ")} file.`);
      return;
    }
    if (q.upload_max_mb && file.size > q.upload_max_mb * 1024 * 1024) {
      setError(`That file is larger than ${q.upload_max_mb} MB.`);
      return;
    }
    setBusy(true);
    try {
      await onUpload(file);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  return (
    <div>
      {isFileAnswer(value) ? (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-accent-cta bg-accent-cta/10 px-4 py-3 text-sm">
          <span aria-hidden className="text-accent-cta">
            ✓
          </span>
          <span className="flex-1 truncate">
            {value.filename} <span className="text-primary/55">· {humanSize(value.size)}</span>
          </span>
          <button type="button" className="underline decoration-accent-cta underline-offset-2" onClick={() => input.current?.click()} disabled={busy}>
            {busy ? "Uploading…" : "Replace"}
          </button>
          {q.type !== "file_upload" && (
            <button type="button" className="text-primary/60 underline underline-offset-2" onClick={() => onChange(null)} disabled={busy}>
              Remove
            </button>
          )}
        </div>
      ) : (
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            pick(e.dataTransfer.files?.[0]);
          }}
          disabled={busy || !onUpload}
          className="flex w-full flex-col items-center gap-1 rounded-md border border-dashed border-primary/30 px-4 py-8 text-sm transition-colors hover:border-accent-cta disabled:opacity-50"
        >
          <span className="font-medium">{busy ? "Uploading…" : "Choose a file or drop it here"}</span>
          <span className="text-xs text-primary/55">
            {kinds.map((k) => k.toUpperCase()).join(", ")}
            {q.upload_max_mb ? ` · up to ${q.upload_max_mb} MB` : ""}
          </span>
        </button>
      )}
      <input ref={input} type="file" accept={accept} className="sr-only" aria-label={`Upload file for: ${q.prompt}`} onChange={(e) => pick(e.target.files?.[0])} />
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {q.upload_role === "resume" && isFileAnswer(value) && (
        <p className="mt-2 text-xs text-primary/60">
          We’re reading your CV now.{" "}
          <Link href="/profile" target="_blank" className="underline decoration-accent-cta underline-offset-2">
            Check what we found
          </Link>{" "}
          — any time before or after you finish this form.
        </p>
      )}
    </div>
  );
}
