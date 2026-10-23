# Changelog

All notable changes, newest first. Format: conventional-commit style entries.

## [Unreleased] — Phase 6: Polish

### feat(auth): refresh rotation, reset, lockout
- Opaque refresh tokens (single-use rotation), logout revocation, emailed
  (or dev-logged) password reset with policy reuse + session revocation,
  5-fail 15-min lockout. Forgot/reset pages, refresh-aware auth state.

### feat(ops): docker + CI
- Backend/frontend Dockerfiles (AI optional), compose with healthchecks,
  nginx /api proxy; GitHub Actions for backend (mongo service) + frontend.

### feat(ui/tests): vitest suite, e2e spec, dark mode
- 7 Vitest + RTL tests (Login, lab table, access flow); Playwright demo spec;
  dark-mode toggle, focus/reduced-motion/responsive polish, aria labels.

### docs: README rewrite + USER_GUIDE
- Features, mermaid diagram, local/docker setup, env vars, API table,
  security model, eval link, limitations; 10-minute viva demo script.

## [Unreleased] — Phase 5: Evaluation chapter

### docs(eval): synthetic dataset + runner + results
- `backend/evaluation/`: seeded `make_dataset.py` (76 records, all synthetic),
  `run_eval.py` (rule-based vs SciSpacy-if-present vs mock LLM; P/R/F1,
  negation, lab accuracy, faithfulness), outputs in `docs/evaluation/`
  (results.md/csv, F1 + confusion charts, METHODOLOGY.md with limitations).

## [Unreleased] — Phase 4: AI features

### feat(ai): source quotes + verification + highlighting
- `source_quote`/`verified` on findings; normalized/fuzzy backend check;
  verified/unverified badges; verified spans highlighted in extracted text.

### feat(ai): grounded report chat with refusals
- `POST /reports/{id}/chat` (retrieval over chunks, diagnosis/treatment
  refusal, history cap, rate limit, offline fallback); chat panel UI.

### feat(ai): language + audio
- `language` param on interpret (8 languages, term-in-brackets);
  language selector + Listen button (browser speech synthesis).

### feat(uploads): background processing mode
- `SYNC_UPLOAD` flag (default true); async returns processing + background
  task; frontend polls with backoff.

### feat(llm): repair retry + usage logs + model overrides
- One JSON-repair retry; token usage logged; `LLM_MODEL_*` settings.

## [Unreleased] — Phase 3: Consent + audit

### feat(consent): request/approve/deny/revoke with expiry
- `access_requests` + `access_grants` collections; scopes reports/prescriptions/
  history; default 30-day expiry (max 365). Duplicate-pending and
  already-have-access return 409.

### feat(security): grant enforcement on every doctor path
- Patients list/get/put, reports list/get/labs/trends, history, Rx create all
  require active grants (reads 404, writes 403); authored Rxs stay accessible;
  admins bypass. Audit entries on all PHI reads/writes + grant events.

### feat(ui): Access & Privacy + request flow + admin audit
- Patient page (approve/deny/revoke/audit), doctor request-access card,
  admin audit table with filters, patient nav entry.

## [Unreleased] — Phase 2: Safety, QR, reminders, emergency card, scan

### feat(rx-safety): interaction + allergy checks with acknowledgement gate
- `safety_service.py` + 67-pair `drug_interactions.json` + allergy class map.
  `safety_warnings` on create/update responses and stored Rx; severe blocks
  saving/issuing without ack + reason. Warnings UI in Prescriptions.jsx.

### feat(rx-verify): QR verification with revocation
- `verification_token` + HMAC hash; QR embedded in PDF; public
  `GET /verify/prescription/{token}` (valid/revoked/modified + doctor +
  issue date); `/verify/:token` page; author-only revoke.

### feat(reminders): notifications + scheduler + optional SMTP
- `notifications` collection, `GET /notifications`, `PATCH .../read`,
  `POST /read-all`; asyncio scheduler in lifespan (follow-ups + course-end);
  bell with unread count in Layout. New `FRONTEND_URL`, `SMTP_*` settings.

### feat(emergency): card PDF + revocable public page
- `GET /patients/me/emergency-card` (PDF), rotate/revoke token endpoints,
  public `GET /verify/emergency/{token}` (3 fields only); Profile UI.

### feat(scan): draft-only handwritten prescription scan
- `POST /prescriptions/scan` (rules first, validated LLM fallback, never saves).

## [Unreleased] — Phase 1: Lab flagging + trends

### feat(labs): deterministic parser + reference table
- `reference_ranges.py` (20 tests, educational dataset) + `lab_parser.py`
  (printed range wins; unit normalization incl. mmol/L, g/L, lakh/cumm,
  /cumm counts; unknown unit → flag "unknown").
- `lab_results` computed at upload (additive field), `GET /reports/{id}/labs`,
  `GET /reports/trends?test=&patient_id=`.
- Frontend: lab table with badges + range source; Lab Trends tab (recharts
  line + reference band + test selector).
- Tests: 46-snippet `lab_snippets.jsonl` fixture (Phase 5 reuses it);
  endpoint tests for upload/labs/trends + access rules.

## [Unreleased] — Phase 0.5: Verify Phase 0

### tests(security): proof tests
- 14 tests: unverified 403s, rejected-old-token blocked, patient isolation,
  admin/query-param 422s, 11th-login 429.

## [Unreleased] — Phase 0: Security fixes

### feat(security): JSON registration with password policy
- `POST /api/v1/auth/register` now takes a JSON body (`RegisterRequest`:
  EmailStr, min-8 + letter + digit password, role patient/doctor, full_name,
  optional license_number). Query-param registration removed.
- Frontend Login gained a register mode posting JSON, with policy hint and
  optional license field for doctors.

### feat(security): doctor verification + admin role
- Doctor profiles: `is_verified`, `verification_status` (pending/approved/rejected).
- New `admin` role, `GET /api/v1/admin/pending-doctors`,
  `POST /api/v1/admin/doctors/{id}/approve|reject` (admin-only).
- `scripts/seed_admin.py` seeds the first admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
- New `get_current_verified_doctor` dependency enforced on all doctor paths
  touching patient data (patients, prescriptions, history, reports).
- Frontend: unverified doctors see a pending-approval screen; new Admin page;
  Profile shows verification status; `admin` added to valid roles/nav.

### fix(security): patient access + search injection
- `GET /patients/{id}`: patients read only own profile; verified doctors only;
  404 for unknown/forbidden (no existence leak).
- Patient search escapes input with `re.escape()` and caps length.

### fix: repo hygiene + OCR + config consistency
- `.gitignore` covers `.env`, `.venv/venv`, `.pytest_cache`, `__pycache__`,
  `node_modules`, `backend/uploads/*` (keeps `.gitkeep`).
- Deleted stray `@{id=4; result=}` and redundant `backend/test_ocr_pipeline.py`.
- Fixed `OCRService._get_reader` (`self._reader` AttributeError).
- Removed `dcm` from default `allowed_extensions` (matches `.env.example`).

### feat(security): rate limiting
- slowapi on register, login (10/min) and report upload (20/min); handler wired
  in `main.py`. New `RATE_LIMIT_*` vars in `backend/.env.example`.
- Disabled automatically in pytest via `tests/conftest.py`.

### tests
- Updated register tests to JSON + policy cases; added
  `tests/test_phase0_security.py` (16 tests: admin auth, verification gates,
  patient isolation, regex escaping, OCR fix, config, limiter wiring).
- Suite: 114 passed. Frontend `npm run build` passes.
