"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  contentApi,
  describeError,
  type ContentRow,
  type ContentTypeSpec,
  type ContentVersion,
  type ValidationError,
} from "@/lib/content";

import ContentForm, { fromForm, toForm, type FormValues } from "./ContentForm";

type Selection = { mode: "new" } | { mode: "item"; key: string } | null;
type Notice = { kind: "ok" | "error"; text: string } | null;
type StatusFilter = "" | "draft" | "published";

const btn =
  "rounded-md border border-primary/15 px-3 py-1.5 text-sm hover:bg-primary/5 disabled:opacity-40";
const btnPrimary =
  "rounded-md bg-accent-cta px-3 py-1.5 text-sm text-primary hover:bg-accent-cta/85 disabled:opacity-40";

export default function ContentAdmin() {
  const [types, setTypes] = useState<ContentTypeSpec[]>([]);
  const [typeName, setTypeName] = useState<string>("");
  const [loadError, setLoadError] = useState<string>("");

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  // Bumped after every write so the table and reference pickers reload.
  const [dataVersion, setDataVersion] = useState(0);
  const rowsQuery = `${typeName}|${statusFilter}|${dataVersion}`;
  const [loadedRows, setLoadedRows] = useState<{ query: string; rows: ContentRow[] }>({ query: "", rows: [] });
  const rows = loadedRows.rows;
  const rowsLoading = loadedRows.query !== rowsQuery;
  const [refOptions, setRefOptions] = useState<Record<string, ContentRow[]>>({});

  const [selection, setSelection] = useState<Selection>(null);
  const [history, setHistory] = useState<ContentVersion[]>([]);
  const [viewVersion, setViewVersion] = useState<number | null>(null);
  const [newKey, setNewKey] = useState("");
  const [values, setValues] = useState<FormValues>({});
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [notice, setNotice] = useState<Notice>(null);
  const [busy, setBusy] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");

  const spec = useMemo(() => types.find((t) => t.name === typeName), [types, typeName]);
  const viewing = history.find((v) => v.version === viewVersion) ?? null;
  const draft = history.find((v) => v.status === "draft") ?? null;
  const editable = selection?.mode === "new" || viewing?.status === "draft";

  useEffect(() => {
    contentApi
      .types()
      .then((t) => {
        setTypes(t);
        setTypeName((current) => current || t[0]?.name || "");
      })
      .catch((err) => setLoadError(describeError(err).message));
  }, []);

  useEffect(() => {
    if (!typeName) return;
    let cancelled = false;
    contentApi
      .list(typeName, statusFilter || undefined)
      .then((r) => !cancelled && setLoadedRows({ query: rowsQuery, rows: r }))
      .catch((err) => {
        if (cancelled) return;
        setLoadedRows({ query: rowsQuery, rows: [] });
        setNotice({ kind: "error", text: describeError(err).message });
      });
    return () => {
      cancelled = true;
    };
  }, [typeName, statusFilter, rowsQuery]);

  useEffect(() => {
    if (!spec) return;
    let cancelled = false;
    const refTypes = [...new Set(spec.fields.map((f) => f.ref_type).filter((t): t is string => !!t))];
    Promise.all(refTypes.map(async (t) => [t, await contentApi.list(t, "published")] as const))
      .then((entries) => !cancelled && setRefOptions(Object.fromEntries(entries)))
      .catch((err) => !cancelled && setNotice({ kind: "error", text: describeError(err).message }));
    return () => {
      cancelled = true;
    };
  }, [spec, dataVersion]);

  const showVersion = useCallback(
    (version: ContentVersion) => {
      if (!spec) return;
      setViewVersion(version.version);
      setValues(toForm(spec, version.data));
      setErrors([]);
    },
    [spec],
  );

  const openItem = useCallback(
    async (key: string, preferVersion?: number) => {
      if (!typeName || !spec) return;
      if (selection?.mode !== "item" || selection.key !== key) {
        // Blank form until the item's versions arrive, so no stale values from another type render.
        setHistory([]);
        setViewVersion(null);
        setValues(toForm(spec, {}));
      }
      setSelection({ mode: "item", key });
      setNotice(null);
      try {
        const { versions } = await contentApi.history(typeName, key);
        setHistory(versions);
        const pick =
          versions.find((v) => v.version === preferVersion) ?? versions.find((v) => v.status === "draft") ?? versions[0];
        if (pick) showVersion(pick);
      } catch (err) {
        setNotice({ kind: "error", text: describeError(err).message });
      }
    },
    [typeName, spec, selection, showVersion],
  );

  const selectType = (name: string) => {
    setTypeName(name);
    setSelection(null);
    setHistory([]);
    setNotice(null);
    setErrors([]);
    setStatusFilter("");
  };

  const startNew = () => {
    if (!spec) return;
    setSelection({ mode: "new" });
    setHistory([]);
    setViewVersion(null);
    setNewKey("");
    setValues(toForm(spec, {}));
    setErrors([]);
    setNotice(null);
  };

  /** Run an action, show its outcome, then refresh the table (and reload the item if given). */
  const run = async (action: () => Promise<{ text: string; key?: string; version?: number } | void>) => {
    setBusy(true);
    setNotice(null);
    try {
      const result = await action();
      if (result) {
        if (result.key) await openItem(result.key, result.version);
        setNotice({ kind: "ok", text: result.text });
        setErrors([]);
      }
    } catch (err) {
      const { message, errors: fieldErrors } = describeError(err);
      setNotice({ kind: "error", text: message });
      setErrors(fieldErrors);
    } finally {
      setBusy(false);
      setDataVersion((v) => v + 1);
    }
  };

  const formData = () => {
    const { data, errors: formErrors } = fromForm(spec!, values);
    if (formErrors.length) {
      setErrors(formErrors);
      throw Object.assign(new Error("Fix the highlighted fields"), { body: { detail: "Fix the highlighted fields", errors: formErrors } });
    }
    return data;
  };

  const key = selection?.mode === "item" ? selection.key : newKey.trim();

  const generateAi = () =>
    run(async () => {
      if (!spec || !aiInstruction.trim()) return;
      let existing: Record<string, unknown> | undefined;
      try {
        existing = fromForm(spec, values).data;
      } catch {
        existing = undefined;
      }
      const { data } = await contentApi.generate(typeName, aiInstruction.trim(), existing && Object.keys(existing).length ? existing : undefined);
      setValues(toForm(spec, data));
      setAiInstruction("");
      return { text: "AI drafted this content — review and edit it, then Create/Save." };
    });

  const importFile = (file: File) =>
    run(async () => {
      const res = await contentApi.importFile(typeName, file);
      const parts = [`${res.created.length} created`];
      if (res.skipped.length) parts.push(`${res.skipped.length} skipped (already exist)`);
      if (res.errors.length) parts.push(`${res.errors.length} with errors`);
      return { text: `Import: ${parts.join(", ")}.` };
    });

  const create = () =>
    run(async () => {
      const item = await contentApi.create(typeName, key, formData());
      return { text: `Created ${item.key} v${item.version} as a draft`, key: item.key, version: item.version };
    });
  const save = () =>
    run(async () => {
      const item = await contentApi.saveDraft(typeName, key, formData());
      return { text: `Saved draft v${item.version}`, key: item.key, version: item.version };
    });
  const validate = () =>
    run(async () => {
      await contentApi.saveDraft(typeName, key, formData());
      const result = await contentApi.validate(typeName, key);
      setErrors(result.errors);
      if (!result.ok) throw { body: { detail: `${result.errors.length} problem(s) must be fixed before publishing`, errors: result.errors } };
      return { text: "Draft saved and valid — ready to publish" };
    });
  const publish = () =>
    run(async () => {
      await contentApi.saveDraft(typeName, key, formData());
      const item = await contentApi.publish(typeName, key);
      return { text: `Published ${item.key} v${item.version} — this version is now locked`, key: item.key, version: item.version };
    });
  const newVersion = () =>
    run(async () => {
      const item = await contentApi.newVersion(typeName, key);
      return { text: `Started draft v${item.version} from v${item.based_on_version}`, key: item.key, version: item.version };
    });
  const discard = () => {
    if (!draft || !window.confirm(`Discard draft v${draft.version} of ${key}? This cannot be undone.`)) return;
    run(async () => {
      const item = await contentApi.discardDraft(typeName, key);
      const remaining = history.filter((v) => v.version !== item.version);
      if (remaining.length) {
        await openItem(key);
      } else {
        setSelection(null);
        setHistory([]);
      }
      return { text: `Discarded draft v${item.version}` };
    });
  };

  if (loadError) {
    return (
      <p role="alert" className="p-8 text-sm text-red-700">
        Could not load content types: {loadError}
      </p>
    );
  }

  return (
    <div className="grid flex-1 grid-cols-1 content-start gap-6 p-6 lg:grid-cols-[180px_minmax(0,1fr)] xl:grid-cols-[200px_minmax(0,1fr)_minmax(400px,480px)]">
      <nav aria-label="Content types" className="flex flex-wrap gap-1 lg:block lg:space-y-1">
        {types.map((t) => (
          <button
            key={t.name}
            onClick={() => selectType(t.name)}
            aria-current={t.name === typeName ? "page" : undefined}
            className={`rounded-md px-3 py-1.5 text-left text-sm lg:block lg:w-full ${
              t.name === typeName ? "bg-accent-cta text-primary" : "hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <section className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold">{spec?.label ?? "…"}</h2>
          <select
            aria-label="Filter by status"
            className="rounded-md border border-primary/15 bg-surface-card px-2 py-1 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          >
            <option value="">All</option>
            <option value="draft">Has draft</option>
            <option value="published">Published</option>
          </select>
          <span className="text-sm text-primary/50">{rowsLoading ? "Loading…" : `${rows.length} items`}</span>
          <label className={`${btn} ml-auto cursor-pointer`} title="Bulk-create items from a JSON file">
            Import file
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              disabled={!spec || busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) importFile(f);
              }}
            />
          </label>
          <button className={btnPrimary} onClick={startNew} disabled={!spec}>
            + New
          </button>
        </div>

        <div className="overflow-x-auto rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)]">
          <table className="w-full text-sm">
            <thead className="bg-primary/[0.03] text-left text-xs uppercase tracking-wide text-primary/60">
              <tr>
                <th className="px-3 py-2">Key</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Latest</th>
                <th className="px-3 py-2">Live version</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const selected = selection?.mode === "item" && selection.key === r.key;
                return (
                  <tr
                    key={r.key}
                    onClick={() => openItem(r.key)}
                    className={`cursor-pointer border-t border-primary/5 ${
                      selected ? "bg-primary/[0.06]" : "hover:bg-primary/[0.03]"
                    }`}
                  >
                    <td className="px-3 py-2 font-mono text-xs">
                      <button
                        className="text-left hover:underline"
                        onClick={(e) => {
                          e.stopPropagation();
                          openItem(r.key);
                        }}
                      >
                        {r.key}
                      </button>
                    </td>
                    <td className="max-w-0 truncate px-3 py-2" title={String(r.title ?? "")}>
                      {String(r.title ?? "") || <span className="text-primary/40">(untitled)</span>}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      v{r.latest_version} <StatusBadge status={r.latest_status} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {r.published_version ? `v${r.published_version}` : <span className="text-primary/40">—</span>}
                    </td>
                  </tr>
                );
              })}
              {!rowsLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-8 text-center text-primary/50">
                    Nothing here yet. Use “+ New” to create the first {spec?.label.toLowerCase() ?? "item"}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="min-w-0 lg:col-start-2 xl:col-start-auto">
        {!selection || !spec ? (
          <p className="rounded-lg border border-dashed border-primary/15 p-6 text-sm text-primary/50">
            Select an item to view or edit it, or create a new one.
          </p>
        ) : (
          <div className="space-y-4 rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-4">
            <div>
              {selection.mode === "new" ? (
                <>
                  <h3 className="font-semibold">New {spec.label.toLowerCase()} item</h3>
                  <label htmlFor="new-key" className="mb-1 mt-3 block text-sm font-medium">
                    Key<span className="text-red-600"> *</span>
                  </label>
                  <input
                    id="new-key"
                    className="w-full rounded-md border border-primary/15 bg-surface-card px-2.5 py-1.5 font-mono text-sm"
                    value={newKey}
                    placeholder={spec.key_help || "Unique key"}
                    onChange={(e) => setNewKey(e.target.value)}
                  />
                  <p className="mt-1 text-xs text-primary/50">
                    Permanent id across versions. Letters, digits, “.”, “_” and “-”.
                  </p>
                  {errors
                    .filter((e) => e.field === "key")
                    .map((e, i) => (
                      <p key={i} className="mt-1 text-xs text-red-700">
                        Key: {e.message}
                      </p>
                    ))}
                </>
              ) : (
                <>
                  <h3 className="font-mono font-semibold">{selection.key}</h3>
                  <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="Versions">
                    {history.map((v) => (
                      <button
                        key={v.version}
                        onClick={() => showVersion(v)}
                        aria-pressed={v.version === viewVersion}
                        className={`rounded-full border px-2.5 py-0.5 text-xs ${
                          v.version === viewVersion
                            ? "border-accent-cta bg-accent-cta text-primary"
                            : "border-primary/15 hover:bg-primary/5"
                        }`}
                      >
                        v{v.version} · {v.status}
                      </button>
                    ))}
                  </div>
                  {viewing && (
                    <p className="mt-2 text-xs text-primary/50">
                      {viewing.status === "published"
                        ? `Published ${new Date(viewing.published_at!).toLocaleString()} by ${viewing.published_by} — locked, read-only.`
                        : `Draft${viewing.based_on_version ? ` based on v${viewing.based_on_version}` : ""}, last saved ${new Date(
                            viewing.updated_at,
                          ).toLocaleString()} by ${viewing.updated_by}.`}
                    </p>
                  )}
                </>
              )}
            </div>

            {notice && (
              <p
                role={notice.kind === "error" ? "alert" : "status"}
                className={`rounded-md px-3 py-2 text-sm ${
                  notice.kind === "error"
                    ? "bg-red-50 text-red-800"
                    : "bg-green-50 text-green-800"
                }`}
              >
                {notice.text}
              </p>
            )}

            {editable && (
              <div className="rounded-md border border-accent-cta/40 bg-accent-cta/5 p-3">
                <label htmlFor="ai-instruction" className="block text-sm font-medium">
                  ✨ Generate with AI
                </label>
                <p className="mt-0.5 text-xs text-primary/55">Describe what you want; AI drafts the fields below for you to review and edit.</p>
                <div className="mt-2 flex gap-2">
                  <input
                    id="ai-instruction"
                    className="min-w-0 flex-1 rounded-md border border-primary/15 bg-surface-card px-2.5 py-1.5 text-sm"
                    placeholder={`e.g. ${aiPlaceholder(typeName)}`}
                    value={aiInstruction}
                    disabled={busy}
                    onChange={(e) => setAiInstruction(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && aiInstruction.trim() && generateAi()}
                  />
                  <button className={btnPrimary} onClick={generateAi} disabled={busy || !aiInstruction.trim()}>
                    {busy ? "Drafting…" : "Draft"}
                  </button>
                </div>
              </div>
            )}

            <ContentForm spec={spec} values={values} onChange={setValues} readOnly={!editable || busy} errors={errors} refOptions={refOptions} />

            {errors.some((e) => !spec.fields.some((f) => f.name === e.field) && e.field !== "key") && (
              <ul className="list-disc pl-5 text-xs text-red-700">
                {errors
                  .filter((e) => !spec.fields.some((f) => f.name === e.field) && e.field !== "key")
                  .map((e, i) => (
                    <li key={i}>
                      {e.field}: {e.message}
                    </li>
                  ))}
              </ul>
            )}

            <div className="flex flex-wrap gap-2 border-t border-primary/10 pt-4">
              {selection.mode === "new" ? (
                <button className={btnPrimary} onClick={create} disabled={busy || !newKey.trim()}>
                  Create draft
                </button>
              ) : editable ? (
                <>
                  <button className={btn} onClick={save} disabled={busy}>
                    Save draft
                  </button>
                  <button className={btn} onClick={validate} disabled={busy}>
                    Validate
                  </button>
                  <button className={btnPrimary} onClick={publish} disabled={busy}>
                    Publish v{viewing?.version}
                  </button>
                  <button className={`${btn} ml-auto text-red-700`} onClick={discard} disabled={busy}>
                    Discard draft
                  </button>
                </>
              ) : draft ? (
                <button className={btn} onClick={() => showVersion(draft)} disabled={busy}>
                  Go to open draft v{draft.version}
                </button>
              ) : (
                <button className={btnPrimary} onClick={newVersion} disabled={busy}>
                  Create new version
                </button>
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function aiPlaceholder(type: string): string {
  const map: Record<string, string> = {
    support_kb: "Write a help entry explaining our refund policy",
    questions: "A single-choice question testing MECE issue trees, with 4 options and the correct answer",
    site_content: "Landing copy for a consulting readiness assessment aimed at graduates",
    competencies: "A competency for commercial and financial acumen",
    videos: "An explainer video entry titled 'Welcome to METI'",
    prompts: "A scoring prompt that grades a memo on clarity",
  };
  return map[type] ?? "Describe the item you want to create";
}

function StatusBadge({ status }: { status: "draft" | "published" }) {
  return (
    <span
      className={`ml-1 rounded-full px-2 py-0.5 text-xs ${
        status === "published"
          ? "bg-green-100 text-green-800"
          : "bg-amber-100 text-amber-800"
      }`}
    >
      {status}
    </span>
  );
}
