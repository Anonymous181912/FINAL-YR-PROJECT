# Decisions Log

Append-only record of significant assumptions and choices. Newest at the bottom.

## Phase 0.5 — Verify Phase 0 (2026-09-19)

- New `backend/tests/test_phase05_verify.py` (14 tests): unverified-doctor 403
  on 5 endpoints; rejected-doctor-with-old-token blocked (proves per-request
  DB verification — JWT carries no verification claim, asserted in a test);
  patient-A/B isolation on profile/reports/prescriptions/history;
  admin-role registration rejected (422); query-param registration 422;
  11th login in a minute returns 429 (limiter re-enabled + storage reset
  inside that test only; suite stays unthrottled via conftest).
- Suite: 128 passed.

## Phase 1 — Lab flagging + trends (2026-09-19)

- New `reference_ranges.py` (20 tests, sex-specific Hb/RBC/Hct/creatinine/HDL)
  labelled EDUCATIONAL, NOT CLINICAL ADVICE. Urea/BUN table range is the BUN
  interval (7–20); printed report ranges always win so explicit lab ranges are
  unaffected — documented in code.
- `lab_parser.py` is purely deterministic (no LLM). Printed range wins even
  when the unit looks odd (value and printed range share printed units);
  missing/unknown/unusable unit with no printed range returns the table range
  for display but flag "unknown" — never guesses.
- `range_source`: "report" (printed), "table" (sex-matched or table has no sex
  split), "default_adult" (gender unknown + sex-split test). Paediatric ranges
  out of scope (adult table; `age_years` plumbed for future use).
- `lab_results` added optionally to Report model/schema/response (backward
  compatible; old docs default None). Computed at upload; failures never break
  uploads. Upload response now includes `lab_results`.
- Trends route is `GET /reports/trends` (spec) registered BEFORE `/{report_id}`
  so "trends" isn't mistaken for an id. <2 points returns 200 with empty
  points (never an error). Doctors must pass patient_id (400 otherwise);
  patients always see own data. Canonical patient resolution copied from the
  history service (no second ID scheme).
- Frontend: lab table with Low/Normal/High/Unknown badges + range source in
  report detail and post-upload card; "Lab Trends" tab in Reports with test
  selector, recharts line + shaded reference band, "need 2 reports" message.
  recharts added (bundle warning accepted; code-split later if needed).
- Fixtures: `backend/tests/fixtures/lab_snippets.jsonl` (46 cases incl. OCR
  noise, conversions, missing/unknown units, multi-line) reused by Phase 5.
- Suite: 191 passed; `npm run build` passes.

## Phase 2 — Safety, QR, reminders, emergency card, scan (2026-09-19)

- Interaction dataset (67 pairs: 34 severe / 27 moderate / 6 minor) + allergy
  class map labelled EDUCATIONAL, NOT CLINICAL ADVICE. Matching is
  whole-word/substring-based (over-warning preferred to under-warning for a
  teaching tool). Allergy clashes are always severe; duplicate therapy is
  moderate. Severe blocks create AND issuing (status→issued) unless
  acknowledge_warnings=true with a non-empty reason; drafts still save with
  warnings visible. `safety_warnings` stored on the Rx and returned always.
- Verification HMAC covers clinical content only (patient/doctor/date/items/
  notes/advice/follow-up), computed pre-create in one DB call; verify returns
  valid/revoked/modified + doctor name + issue date only. PDF embeds QR to
  FRONTEND_URL/verify/{token} (new setting). Doctors revoke via
  POST /prescriptions/{id}/revoke (author only).
- Notifications collection with dedupe_key (unique sparse) so the scheduler
  never spams; asyncio task in lifespan (hourly default, first cycle ~60s
  after boot); SMTP optional (unset = in-app only). Bell in sidebar with
  unread count + dropdown + mark-read.
- Emergency token lives on the patient profile (None = revoked); card PDF has
  only blood group/allergies/contact + QR; public page returns only those
  fields. Rotate + revoke endpoints; UI in Profile.
- Scan is draft-only, never saves; LLM fallback only when rules find nothing
  and a key is configured, validated with PrescriptionItem (uses existing
  `_post`, no new LLM plumbing).
- Test-helper note: mock-Rx factories needed the new response fields;
  `verify_token` is sync (router calls it without await).
- Suite: 209 passed; `npm run build` passes.

## Phase 3 — Consent + audit (2026-09-19)

- Two collections per spec: access_requests (pending/approved/denied/cancelled)
  + access_grants (active/revoked/expired, expires_at, scope subset of
  reports/prescriptions/history, default 30d, max 365d). Expiry is time-based;
  encountered-expired grants are flipped to "expired" on read (no cron needed).
- Enforcement map (all verified-doctor paths + grant): patients list (only
  granted ids; $or on patient_id/user_id), patients get/put (grant, 404),
  reports list (doctor needs patient_id + grant; no id -> []), reports
  get/labs (grant on report.patient_id, 404), trends (grant, 404), history
  doctor endpoint (grant scope history, 404), Rx create (grant scope
  prescriptions, 403 with "request access" message). Rx get/update/delete/pdf
  stay author-scoped (doctors keep authored Rxs). Admins bypass grants.
- Reads -> 404 (no existence leak); writes -> 403 (actionable). Unverified
  doctors still 403 first (verification precedes grants).
- Audit on every PHI read/write (incl. patient self-reads) + grant events,
  with ip/user-agent best-effort; never raises. GET /audit/me (patient),
  GET /audit/ admin-only with actor/action/patient/resource filters.
- Test strategy: conftest allow-stubs the 5 grant helpers (pre-existing tests
  predate consent); Phase-3 tests re-patch with deny cases, unit-test the
  helper (expired/revoked/scope/404), and cover the full request flow +
  wrong-patient negatives + audit writes. Real helper functions captured at
  test-module import to dodge the stub.
- Frontend: patient Access & Privacy page (pending/approve-with-expiry/deny,
  active grants + revoke, audit table); doctor Patients page request-access
  card + outgoing list (directory already grant-filtered server-side); admin
  audit table with filters; patient nav gains Access & Privacy.
- Suite: 224 passed; `npm run build` passes.

## Phase 4 — AI features (2026-09-19)

- Quotes: prompt demands VERBATIM source_quote per finding; backend
  normalized-substring + token-overlap(>=0.8)/char-fuzzy(>=0.9) check, else
  verified=false + "unverified" badge; frontend highlights verified spans
  with <mark>. No silent grounding claims.
- Chat: chunking + BM25 when rank_bm25 installed else keyword overlap;
  diagnosis/treatment regex refusal; top-3 chunks; history capped to 6 and
  never stored; 30/min limit; offline extractive fallback so the feature (and
  tests) work without a key. Doctor chat needs an active grant; reads audited.
- Language: interpret?language= (en/hi/mr/ta/te/bn/es/fr, 400 otherwise);
  patient-facing text translated with English term kept in brackets; finding
  titles stay English; response carries language. Listen via SpeechSynthesis.
- Background: SYNC_UPLOAD=true default (old path untouched, tests pass);
  false -> 201 processing + BackgroundTasks pipeline (shared update_processing
  repo method); frontend polls with backoff and refreshes.
- Robustness: single repair retry on JSON/validation failure; token usage
  logged (never content); LLMService(model=...) override via
  LLM_MODEL_INTERPRET/LLM_MODEL_CHAT.
- Suite: 238 passed; `npm run build` passes.

## Phase 5 — Evaluation chapter (2026-09-19)

- Generator is seeded (20260919) and asserts parser agreement with
  hand-computed lab flags at build time; newline-joined sentences (spaces
  broke per-line ranges); duplicate-test reports matched as multisets.
- Lab gold derives from the same table -> tests implementation, not medical
  validity (stated in METHODOLOGY). measurement-F1 ~0 is a schema mismatch
  (labs scored on their own axis), documented. Mock LLM is scripted (drops
  OOV, fabricates 1 in 5) to show metric behaviour; real-LLM runs need a key
  + clinician review. SciSpacy skipped unless en_core_sci_sm loads.
- Results (synthetic): rule F1 disease .89/symptom .90/finding 1.0/
  medication 1.0; negation .76 (bare "No X" probes fail by design);
  lab flag/value 1.0; faithfulness .95 (fabrications caught).
- matplotlib added to requirements (needed by run_eval + its test).
- Suite: 239 passed.

## Phase 6 — Polish (2026-09-19)

- Auth: refresh tokens are opaque (SHA-256 stored, single-use rotation);
  logout revokes; reset tokens 60-min single-use, always-200 forgot endpoint,
  dev logs the link when SMTP unset; lockout in User doc (5 fails -> 15 min,
  403 while locked, success resets); reset also revokes all sessions.
  Login mock helper needed lockout fields (AsyncMock comparison TypeError).
  `reset@local.test` rejected by email-validator (reserved TLD) ->
  `reset@example.com` used for policy reuse.
- Docker: backend slim image with INSTALL_AI build arg (default off);
  frontend nginx build proxying /api; compose with healthchecks + volumes.
  No Docker binary here -> first `compose up` is a manual check (README +
  PROGRESS say so).
- CI: backend job with mongo:7 service; frontend job runs vitest + build
  (no eslint gate — eslint isn't installed).
- Frontend tests: vitest 2 (vite 5 peer compat), 7 tests green; Playwright
  spec written but browsers can't download here -> manual
  (`npx playwright install chromium`).
- UI: dark mode = CSS var overrides under [data-theme], persisted, OS-aware
  default; focus-visible outlines; reduced-motion; small-screen grid tweak.
- README rewritten (features, mermaid, setup, env, API table, security,
  eval, limitations); USER_GUIDE.md is a 10-minute viva demo script.
- Verified: 249 backend tests, 7 vitest, build green, all Phase 6 artefacts
  present, settings <-> .env.example complete (OMNIROUTE_* via aliases),
  no secret-looking lines in examples, .env git-ignored.
- Suite: 249 passed; `npm run build` + `npm test` pass.

## Longitudinal health trends (2026-10-28)

- Supersedes the Phase 1 `/reports/trends` route and Reports "Lab Trends" tab.
  New routes: `GET /trends/summary`, `GET /trends/{canonical_test}`, and
  patient-only `PATCH /trends/{canonical_test}/points/{report_id}`. Doctors must
  pass `patient_id`, need an active grant, and get 404 when it is missing.
- Stored lab values keep both standardized and original units; bounds are
  converted with the value. A missing/unusable unit is not coerced: it is
  excluded from the series and counted under `not_comparable`.
- Date priority is collection date printed on the report, then reported date,
  then upload date. The source is returned so the UI can explain fallbacks.
  Duplicate reports with the same normalized value and date collapse to one
  point instead of pretending there are two observations.
- Change is latest vs previous; stable means `abs(change_pct) < 5%`
  (`TREND_STABLE_THRESHOLD_PCT`). The template explanation compares first to
  latest, states range events, and always ends with the non-diagnosis
  disclaimer. No AI/variable prose is generated for trends.
- Patients can exclude a point or correct a transcription error for that trend
  only; corrections are audited and reparse scripts preserve them. Doctors are
  read-only. A single point is `insufficient_data` with no fabricated trend.
- Reparse/backfill is explicit (`scripts/reparse_labs.py`); demo data is
  idempotent (`scripts/seed_demo_trends.py`). Existing reports are never
  silently rewritten during unrelated reads.
- Suite: 298 passed, 1 unrelated evaluation failure because `matplotlib` is
  absent on Python 3.13; frontend 24 vitest pass + build passes.

## Phase 0 — Security fixes (2026-09-19)

- **No git binary in this environment.** The task requires working on branch
  `feature/upgrade` with a commit per phase. `git` is not installed here, so
  all Phase 0 changes were made directly in the working tree without
  branching/committing. Manual step: create the branch and commit
  (`git checkout -b feature/upgrade && git add -A && git commit -m "feat(security): phase 0 hardening"`).
- **Register is JSON-only (breaking).** Old query-param `POST /auth/register?...`
  removed; new `RegisterRequest` body enforces EmailStr + password policy
  (min 8, ≥1 letter, ≥1 digit). Frontend Login now has a register mode posting
  JSON. Existing tests updated to JSON.
- **Admin role added; self-registration stays patient/doctor only.** Admins are
  seeded via `backend/scripts/seed_admin.py` from `ADMIN_EMAIL`/`ADMIN_PASSWORD`
  env vars. New settings added to `config.py` + `backend/.env.example` with
  empty safe defaults.
- **Doctor verification defaults:** `is_verified=false`,
  `verification_status=pending` on registration. `DoctorRepository.update_profile`
  strips verification fields so `/doctors/me` can never self-approve; only
  `POST /admin/doctors/{id}/approve|reject` changes them.
- **Patient-data gate (pre-consent):** every doctor read/write path touching
  patient data requires a verified doctor (`get_current_verified_doctor` or an
  inline verified check for mixed-role endpoints). Phase 3 will add
  per-patient consent grants on top; until then verified doctors retain broad
  access (documented in code).
- **GET /patients/{id}:** patients get only their own profile; doctors need
  verification; unknown and forbidden ids both return 404 to avoid leaking
  existence. Admins can read all.
- **Search hardening:** `search` capped at 100 chars (Query) and 50 chars +
  `re.escape()` before `$regex`.
- **`dcm` removed** from `allowed_extensions` default (was in config but not in
  `.env.example`; no DICOM handling exists). `uploads` keep `.gitkeep`;
  `.gitignore` now ignores `backend/uploads/*` except `.gitkeep`, plus
  `.pytest_cache`.
- **Stray files:** deleted `@{id=4; result=}` and `backend/test_ocr_pipeline.py`
  (redundant hardcoded-path script; OCR covered by `backend/tests/test_ocr.py`).
- **`ocr._get_reader` fix:** was returning non-existent `self._reader`
  (would raise AttributeError if called). Now lazily inits both engines and
  returns `{"paddle": ..., "easy": ...}`. Method is still unused by
  `extract_text()` (which has its own lazy init); kept for compatibility.
- **Rate limiting (slowapi):** `Limiter` in `app/core/rate_limit.py`, attached
  in `main.py` with `RateLimitExceeded` handler. Limits: register/login
  10/min, upload 20/min (chat later in Phase 4). Disabled in tests via
  `backend/tests/conftest.py` autouse fixture (shared `testclient` IP would
  otherwise flake the suite).
- **Test compatibility:** added conftest default verified-doctor stub for
  `DoctorRepository.get_by_user_id` so pre-existing doctor tests (which mock
  `get_current_user`) keep passing; negative tests re-patch with
  unverified/None. `test_profiles` mock helper extended with new doctor fields.
- **Frontend render tests deferred:** global rules ask for render tests with
  new UI, but no Vitest/RTL harness exists yet (scheduled Phase 6d). Phase 0
  verifies with `npm run build` only; this is recorded as a known gap.
