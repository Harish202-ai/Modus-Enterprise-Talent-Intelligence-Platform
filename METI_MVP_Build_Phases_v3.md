# METI-MC — Trimmed MVP Build Plan (v3)

**Stack:** Next.js (React) + Tailwind · FastAPI (Python, async) · MongoDB (Motor) · Redis · Real LLM provider (config-swappable) · Voice STT/TTS provider (config-swappable, your free API key) · Docker

**What changed from v2:**
- Locked design system: exact color palette + typography (below).
- Phase 8 (AI Explainer) is now **voice-enabled**, not text-only.
- New **Phase 9 — Development Roadmap module**, split out from the report so it gets proper screen real estate instead of being one section buried in a PDF.
- Phase numbers shifted accordingly (12 phases → 13).

---

## Design System (locked)

**Color palette (60/30/10 rule enforced in Tailwind config — not ad hoc per screen):**

| Role | Hex | Usage |
|---|---|---|
| 60% Dominant Background | `#F4F3EF` (Soft Warm Alabaster) | Page backgrounds, large surface areas |
| 30% Secondary Text & Borders | `#1C2321` (Off-Black Forest Charcoal) | Body text, headings, borders, icons |
| 10% Accent / CTA | `#C5A880` (Muted Warm Ochre/Gold) | Primary buttons, active states, links, highlights — used *sparingly* per the 10% rule, not on every element |
| Supporting Surface | `#FFFFFF` | Cards, modals, form fields — for clear separation from the alabaster background |

This is a restrained, editorial palette (fits the "consulting firm / fintech" register you specified) — the discipline of keeping gold to ~10% of visual weight is what will make the UI look calm and premium instead of busy. I'll enforce this as Tailwind theme tokens (`bg-surface-base`, `text-primary`, `accent-cta`, `bg-surface-card`) so no screen invents its own shade.

**Typography:**
| Role | Font | Weight |
|---|---|---|
| Headings | Plus Jakarta Sans | 600 / 700 |
| Body | Satoshi (fallback: General Sans, then system sans) | 400 |

Both load via Google Fonts / self-hosted `@font-face` — no CDN dependency that could break the published-page constraint later if you ever turn a report into a shareable artifact.

**Applied specifically:**
- Landing hero, report headlines, section titles → Plus Jakarta Sans Bold.
- Assessment question text, report body copy, chat messages → Satoshi Regular.
- The gold accent goes on: primary CTA buttons, progress indicators, the AI Explainer's active/listening state, score highlight numbers — not on backgrounds, not on every border.

---

## Phase 0 — Foundation
*(unchanged from v2)* Repo, docker-compose, config, Motor client, health check.

## Phase 1 — Content Model & Admin Core
*(unchanged)* Versioned collections, basic admin CRUD, seed script.

## Phase 2 — Auth & Access (2 roles)
*(unchanged)* candidate / admin, JWT, single consent checkbox.

## Phase 3 — Landing & Orientation
*(unchanged, now styled to the locked design system)* One explainer video, "mark as watched."

## Phase 4 — Commerce
*(unchanged)* Flat pricing, Stripe test mode, webhook-driven entitlements.

## Phase 5 — Assessment Engine (7 forms, 5 question types)
*(unchanged)* Generic runner, autosave, resume.

## Phase 6 — Deterministic Scoring (Talent DNA & Values)
*(unchanged)* Rank scoring, Schwartz centering, values wheel — now rendered in the gold/charcoal/alabaster palette.

## Phase 7 — AI Scoring Service
*(unchanged)* One scoring service, upload-based video/case evidence, schema-validated AI scores.

## Phase 8 — Composite Score, Reports & AI Results Explainer (now voice-enabled)

- Composite scores (Readiness, Evidence Confidence), Summary of Findings, Detailed Report — as in v2.
- **AI Results Explainer becomes a voice + text chat.** Candidate can type *or* speak a question ("why is this a strength?"); response can be read back via TTS or shown as text — user toggles which.
- **Provider abstraction**: `ai/voice_provider.py` — same pattern as the LLM abstraction, config-swappable via `.env`, so whichever free STT/TTS API you provide (e.g., a browser-native Web Speech API for a zero-cost MVP path, or a hosted free-tier service) plugs in without touching the rest of the app.
- Answers remain strictly grounded in the candidate's locked score/evidence — voice doesn't loosen that rule, it's just a different input/output channel on the same constrained agent.
- UI treatment: a calm, single focal chat panel — mic button in the gold accent color, waveform/listening indicator, no visual clutter competing with it.

**DoD:** Candidate can ask a question by voice or text and get a grounded answer, spoken back or shown as text.

## Phase 9 — Development Roadmap Module (new, split from the report)

- `roadmaps` collection: generated from the candidate's composite score + gap analysis, not static copy.
- Clean, dedicated screen (not just a report page section): a horizontal or vertical timeline of 6–8 weekly/milestone blocks, each with 1–2 concrete actions and a linked resource (video/reading/exercise from the content model).
- Only unlocked with the Detailed Report entitlement, consistent with the commercial model.
- Same AI Explainer chat is available on this screen too, so a candidate can ask "why this milestone first?" grounded in the same roadmap data.

**DoD:** A candidate with the upgrade entitlement gets a real, DB-generated roadmap on its own clean screen, explorable via the same Explainer.

## Phase 10 — Admin Panel
*(was Phase 9)* Content CRUD, one override/approve action per AI score.

## Phase 11 — UI/UX Pass
*(was Phase 10)* Design system now has the exact tokens above baked in from Phase 0 forward, so this phase becomes **enforcement + polish** — auditing every screen against the palette/type rules, empty/error/loading states, responsive pass, accessibility (including making sure the voice feature has a text fallback for accessibility, not just a mic-only path).

## Phase 12 — Test & Deploy
*(was Phase 11)* Scoring-math unit tests, one E2E smoke flow (now including the voice explainer and roadmap unlock), Docker deploy.

---

## Note on the voice API

Whatever free API you're planning to provide — tell me which one (e.g., browser Web Speech API needs no key at all and is the simplest zero-cost path since it runs client-side; a hosted STT/TTS service needs a key in `.env` like the LLM provider) and I'll wire Phase 8 to match it exactly when we get there. No need to decide now — the abstraction means we can swap it later without rework.

---

Say **"START PHASE 0"** and I'll scaffold this version.
