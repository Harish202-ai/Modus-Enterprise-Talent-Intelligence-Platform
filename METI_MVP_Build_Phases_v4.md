# METI-MC — Trimmed MVP Build Plan (v4)

**Stack:** Next.js (React) + Framer Motion + Tailwind · FastAPI (Python, async) · MongoDB (Motor) + a vector index for RAG (Mongo Atlas Vector Search or a lightweight local index — see Phase 10) · Redis · Real LLM provider (config-swappable) · Voice STT/TTS provider (config-swappable) · Docker

**What changed from v3:**
- New **Phase 10 — Site-Wide RAG Support Chatbot** (general "how does this work" bot, separate from the personal Results Explainer).
- Phase 11 (UI/UX pass) now explicitly includes a **Motion & Interactivity Layer** — page transitions, micro-interactions, looping ambient video/animation.
- Voice API key location given below — you can drop your key in whenever you have it, doesn't block any earlier phase.

---

## 📍 Where your free voice API key goes

When you have it, put it in **`backend/.env`**:

```env
VOICE_PROVIDER=elevenlabs        # or azure_speech, google_speech, webspeech, etc. — whichever you're giving me
VOICE_API_KEY=your_key_here
VOICE_API_REGION=                # only needed for providers like Azure that require a region
```

`backend/app/config.py` reads these into a `VoiceSettings` object; `backend/app/ai/voice_provider.py` picks the right adapter based on `VOICE_PROVIDER` at startup. **You never put the key in frontend code** — the browser talks to our backend, our backend talks to the voice provider. If you end up going with the browser's built-in Web Speech API instead (zero cost, no key, runs entirely client-side), just set `VOICE_PROVIDER=webspeech` and leave the key blank — I'll route around the backend for that one specifically since it doesn't need a server-side key at all.

---

## Phase 0 — Foundation
*(unchanged)*

## Phase 1 — Content Model & Admin Core
*(unchanged)*

## Phase 2 — Auth & Access
*(unchanged)*

## Phase 3 — Landing & Orientation
*(unchanged in function — gets its motion treatment in Phase 11)*

## Phase 4 — Commerce
*(unchanged)*

## Phase 5 — Assessment Engine
*(unchanged)*

## Phase 6 — Deterministic Scoring
*(unchanged)*

## Phase 7 — AI Scoring Service
*(unchanged)*

## Phase 8 — Composite Score, Reports & Personal AI Explainer (voice-enabled)
*(unchanged from v3)* — grounded strictly in **this candidate's own** locked evidence. Never answers questions about the platform in general; that's Phase 10's job.

## Phase 9 — Development Roadmap Module
*(unchanged from v3)*

---

## Phase 10 — Site-Wide RAG Support Chatbot (new)

**Objective:** A small, floating chat widget present on every page — landing, pricing, dashboard, report — that answers general questions about the platform itself: "what's included in the paid report," "how long does the assessment take," "what happens to my video," "how is my data used." This is the "small chatbot" you asked for.

**Critical design rule — this is a hard boundary, not a preference:** this bot's knowledge base is **public site content only** — FAQs, product descriptions, methodology explanations, pricing, privacy policy. It has **no access** to any candidate's scores, responses, or evidence. Mixing this up would mean one candidate's chatbot session could leak another candidate's private data. Two separate agents, two separate retrieval scopes, enforced at the query layer, not just by prompt instruction.

- `support_kb` collection: chunked FAQ/help content, admin-editable (Phase 1 pattern — no hardcoded chatbot answers).
- Simple RAG: embed `support_kb` chunks (via the same LLM provider's embeddings endpoint or a small local embedding model), store vectors in Mongo (Atlas Vector Search if you're on Atlas, otherwise a lightweight in-memory/FAISS index for MVP — real either way, just sized to MVP scale), retrieve top-k on each query, answer grounded in retrieved chunks only.
- If the bot doesn't find a confident answer in the KB, it says so and offers a "contact us" / "log in to ask about your results" path — it does not guess.
- Widget UI: small floating bubble (bottom-right), expands to a compact panel — deliberately lightweight, not a full-screen takeover, so it doesn't compete with the calm report/explainer screens from Phase 8.

**DoD:** Any visitor, logged in or not, can ask a general platform question and get a grounded answer from admin-editable content — with zero access to any private candidate data.

---

## Phase 11 — Admin Panel
*(was Phase 10 in v3)* Now also includes: managing `support_kb` content for the Phase 10 chatbot.

## Phase 12 — UI/UX Pass + Motion & Interactivity Layer

**Objective:** This is where "dynamic, interactive, moving" actually gets built — as a dedicated sub-focus, not an afterthought.

- **Page transitions**: Framer Motion route transitions (fade/slide) instead of hard page jumps.
- **Micro-interactions**: buttons with subtle hover/press states in the gold accent, form fields with focus animations, toast notifications that slide in/out.
- **Animated data reveals**: score numbers count up on the report page instead of appearing static; progress rings animate to their value; the competency radar chart draws itself in rather than popping in instantly.
- **Small looping ambient motion** on the landing/hero and dashboard — short (3–6 sec), silent, looping video or Lottie animation related to the project's theme (e.g., an abstract animated line/network graphic suggesting "enterprise strategy," a subtle animated chart, or a looping abstract gradient) — **not** a literal gif meme, something that reads as premium-consulting-brand motion rather than decorative clutter. I'll source or generate this as a lightweight looping MP4/WebM or Lottie JSON (much smaller and crisper than an actual .gif) and keep it muted/non-distracting per the "calm, not busy" design principle from v3.
- **Chat widgets** (both the Phase 8 Explainer and Phase 10 support bot) get entrance/typing animations so responses feel alive, not static text dumps.
- Enforce the locked palette/type tokens across all of the above — motion should never introduce a color or font that breaks the 60/30/10 system.
- Accessibility check: every animation respects `prefers-reduced-motion`.

**DoD:** Landing, dashboard, and report screens feel alive and responsive to interaction — without becoming visually noisy.

## Phase 13 — Test & Deploy
*(was Phase 12)* Now also smoke-tests the RAG chatbot (Phase 10) answers correctly and never returns private data, and that reduced-motion mode works.

---

Say **"START PHASE 0"** and I'll scaffold this version.
