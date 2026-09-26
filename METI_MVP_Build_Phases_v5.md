# METI-MC — Trimmed MVP Build Plan (v5)

**Stack:** Next.js (React) + Framer Motion + Tailwind · FastAPI (Python, async) · MongoDB (Motor) + vector index for RAG · Redis · Real LLM provider (config-swappable) · Voice STT/TTS provider (config-swappable) · Docker

**What changed from v4 — closing the 10-stage journey gap:**
- Phase 5 now explicitly includes **resume upload**.
- New: **Phase 5b — AI Profile Understanding** (resume parsing agent, brought back from the original TDD's A03).
- Phase 7's scoring service output is now explicitly structured into the 3 named dimensions your diagram calls for: **Reasoning, Knowledge, Communication**.
- Phase 9's Roadmap is now explicitly tied to **AI Development Coach** framing — the Explainer chat has a "coach mode" grounded in the roadmap, not just the raw scores.
- New: **Phase 13 — Reassessment & Progress** (restored — you want the full loop, not a one-shot assessment).

This version maps 1:1 to your 10-stage flow. Full mapping table below, then the phase changes.

---

## Your 10-Stage Journey → Build Phases (complete mapping)

| Your stage | Phase | What it is in this plan |
|---|---|---|
| 1. User Profile | Phase 5 | Profile form + **resume/CV upload** |
| 2. AI Profile Understanding | **Phase 5b (new)** | Parses resume → structured skills/roles/experience, feeds into scoring context |
| 3. Adaptive Assessment | Phase 5 | 7 forms: MCQ (single/multi-choice), Case Study, Written/Video Communication |
| 4. AI Evidence Analysis | Phase 7 | One scoring service, output split into Reasoning / Knowledge / Communication scores per response |
| 5. AI Competency Profile | Phase 8 | Composite scores (Readiness, Evidence Confidence) + Strengths/Gaps in Summary report |
| 6. AI "Why" Explanation | Phase 8 | AI Results Explainer (voice + text) |
| 7. AI Development Coach | Phase 8 + 9 | Explainer in "coach mode," grounded in the Phase 9 roadmap — answers "what should I practice" using real gap data |
| 8. Personalized Roadmap | Phase 9 | Milestone-based roadmap screen |
| 9. AI Report + Dashboard | Phase 8 | Summary + Detailed report, candidate dashboard |
| 10. Reassessment & Progress | **Phase 13 (new)** | Retake flow, score-over-time comparison |

---

## Phase 0–4
*(unchanged from v4 — Foundation, Content Model, Auth, Landing, Commerce)*

## Phase 5 — Assessment Engine (7 forms, 5 question types) + Resume Upload

*(unchanged core, adding explicit resume intake)*

Forms:
1. Profile & Experience — **now includes a resume/CV file upload field** (PDF/DOCX, stored in object storage, linked to the candidate record)
2. Career Motivation
3. Talent DNA (ranked)
4. Values (Schwartz-informed)
5. Consulting Capability (merged domain module)
6. Communication Response (written text or uploaded video — candidate's choice)
7. Case Study (written or file upload)

**DoD:** Resume file uploads and saves against the candidate's profile, ready for Phase 5b to process.

---

## Phase 5b — AI Profile Understanding (new)

**Objective:** Parse the uploaded resume into structured data the rest of the pipeline can use — this was cut too aggressively in the trim; it's genuinely one of your 10 stages, not optional.

- One focused AI call: resume file → structured JSON (roles, years of experience, industries, key skills claimed, education) — schema-validated like every other AI output in this plan.
- Stored as `EvidenceClaims` linked to the candidate — explicitly tagged as **self-reported evidence** (lowest confidence weight, per the evidence-hierarchy principle carried through from the original TDD).
- Feeds into Phase 7's scoring context (e.g., "candidate claims 3 years of process-improvement experience — does their case-study answer support that?") and into Phase 8's competency profile as context, not as a score booster on its own.
- Frontend: a simple "Here's what we found in your resume — confirm or edit" screen before the candidate proceeds to the adaptive assessment. Keeps the candidate in the loop rather than silently trusting the parse.

**DoD:** Uploading a resume produces a real structured profile the candidate can review/correct before assessment.

---

## Phase 6
*(unchanged — Deterministic Scoring: Talent DNA & Values)*

## Phase 7 — AI Scoring Service (now with 3 named evidence-analysis dimensions)

**Objective:** Same single scoring service as v4, but its output schema now explicitly produces the three dimensions your diagram names, on every relevant response:

```json
{
  "reasoning_score": 0-100,
  "reasoning_evidence": "...",
  "knowledge_score": 0-100,
  "knowledge_evidence": "...",
  "communication_score": 0-100,
  "communication_evidence": "...",
  "overall_confidence": 0-100
}
```

- Reasoning = problem structuring, logic, trade-off handling (from case/written responses)
- Knowledge = factual/domain correctness (from MCQ + scenario items)
- Communication = clarity, structure, audience adaptation (from written/video responses)

This is still **one AI call per evidence item**, not three separate agents — just a richer, named output schema instead of one flat score. Matches your diagram without reintroducing the agent-sprawl I cut earlier.

**DoD:** Every scored response returns all three named dimensions with cited evidence, not a single opaque number.

---

## Phase 8 — Composite Score, Reports & AI Explainer (Explainer now has an explicit "Coach Mode")

*(Readiness/Evidence Confidence, Summary/Detailed reports, voice-enabled chat — unchanged from v4)*

**Addition:** The Explainer has two conversational modes, same underlying agent, different system framing:
- **"Why" mode** (default on the report page) — explains *why* a score is what it is, grounded in evidence.
- **"Coach" mode** (default on the roadmap page, Phase 9) — answers "what should I learn/practice/improve," grounded in the gap analysis + roadmap content, not just raw scores.

Both remain strictly grounded in that candidate's own locked data — no free-form advice untethered from their actual evidence.

**DoD:** Same chat component, context-aware framing depending on which screen it's opened from.

## Phase 9 — Development Roadmap Module
*(unchanged from v4, now explicitly the data source for Phase 8's Coach Mode)*

## Phase 10 — Site-Wide RAG Support Chatbot
*(unchanged from v4)*

## Phase 11 — Admin Panel
*(unchanged from v4)*

## Phase 12 — UI/UX Pass + Motion & Interactivity Layer
*(unchanged from v4)*

---

## Phase 13 — Reassessment & Progress (restored)

**Objective:** Close the loop — your diagram's stage 10, previously cut. Without this, the roadmap and coach mode have nowhere to lead.

- `reassessment_schedule` field on the roadmap (e.g., "retake the Consulting Capability module in 8 weeks").
- Candidate can start a **new attempt** of a specific module without losing their prior one — each attempt is its own versioned record (consistent with the "immutable, versioned" principle carried through the whole plan).
- Simple **progress view**: prior score vs. new score, side by side, per competency — a before/after, not a complex trend-analytics dashboard (keeping it MVP-sized).
- Roadmap regenerates after a reassessment reflecting the updated gaps.

**DoD:** A candidate can retake an assessment, see their score change against their prior attempt, and get an updated roadmap — the full loop from your diagram closes.

## Phase 14 — Test & Deploy
*(was Phase 13)* Now also smoke-tests reassessment flow and the resume-parsing step.

---

Say **"START PHASE 0"** and I'll scaffold this version — now a complete match to your 10-stage diagram.
