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
cp .env.example .env               # add GOOGLE_API_KEY from https://aistudio.google.com/apikey
uvicorn app.main:app --reload --port 8080

# Frontend → http://localhost:5173 (proxies /api to :8080)
cd frontend
npm install
cp .env.example .env.local         # Firebase web app config (optional: without it you're a local guest)
npm run dev
```

By default the backend serves the seeded catalogue from memory, so nothing but the Gemini API is needed.

### Optional: Firestore emulator (needs Java 11+)

```bash
cd infra && npx firebase-tools@15 emulators:start --only firestore      # UI at http://localhost:4000
# in backend/.env: FIRESTORE_EMULATOR_HOST=127.0.0.1:8081, then once:
cd backend && python -m seed.load
```

Seed data is generated deterministically by `python -m seed.generate_seed` (writes `backend/seed/data/`).

Checks (same as CI):

```bash
cd backend && ruff check . && ruff format --check . && pytest -q
cd frontend && npm run lint && npm run build
```

## Deploy

See [infra/deploy.md](infra/deploy.md) for manual commands and the one-time setup for continuous deployment.

## Status

- [x] M0 Skeleton: `/api/health`, Google sign-in, Hosting rewrite, CI/CD
- [x] M1 Seed + parsing
- [ ] M2 Ranking + optimiser
- [ ] M3 Vouchers + checkout
- [ ] M4 Deploy
- [ ] M5 Live prices + chat
- [ ] M6 Submission
