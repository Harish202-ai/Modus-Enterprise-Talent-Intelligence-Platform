# METI-MC — Management Consulting Assessment & Development Platform

A reduced MVP: a candidate takes a consulting assessment, gets AI-scored results, a report, a personal AI explainer (voice or text) and a development roadmap; an admin edits all content without code changes.

**Build plan (authoritative):** [`METI_MVP_Build_Phases_v5.md`](METI_MVP_Build_Phases_v5.md) — maps 1:1 to the 10-stage journey (adds resume upload, Phase 5b AI Profile Understanding, 3-dimension AI scoring, coach mode, Phase 13 reassessment). Phases it marks *(unchanged)* take their detail from [v4](METI_MVP_Build_Phases_v4.md) (RAG support bot, motion layer), [v3](METI_MVP_Build_Phases_v3.md) (design system, voice explainer, roadmap) and [v2](METI_MVP_Build_Phases_v2.md) (collections, auth, the 7 forms). Anything in the original [`METI_MVP_Build_Phases.md`](METI_MVP_Build_Phases.md) or the TDD PDF that contradicts v4 is ignored; the TDD is still the reference for formulas (rank 4-3-2-1, Schwartz centering) and seed wording.

**Stack (locked):** Next.js 16 + Tailwind 4 + Framer Motion (from Phase 12) · FastAPI (async) · MongoDB Atlas (Motor) · Redis · config-swappable LLM + voice providers · Docker Compose

**Ground rules:** nothing business-related is hardcoded (questions, prices, prompts, report templates are MongoDB content edited by the admin) · every screen is wired to real APIs with loading/empty/error/success states · two roles only: **candidate** and **admin**.

---

## Build plan lineage (v2 → v5)

The plan evolved in four documents. **v5 is authoritative**; wherever a phase says *(unchanged)* its detail is inherited from the most recent earlier version that defines it. The original `METI_MVP_Build_Phases.md` (18 phases) and the TDD are reference only (formulas, seed wording).

| Version | What it contributed (still in force unless a later version changed it) |
|---|---|
| [v2](METI_MVP_Build_Phases_v2.md) — the trim | 2 roles (candidate + admin) · email + password · one consent checkbox · 7 forms (was 22) · 5 question types · simple “if answer = X, skip section” · 6–8 competencies (was 20) · 2 composite scores (Readiness, Evidence Confidence) · 1 scoring service + 1 report generator + 1 explainer (was 11 agents) · flat prices + Stripe test mode + webhook entitlements · ground rules: nothing hardcoded, all four UI states, few calm screens |
| [v3](METI_MVP_Build_Phases_v3.md) — design + voice | Locked **design system** (60/30/10 palette `#F4F3EF` / `#1C2321` / `#C5A880` + `#FFFFFF`; Plus Jakarta Sans headings, Satoshi body) from Phase 0 · AI Results Explainer becomes **voice + text** via a swappable `voice_provider` · new **Development Roadmap** module (6–8 milestones, unlocked by the Detailed Report) |
| [v4](METI_MVP_Build_Phases_v4.md) — support + motion | **Site-wide RAG support chatbot** (public `support_kb` only — hard boundary from candidate data) · **Motion & interactivity layer** (Framer Motion transitions, micro-interactions, animated score reveals, looping ambient video, `prefers-reduced-motion`) · where the voice API key goes |
| [v5](METI_MVP_Build_Phases_v5.md) — the 10-stage journey | **Resume/CV upload** + **Phase 5b AI Profile Understanding** (self-reported evidence, confirm/edit) · communication as **written or video**, case as **written or document** · AI scoring output split into **Reasoning / Knowledge / Communication** with cited evidence · explainer **“Why” mode + “Coach” mode** (coach grounded in the roadmap) · restored **Phase 13 Reassessment & Progress** · Test & Deploy becomes Phase 14 |

### The 10-stage candidate journey (v5) → where it's built

```
1 User Profile ─▶ 2 AI Profile Understanding ─▶ 3 Adaptive Assessment ─▶ 4 AI Evidence Analysis ─▶ 5 AI Competency Profile
   (Phase 5 ✅)       (Phase 5b ✅)                (Phase 5 ✅)              (Phase 7 ✅)               (Phase 8 ✅)
                                                                                                          │
10 Reassessment & Progress ◀─ 9 AI Report + Dashboard ◀─ 8 Personalised Roadmap ◀─ 7 AI Development Coach ◀─ 6 AI "Why" Explanation
   (Phase 13 ✅)                (Phase 8 ✅)              (Phase 9 ✅)              (Phase 8+9 ✅)            (Phase 8 ✅)
```

Supporting phases around the journey: 0 Foundation · 1 Content & Admin core · 2 Auth · 3 Landing · 4 Commerce · 6 Deterministic scoring (Talent DNA + Values + Capability) ✅ · 10 Support chatbot ✅ · 11 Admin panel ✅ · 12 UI/UX + motion ✅ · 14 Test & deploy ✅.

---

## Phase status

| # | Phase (v5) | Journey stage | Status |
|---|---|---|---|
| 0 | Foundation (+ locked design system tokens) | — | ✅ Built |
| 1 | Content Model & Admin Core | — | ✅ Built |
| 2 | Auth & Access — 2 roles, email + password, one consent checkbox | — | ✅ Built |
| 3 | Landing & Orientation — `site_content`, explainer video, "mark as watched" | — | ✅ Built |
| 4 | Commerce — flat prices, Stripe test mode, entitlements | — | ✅ Built — needs Stripe test keys to verify |
| 5 | Assessment Engine — 7 forms, question types, skip logic, autosave/resume, **resume + answer uploads** | 1 User Profile · 3 Adaptive Assessment | ✅ Built — awaiting your verification |
| 5b | **AI Profile Understanding** — resume → structured, self-reported claims → confirm/edit | 2 AI Profile Understanding | ✅ Built — verified live with Groq (openai/gpt-oss-120b) |
| 6 | Deterministic Scoring — Talent DNA rank scoring, Schwartz MRAT centering, values wheel, capability key scoring | — | ✅ Built — awaiting your verification |
| 7 | AI Scoring Service — **Reasoning / Knowledge / Communication** per response, cited evidence | 4 AI Evidence Analysis | ✅ Built — verify with an AI key (falls back to `pending` without one) |
| 8 | Composite Score, Reports & AI Explainer — **"Why" + "Coach" modes**, voice + text | 5 Competency Profile · 6 "Why" · 7 Coach · 9 Report | ✅ Built — Explainer needs an AI key; voice = browser Web Speech |
| 9 | Development Roadmap (data source for Coach mode) | 8 Personalised Roadmap | ✅ Built |
| 10 | Site-Wide RAG Support Chatbot | — | ✅ Built — works without an AI key (extractive); richer with one |
| 11 | Admin Panel — score review/override + support KB editing | — | ✅ Built |
| 12 | UI/UX Pass + Motion & Interactivity Layer | — | ✅ Built — CSS/Web-API motion (Framer Motion optional) |
| 13 | **Reassessment & Progress** — retake, before/after per competency, roadmap regenerates | 10 Reassessment & Progress | ✅ Built |
| 14 | Test & Deploy | — | ✅ Built — end-to-end smoke test; Docker Compose from Phase 0 |

### What the v4 reduction changed in Phases 0–2

| Area | Before (original plan) | Now (v4) |
|---|---|---|
| Assessments | 22 forms (F01–F22) | **7 forms**: profile, motivation, talent_dna, values, capability, written_communication, case_study |
| Question types | 15 | **5**: single_choice, multi_select, likert, rank, free_text |
| Branching | per-question jumps + section branch rules | **"if answer = X, skip section"** (`skip_if` on a section) |
| Competencies | 20 (C01–C20) | **8** grouped competencies (each tagged with the TDD codes it merges) |
| AI prompts | 20 agents (A01–A20) | **4**: scoring, report_generator, results_explainer, support_chatbot |
| Pricing | separate `price_book` (regions, dates, tax) | **one flat `price` + `currency` on each product** |
| Roles | candidate, assessor, mentor, admin, tenant_admin | **candidate, admin** |
| Sign-in | email one-time code (OTP) + SMTP | **email + password** |
| Consent | versioned policies + consent records | **one checkbox at registration, timestamped** (`consent_accepted_at`) |
| Removed code | — | OTP + email service, consent policies/records API, `price_book`, `assessment_definitions`, `prompt_versions` |
| Added | — | design-system tokens (palette + fonts) applied to every screen |

---

## Design system (locked, plan v3)

| Token (Tailwind) | Hex | Use |
|---|---|---|
| `bg-surface-base` (60%) | `#F4F3EF` alabaster | page backgrounds |
| `text-primary` / `border-primary/…` (30%) | `#1C2321` charcoal | text, headings, borders, icons |
| `bg-accent-cta` (10%) | `#C5A880` gold | primary buttons, active states, progress, score highlights — sparingly |
| `bg-surface-card` | `#FFFFFF` | cards, modals, form fields |

Headings: **Plus Jakarta Sans** 600/700 (loaded via `next/font`). Body: **Satoshi** → General Sans → system sans. Satoshi isn't on Google Fonts: to use it everywhere, add its `.woff2` files to `frontend/public/fonts/` with an `@font-face` in `globals.css`; until then the fallback stack is used. Tokens live in `frontend/src/app/globals.css`; no screen uses ad-hoc colours (semantic red/green only for error/success messages).

---

## Project structure

`✅` built · `⏳ Phase N` planned (folder/file it will live in). Every business value — questions, prices, prompts, page copy — is **data** (MongoDB, seeded from `backend/seed/*.json`), never code.

```
METI/
├── README.md                              this file
├── METI_MVP_Build_Phases_v5.md            ★ authoritative plan (10-stage journey)
├── METI_MVP_Build_Phases_v4.md / _v3 / _v2   earlier plans — v5 inherits their "(unchanged)" phases
├── METI_MVP_Build_Phases.md               original 18-phase plan (reference only)
├── METI_Management_Consulting_Assessment_TDD_v1.1 (2) (3).pdf   requirements TDD (formulas, wording)
├── .gitignore                             secrets (.env), venv, node_modules, uploads
├── .venv/                                 Python virtualenv (local runs + tests)
│
├── infra/
│   ├── docker-compose.yml                 ✅ redis + backend + frontend; volumes redis_data, uploads_data (MongoDB = Atlas)
│   ├── .env / .env.example                optional compose overrides (REDIS_URI, NEXT_PUBLIC_API_URL) — never the Mongo URI
│
├── backend/                               FastAPI (Python 3.10, async)
│   ├── Dockerfile · requirements.txt · pytest.ini · .dockerignore
│   ├── .env (gitignored) · .env.example   every setting: Atlas URI, JWT, Stripe, AI provider, uploads, voice
│   ├── app/
│   │   ├── main.py                        ✅ app: CORS, JSON request logging (X-Request-ID), error handlers, routers
│   │   ├── config.py                      ✅ Settings from env; refuses weak JWT secret outside local/dev
│   │   ├── database.py                    ✅ Motor client, collection accessors, INDEXES registry, ensure_indexes()
│   │   ├── cache.py                       ✅ Redis client (rate limits; later queues)
│   │   ├── logging_config.py              ✅ structured JSON logs
│   │   ├── security.py                    ✅ JWT access/refresh tokens, bcrypt password hashing, IP hashing
│   │   ├── payments.py                    ✅ Stripe gateway — the only module that talks to Stripe (Phase 4)
│   │   ├── ai/
│   │   │   ├── provider.py                ✅ the one LLM abstraction: anthropic | openai-compatible (Groq/OpenAI/Ollama);
│   │   │   │                                 pydantic-validated JSON, one repair retry, then needs_review (Phase 5b)
│   │   │   ├── scoring.py                 (unused — the AI scoring pipeline lives in services/ai_scoring.py; provider.py is the only LLM entry)
│   │   │   ├── explainer.py               ✅ Phase 8  "Why" + "Coach" modes, grounded in the candidate's locked data (graceful without a key)
│   │   │   ├── voice_provider.py          ✅ Phase 8  VOICE_PROVIDER capability; default "webspeech" = browser Web Speech (client-side, zero-cost)
│   │   │   ├── content_gen.py              ✅ post-MVP  draft any content type's data from an admin instruction (AI-assisted authoring)
│   │   │   └── (embeddings)               Phase 10 uses keyword retrieval (support_kb.py); no embeddings dependency in the MVP
│   │   ├── content/
│   │   │   ├── registry.py                ✅ the 11 authorable content types + field specs (drive validation AND admin forms)
│   │   │   └── validation.py              ✅ publish checks: required fields, types, per-type rules, no orphan references
│   │   ├── models/                        ✅ common (tenant_id base) · tenant · audit · content (versions) · user
│   │   ├── api/                           HTTP routes (all under /v1 except /health)
│   │   │   ├── deps.py                    ✅ get_current_user · require_role([...]) · require_tenant_scope · current_tenant
│   │   │   ├── health.py                  ✅ Phase 0  GET /health
│   │   │   ├── admin_content.py           ✅ Phase 1  /admin/content/* — draft → validate → publish, versions (admin)
│   │   │   ├── auth.py                    ✅ Phase 2  register · login · refresh · logout · me
│   │   │   ├── candidates.py              ✅ Phase 2/3 /candidates/me (+ /orientation "mark as watched")
│   │   │   ├── site.py                    ✅ Phase 3  /site/{key} public page copy + pinned explainer video
│   │   │   ├── commerce.py                ✅ Phase 4  /products · /payments/checkout|confirm|webhook · /entitlements/me
│   │   │   ├── assessments.py             ✅ Phase 5  /assessments/{code} (sanitised for candidates, full for admin preview)
│   │   │   ├── attempts.py                ✅ Phase 5  /me/assessments · start/resume · autosave · file answers · submit
│   │   │   ├── profile.py                 ✅ Phase 5b /me/resume (upload, review, confirm, retry) · /files/{id} download
│   │   │   ├── scores.py                  ✅ Phase 6–7  GET /me/scores (deterministic + AI areas) · POST /me/scores/{key}/rescore (re-run AI scoring)
│   │   │   ├── reports.py                 ✅ Phase 8  GET summary / detailed report · POST explainer chat · GET voice capability
│   │   │   ├── roadmap.py                 ✅ Phase 9  GET/regenerate roadmap (gated by the upgrade)
│   │   │   ├── support.py                 ✅ Phase 10 POST /support/chat (public, support_kb only)
│   │   │   ├── admin_scores.py            ✅ Phase 11 review queue + marked list · override (reason required) · approve
│   │   │   ├── admin_users.py             ✅ post-MVP  admin: students ranked by Readiness · one student's complete report
│   │   │   ├── interview.py               ✅ post-MVP  video interview questions/config + recording upload with proctoring metadata
│   │   │   └── progress.py                ✅ Phase 13 before/after comparison of the two latest attempts
│   │   └── services/                      business logic (routes stay thin)
│   │       ├── content.py                 ✅ versioning: create · update draft · new version · publish (immutable) · discard
│   │       ├── tenants.py · audit.py      ✅ tenant bootstrap · append-only audit events
│   │       ├── auth.py · rate_limit.py    ✅ sessions with refresh rotation + reuse detection · Redis rate limits
│   │       ├── orientation.py             ✅ explainer "mark as watched"
│   │       ├── commerce.py                ✅ catalogue · checkout · idempotent fulfilment · 402 access gate
│   │       ├── attempts.py                ✅ the assessment engine (pinned versions, skip logic, answer validation)
│   │       ├── files.py                   ✅ uploads: magic-byte checks, size caps, sha256, volume storage
│   │       ├── profile_ai.py              ✅ Phase 5b resume → text → AI → self-reported evidence_claims
│   │       ├── scoring_rules.py           ✅ Phase 6  rank 4-3-2-1, Schwartz MRAT centering, capability key scoring (pure maths + persistence)
│   │       ├── ai_scoring.py              ✅ Phase 7  one AI call per free-text response → reasoning / knowledge / communication + cited evidence; PDF/DOCX/PPTX extraction; video → needs_transcript (Phase 8); pending / needs_review fallbacks + rescore
│   │       ├── composite.py               ✅ Phase 8  Readiness + Evidence Confidence (deterministic, renormalised over what's present)
│   │       ├── reports.py · roadmap.py    ✅ Phase 8–9  deterministic report assembly · roadmap generation
│   │       ├── support_kb.py              ✅ Phase 10 keyword retrieve over public support_kb + grounded/extractive answer
│   │       ├── reassessment.py            ✅ Phase 13 before/after metrics per area
│   │       ├── interview.py               ✅ post-MVP  interview questions (gated), save recording + proctoring, admin/candidate reads
│   │       ├── admin_users.py             ✅ post-MVP  candidate list (Readiness-ranked) + full per-student report aggregation
│   │       └── admin_scores.py            ✅ Phase 11 score review/override service
│   ├── seed/                              ✅ seed DATA (JSON), loaded by scripts/seed_content.py in dependency order
│   │   ├── competencies.json              8 grouped competencies (tagged with the TDD C01–C20 they merge)
│   │   ├── values_taxonomy.json           10 Schwartz basic values + 4 higher-order views
│   │   ├── questions.json                 63 questions for the 7 forms (CV upload, ranking, portrait, capability, memo, case)
│   │   ├── sections.json                  13 sections (incl. the skip rule on programme experience)
│   │   ├── assessments.json               the 7 forms → their sections
│   │   ├── prompts.json                   3 AI prompt placeholders (report, explainer, support bot) — drafts
│   │   ├── prompts_live.json              published prompts: profile_parser (Phase 5b), scoring (Phase 7)
│   │   ├── videos.json · site_content.json   explainer video entry (draft until URL) · landing page copy
│   │   ├── products.json                  4 products with flat prices
│   │   ├── rubrics.json                   ✅ Phase 7  memo + case rubrics (reasoning / knowledge / communication anchors), pinned by WC-01 / CASE-01 / CASE-02
│   │   └── support_kb.json                ✅ Phase 10 public FAQ / help content (the bot's whole knowledge base)
│   ├── scripts/                           ✅ bootstrap_indexes · seed_tenant · seed_content · create_admin · grant_product
│   │                                         · reset_content · drop_database
│   └── tests/                             ✅ pytest on Atlas db meti_test — conftest (fixtures), fixture_files (real DOCX/PDF/MP4),
│                                             test_phase0 … test_phase14 + examflow/admin2/interview (~97 tests)
│
└── frontend/                              Next.js 16 (App Router) + Tailwind 4 · Framer Motion arrives in Phase 12
    ├── Dockerfile · package.json · next.config.ts · tsconfig.json · eslint.config.mjs · postcss.config.mjs
    ├── .env.local / .env.example          NEXT_PUBLIC_API_URL
    └── src/
        ├── app/                           one folder per route
        │   ├── layout.tsx · globals.css   ✅ AuthProvider, fonts, design-system tokens (60/30/10)
        │   ├── page.tsx · LandingView.tsx ✅ Phase 3  landing (all copy from site_content) + explainer video
        │   ├── status/                    ✅ system status (API / Mongo / Redis)
        │   ├── register/ · login/         ✅ Phase 2  email + password, consent checkbox
        │   ├── account/                   ✅ profile, purchases, orientation, consent
        │   ├── pricing/ · checkout/success/   ✅ Phase 4  products, Stripe checkout, payment confirmation
        │   ├── assessments/               ✅ Phase 5  "Your assessments" (start / continue / done)
        │   │   └── [code]/Runner.tsx      ✅ the one runner for all 7 forms (autosave, skip logic, review & submit)
        │   ├── profile/                   ✅ Phase 5b "Here's what we found in your CV" — confirm or edit
        │   ├── admin/content/             ✅ Phase 1  content editor (forms generated from backend field specs)
        │   ├── results/                   ✅ Phase 6–7  values wheel, talent DNA bars, competency radar, AI evidence scores
        │   ├── report/                    ✅ Phase 8  Summary of Findings, gauges (count-up), Why explainer
        │   ├── admin/                     ✅ post-MVP  friendly Admin home (cards) at /admin
        │   ├── admin/scores/              ✅ Phase 11 AI marks: needs-review + already-marked, with override
        │   ├── admin/users/ · users/[id]/ ✅ post-MVP  students ranked by performance · complete student report (scores, CV, video, marks)
        │   ├── interview/                 ✅ post-MVP  proctored AI video interview (spoken Qs, webcam, MediaPipe attention, auto-submit)
        │   ├── roadmap/                   ✅ Phase 9  milestone timeline + Coach explainer
        │   ├── progress/                  ✅ Phase 13  before/after per competency, retake link
        │   └── (support_kb editing uses the existing admin/content editor — support_kb is a content type)
        ├── components/
        │   ├── SiteHeader · RequireAuth · AuthForm · ExplainerVideo   ✅
        │   ├── engine/QuestionField.tsx   ✅ all question types incl. ranking (drag / buttons / Alt+arrows) and file uploads
        │   ├── charts/                    ✅ Phase 6  ValuesWheel · TalentDnaBars · CapabilityRadar · ✅ Phase 7 EvidenceScores (pure SVG/bars; animated in Phase 12)
        │   ├── chat/                      ✅ Phase 8/10 Explainer (voice + text, Web Speech) · SupportBubble (floating, all pages)
        │   └── motion/                    ✅ Phase 12  CountUp + CSS reveal/animate utilities (prefers-reduced-motion aware)
        └── lib/                           ✅ api (fetch + token refresh + uploads) · auth · content · site · orientation
                                              · commerce · engine · profile · scores
```

### Runtime architecture

```
Browser (Next.js, :3000) ──HTTPS/JSON──▶ FastAPI (:8000) ──▶ MongoDB Atlas (db METI)   content versions, users, attempts, claims, scores…
        ▲  access token in memory,              │         ──▶ Redis (container)        rate limits (later: queues)
        │  refresh token = httpOnly cookie      │         ──▶ uploads volume           CVs, case documents, videos
        │                                       ├────────▶ Stripe (test mode)         checkout + signed webhooks
        └── Stripe-hosted checkout ◀────────────┘         ──▶ LLM provider             Groq (OpenAI-compatible) today — swappable
```

---

## Setup & running

Prerequisites: Docker Desktop, Python 3.10+ (venv at `.venv`), Node 22.

```cmd
cd /d D:\METI
py -3.10 -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
copy backend\.env.example backend\.env        :: then put your Atlas MONGO_URI and a random JWT_SECRET in it
copy frontend\.env.example frontend\.env.local
cd frontend && npm install
```

Run everything (from `D:\METI\infra`):

```cmd
docker compose up -d --build
docker compose exec backend python -m scripts.seed_tenant
docker compose exec backend python -m scripts.seed_content
docker compose exec backend python -m scripts.create_admin --email you@company.com --name "Your Name"
```

| URL | What |
|---|---|
| http://localhost:3000 | Landing page (explainer video, narrative, journey, sign-up) |
| http://localhost:3000/register · /login · /account | Candidate sign-up, sign-in, account |
| http://localhost:3000/admin/content | Content admin (admin role) |
| http://localhost:3000/pricing | Products + prices, Stripe checkout |
| http://localhost:3000/assessments | Candidate's assessments (start / continue / done) → runner at /assessments/{code} |
| http://localhost:3000/status | System status (API / Mongo / Redis) |
| http://localhost:8000/health · /docs | Backend health · Swagger |

Stop: `docker compose down`. Backend logs: `docker compose logs -f backend`.

---

## Configuration (`backend/.env`, gitignored)

| Variable | Purpose |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string — **required**; only ever in `backend/.env`, never in an `.env.example` |
| `MONGO_DB` | `METI` (upper case — Atlas still reserves that name from an old database, so lower-case `meti` is rejected) |
| `REDIS_URI` | Redis (Compose points the backend at its redis container) |
| `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` | runtime basics |
| `DEFAULT_TENANT_SLUG` / `_NAME` | single tenant the MVP runs as (`tenant_id` is on every document) |
| `JWT_SECRET`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_DAYS` | tokens; outside local/dev the app refuses to start with a weak secret |
| `AUTH_RATE_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_PER_EMAIL`, `AUTH_RATE_LIMIT_PER_IP` | sign-in attempt limits (429 + `Retry-After`) |
| `AI_PROVIDER` (`anthropic` \| `openai`), `AI_MODEL`, `AI_API_KEY`, `AI_BASE_URL` | the LLM behind every AI feature (from Phase 5b). `openai` = OpenAI or any OpenAI-compatible server (Ollama, Groq, LM Studio …) via `AI_BASE_URL`. Unset → AI features degrade gracefully (e.g. the candidate fills in their CV profile by hand) |
| `UPLOADS_DIR`, `UPLOAD_MAX_MB_DOCUMENT` (10), `UPLOAD_MAX_MB_VIDEO` (200) | where uploads are stored (Docker: `/data/uploads` volume) and size caps |
| `VOICE_PROVIDER`, `VOICE_API_KEY`, `VOICE_API_REGION` | voice STT/TTS (Phase 8) — add when you have the key; `webspeech` needs none |
| `STRIPE_SECRET_KEY` (`sk_test_…`), `STRIPE_PUBLISHABLE_KEY` (`pk_test_…`) | Stripe **test mode** (Phase 4). Without the secret key, checkout answers 503 “Payments aren't configured yet” |
| `STRIPE_WEBHOOK_SECRET` (`whsec_…`) | optional locally — needed only if Stripe webhooks can reach the backend (`stripe listen --forward-to localhost:8000/v1/payments/webhook`, or a deployed URL) |
| `FRONTEND_URL` | where Stripe Checkout returns the browser (default http://localhost:3000) |
| `NEXT_PUBLIC_API_URL` (frontend) | browser-visible backend URL |

---

## API (so far)

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/health` | public | 200 when Mongo + Redis respond |
| GET | `/v1/site/{key}` | public | published `site_content` page (e.g. `landing`) with its explainer video at the pinned version (YouTube → privacy-enhanced embed URL). Drafts are never served |
| POST | `/v1/auth/register` | public | `{email, full_name, password, consent: true, orientation?: {video_key, video_version}}` → candidate account, signed in (201). Password: 8+ chars with a letter and a number. `orientation` = the video watched before signing up (must be a published version) |
| POST | `/v1/auth/login` | public | `{email, password}` → access token + httpOnly refresh cookie. Wrong email or password → the same 401 |
| POST | `/v1/auth/refresh` | cookie | rotates the refresh token; replaying an old one revokes all the user's sessions |
| POST | `/v1/auth/logout` | cookie | ends the session (204) |
| GET | `/v1/auth/me` | signed in | current user |
| GET/PUT | `/v1/candidates/me` | candidate | profile; PUT `{full_name}` |
| POST | `/v1/candidates/me/orientation` | candidate | `{video_key, video_version}` — "mark as watched" |
| GET | `/v1/assessments/{code}` | candidate with a paid entitlement (admins preview) | latest published assessment with its sections + questions at their pinned versions. **402** if not bought |
| GET | `/v1/me/assessments` | candidate | unlocked assessments with status (not_started / in_progress / submitted) and progress |
| POST | `/v1/assessments/{code}/attempts` | candidate (owns it) | start, or resume the open attempt — pinned to the published version it started on; returns the **sanitised** definition + saved answers |
| GET | `/v1/attempts/{id}` | owner | attempt + definition + answers |
| PUT | `/v1/attempts/{id}/answers` | owner | autosave `{answers: {question_key: value \| null}, current_section_key?}` — merges; rejects unknown questions / wrong kinds of value (422); 409 once submitted |
| POST | `/v1/attempts/{id}/files?question_key=…` | owner | multipart upload as a question's answer (resume, communication video, case document); type checked by content, size-capped; a resume starts AI Profile Understanding |
| POST | `/v1/me/resume` | candidate | upload / replace the CV (PDF/DOCX ≤ 5 MB) → claim `processing`, parsed in the background |
| GET | `/v1/me/resume` | candidate | latest claim: `processing` → `parsed` \| `needs_review` \| `unreadable` \| `unavailable` → `confirmed` |
| PUT | `/v1/me/resume/{claim_id}` | candidate | confirm / correct the profile (the confirmed version is what later phases use) |
| POST | `/v1/me/resume/{claim_id}/retry` | candidate | parse again (after `unavailable` / `needs_review`) |
| GET | `/v1/files/{id}` | owner or admin | download |
| POST | `/v1/attempts/{id}/submit` | owner | `{skipped?: [question_key]}` — every non-skipped-section question must be answered or explicitly skipped (422 lists the rest), then locks it; deterministically scores Talent DNA / Values / Capability and kicks off AI scoring for the memo/case |
| GET | `/v1/me/scores` | candidate | all scores by area — deterministic: `talent_dna` (9 dimensions), `values` (10 basic values + 4 higher-order, MRAT-centred), `capability` (weighted % per competency); AI (Phase 7): `written_communication`, `case_study` (per-response Reasoning / Knowledge / Communication 0-100 + cited evidence + overall confidence). Each area is `{status: not_submitted}` until done; deterministic areas compute on read, AI areas show `pending` until scored |
| POST | `/v1/me/scores/{assessment_key}/rescore` | candidate (owner) | re-run AI scoring for the latest submitted `written_communication` / `case_study` attempt (e.g. after a provider outage left it `pending`); 404 for a non-AI-scored assessment |
| GET | `/v1/me/report` | candidate | Summary of Findings — Readiness + Evidence Confidence composites, strengths and development themes, from locked scores (works with no AI key) |
| GET | `/v1/me/report/detailed` | candidate (owns upgrade) | full report: composites + every competency, the values profile and the graded responses; **402** without the report_upgrade |
| POST | `/v1/me/explainer` | candidate | `{question, mode: why\|coach}` → an answer grounded strictly in the candidate's own results (and roadmap in coach mode); honest "not available" without an AI key |
| GET | `/v1/me/voice` | candidate | voice capability for the Explainer (default `webspeech` = browser Web Speech, client-side) |
| GET | `/v1/me/roadmap` · POST `/v1/me/roadmap/regenerate` | candidate (owns upgrade) | the development roadmap (generated on first read from the gaps); **402** without the upgrade |
| GET | `/v1/me/progress` · `/v1/me/progress/{assessment_key}` | candidate | which assessments were submitted; before/after of the two most recent attempts per competency |
| POST | `/v1/support/chat` | **public** | general platform question → grounded answer from public `support_kb` only (never candidate data) |
| GET | `/v1/me/interview` | candidate (owns the assessment) | the timed interview questions + proctoring config (max warnings); **402** without access |
| POST | `/v1/me/interview` | candidate | multipart upload of the recording + proctoring metadata (`warnings`, `auto_submitted`, `answered`, `duration_seconds`) |
| GET | `/v1/me/interview/latest` | candidate | the candidate's most recent interview record |
| GET | `/v1/admin/scores/review` | admin | AI-scored answers — those needing review and those already marked (each row flagged `needs_review`) |
| POST | `/v1/admin/scores/{attempt_id}/responses/{question_key}/override` | admin | replace a response's dimension scores (reason required, audited) |
| POST | `/v1/admin/scores/{attempt_id}/approve` | admin | mark an attempt's AI scores reviewed |
| GET | `/v1/admin/candidates` | admin | students ranked by overall Readiness, with exams-done count |
| GET | `/v1/admin/candidates/{user_id}` | admin | one student's complete report — scores, report, AI marks, CV, uploads, video interviews, attempts |
| POST | `/v1/admin/content/{type}/generate` | admin | draft a content item's `data` with AI from an instruction (admin edits before saving); 503 without an AI key |
| POST | `/v1/admin/content/{type}/import` | admin | bulk-create items from an uploaded JSON file (list of `{key, data}`) |
| GET | `/v1/products` | public | published products with flat prices, sorted for the pricing page |
| POST | `/v1/payments/checkout` | candidate | `{product_key}` → Stripe Checkout URL (409 if already owned / prerequisite missing) |
| POST | `/v1/payments/confirm` | candidate | `{session_id}` → the backend verifies the session **with Stripe** and fulfils it if paid (success page) |
| POST | `/v1/payments/webhook` | Stripe (signed) | `checkout.session.completed` / `async_payment_succeeded` → fulfil; `expired` / `failed` → mark. Bad signature → 400 |
| GET | `/v1/entitlements/me` | candidate | owned products, unlocked assessment keys, payment history |
| GET | `/v1/admin/content/types` | admin | the 12 content types and their fields (drives the admin forms) |
| GET/POST | `/v1/admin/content/{type}` | admin | list (one row per key) / create draft v1 |
| GET | `/v1/admin/content/{type}/{key}` · `/current` · `/versions/{n}` | admin | history / live version / one version |
| PUT · POST · DELETE | `/v1/admin/content/{type}/{key}/draft` | admin | save draft · start new version from the live one · discard draft |
| POST | `/v1/admin/content/{type}/{key}/validate` · `/publish` | admin | check · lock the draft (422 with field errors if invalid) |

No token → 401. Candidate on an admin route → 403 `Requires role: admin`.

## Data model

Every document carries `tenant_id`; ids are UUID hex in `_id`; times are UTC.

| Collection | Notes |
|---|---|
| `tenants`, `audit_events` | Phase 0 |
| `users` | `{email, full_name, role: candidate\|admin, password_hash (bcrypt), status, consent_accepted_at, orientation: {video_key, video_version, watched_at}, last_login_at}` |
| `auth_sessions` | one per refresh token (jti); TTL-expired |
| `payments` | `{user_id, product_key, product_version, amount, amount_minor, currency, status: pending\|paid\|expired\|failed\|amount_mismatch, stripe_session_id}` |
| `attempts` | `{user_id, assessment_key, assessment_version (pinned), status: in_progress\|submitted, answers, current_section_key, skipped_sections, started_at, submitted_at}` — one open attempt per candidate per assessment (partial unique index) |
| `files` | `{user_id, kind: pdf\|docx\|pptx\|mp4\|mov\|webm, filename, size, sha256, purpose}` — bytes on the uploads volume |
| `evidence_claims` | Phase 5b: `{source: resume, evidence_tier: self_reported, file_id, status, parsed, confirmed, model, prompt_version, edited_by_candidate}` |
| `roadmaps` | Phase 9: one per candidate (unique on `tenant_id`+`user_id`) `{readiness, milestones:[{week, title, focus, actions, resource}], reassessment_schedule, generated_at}` — regenerated on reassessment |
| `scores` | Phases 6–7: one per attempt (unique on `tenant_id`+`attempt_id`). Deterministic (`method: deterministic`, area `talent_dna\|values\|capability`, `rules_version`, `result`) — recomputed idempotently; bump `rules_version` in `scoring_rules.py` to force a recompute. AI (`method: ai`, area `written_communication\|case_study`, `model`, `prompt_version`, `result: {status, responses:[{question_key, status, scores:{reasoning/knowledge/communication + evidence, overall_confidence}, rubric_key, rubric_version}]}`) — produced on submit or by rescore |
| `entitlements` | one per user per product (unique) `{product_key, product_version, source: stripe\|bundle:<key>, payment_id, granted_at}` |
| `interviews` | Post-MVP: one per video-interview recording `{user_id, file_id, file, warnings, auto_submitted, answered, questions_total, duration_seconds, created_at}` — the recording is a normal owner-or-admin file |
| `assessments`, `sections`, `questions`, `rubrics`, `competencies`, `values_taxonomy`, `videos`, `products`, `prompts`, `site_content`, `interview_questions`, `support_kb`, `report_templates` | versioned content: `{key, version, status: draft\|published, data, ref_versions, …}`; published versions never change; one open draft per key; every reference must be published and is pinned at publish |

**Seed (`seed_content`, idempotent):** 8 competencies and the 10 Schwartz values + 4 higher-order views (**published**); the 2 rubrics (memo, case) with reasoning/knowledge/communication anchors (**published**, Phase 7); the 7 assessment skeletons and 3 AI prompt placeholders (**drafts** — they get sections / real prompts in Phases 8, 10); the 63 questions / 13 sections behind the 7 forms incl. the CV upload, video option (communication) and document option (case), with WC-01 / CASE-01 / CASE-02 pinning their rubric (**published**); the live `profile_parser` (Phase 5b) and `scoring` (Phase 7) AI prompts (**published**); `seed_content` keeps content it owns up to date — new versions when an item or what it references changes — and never touches anything an admin edited); the `landing` page copy (**published**) and the `explainer` video entry (**draft** until you paste the real video URL); 4 products (**published**): Management Consulting Assessment USD 25, Personality & Values USD 25, Bundle USD 40 (starter price), Detailed Report upgrade USD 250.

## Scripts (`docker compose exec backend python -m scripts.<name>`, or from `backend/` with the venv)

| Script | Does |
|---|---|
| `seed_tenant` | create the default tenant (idempotent) |
| `seed_content` | load `backend/seed/*.json` (skips keys that exist) |
| `grant_product --email … --product bundle` | give a candidate a product without payment (sponsored / complimentary; audited) — also handy for testing before Stripe keys are set |
| `create_admin --email … --name …` | create an admin, or promote an existing user to admin; asks for the password |
| `reset_content` | shows then drops all content collections + retired pre-v4 collections, after you type `RESET` (keeps tenants, users, audit) |
| `drop_database <NAME>` | shows then drops a whole database, after you type its name |
| `bootstrap_indexes` | create all collections + indexes |

## Tests

```cmd
cd /d D:\METI\backend
..\.venv\Scripts\python.exe -m pytest -v
```

~97 tests (Stripe and the LLM are faked in tests; webhooks are really signed; uploads use real DOCX/PDF/MP4 bytes; the full run takes ~25 min because each test re-seeds over the network — the pure-maths and parsing tests are the fast exception, needing no network). They use Atlas + Redis, in the separate `meti_test` database (collections emptied before/after each test — the app's `METI` data is never touched).

---

## Verification checklist — Phases 0–2 (v4)

**One-time migration of your Atlas `METI` database to the v4 model** (it still holds the old 22 forms, 20 competencies, 20 prompts, consent records and code-based accounts):

1. `docker compose exec -it backend python -m scripts.reset_content` → review the list → type `RESET`.
2. `docker compose exec backend python -m scripts.seed_content` → competencies 8 / values 14 published, assessments 7 / prompts 4 drafts.
3. `docker compose exec -it backend python -m scripts.create_admin --email <your email> --name "<your name>"` → enter a password (accounts from the old code-based sign-in have none; this gives yours one and makes it admin).

**Checks:**

4. `curl.exe http://localhost:8000/health` → `"status":"ok"`, mongo + redis `up`.
5. http://localhost:3000 → alabaster background, gold buttons, Plus Jakarta Sans headings.
6. http://localhost:3000/register → name, email, password, tick the consent box → lands on **/account**, showing when you accepted. Without the tick the button stays disabled (and the API rejects it).
7. As that candidate open http://localhost:3000/admin/content → "You don’t have access to this page".
8. Sign out → sign in at /login with a wrong password → "Incorrect email or password"; 5 wrong tries → "Too many sign-in attempts".
9. Sign in as your admin → /admin/content shows the content types (incl. Support knowledge base); Assessments lists the 7 forms as `v1 draft`.
10. Admin: Questions → + New (type `single_choice`, options JSON) → Publish; Sections → + New with that question → Publish; Assessments → `case_study` → add the section → Publish. Then signed in, `GET /v1/assessments/case_study` returns it.
11. `pytest -v` in `backend/` → 27 passed.

## Verification checklist — Phase 3 (Landing & Orientation)

1. `docker compose up -d --build`, then `docker compose exec backend python -m scripts.seed_content` → `videos created=1 published=0`, `site_content created=1 published=1`.
2. http://localhost:3000 → hero, “Why enterprise management consulting” (3 cards), “How it works” (4 steps), closing call-to-action and privacy note — all from Admin → **Site content** → `landing`. No video section yet.
3. **Add your explainer video:** Admin → **Videos** → `explainer` → paste the URL (YouTube watch / youtu.be link, or an https `.mp4`; optional `.vtt` captions and transcript) → **Publish v1**.
4. Admin → **Site content** → `landing` → **Create new version** → *Explainer video* = `explainer` → **Publish v2**.
5. Signed out, reload http://localhost:3000 → the video appears → **Mark as watched** → “✓ Marked as watched” and a **Create your account** button → register → **/account** shows “You marked the explainer video as watched on …”.
6. A candidate who registered without watching sees “Watch it now” on /account → mark it on the landing page → /account shows it as watched.
7. Change any landing text in Admin → publish a new version → reload the landing page: updated, no redeploy.
8. `pytest -v` → 27 passed (34 after Phase 4).

## Verification checklist — Phase 4 (Commerce)

1. Stripe dashboard → **Test mode** → Developers → API keys → put `STRIPE_SECRET_KEY=sk_test_…` and `STRIPE_PUBLISHABLE_KEY=pk_test_…` in `backend/.env` → `docker compose up -d --build`.
2. `docker compose exec backend python -m scripts.seed_content` → `products created=4 published=4`.
3. http://localhost:3000/pricing → 4 products with prices; the Detailed Report says “Available after you buy an assessment”.
4. As a candidate, before buying: `GET /v1/assessments/capability` with your token → **402** “Purchase required…” (blocked even via direct API call).
5. **Buy** Management Consulting Assessment → Stripe test checkout → card `4242 4242 4242 4242`, any future date, any CVC → back on **/checkout/success** → “Payment received”.
6. /account → **Your purchases** lists it; /pricing shows “✓ You own this”, and the Detailed Report is now buyable.
7. Cancel a checkout → back on /pricing with “Checkout was cancelled — you haven’t been charged”.
8. Admin → Products → change a price → publish → /pricing shows the new price (no redeploy).
9. `pytest -v` → 34 passed.

## Verification checklist — Phase 5 (Assessment Engine)

1. `docker compose up -d --build`, then `docker compose exec backend python -m scripts.seed_content` → `questions created=62`, `sections created=13`, `assessments updated=7 published=7`.
2. Give your test candidate the bundle (or buy it once Stripe keys are in): `docker compose exec backend python -m scripts.grant_product --email <candidate email> --product bundle`.
3. Sign in as that candidate → you land on **/assessments** with the 7 forms, “Not started”.
4. **Profile & Experience** → answer “None yet” to years of experience → the “Programme experience” section is skipped (skip logic). Try it again with “3–5 years” on a fresh candidate: the section appears.
5. **Talent DNA** → reorder statements by dragging, the ↑/↓ buttons, or Alt+↑/↓ on a focused item.
6. **Autosave / resume:** answer a few Consulting Capability questions → “✓ All changes saved” → close the tab, sign in on another browser/device → **Continue** → same section, same answers.
7. **Next section** with a blank question → it's highlighted; **Review answers** → **Submit assessment** → locked (“submitted”).
8. As a candidate who hasn't bought an assessment: /assessments shows “Choose an assessment”; the API returns 402 for any attempt.
9. `pytest -v` → 42 passed.

## Verification checklist — Phase 5 uploads + Phase 5b (AI Profile Understanding)

1. `docker compose up -d --build` → `docker compose exec backend python -m scripts.seed_content` → `questions updated … created=1` (the CV question), `sections updated`, `assessments updated`, `prompts created=1 published=1` (profile_parser).
2. **Without an AI key** (current state): Profile & Experience → first question **Upload your CV** → pick a PDF/DOCX → ✓ file chip → “Check what we found” → **/profile** says it couldn't read it automatically and shows the empty form → fill in roles/industries/skills → **Confirm my profile** → ✓ Confirmed.
3. **With an AI key**: add to `backend/.env` e.g. `AI_PROVIDER=anthropic`, `AI_MODEL=claude-sonnet-5`, `AI_API_KEY=sk-ant-…` (or `AI_PROVIDER=openai` + `AI_MODEL` + `AI_API_KEY`, or `AI_BASE_URL` for Ollama) → `docker compose up -d` → on /profile **Try reading again** or upload a CV → “Reading your CV…” → roles, years, industries, skills, education appear pre-filled → edit anything → **Confirm**.
4. Wrong files are refused with a clear message: a .txt, an .exe renamed to .pdf, a file over 5 MB.
5. **Written Communication** → “Upload a video” tab → an .mp4 → ✓ → Submit. **Case Study** → “Upload a document” → a .docx/.pdf/.pptx → Submit.
6. `pytest -v` → 50 passed.

## Verification checklist — Phase 6 (Deterministic Scoring)

No new seed or env is needed — Phase 6 scores the answers already collected in Phase 5.

1. `docker compose up -d --build` (Phase 6 adds the `scores` collection automatically at startup).
2. Sign in as a candidate with the bundle (or `grant_product --email … --product bundle`), then complete and **submit** three forms: **Talent DNA**, **Values** and **Consulting Capability**.
3. Open **Results** in the header (http://localhost:3000/results):
   - **Talent DNA** — nine dimensions as bars, strongest first (0–100).
   - **Values** — a values wheel: values you rate above your own average reach outward in gold, below it point inward; four higher-order tiles below.
   - **Consulting Capability** — a competency radar plus an overall %.
   Forms you haven't submitted show a “not submitted yet” card, not an error.
4. **Reproducible:** reload — the numbers are identical. Or check the API directly: `curl.exe -H "Authorization: Bearer <token>" http://localhost:8000/v1/me/scores` returns the same three areas.
5. **Fast unit check (no Docker needed):** the scoring maths is pure and exactly tested —
   ```cmd
   cd /d D:\METI\backend
   ..\.venv\Scripts\python.exe -m pytest tests/test_phase6.py -v
   ```
   → 8 passed (5 pure-maths unit tests run in seconds; 3 end-to-end tests re-seed over the network).
6. `pytest -v` (whole suite) → 58 passed.

## Verification checklist — Phase 7 (AI Scoring Service)

Phase 7 needs an AI key to produce real scores; without one, responses show `pending` and can be re-run later.

1. Put an AI key in `backend/.env` (e.g. `AI_PROVIDER=anthropic`, `AI_MODEL=claude-sonnet-5`, `AI_API_KEY=sk-ant-…`; or `AI_PROVIDER=openai` + `AI_MODEL` + `AI_API_KEY`, or `AI_BASE_URL` for Ollama/Groq) → `docker compose up -d --build`.
2. `docker compose exec backend python -m scripts.seed_content` → `rubrics created=2 published=2`, `prompts … scoring` published, `questions updated` (WC-01/CASE-01/CASE-02 now pin a rubric).
3. As a bundle candidate, complete and **submit** **Written Communication** (type a 150+ word memo, or upload a short video) and **Case Study** (type, or upload a PDF/DOCX/PPTX).
4. Open **Results** → each shows, per response, **Reasoning / Knowledge / Communication** bars with a short evidence quote beneath each and an overall confidence. A video answer says it will be scored once transcription is enabled (Phase 8).
5. If a response is still `pending` (scoring runs in the background just after submit, or the provider was down), press **Score now** — or `curl.exe -X POST -H "Authorization: Bearer <token>" http://localhost:8000/v1/me/scores/written_communication/rescore`.
6. **Without a key:** the responses show `pending` and “Score now” returns them once a key is added — no crash, no faked score.
7. `pytest -v` (whole suite) → 67 passed (Phase 7's LLM is faked in tests; 3 of its 9 tests are fast pure-maths/parsing tests needing no network).


## Verification checklist — Phases 8–14 (Reports, Explainer, Roadmap, Support, Admin, Progress)

1. `docker compose up -d --build`, then `docker compose exec backend python -m scripts.seed_content` → `rubrics`, `support_kb` and the live prompts (scoring, results_explainer, support_chatbot) all publish.
2. As a candidate with the **bundle + Detailed Report** (buy them, or `grant_product --email … --product detailed_report`), submit the Capability and Written Communication assessments.
3. **Report** (`/report`) → Readiness + Evidence Confidence gauges count up; strengths and development themes appear. Ask the **Explainer** a "why" question — with an AI key it answers grounded in your results; without one it says it's unavailable (never invents).
4. **Voice:** in a supported browser, the Explainer shows a mic (speak your question) and a speaker toggle (answers read aloud) — all in-browser, no key.
5. **Roadmap** (`/roadmap`) → a milestone timeline + reassessment schedule; the Coach chat answers "what should I do first?" grounded in the roadmap. Without the upgrade the page prompts to unlock it (API returns 402).
6. **Support bot:** the "?" bubble (bottom-right, on every page, no login) answers "how long does it take?" from help content and says so when it doesn't know. It has no access to any candidate data.
7. **Admin** → `/admin/scores`: any AI response needing review is listed; override its scores with a reason, or approve. The candidate then sees the overridden score.
8. **Progress** (`/progress`): retake Capability from `/assessments/capability`, submit again, and see the before/after per competency.
9. `pytest -v` (whole suite) → 87 passed (LLM/voice faked; the app runs end-to-end with no external keys — Stripe and an AI key only unlock payments and richer AI text).

---

## Changelog

### Post-MVP iterations (from usage feedback)
Refinements after all 14 phases were built, driven by using the running app:

- **Free enrolment without Stripe (local/dev).** With no `STRIPE_SECRET_KEY`, "buy" now enrols the candidate for free (grants the product + bundled products) and sends them to their assessments, instead of a "payments not configured" error. Real Stripe is used when a key is set; **production** still returns the clear 503. (`commerce.start_checkout` → `_free_enroll`.)
- **Exam experience reworked to one question at a time.** The runner shows a single question, **auto-advances** when you pick a multiple-choice answer, has a **Skip** button (skipped knowledge questions score as wrong), and a final Review + Submit. `POST /attempts/{id}/submit` accepts an explicit `skipped` list (back-compatible: without it, unanswered still blocks submit); capability scoring counts every question so a skip = incorrect.
- **Real exam timer.** Each exam counts down the admin-set time (anchored to when the attempt started, so it survives reloads); at 0:00 it **auto-submits**. Shown as ⏱ mm:ss, red under a minute.
- **Guided candidate flow.** `/assessments` is now one numbered journey in the main body — 1 profile → 2 exams → 3 AI video interview → 4 results (results unlock after the first submission). The interview is a step here, not a separate nav item.
- **AI video interview (proctored).** New `/interview`: the interviewer **asks each question aloud** (browser speech synthesis) with a per-question countdown; the webcam records; **attention is monitored with MediaPipe FaceLandmarker** (loaded from CDN) — turning away, looking down or leaving the frame raises a warning, and **5 warnings auto-submits**. Recording + proctoring metadata (warnings, auto-submitted) are saved for admin review. Questions are the admin-editable `interview_questions` content type. Camera needs Chrome on `localhost`/https; if the CDN model can't load it records but disables warnings (never a fake pass).
- **Admin made friendlier.** Admins land on a plain-language **Admin home** (`/admin`) with three cards (Students & reports · Check AI marks · Edit content); the top bar is trimmed to just "Admin" (navigation is via the cards); every admin page has a **back** link; the admin's own account page shows an "Administrator" panel instead of candidate consent/orientation sections; a "no access" page sends admins to `/admin`.
- **Admin authoring without typing everything.** In the content editor: **"Generate with AI"** drafts a content item from a plain-English instruction (admin edits, then publishes), and **"Import file"** bulk-creates items from a JSON file. (`ai/content_gen.py`, `POST /admin/content/{type}/generate` and `/import`.)
- **Complete per-student report for admins.** `/admin/users` lists students ranked by overall **Readiness** (best first) with an "exams done" count; a student's page shows the full report — overall Readiness/Evidence Confidence, the consulting-knowledge radar, Talent DNA, Values wheel, written & case **AI marks with evidence**, the **video interview (playback + warnings)**, their **complete parsed CV**, uploads, and the attempts log.
- **"Check AI marks" shows the marks.** It now lists both answers **needing review** and those **already marked by the AI** (Reasoning / Knowledge / Communication + confidence), each with a "Change this mark" override — no longer empty when everything scored cleanly.
- New content type **`interview_questions`** (timed questions the interview asks) and new **`interviews`** collection (one per recording, with proctoring metadata). Tests: `test_examflow.py`, `test_admin2.py`, `test_interview.py`, updated `test_phase4.py`. Suite ~97 tests.

### Phases 8–14 — Reports, Explainer, Roadmap, Support bot, Admin, Motion, Reassessment, Deploy
- **Phase 8 — Composite, Reports & Explainer.** `composite.py` computes **Readiness** and **Evidence Confidence** deterministically from the Phase 6/7 outputs (weights renormalise over whatever the candidate has done). `reports.py` assembles a **Summary of Findings** (any paid assessment) and a **Detailed Report** (gated by the report_upgrade) from locked scores — works with no AI key. The **AI Explainer** (`ai/explainer.py`) answers grounded strictly in the candidate's own results, in **Why** mode (report) and **Coach** mode (roadmap); voice is the browser Web Speech API (`voice_provider.py`, `webspeech`, zero-cost). Frontend `/report` with count-up gauges + the Why chat.
- **Phase 9 — Roadmap.** `roadmap.py` generates 6–8 milestones from the gap analysis (+ a strength to consolidate) with a reassessment schedule, stored per candidate, gated by the upgrade; Coach mode grounds on it. Frontend `/roadmap` timeline + Coach chat.
- **Phase 10 — Support chatbot.** `support_kb` content type + seed; `support_kb.py` does keyword retrieval over **public content only** (hard boundary — never candidate data) and answers extractively without an AI key or via the `support_chatbot` prompt with one. Public `POST /support/chat` + a floating `SupportBubble` on every page.
- **Phase 11 — Admin.** `admin_scores.py` — a review queue of AI-scored responses, a per-response **override with a required reason** (audited), and approve; `/admin/scores` UI. Support KB is edited through the existing content admin (it's a content type).
- **Phase 12 — Motion.** A calm motion layer with **CSS reveals**, **animated bars** and a **CountUp** component, all disabled under `prefers-reduced-motion`. (Implemented with CSS + Web APIs rather than adding Framer Motion, to keep the build dependency-free; Framer Motion can be dropped in later behind the same components.)
- **Phase 13 — Reassessment & Progress.** Retaking just starts a new attempt (the prior one is immutable and kept); `reassessment.py` builds a **before/after** of the two most recent attempts per competency/dimension; submitting a reassessment regenerates the roadmap. Frontend `/progress`.
- **Phase 14 — Test & Deploy.** End-to-end smoke test (register → grant → assess → score → report → roadmap → support), health checks, and the Docker Compose stack from Phase 0.
- Tests: 20 new across `test_phase8`…`test_phase14` (composite maths, report gating, grounded explainer, roadmap generation, support retrieval + boundary, admin override, retake before/after, full-journey smoke). LLM/voice faked; the whole thing runs with no external keys.

### Phase 7 — AI Scoring Service (Reasoning / Knowledge / Communication)
- One scoring service (`services/ai_scoring.py`), not a swarm of agents: **one AI call per free-text response** returns the three named dimensions the v5 diagram calls for — Reasoning, Knowledge, Communication (0-100 each) — with a **cited evidence quote** per dimension and an overall confidence, validated against a pydantic schema (`AIScore`). Invalid output is repaired once then flagged `needs_review`; an unreachable provider leaves the response `pending`; a video answer waits for the Phase 8 transcription (`needs_transcript`) — never a faked score.
- Responses can be **typed or uploaded**: PDF / DOCX / PPTX documents are extracted to text (PPTX via the slide XML, no new dependency) and scored; the memo (WC-01) and case (CASE-01/02) responses each carry a rubric whose anchors calibrate the 0-100 scale.
- New seed: `rubrics.json` (memo + case rubrics, published before questions so WC-01 / CASE-01 / CASE-02 pin them) and the live `scoring` prompt moved into `prompts_live.json` (the placeholder left `prompts.json`, so a re-seed can't regress it).
- Scored in the **background on submit** (deterministic forms stay inline); stored one-per-attempt in `scores` (`method: ai`). `GET /v1/me/scores` now returns the AI areas alongside the deterministic ones; `POST /v1/me/scores/{key}/rescore` re-runs a `pending` memo/case.
- Frontend `/results`: an **EvidenceScores** panel per AI-scored area — the three dimensions as bars with the evidence quote beneath each — plus a “Score now” action while a response is pending, and calm states for pending / awaiting-transcription / review.
- Tests: 9 new (`test_phase7.py`) — pure tests for PPTX extraction and the score schema, and end-to-end submit → three named dimensions with evidence, per-response case scoring, video-waits-for-transcript, provider-outage → pending → rescore, and privacy. LLM faked as everywhere else.

### Phase 6 — Deterministic Scoring (Talent DNA, Values, Consulting Capability)
- Three deterministic scorers in `services/scoring_rules.py`, computed in code so the same answers always give the same profile (TDD §9):
  - **Talent DNA** — rank-order items scored 4-3-2-1; each placed option credits its `maps_to` dimension, normalised 0–100 against the best/worst it could reach on the items where it appeared (so dimensions on different numbers of items compare fairly). Nine dimensions.
  - **Values** — 6-point Schwartz portrait items; each basic value = mean of its items, then **MRAT-centred** (minus the candidate's own overall mean) to remove scale-use bias and yield a relative value-priority profile. Ten basic values (circumplex/wheel order) + four higher-order views (constituents weighted 1, partial 0.5).
  - **Consulting Capability** — correct-option knowledge items; each item's correctness credits its competency (weighted by `competency_map`), giving a per-competency % for the radar + an overall %.
- Scored automatically the moment a deterministic form is submitted (best-effort — a scoring error never blocks the submission); stored one-per-attempt in the new `scores` collection, idempotent on recompute. `GET /v1/me/scores` reads them and back-fills any that are missing (e.g. attempts submitted before Phase 6).
- Frontend `/results`: **ValuesWheel**, **TalentDnaBars** and **CapabilityRadar** (pure SVG in the locked palette, real data — no static images) with loading / empty / not-submitted states; “Results” added to the candidate header.
- Tests: 8 new (`test_phase6.py`) — pure-maths unit tests asserting exact rank/MRAT/weighted numbers, plus end-to-end submit → read, reproducibility, missing-score recompute and per-candidate privacy.

### Phase 5 (v5 additions) + Phase 5b — Uploads & AI Profile Understanding
- Uploads: `file_upload` question type (the CV) and an optional “or upload a file” on free-text questions (communication video, case document). Files are validated by content (magic bytes / DOCX-PPTX structure), size-capped while streaming, sha256-fingerprinted, stored on a Docker volume behind `services/files.py`, and only downloadable by their owner or an admin. File answers can only be set by the upload endpoint (no forged file ids via autosave).
- `app/ai/provider.py`: the single LLM abstraction (Anthropic or any OpenAI-compatible API), pydantic-validated JSON output, one repair retry, then `needs_review` — never a made-up result.
- Phase 5b: CV text (PDF/DOCX) → published `profile_parser` prompt → structured profile stored in `evidence_claims` as **self-reported** evidence; candidate reviews/corrects it on **/profile** (“Here’s what we found in your CV”); AI unavailable / scanned PDF / invalid output all fall back to manual entry with a retry.
- Seed keeps its own published content current (new version when the item or its references change), so existing databases receive the new CV question without manual edits.

### Phase 5 — Assessment Engine
- One generic engine (`services/attempts.py`) and one runner (`/assessments/[code]`) for all 7 forms, driven entirely by question data; 5 types: single choice, multi-select (min/max), Likert, rank-N (drag + buttons + Alt+arrows), free text (min words, max length).
- Attempts pin the assessment version they started on; server-side autosave (debounced ~0.8 s, retry on failure, unload warning) → resume on any device; submit checks completeness and locks the attempt.
- “If answer = X, skip section” evaluated identically on server and client.
- Candidates only ever receive sanitised questions — no correct answers, competency/value maps or rubrics (also fixed on `GET /v1/assessments/{code}`).
- Seed item bank: 62 original questions in 13 sections — Talent DNA ranking items mapped to the TDD dimensions, 20 Schwartz-informed portrait items, 20 capability items mapped to the 8 competencies, one memo, one case (Harbour Bank).
- `grant_product` script; candidates now land on /assessments after sign-in.

### Phase 4 — Commerce
- 4 products as published content with one flat price each (TDD defaults); product fields for bundled products, prerequisites (“buy after an assessment”) and pricing-page order. Products may list assessments that are still drafts.
- Stripe test-mode Checkout; `payments` + `entitlements` collections. Entitlements are granted only when Stripe reports the session **paid** and the amount/currency match — via the signed webhook or the success page's server-side check with Stripe (both idempotent). Bundles also grant each bundled product.
- `/v1/assessments/{code}` now returns 402 unless the candidate owns a product that includes it.
- Frontend: /pricing, /checkout/success (confirming / paid / processing / failed states), purchases on /account, Pricing link in the header.

### Phase 3 — Landing & Orientation
- `site_content` content type (headline, sub-headline, CTA, narrative blocks, journey steps, privacy note, closing, linked explainer video) + public `GET /v1/site/{key}` serving published versions only, video pinned to the version published with the page.
- Video validation: https links only; YouTube links normalised to a privacy-enhanced (`youtube-nocookie`) embed; mp4 with optional captions track; transcript as the accessible alternative.
- “Mark as watched”: before sign-up it's remembered in the browser and sent with registration; signed-in candidates mark it via `POST /v1/candidates/me/orientation`; stored on the user with the exact video version; audited. No milestone tracking or quiz gate (plan v2).
- Landing page in the locked design system with loading / not-published / error states; system status moved to `/status`; account page shows orientation status.
- Seed: landing copy (TDD public story) published; explainer video entry as a draft awaiting the real URL.

### v4 alignment (Phases 0–2 reduced to the final plan)
- Content model: 12 types → 10 (`assessments`, `sections`, `questions`, `rubrics`, `competencies`, `values_taxonomy`, `videos`, `products`, `prompts`, `report_templates`); 5 question types; section `skip_if` replaces branching; flat product price replaces `price_book`.
- Seed: 7 forms, 8 grouped competencies, 4 AI prompts (values taxonomy unchanged).
- Auth: email + password (bcrypt), two roles, one timestamped consent checkbox; OTP, SMTP and the versioned consent system removed. Refresh-token rotation, rate limits, tenant scope kept.
- Design system tokens (plan v3) added and applied to every existing screen.
- New scripts: `reset_content` (migrate an old database), `create_admin` now sets a password.

### Phase 2 — Auth & Access (first version, superseded by the v4 alignment)
- JWT access token (memory) + rotating refresh token (httpOnly cookie); `require_role`, `require_tenant_scope`; Redis rate limits; audit events.

### Phase 1 — Content Model & Admin Core
- Versioned content (draft → validate → publish, immutable, pinned references), admin API + `/admin/content` UI generated from field specs, JSON seed data.

### Phase 0 — Foundation
- Monorepo, Docker Compose, env-only config, Motor + index bootstrap, `/health`, JSON logging with request ids, CORS; MongoDB moved fully to Atlas.
