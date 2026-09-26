"use client";

import type { ReactNode } from "react";

import type { ContentRow, ContentTypeSpec, FieldSpec, ValidationError } from "@/lib/content";

/** Form state: every field kept as what its input edits (text, checkbox, ordered key list). */
export type FormValues = Record<string, string | boolean | string[]>;

export function toForm(spec: ContentTypeSpec, data: Record<string, unknown>): FormValues {
  const values: FormValues = {};
  for (const f of spec.fields) {
    const raw = data[f.name] ?? f.default;
    if (f.kind === "bool") values[f.name] = Boolean(raw);
    else if (f.kind === "refs") values[f.name] = Array.isArray(raw) ? raw.map(String) : [];
    else if (f.kind === "tags") values[f.name] = Array.isArray(raw) ? raw.join(", ") : "";
    else if (f.kind === "json") values[f.name] = raw === undefined || raw === null ? "" : JSON.stringify(raw, null, 2);
    else values[f.name] = raw === undefined || raw === null ? "" : String(raw);
  }
  return values;
}

/** Convert form state back to a content `data` object; empty optional inputs are left out. */
export function fromForm(
  spec: ContentTypeSpec,
  values: FormValues,
): { data: Record<string, unknown>; errors: ValidationError[] } {
  const data: Record<string, unknown> = {};
  const errors: ValidationError[] = [];
  for (const f of spec.fields) {
    const v = values[f.name];
    switch (f.kind) {
      case "bool":
      case "refs":
        data[f.name] = v;
        break;
      case "tags":
        data[f.name] = String(v ?? "")
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
        break;
      case "number":
      case "integer": {
        const s = String(v ?? "").trim();
        if (!s) break;
        const n = Number(s);
        if (Number.isNaN(n)) errors.push({ field: f.name, message: "must be a number" });
        else data[f.name] = n;
        break;
      }
      case "json": {
        const s = String(v ?? "").trim();
        if (!s) break;
        try {
          data[f.name] = JSON.parse(s);
        } catch {
          errors.push({ field: f.name, message: "is not valid JSON" });
        }
        break;
      }
      default: {
        const s = String(v ?? "");
        if (s.trim()) data[f.name] = s;
      }
    }
  }
  return { data, errors };
}

const inputCls =
  "w-full rounded-md border border-primary/15 bg-surface-card px-2.5 py-1.5 text-sm outline-none focus:border-accent-cta disabled:opacity-70";

type Props = {
  spec: ContentTypeSpec;
  values: FormValues;
  onChange: (values: FormValues) => void;
  readOnly: boolean;
  errors: ValidationError[];
  refOptions: Record<string, ContentRow[]>;
};

export default function ContentForm({ spec, values, onChange, readOnly, errors, refOptions }: Props) {
  const set = (name: string, value: FormValues[string]) => onChange({ ...values, [name]: value });

  return (
    <div className="space-y-4">
      {spec.fields.map((f) => {
        const fieldErrors = errors.filter((e) => e.field === f.name);
        return (
          <div key={f.name}>
            <label htmlFor={`f-${f.name}`} className="mb-1 block text-sm font-medium">
              {f.label}
              {f.required && <span className="text-red-600"> *</span>}
            </label>
            <FieldInput field={f} value={values[f.name]} set={(v) => set(f.name, v)} readOnly={readOnly} refOptions={refOptions} />
            {f.help && <p className="mt-1 text-xs text-primary/50">{f.help}</p>}
            {fieldErrors.map((e, i) => (
              <p key={i} className="mt-1 text-xs text-red-700">
                {f.label} {e.message}
              </p>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function FieldInput({
  field: f,
  value,
  set,
  readOnly,
  refOptions,
}: {
  field: FieldSpec;
  value: FormValues[string];
  set: (v: FormValues[string]) => void;
  readOnly: boolean;
  refOptions: Record<string, ContentRow[]>;
}) {
  const id = `f-${f.name}`;
  const options = f.ref_type ? (refOptions[f.ref_type] ?? []) : [];
  const text = typeof value === "string" ? value : "";

  switch (f.kind) {
    case "textarea":
      return <textarea id={id} rows={3} className={inputCls} value={text} disabled={readOnly} onChange={(e) => set(e.target.value)} />;
    case "json":
      return (
        <textarea
          id={id}
          rows={5}
          spellCheck={false}
          className={`${inputCls} font-mono text-xs`}
          value={text}
          disabled={readOnly}
          onChange={(e) => set(e.target.value)}
        />
      );
    case "number":
    case "integer":
      return (
        <input
          id={id}
          type="number"
          step={f.kind === "integer" ? 1 : "any"}
          min={f.min ?? undefined}
          max={f.max ?? undefined}
          className={inputCls}
          value={text}
          disabled={readOnly}
          onChange={(e) => set(e.target.value)}
        />
      );
    case "bool":
      return (
        <input id={id} type="checkbox" className="h-4 w-4" checked={Boolean(value)} disabled={readOnly} onChange={(e) => set(e.target.checked)} />
      );
    case "select":
      return (
        <select id={id} className={inputCls} value={text} disabled={readOnly} onChange={(e) => set(e.target.value)}>
          <option value="">— select —</option>
          {f.options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      );
    case "ref": {
      const current = text;
      return (
        <select id={id} className={inputCls} value={current} disabled={readOnly} onChange={(e) => set(e.target.value)}>
          <option value="">— none —</option>
          {current && !options.some((o) => o.key === current) && <option value={current}>{current} (not published)</option>}
          {options.map((o) => (
            <option key={o.key} value={o.key}>
              {o.key} — {String(o.title ?? "")}
            </option>
          ))}
        </select>
      );
    }
    case "refs":
      return <RefsInput id={id} value={Array.isArray(value) ? value : []} set={set} readOnly={readOnly} options={options} />;
    default:
      return <input id={id} type="text" className={inputCls} value={text} disabled={readOnly} onChange={(e) => set(e.target.value)} />;
  }
}

/** Ordered list of references: add from published items, reorder, remove. */
function RefsInput({
  id,
  value,
  set,
  readOnly,
  options,
}: {
  id: string;
  value: string[];
  set: (v: string[]) => void;
  readOnly: boolean;
  options: ContentRow[];
}) {
  const titles = new Map(options.map((o) => [o.key, String(o.title ?? "")]));
  const move = (i: number, delta: number) => {
    const next = [...value];
    [next[i], next[i + delta]] = [next[i + delta], next[i]];
    set(next);
  };
  const available = options.filter((o) => !value.includes(o.key));

  return (
    <div className="space-y-1.5">
      {value.length === 0 && <p className="text-xs text-primary/50">None selected.</p>}
      <ol className="space-y-1">
        {value.map((key, i) => (
          <li key={key} className="flex items-center gap-2 rounded-md border border-primary/10 px-2 py-1 text-sm">
            <span className="font-mono text-xs">{key}</span>
            <span className="flex-1 truncate text-primary/60">
              {titles.get(key) ?? <span className="text-amber-700">not published</span>}
            </span>
            {!readOnly && (
              <>
                <IconButton label={`Move ${key} up`} disabled={i === 0} onClick={() => move(i, -1)}>
                  ↑
                </IconButton>
                <IconButton label={`Move ${key} down`} disabled={i === value.length - 1} onClick={() => move(i, 1)}>
                  ↓
                </IconButton>
                <IconButton label={`Remove ${key}`} onClick={() => set(value.filter((k) => k !== key))}>
                  ✕
                </IconButton>
              </>
            )}
          </li>
        ))}
      </ol>
      {!readOnly && (
        <select
          id={id}
          className={inputCls}
          value=""
          disabled={available.length === 0}
          onChange={(e) => e.target.value && set([...value, e.target.value])}
        >
          <option value="">{available.length ? "+ add published item…" : "No more published items to add"}</option>
          {available.map((o) => (
            <option key={o.key} value={o.key}>
              {o.key} — {String(o.title ?? "")}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

function IconButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded px-1.5 text-xs hover:bg-primary/5 disabled:opacity-30"
    >
      {children}
    </button>
  );
}
