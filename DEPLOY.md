# Deploying METI-MC

The app is four pieces:

| Piece | What | Where |
|---|---|---|
| **Frontend** | Next.js 16 (standalone Docker) | Railway / Render / Vercel |
| **Backend** | FastAPI (Docker, uvicorn :8000) | Railway / Render |
| **MongoDB** | Atlas | you already have it |
| **Redis** | sessions + rate limits | Railway/Upstash add-on |

> Everything sensitive (`MONGO_URI`, `JWT_SECRET`, `AI_API_KEY`) is **not** in this repo — you set it in the host's dashboard. `.env.example` files are placeholder templates only.

---

## Recommended: Railway (one project, both services + Redis)

1. **railway.app → New Project → Deploy from GitHub repo** → pick
   `Harish202-ai/Modus-Enterprise-Talent-Intelligence-Platform`.

2. **Backend service** — set *Root Directory* = `backend` (it uses `backend/Dockerfile`). Add the env vars from the table below.

3. **Add Redis** — in the project: *New → Database → Add Redis*. Copy its connection URL into the backend's `REDIS_URI`.

4. **Frontend service** — *New → GitHub Repo* (same repo) → *Root Directory* = `frontend`. Add a **build-time** variable `NEXT_PUBLIC_API_URL` = the backend service's public URL (e.g. `https://meti-backend.up.railway.app`).

5. **Wire CORS** — set the backend's `CORS_ORIGINS` to the frontend's public URL, then redeploy the backend.

6. **Seed the database once** — open the backend service → *Shell* (or a one-off command) and run:
   ```bash
   python -m scripts.seed_tenant
   python -m scripts.seed_content
   python -m scripts.create_admin --email you@company.com --name "Your Name"
   ```

Frontend URL is now your live site. ✅

---

## Alternative: Render (backend, Docker) + Vercel (frontend)

- **Backend on Render:** New → Web Service → the repo → *Root Directory* `backend`, *Runtime* Docker. Add the backend env vars. Add a **Key Value (Redis)** instance and point `REDIS_URI` at it.
- **Frontend on Vercel:** Import the repo → *Root Directory* = `frontend` (Vercel auto-detects Next.js). Add env var `NEXT_PUBLIC_API_URL` = your Render backend URL. Deploy.
- Set the backend's `CORS_ORIGINS` to the Vercel URL and redeploy.
- Seed the DB via Render's Shell (same three commands as above).

---

## Environment variables

### Backend (set in the host dashboard — never commit)
| Var | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `prod` | outside dev the app **requires** a strong JWT secret |
| `MONGO_URI` | your Atlas SRV string | **secret** |
| `MONGO_DB` | `METI` | uppercase (Atlas reserves it) |
| `REDIS_URI` | from the Redis add-on | **secret** |
| `JWT_SECRET` | 32+ random chars | generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` — **secret** |
| `AI_PROVIDER` | `openai` | Groq is OpenAI-compatible |
| `AI_MODEL` | `openai/gpt-oss-120b` | |
| `AI_BASE_URL` | `https://api.groq.com/openai/v1` | |
| `AI_API_KEY` | your Groq key (`gsk_…`) | **secret**; unset → AI degrades gracefully |
| `CORS_ORIGINS` | your frontend URL | e.g. `https://your-app.vercel.app` |
| `FRONTEND_URL` | your frontend URL | Stripe return URL |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` / `STRIPE_WEBHOOK_SECRET` | optional | without them, prod checkout returns 503 |
| `VOICE_PROVIDER` | `webspeech` | browser voice, no key |

### Frontend
| Var | Value |
|---|---|
| `BACKEND_URL` | the backend's public URL — the frontend proxies `/v1/*` to it at runtime. Optional: a sensible default is baked into `frontend/src/middleware.ts`, so it works after a push even if unset. |

> The frontend does **not** need `NEXT_PUBLIC_API_URL` in production. The browser calls same-origin `/v1/*` and Next.js middleware proxies to `BACKEND_URL` at runtime (no build-time baking, no CORS).

---

## Issues we hit on Railway — and the fix for each

These are the real problems encountered bringing this stack up, in the order they appear:

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Build fails: *"Railpack could not determine how to build the app"* (lists only `README.md`, `*.md`) | Railway built the **repo root**, which has no app | Set each service's **Root Directory** (`backend` / `frontend`). `railway.json` in each folder forces the **Dockerfile** builder. |
| 2 | *"Application failed to respond"* / *"no open ports"* | Backend hard-coded port `8000`, Railway assigns a dynamic `$PORT` | Dockerfile `CMD` uses `--port ${PORT:-8000}`. Frontend: set `PORT=3000` if needed. |
| 3 | Backend crash: `ValidationError … mongo_uri Field required` | `MONGO_URI` not set on the service | Add all backend **Variables** (`MONGO_URI`, `JWT_SECRET`, `AI_*`, `ENVIRONMENT=prod`, `MONGO_DB=METI`). |
| 4 | `JWT_SECRET must be a random string of 32+ characters` | `ENVIRONMENT=prod` with a weak/empty secret | Set a strong `JWT_SECRET` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). |
| 5 | Frontend loads, but **all `/v1/*` calls → 404** (login/landing/pricing) | The frontend didn't know the backend's address | Set **`BACKEND_URL`** on the frontend service (or rely on the default baked into `middleware.ts`); push + redeploy the frontend. |
| 6 | Landing shows *"hasn't been published yet"* | Deployed DB not seeded / different DB than local | `LandingView` now renders **built-in default content** as a fallback. To show real content, seed the deployed DB or point `MONGO_URI` at the seeded one. |
| 7 | `/v1/*` returns **500**, `/health` shows `"mongo":"down"` | Backend can't reach MongoDB Atlas | (a) **Atlas → Network Access → allow `0.0.0.0/0`**; (b) `MONGO_URI` must match local exactly; (c) `MONGO_DB=METI` (uppercase — lowercase is rejected). |
| 8 | Mongo still `down` even with allowlist open & correct URI | TLS handshake fails in the slim container (`SSL CERTIFICATE_VERIFY_FAILED`) although the same URI works locally | Mongo client now pins **certifi's CA bundle** (`tlsCAFile=certifi.where()`); `certifi` added to `requirements.txt`. Redeploy backend. |
| 9 | Sign-in hangs / 500s | Redis down took down auth (rate-limiting) | Rate-limiting is **fail-open**; the Redis client **fails fast** (2s, no retries). Add a Railway Redis plugin + `REDIS_URI` for full function. |
| 10 | Uploaded videos/CVs disappear after a redeploy | Container filesystem is **ephemeral** | Attach a **Volume** at `/data/uploads` and set `UPLOADS_DIR=/data/uploads`. |
| 11 | CORS error on file download / a missing file 500s | Error responses lacked CORS headers; missing bytes crashed `FileResponse` | Missing files now return a clean **410** (with CORS headers). |

**How to diagnose a `mongo: down`:** open the backend service **Logs**, find `mongo ping failed`, and read the error underneath — it names the exact cause (auth, DNS/SRV, SSL, timeout).

## Other gotchas
- **HTTPS is required** — the refresh-token cookie and the video-interview camera need a secure context. Managed hosts give you HTTPS automatically.
- **Free-tier cold starts** — the first request after idle can be slow; refresh and wait ~30s.
- **Payments** — real Stripe needs the keys above and a webhook to `/v1/payments/webhook`; otherwise leave unset (checkout returns a clear 503 in prod).
- **Two databases drifting** — local and deployed can point at different DBs; keep `MONGO_URI`/`MONGO_DB` aligned so seeded content and the admin account appear on the live site.
