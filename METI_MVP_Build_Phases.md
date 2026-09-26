# METI-MC — Complete MVP Build Phase Plan

**Stack:** Next.js (React) + Tailwind · FastAPI (Python, async) · MongoDB (Motor) · Redis (session/queue) · Real LLM provider (config-swappable) · Docker

**Ground rules for every phase below (non-negotiable):**
- Nothing is hardcoded. Questions, rubrics, videos, competencies, weights, prompts, prices, roles, report templates — all MongoDB documents, editable via the admin layer, never inline in code.
- Every screen ships fully wired to real APIs — no dead buttons, no placeholder data.
- AI features call a real provider through one abstraction (`ai/provider.py`), config-selectable — not mocked, but not required to stream in real time.
- Every phase ends in a working, demoable slice — not a half-built layer.

---

## Phase 0 — Foundation

**Objective:** Repo, environments, and the "everything from DB" skeleton exist before any feature is built.

- Monorepo: `/frontend` (Next.js), `/backend` (FastAPI), `/infra` (Docker Compose: mongo, redis, backend, frontend).
- `backend/app/config.py` — all env vars (Mongo URI, Redis URI, JWT secret, AI provider + key, payment keys) via `.env`, never hardcoded.
- `backend/app/database.py` — Motor client, collection accessors, index-creation bootstrap script.
- Base collections created with indexes: `tenants`, `users`, `audit_events`.
- Tenant model stood up (`tenant_id` on every future collection) even though MVP runs single-tenant — cheap to do now, expensive to retrofit.
- Health check endpoint, structured logging, CORS config.

**Definition of Done:** `docker compose up` boots Mongo + Redis + FastAPI + Next.js; `/health` returns 200; a seed script can create a tenant.

---

## Phase 1 — Content Model & Admin Authoring Core

**Objective:** The "no hardcoding" backbone. Build this *before* any candidate-facing feature so every later phase reads from DB.

- Collections: `assessment_definitions`, `sections`, `questions`, `rubrics`, `competencies`, `values_taxonomy`, `videos`, `products`, `price_book`, `prompt_versions`, `report_templates`.
- Every content collection is **versioned**: draft → published, immutable once published, edits create a new version.
- Minimal admin UI (`/admin/content`): CRUD for questions, rubrics, competencies, videos, prices — table + form views, not fancy yet.
- Publish workflow: draft → validate (required fields, no orphan branch refs) → publish (locks the version).
- Seed script loads F01–F22 skeletons, C01–C20 competencies, the 10 Schwartz values + 4 higher-order groupings, and the 20 agent prompt placeholders as **data**, not code.

**Definition of Done:** An admin can create a question, publish an assessment version, and see it via API — with zero backend redeploy.

---

## Phase 2 — Auth, RBAC, Consent

**Objective:** Every subsequent endpoint can be protected correctly from day one.

- `users` collection: email OTP login (simplify SSO to "later"), JWT access + refresh tokens, role field (`candidate`, `assessor`, `mentor`, `admin`, `tenant_admin`).
- FastAPI dependency: `require_role([...])`, `require_tenant_scope`.
- `consent_records` collection: privacy consent + AI-scoring consent, versioned, timestamped, withdrawable.
- Frontend: login/register pages, auth state management (context/hook), protected route wrapper.
- Password/OTP hashing via `passlib`/`bcrypt`; rate-limit login attempts.

**Definition of Done:** Candidate can register, verify OTP, log in, and hit a protected `/candidates/me` endpoint; admin-only endpoints 403 for candidates.

---

## Phase 3 — Video-Led Orientation

**Objective:** Landing → explainer video → guidance video → knowledge check, fully DB-driven.

- `videos` collection (from Phase 1) rendered dynamically: YouTube embed or hosted MP4, both via `VideoSource` field.
- Frontend player tracks 25/50/75/90/100% milestones via `POST /v1/videos/{id}/progress`; unlock threshold read from video's own config (default 80%), not hardcoded in frontend.
- Post-video knowledge-check questions pulled from the same `questions` collection (reuse engine, don't build a second one).
- Landing page content (hero copy, journey steps) editable via a simple `site_content` collection rather than hardcoded JSX strings.

**Definition of Done:** Candidate cannot reach registration until required video completion is recorded server-side (not just a frontend flag).

---

## Phase 4 — Commerce: Products, Entitlements, Payments

**Objective:** Real purchase flow gates real feature access.

- `products` (MC-A, PV-A, COMBO-A, D250), `price_book` (tenant/country/campaign configurable), `payments`, `entitlements` collections.
- One real payment provider integrated (Stripe test mode is fine for MVP — still a real webhook flow, not a fake "mark as paid" button).
- Webhook handler is the **only** thing that activates an entitlement — UI redirect never grants access directly.
- Entitlement check middleware: gates which assessment modules and report tiers a candidate can reach.
- Frontend: product selection screen, checkout, entitlement-aware dashboard ("you have access to X, upgrade for Y").

**Definition of Done:** Paying via Stripe test card actually unlocks the corresponding assessment product server-side; an unpaid user is blocked from those routes even by direct API call.

---

## Phase 5 — Assessment Engine Core

**Objective:** The general-purpose runner that all 22 forms (F01–F22) reuse — this is the single most important MVP piece.

- `attempts`, `responses` collections. `POST /v1/assessments/{code}/attempts`, `GET /v1/attempts/{id}/next`, `PUT /v1/attempts/{id}/responses/{qId}` (idempotent autosave), `POST /v1/attempts/{id}/submit`.
- Branching engine: reads `branch_expression` stored per section, evaluates against prior responses, stores the resolved path per attempt (so it's reproducible later even if the definition changes).
- Frontend "Assessment Runner" component renders any question type generically from its `type` field — single choice, multi-select, matrix Likert, rank-N (drag + keyboard-accessible), scenario, free text — one component library, driven entirely by the question document's schema.
- Autosave on every change, visible "Saved" indicator, resume from any device.
- Question types QT01–QT09 built now; QT10–QT15 (video/case/AI role-play/visual mapping) deferred to Phases 6–8 since they need their own sub-engines.

**Definition of Done:** F01–F05 (registration, profile, motivation, Talent DNA, values) run end-to-end through this one generic engine with real autosave and resume.

---

## Phase 6 — Talent DNA & Schwartz Values Scoring

**Objective:** First real scoring logic, on top of the engine from Phase 5.

- Rank-4 scoring (4-3-2-1 mapping) computed deterministically in code (not AI) per §9.1.
- Schwartz centering algorithm implemented exactly per §9.4 (raw mean → MRAT → centered value → higher-order domains).
- `values_profiles` and `talent_dna_profiles` collections, versioned by scoring-profile version.
- Frontend: values wheel visualization + higher-order balance view (SVG, driven by real computed data, not a static image).

**Definition of Done:** Completing F04+F05 produces a real, reproducible values profile you can regenerate from stored responses + the scoring-profile version.

---

## Phase 7 — Consulting Capability Modules + Competency Model

**Objective:** F06–F14 domain assessments, mapped to C01–C20.

- Extend question bank with F06–F14 content (via admin authoring from Phase 1 — not migration scripts full of hardcoded questions).
- `competency_scores` collection: raw → normalized → confidence-weighted per the formula in Appendix C.
- Evidence-confidence weighting table (§10.2) implemented as configurable weights per evidence type, stored in `scoring_profiles`, not constants in code.
- Competency radar visualization (C01–C20) on candidate dashboard.

**Definition of Done:** A candidate's self-report vs. structured-knowledge answers produce visibly different confidence-weighted scores, matching the documented formula.

---

## Phase 8 — Video & Case Evidence Engine

**Objective:** The two "demonstrated evidence" evidence types — highest-weight inputs per §10.2.

- **Video:** MediaRecorder-based in-browser recording + upload fallback → object storage (S3-compatible/minio for MVP) → real speech-to-text transcription (a real API, e.g. Whisper) → deterministic delivery metrics (WPM, filler ratio, pauses) computed in code → LLM rubric scoring against the 7-dimension rubric (§11) with cited transcript segments.
- **Case workspace:** case brief + exhibits + timer + structured response tabs + file upload, all driven by a `cases` collection; 4 AI-usage modes (§12.1) enforced (e.g., "Closed AI" mode disables the in-app AI assist).
- Case/video scoring returns structured JSON (`dimension_score`, `evidence_quotes`, `rationale`, `confidence`) — schema-validated, retried once on failure, routed to human review on repeated failure or low confidence.

**Definition of Done:** Recording a video response produces a real transcript and a real AI-generated rubric score with cited evidence, stored and retrievable.

---

## Phase 9 — AI Agent Layer & Orchestration

**Objective:** Consolidate the scoring/report agents into one real, swappable pipeline (a trimmed version of A01–A20 — MVP doesn't need all 20, but the ones that touch scoring/reporting must be real).

- `ai/provider.py` — single interface (`complete(prompt, schema) -> validated_json`), swappable provider (Grok/OpenAI/Claude) via env var — **this is what "not real-time" simplifies**: called synchronously inside a background task (FastAPI `BackgroundTasks` or a lightweight Redis queue), not a live streaming session.
- Core agents built for MVP: Journey Orchestrator (A01), Talent DNA (A05, deterministic — no LLM needed), Values (A06, deterministic), Consulting Capability aggregator (A07), Case Assessment (A09), Communication (A10), Scoring/Calibration (A13), Recommendation (A14), Report Generator (A16). Remaining agents (A02–A04, A08, A11, A12, A15, A17–A20) are documented as post-MVP.
- Every agent call stores: prompt version, model, input evidence IDs, output JSON hash, confidence — into `ai_call_log` for auditability, even in MVP.
- Schema validation with one repair-retry, then fail-safe to a "pending human review" state — never silently invent a score.

**Definition of Done:** Submitting a case triggers a real agent call, produces a schema-valid structured score, and logs full provenance.

---

## Phase 10 — Composite Scoring & Role Matching

**Objective:** CCI / CPI / CRI / EC / DG and role-fit, computed per Appendix C's formulas — deterministic aggregation over Phase 6–9 outputs, not another AI call.

- `composite_score_sets` collection, versioned by `scoring_profile_version`.
- Role requirement vectors stored in `roles` collection (admin-editable); cosine/weighted-similarity role match computed in code.
- Client-readiness gate logic (`CCI ≥ threshold AND Communication ≥ threshold AND ... AND human_review = approved`) implemented exactly, thresholds pulled from `scoring_profiles` — not literals.

**Definition of Done:** Given a completed attempt, composite scores and top-3 role matches regenerate identically from stored data + version IDs (reproducibility test).

---

## Phase 11 — Reports (Summary + D250 Detailed)

**Objective:** The commercial payoff — two report tiers from one evidence snapshot.

- `reports` collection: locked evidence snapshot + generated content, versioned, immutable once generated.
- Summary of Findings: auto-generated immediately after any paid assessment completes (headline scores, 3–5 strengths, 3–5 development themes, next-step CTA).
- D250 Detailed Report: unlocked only via active `D250` entitlement — full score explanations, competency sections, roadmap, "why this finding" grounding.
- Report Generator Agent (A16) drafts narrative sections grounded strictly in the locked score/evidence JSON — no free-form claims.
- PDF export (WeasyPrint or similar) + dashboard view share the exact same score snapshot.
- "How this was calculated" expandable panel on every score, linking to contributing evidence.

**Definition of Done:** A candidate without D250 sees the Summary only; purchasing D250 immediately unlocks the full report from the *same* underlying attempt, no re-scoring needed.

---

## Phase 12 — Development Journey & Mentor Workspace

**Objective:** Turn scores into an actionable roadmap — the platform's retention loop.

- `learning_plans`, `milestones` collections; pathway selection (P1–P8) driven by composite scores + thresholds from `scoring_profiles`.
- Mentor workspace: view assigned candidates' evidence-linked gaps, assign tasks, track progress from evidence completion (not just "video watched").
- Reassessment scheduling (date-driven reminder, new attempt version linked to prior for progress comparison).

**Definition of Done:** A candidate with a scored profile gets a real, DB-generated 8/12-week plan with linked learning modules — not static copy.

---

## Phase 13 — Admin Panel (Full)

**Objective:** Everything from Phase 1's minimal CRUD, matured into the real governance layer — this is what makes "no hardcoding" actually true in production use.

- Assessment builder: sections, branching-rule editor with preview, question bank with tagging/filtering.
- Rubric manager, case library, video manager (upload/link + transcript + completion-rule config).
- Scoring profile editor: weights, thresholds, confidence rules — with a "what would this change" preview against sample data.
- Prompt/model registry: edit agent prompts, pick model, see version history, rollback.
- Pricing/entitlement admin: products, bundles, coupons, regional prices.
- Publishing workflow UI: draft → review → publish, with a diff view against the previous version.

**Definition of Done:** A non-developer can create a new question, attach it to a scoring rubric, and publish a new assessment version — with zero code changes or redeploy.

---

## Phase 14 — Human Review / Assessor Workflow

**Objective:** The human-in-the-loop gate required before any client-facing recommendation is exposed.

- Assessor dashboard: AI score summary, evidence viewer (transcript/video/case side-by-side with rubric), approve/override with mandatory reason.
- Every override writes an `AuditEvent` (old state, new state, reason, actor) — never silently overwritten.
- `client_facing` gate flips only after `ReviewDecision = approved`.

**Definition of Done:** A borderline/high-stakes score cannot reach "client-ready" status without a logged human approval.

---

## Phase 15 — UI/UX Standardization Pass

**Objective:** Turn the working prototype into something that reads as a real product, not a stitched-together demo — since you flagged this as very important, it gets its own dedicated phase rather than being an afterthought.

- Design system: one Tailwind config (colors, spacing, type scale) shared across every screen — no per-page ad hoc styling.
- Component library: buttons, cards, tables, modals, tabs, toasts, empty/error/loading states — built once, reused everywhere.
- Every screen gets all four states designed: loading, empty, error, success — not just the happy path.
- Responsive pass: desktop-first for assessment/case screens (per TDD §17.1), but dashboard/report/mobile-safe throughout.
- Accessibility baseline: keyboard nav, focus states, captions/transcripts already built in Phase 3, ARIA labels, no color-only meaning.

**Definition of Done:** Every screen in the app uses the same design system; no raw unstyled HTML anywhere.

---

## Phase 16 — Testing Pass

**Objective:** Enough automated coverage that a phase-16 regression doesn't silently break phase-5 functionality.

- Backend: unit tests for scoring formulas (rank conversion, Schwartz centering, composite score math — these must be exact), API contract tests for auth/entitlement gating.
- Integration tests: submit → score → report end-to-end; payment webhook → entitlement → unlock end-to-end.
- Frontend: form validation, protected-route redirects, key user flows (register → assess → pay → report) via Playwright/Cypress smoke tests.

**Definition of Done:** CI runs backend unit+integration tests and one frontend E2E smoke suite on every PR.

---

## Phase 17 — Deployment

**Objective:** A working, demoable, deployed instance.

- Dockerfiles for frontend/backend, docker-compose for local; single-environment deploy target for MVP (e.g., one cloud VM or a managed container service) rather than the TDD's full multi-environment Azure pipeline.
- Env-based config for all secrets (Mongo URI, Redis, JWT secret, AI provider key, Stripe keys).
- Basic logging + error tracking; health checks; automated DB index bootstrap on deploy.

**Definition of Done:** A stakeholder can register, pay (test mode), complete an assessment, and receive an AI-generated report on a live URL.

---

## What's intentionally deferred past MVP (flag if you disagree)

- Neo4j graph database (emulated in Mongo for MVP, as agreed above).
- Full 20-agent roster (11 shipped in Phase 9; remaining 9 — resume intelligence, video-learning tracking as a separate agent, stakeholder simulation, integrity/consistency checks, fairness/compliance agent, admin-intelligence agent — are real gaps, not nice-to-haves, but sequenced after the core loop works).
- Multi-tenant branding/employer view (data model supports it from Phase 0, UI doesn't ship it).
- Formal psychometric calibration (§25.2) — the TDD itself says this can't be done before real pilot data exists.
- Multi-provider payment adapters (Stripe only).
- SSO/Entra ID (email OTP only).

---

## Suggested execution order for you

Say **"START PHASE 0"** and I'll scaffold it (repo structure, docker-compose, config, base collections) with real running code, then wait for you to say **"START PHASE 1"** and so on — matching your original instruction doc's phase-by-phase approach. Each phase will hand you actual working code, not just more planning.
