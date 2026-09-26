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
| `NEXT_PUBLIC_API_URL` | your backend public URL (build-time) |

---

## Gotchas
- **HTTPS is required** — the refresh-token cookie and the video-interview camera need a secure context. Managed hosts give you HTTPS automatically.
- **JWT_SECRET** — with `ENVIRONMENT=prod`, the backend refuses to start on a weak/default secret.
- **CORS** — the browser is blocked until `CORS_ORIGINS` exactly matches the frontend origin (scheme + host, no trailing slash).
- **Port** — the backend Dockerfile listens on `8000`; Railway/Render auto-detect it. If a host injects `$PORT` and requires it, change the Dockerfile `CMD` to `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` (shell form).
- **Payments** — real Stripe needs the keys above and a webhook to `/v1/payments/webhook`; otherwise leave unset (checkout returns a clear 503 in prod).
