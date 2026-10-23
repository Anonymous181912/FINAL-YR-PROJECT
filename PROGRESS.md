# Progress

## Done (Phase 0)
- [x] 0a register JSON body + password policy (backend, Login register mode, tests)
- [x] 0b doctor verification + admin role/router/seed + verified-doctor gate + frontend pending screen + Admin page
- [x] 0c patient-profile isolation on GET /patients/{id}
- [x] 0d regex escape + search cap
- [x] 0e gitignore, stray file + redundant OCR script removed, uploads .gitkeep
- [x] 0f ocr._get_reader fix, allowed_extensions consistent (dcm removed)
- [x] 0g slowapi limits on login/register/upload (+ chat reserved)
- [x] tests: 114 passed; frontend build passes
- [x] DECISIONS.md + CHANGELOG.md written

## Done (Phase 0.5 — verify Phase 0)
- [x] 14 new tests: unverified 403s, rejected-old-token blocked, A/B isolation, admin/query-param 422s, login 429
- [x] Suite: 128 passed

## Done (Phase 1 — lab flagging + trends)
- [x] reference_ranges.py + lab_parser.py (deterministic), lab_results on upload, GET /labs, GET /trends
- [x] Frontend lab table + Trends tab (recharts); 46-snippet fixture shared with Phase 5
- [x] Suite: 191 passed; frontend build passes

## Done (Phase 2 — safety, QR, reminders, emergency card, scan)
- [x] safety_service + 67-pair interaction dataset + allergy map; severe blocks save/issue without ack+reason
- [x] QR verification (token+HMAC, PDF embed, public /verify page, revoke)
- [x] notifications inbox + scheduler (asyncio in lifespan) + optional SMTP; bell in Layout
- [x] emergency card PDF + revocable public page + rotate/revoke; UI in Profile
- [x] POST /prescriptions/scan draft-only (rules first, LLM fallback validated)
- [x] Suite: 209 passed; frontend build passes
## Done (Phase 3 — consent + audit)
- [x] access_requests + access_grants collections; request/approve/deny/revoke flow with expiry
- [x] Grants enforced on every doctor path (patients, reports, labs, trends, history, Rx create); author-Rx kept
- [x] Audit log on PHI reads/writes + grant events; GET /audit/me + admin filtered view
- [x] Frontend: Access & Privacy page, doctor Request-access flow, admin audit table
- [x] Suite: 224 passed; frontend build passes

## Done (Phase 4 — AI features)
- [x] Source quotes (prompt + normalized/fuzzy verify, verified/unverified badges, text highlighting)
- [x] Report chat (grounded retrieval, refusals, history cap, rate limit, offline fallback, panel UI)
- [x] Language param (8 languages) + Listen button (SpeechSynthesis)
- [x] Background upload mode (SYNC_UPLOAD flag, polling with backoff)
- [x] Repair retry + token-usage logs + per-feature model overrides
- [x] Suite: 238 passed; frontend build passes

## Done (Phase 5 — evaluation chapter)
- [x] Seeded generator (30 reports) + 46 lab-fixture reuses = 76 synthetic records
- [x] run_eval.py: rule-based vs SciSpacy-if-present vs mock LLM; P/R/F1, negation, labs, faithfulness
- [x] docs/evaluation/results.md + results.csv + 2 charts + METHODOLOGY.md
- [x] Suite: 239 passed

## Done (Phase 6 — polish)
- [x] Dockerfiles (AI optional build arg) + compose (mongo/backend/frontend, healthchecks, volumes); no Docker binary here so `compose up` is a MANUAL check
- [x] GitHub Actions (backend pytest+mongo service; frontend vitest+build)
- [x] Auth hardening: refresh rotation, logout revoke, reset via emailed/logged token, 5-fail lockout
- [x] Frontend: Vitest+RTL (Login, lab table, access flow: 7 tests) + Playwright demo spec (needs browsers: manual)
- [x] UI: dark mode toggle, focus styles, reduced-motion, responsive tweak, aria labels
- [x] README rewrite + USER_GUIDE.md demo script
- [x] Suite: 249 passed; frontend build + 7 vitest pass

## Remaining
- Nothing scheduled. Manual checks below.

## Manual steps for the user (must do yourself)
1. `git` and `docker` are unavailable here — commit everything on a branch and run `docker compose up --build` yourself (see README).
2. Rotate/set `SECRET_KEY`; create the first admin via the seed command.
3. Set `OMNIROUTE_*` for live AI (offline fallbacks work without it).
4. Set `SMTP_*` to enable reminder/reset emails (else in-app/log only).
5. `npx playwright install chromium` then run the e2e demo test with both servers up.
6. Never commit `backend/.env`.
- Phase 5 evaluation chapter
- Phase 6 polish (docker, CI, auth hardening, frontend tests, README)

## Next command
- Backend: `cd backend && .venv\Scripts\python -m pytest tests -q`
- Frontend: `cd frontend && npm run build`
- Seed first admin: `$env:ADMIN_EMAIL="you@example.com"; $env:ADMIN_PASSWORD="ChangeMe123"; .venv\Scripts\python scripts/seed_admin.py` (run from `backend/`)

## Manual steps for the user
1. `git` is not available in this environment — create branch + commit Phase 0 manually (see DECISIONS.md).
2. Rotate/set `SECRET_KEY`, create the first admin via the seed command, set SMTP later (Phase 2/6).
3. Never commit `backend/.env`.

## STEP 0 — Stabilize half-migrated frontend (2026-09-21)
- NOTE: `AGENTS.md` and `docs/agent/SPEC.md` do not exist in this workspace
  (searched whole tree excl. node_modules/.venv). Their working rules could
  not be followed; P1 scope is unknown. User directed: stop after STEP 0.
- Fix 1: `frontend/src/components/ui/index.js` — removed broken
  `export * from './ProgressMeter'` (no such file; `ProgressMeter` already
  re-exported from `./Avatar`). Barrel now resolves; verified with a temp
  vitest importing the barrel (all ui modules parse), temp file deleted.
- Fix 2: `frontend/src/index.css` — moved all `@fontsource @import`s above
  the `@tailwind` directives. `vite:css "@import must precede"` warnings:
  12 -> 0.
- Left untouched (need SPEC before changing): empty leftover dirs
  `src/components/Layout/`, `src/context/`, `src/hooks/`; legacy `App.css`
  vs Tailwind token mix; `>500kB` chunk advisory (accepted, Phase 1).
- Verified: `npm test` (contrast 34/34 + vitest 7/7) passes;
  `npm run build` passes with no CSS warnings.

## Exact next step
- Provide `AGENTS.md` + `docs/agent/SPEC.md` (with P1 scope and working
  rules), then run P1. Re-verify with: `cd frontend && npm test && npm run build`.
