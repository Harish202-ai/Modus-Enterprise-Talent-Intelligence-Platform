"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import CapabilityRadar from "@/components/charts/CapabilityRadar";
import EvidenceScores from "@/components/charts/EvidenceScores";
import TalentDnaBars from "@/components/charts/TalentDnaBars";
import ValuesWheel from "@/components/charts/ValuesWheel";
import { errorMessage, fetchBlobUrl } from "@/lib/api";
import { adminUsersApi, type CandidateDetail, type CandidateFile } from "@/lib/adminUsers";
import { isScored } from "@/lib/scores";

const card = "rounded-3xl border border-line bg-surface-card shadow-[var(--shadow-soft)] p-5";
const VIDEO = ["mp4", "mov", "webm"];

function FileItem({ file }: { file: CandidateFile }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const isVideo = VIDEO.includes(file.kind);

  const open = async () => {
    setError("");
    try {
      setUrl(await fetchBlobUrl(`/v1/files/${file.id}`));
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="min-w-0">
          <span className="font-medium">{file.filename}</span>
          <span className="ml-2 text-xs uppercase tracking-wide text-primary/50">{file.kind}{file.purpose ? ` · ${file.purpose}` : ""}</span>
        </span>
        {!url && (
          <button onClick={open} className="rounded-md border border-primary/15 px-3 py-1 text-xs hover:bg-primary/5">
            {isVideo ? "Play video" : "Open"}
          </button>
        )}
        {url && !isVideo && (
          <a href={url} download={file.filename} className="rounded-md border border-primary/15 px-3 py-1 text-xs hover:bg-primary/5">Download</a>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      {url && isVideo && <video src={url} controls className="mt-2 w-full max-w-md rounded-md border border-primary/10" />}
    </li>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className={card}>
      <h2 className="text-lg">{title}</h2>
      {hint && <p className="mt-0.5 text-sm text-primary/60">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function CandidateDetailView() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    adminUsersApi
      .detail(id)
      .then((r) => !stop && setD(r))
      .catch((err) => !stop && setError(errorMessage(err)));
    return () => {
      stop = true;
    };
  }, [id]);

  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!d) return <p role="status" className="text-sm text-primary/60">Loading the student report…</p>;

  const s = d.scores;
  const wc = s.written_communication;
  const cs = s.case_study;
  const otherFiles = d.files.filter((f) => f.purpose !== "interview");
  const nothingYet =
    !d.report?.scored && !isScored(s.talent_dna) && !isScored(s.values) && wc.status === "not_submitted" && cs.status === "not_submitted" && d.interviews.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/admin/users" className="text-sm text-accent-cta hover:underline">← All students</Link>
        <h1 className="mt-2 text-2xl">{d.user.full_name ?? d.user.email}</h1>
        <p className="text-sm text-primary/60">
          {d.user.email} · joined {d.user.created_at ? new Date(d.user.created_at).toLocaleDateString() : "—"} · package: {d.entitlements.join(", ") || "none"}
        </p>
      </div>

      {(() => {
        const submitted = d.attempts.filter((a) => a.status === "submitted").length;
        return (
          <div className={`${card} flex flex-wrap gap-6 text-sm`}>
            <span><span className="font-heading text-xl font-bold">{submitted}</span> <span className="text-primary/60">exams submitted</span></span>
            <span><span className="font-heading text-xl font-bold">{d.interviews.length}</span> <span className="text-primary/60">video interview{d.interviews.length === 1 ? "" : "s"}</span></span>
            <span><span className="font-heading text-xl font-bold">{d.report?.readiness ?? "—"}</span> <span className="text-primary/60">readiness{d.report?.readiness_band ? ` · ${d.report.readiness_band}` : ""}</span></span>
          </div>
        );
      })()}

      {nothingYet && <div className={`${card} text-sm text-primary/60`}>This student hasn&apos;t completed anything yet.</div>}

      {/* Resume / CV */}
      {(() => {
        const cv = d.resume?.confirmed ?? d.resume?.parsed;
        if (!cv) return null;
        return (
          <Section title="Resume / CV" hint={d.resume?.confirmed ? "As confirmed by the student." : "Read from their CV by AI (not yet confirmed)."}>
            {cv.summary && <p className="text-sm text-primary/75">{cv.summary}</p>}
            {cv.total_years_experience != null && <p className="mt-2 text-sm"><span className="font-medium">Experience:</span> {cv.total_years_experience} years</p>}
            {!!cv.roles?.length && (
              <div className="mt-3">
                <h3 className="text-sm font-semibold">Roles</h3>
                <ul className="mt-1 space-y-1.5 text-sm">
                  {cv.roles.map((r, i) => (
                    <li key={i}>
                      <span className="font-medium">{r.title}</span>
                      {r.organisation ? ` · ${r.organisation}` : ""}
                      {r.start || r.end ? <span className="text-primary/55"> ({r.start ?? "?"}–{r.end ?? "?"})</span> : null}
                      {!!r.highlights?.length && <ul className="ml-4 list-disc text-primary/70">{r.highlights.map((h, j) => <li key={j}>{h}</li>)}</ul>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!!cv.education?.length && (
              <div className="mt-3">
                <h3 className="text-sm font-semibold">Education</h3>
                <ul className="mt-1 space-y-1 text-sm text-primary/70">
                  {cv.education.map((e, i) => <li key={i}>{e.qualification}{e.institution ? ` · ${e.institution}` : ""}{e.year ? ` (${e.year})` : ""}</li>)}
                </ul>
              </div>
            )}
            {!!cv.industries?.length && <p className="mt-3 text-sm"><span className="font-medium">Industries:</span> {cv.industries.join(", ")}</p>}
            {!!cv.skills?.length && <p className="mt-1 text-sm"><span className="font-medium">Skills:</span> {cv.skills.join(", ")}</p>}
          </Section>
        );
      })()}

      {/* Overall */}
      {d.report?.scored && (
        <Section title="Overall" hint="How ready they are, and how much evidence backs it up.">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="font-heading text-3xl font-bold">{d.report.readiness ?? "—"}</div>
              <div className="text-xs uppercase tracking-wide text-primary/55">Readiness · {d.report.readiness_band}</div>
            </div>
            <div>
              <div className="font-heading text-3xl font-bold">{d.report.evidence_confidence}</div>
              <div className="text-xs uppercase tracking-wide text-primary/55">Evidence confidence</div>
            </div>
          </div>
          {(d.report.strengths.length > 0 || d.report.development_themes.length > 0) && (
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold">Strengths</h3>
                <ul className="mt-1 space-y-1 text-sm text-primary/70">
                  {d.report.strengths.map((x) => <li key={x.label}>• {x.label}</li>)}
                  {d.report.strengths.length === 0 && <li className="text-primary/50">—</li>}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold">To develop</h3>
                <ul className="mt-1 space-y-1 text-sm text-primary/70">
                  {d.report.development_themes.map((x) => <li key={x.label}>• {x.label}</li>)}
                  {d.report.development_themes.length === 0 && <li className="text-primary/50">—</li>}
                </ul>
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Consulting knowledge */}
      {isScored(s.capability) && (
        <Section title="Consulting knowledge (exam)" hint={`Score ${Math.round(s.capability.overall_pct)}% · ${s.capability.correct} of ${s.capability.total} correct.`}>
          <CapabilityRadar competencies={s.capability.competencies} />
        </Section>
      )}

      {/* Talent DNA */}
      {isScored(s.talent_dna) && (
        <Section title="How they work (Talent DNA)" hint="Strongest working styles first.">
          <TalentDnaBars dimensions={s.talent_dna.dimensions} />
        </Section>
      )}

      {/* Values */}
      {isScored(s.values) && (
        <Section title="What matters to them (Values)" hint="Value priorities relative to their own average.">
          <ValuesWheel basic={s.values.basic} />
        </Section>
      )}

      {/* Written communication (AI-scored) */}
      {wc.status !== "not_submitted" && "responses" in wc && (
        <Section title="Written answer (AI-marked)" hint="Reasoning, knowledge and communication, each with the evidence behind it.">
          <EvidenceScores responses={wc.responses ?? []} />
        </Section>
      )}

      {/* Case study (AI-scored) */}
      {cs.status !== "not_submitted" && "responses" in cs && (
        <Section title="Case answer (AI-marked)" hint="Reasoning, knowledge and communication, each with the evidence behind it.">
          <EvidenceScores responses={cs.responses ?? []} />
        </Section>
      )}

      {/* Video interviews */}
      {d.interviews.length > 0 && (
        <Section title="Video interview" hint="Recording, how many questions were answered, and any attention warnings.">
          <ul className="divide-y divide-primary/10">
            {d.interviews.map((iv) => (
              <li key={iv.id} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span>
                    {new Date(iv.created_at).toLocaleString()} · {iv.answered}/{iv.questions_total} questions
                    {iv.duration_seconds ? ` · ${Math.round(iv.duration_seconds / 60)} min` : ""}
                  </span>
                  <span className={`text-xs ${iv.auto_submitted ? "text-red-700" : "text-primary/55"}`}>
                    {iv.warnings} warning{iv.warnings === 1 ? "" : "s"}{iv.auto_submitted ? " · auto-submitted" : ""}
                  </span>
                </div>
                {iv.file && <ul><FileItem file={{ ...iv.file, size: 0, purpose: "interview" }} /></ul>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Other uploads */}
      {otherFiles.length > 0 && (
        <Section title="Uploads" hint="CVs and any documents they submitted.">
          <ul className="divide-y divide-primary/10">
            {otherFiles.map((f) => <FileItem key={f.id} file={f} />)}
          </ul>
        </Section>
      )}

      {/* Attempts log */}
      <Section title="Exam attempts">
        <ul className="space-y-1.5 text-sm">
          {d.attempts.map((a) => (
            <li key={a.id} className="flex justify-between gap-3">
              <span>{a.assessment_key}</span>
              <span className="text-primary/60">{a.status}{a.submitted_at ? ` · ${new Date(a.submitted_at).toLocaleDateString()}` : ""}</span>
            </li>
          ))}
          {d.attempts.length === 0 && <li className="text-primary/50">No attempts yet.</li>}
        </ul>
      </Section>
    </div>
  );
}
