# METI-MC — Trimmed MVP Build Plan (v2)

**Stack:** Next.js (React) + Tailwind · FastAPI (Python, async) · MongoDB (Motor) · Redis · Real LLM provider (config-swappable) · Docker

**What changed from v1:**
- Roles: **candidate + admin only** (was 7). Admin absorbs authoring, pricing, and score approval.
- Forms: **7 assessments** instead of 22 (merged domains, see Phase 5).
- Question types: **5** instead of 15.
- Composite scores: **2** (Readiness, Evidence Confidence) instead of 5.
- AI agents: **1 scoring service + 1 report generator + 1 explainer chatbot** instead of 11 separate agents.
- AI is now a *visible, front-and-center feature* — not just backend scoring. The Results Explainer chatbot is the flagship screen.
- Phases: **12** instead of 18.

**Ground rules (unchanged):**
- Nothing hardcoded — content, pricing, prompts all in MongoDB, editable by Admin.
- Every screen wired to real APIs, all four states (loading/empty/error/success) designed, not just happy path.
- Clean, minimal, uncluttered UI — one design system, no feature-crowding. Fewer screens, done well, beats many screens done thin.

---

## Phase 0 — Foundation

Repo (`/frontend`, `/backend`, `/infra`), docker-compose (mongo, redis, backend, frontend), config via `.env`, Motor client + index bootstrap, health check, structured logging, CORS.

**DoD:** `docker compose up` boots everything; `/health` → 200.

---

## Phase 1 — Content Model & Admin Core

Collections: `assessments`, `sections`, `questions`, `competencies`, `videos`, `products`, `prompts`, `report_templates`. Versioned (draft → published, immutable once published). Basic admin CRUD screens (table + form) for all of the above. Seed script loads starter content as data.

**DoD:** Admin creates a question, publishes an assessment version, it's live via API — no redeploy.

---

## Phase 2 — Auth & Access (2 roles)

`users` collection with `role: candidate | admin`. Email + password login, JWT (skip OTP/SSO for MVP — one less moving part). `require_role()` dependency. Single consent checkbox at registration, logged with timestamp (not a full versioned consent system).

**DoD:** Candidate registers/logs in; admin routes 403 for candidates.

---

## Phase 3 — Landing & Orientation

Clean landing page (hero, why-consulting narrative, CTA) — copy pulled from a `site_content` collection. **One** explainer video (not a multi-video gated sequence) with a simple "mark as watched" completion — no milestone tracking, no knowledge-check quiz gate.

**DoD:** Candidate watches the video, proceeds to registration.

---

## Phase 4 — Commerce

`products` (Consulting Assessment, Personality & Values Assessment, Bundle, Detailed Report upgrade), one flat price per product (no regional/coupon logic), `entitlements`. Stripe test-mode checkout, webhook-driven entitlement activation (still real, not a fake "mark paid" button).

**DoD:** Paying unlocks the right product server-side; unpaid users are blocked even via direct API call.

---

## Phase 5 — Assessment Engine (7 forms, 5 question types)

One generic runner component, driven entirely by question schema. **5 question types**: single choice, multi-select, Likert scale, rank-N (drag + keyboard accessible), free text. Simple conditional skip logic (if answer = X, skip section) instead of a full expression engine.

**The 7 forms (merged from the TDD's 22):**
1. Profile & Experience
2. Career Motivation
3. Talent DNA (ranked)
4. Values (Schwartz-informed)
5. Consulting Capability (merges strategy/value-chain/process/transformation/AI-awareness into one ~20-question module)
6. Written Communication (one memo-style response)
7. Case Study (one case, upload or written response)

Autosave, resume from any device.

**DoD:** All 7 forms run through the one engine, autosave verified.

---

## Phase 6 — Deterministic Scoring (Talent DNA & Values)

Rank scoring (4-3-2-1) and Schwartz centering computed in code, not AI. Clean values-wheel visualization (real data, not a static image).

**DoD:** Completing forms 3–4 produces a reproducible values profile.

---

## Phase 7 — AI Scoring Service (the core AI feature, backend half)

**One scoring service**, not eleven separate agents — it takes an evidence type (form response, written answer, case, video) + its rubric, calls the LLM provider, and returns a structured, schema-validated score with cited reasoning. Video/case submissions are **upload-based** (skip live in-browser recording for MVP) but transcription and AI rubric-scoring are real. Failed schema validation retries once, then flags for admin review — never fakes a score.

**DoD:** Submitting the case or written response produces a real AI-generated, schema-valid score with evidence citations.

---

## Phase 8 — Composite Score, Reports & AI Results Explainer (the flagship AI feature)

- **2 composite scores**: Readiness (0–100) and Evidence Confidence (0–100), computed deterministically from Phase 6–7 outputs.
- **Summary of Findings**: auto-generated after any paid assessment (strengths, development themes, next-step CTA).
- **Detailed Report** (unlocked by the upgrade product): full score breakdown, "why this finding" grounding, personal development themes.
- **AI Results Explainer** — an embedded chat panel on the report page. Candidate asks "why is this a strength?", "what should I focus on first?" in plain language; answers are grounded only in that candidate's locked score/evidence — nothing invented. This is the single most visible AI touchpoint on the site and should get the cleanest UI treatment in the whole app.

**DoD:** Candidate sees Summary immediately; Detailed Report unlocks on upgrade; the Explainer chat answers real questions against real data.

---

## Phase 9 — Admin Panel (single role, light governance)

Content CRUD (from Phase 1, matured slightly): questions, rubrics, videos, pricing. One "regenerate / approve" action per score if an admin wants to override an AI result — no separate reviewer role, no evidence-viewer sub-app, just a simple table with an override field and a reason box.

**DoD:** Admin edits a question and publishes a new version with zero code changes.

---

## Phase 10 — UI/UX Pass (this is where "neat and clean" gets enforced)

One Tailwind design system — consistent type scale, spacing, colors across every screen. Shared component library (buttons, cards, tables, toasts, loading/empty/error states). Deliberately **few screens, generously spaced, no clutter** — resist the urge to show every data point on one page; the report and explainer screens especially should feel calm, not dashboard-crowded. Responsive pass, basic accessibility (keyboard nav, focus states, captions on the one video).

**DoD:** Every screen shares the same design system; nothing looks bolted-on.

---

## Phase 11 — Test & Deploy

Unit tests on the scoring math (rank conversion, Schwartz centering, composite score) since that must be exact. One end-to-end smoke flow: register → pay → assess → get report → chat with explainer. Docker deploy to a single environment, env-based secrets, health checks.

**DoD:** Live URL where a stakeholder can go end-to-end and see the AI Explainer working on a real score.

---

## What's cut vs. the TDD (confirmed deferred, not lost — just not MVP)

- 22 forms → 7; 15 question types → 5; 20 competencies → a smaller set (6–8) for a clean radar chart
- 7 roles → 2; no tenant/mentor/assessor/compliance UI
- 11 AI agents → 1 scoring service + 1 report generator + 1 explainer
- 5 composite indices → 2
- Live video recording, case timers/exhibits, AI-usage-mode switching, coupons/regional pricing, reassessment scheduling, Neo4j graph — all deferred

---

Say **"START PHASE 0"** and I'll scaffold this version.
