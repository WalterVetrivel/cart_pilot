# CartPilot

Agentic shopping assistant for Indian households, built for the AI Builder Cup 2026 (retail and commerce track).
`SPEC.md` is the source of truth; build milestone by milestone (SPEC §12).

```
backend/    FastAPI + Google ADK agents (Gemini), deployed to Cloud Run
frontend/   React + Vite + TypeScript + Tailwind, deployed to Firebase Hosting
infra/      firebase.json (/api/** → Cloud Run), Firestore rules, deploy guide
.github/    CI (lint, tests, build) and CD (Cloud Run + Firebase Hosting)
```

## Run locally

Prerequisites: Python 3.12, Node 22.

```bash
# Backend  → http://localhost:8080/api/health
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env               # add GOOGLE_API_KEY from AI Studio; AUTH_DISABLED=true to skip sign-in checks
uvicorn app.main:app --reload --port 8080

# Frontend → http://localhost:5173 (proxies /api to :8080)
cd frontend
npm install
cp .env.example .env.local         # Firebase web app config
npm run dev
```

Checks (same as CI):

```bash
cd backend && ruff check . && ruff format --check . && pytest -q
cd frontend && npm run lint && npm run build
```

## Deploy

See [infra/deploy.md](infra/deploy.md) for manual commands and the one-time setup for continuous deployment.

## Status

- [x] M0 Skeleton: `/api/health`, Google sign-in, Hosting rewrite, CI/CD
- [ ] M1 Seed + parsing
- [ ] M2 Ranking + optimiser
- [ ] M3 Vouchers + checkout
- [ ] M4 Deploy
- [ ] M5 Live prices + chat
- [ ] M6 Submission
