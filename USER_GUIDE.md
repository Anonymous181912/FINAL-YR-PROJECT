# User Guide (non-technical) — how to start the app and demo it

This guide is for someone who does not code. You only need to follow steps;
a technical friend should do the one-time setup with you.

## What this app does (one paragraph)

Patients upload medical lab reports and get simple-language explanations,
flagged lab values, and trend charts. Doctors (after admin approval AND the
patient's permission) can view patient reports, write digital prescriptions
with safety checks, and set follow-ups. Nothing here is a diagnosis — every
AI answer says so, and all demo data is invented.

## Starting the app

**Option A — your friend already set it up:** open the web address they gave
you (for example `http://localhost:8080`) and skip to "Demo script".

**Option B — local setup (with a technical friend):**
1. Install Python 3.12, Node 20, and MongoDB; start MongoDB.
2. In `backend/`: create a virtual environment, install requirements, copy
   `.env.example` to `.env`, set a strong `SECRET_KEY`, run the tests once.
3. Create the first admin (set `ADMIN_EMAIL` and `ADMIN_PASSWORD`, then run
   the seed script — see README).
4. Start the backend (`uvicorn app.main:app --reload`) and the frontend
   (`npm install`, then `npm run dev`).
5. Open the frontend address and register a patient account.

## Demo script (for a viva — about 10 minutes)

1. **Register + login (1 min).** Register as a patient (password needs 8+
   characters with a letter and a digit). Log in. Point out the role portals.
2. **Upload a report (2 min).** Go to Medical Reports → upload a `.txt` file
   containing e.g. `Hemoglobin 9.5 g/dL` and `WBC 12,000 /cumm`. Show the
   lab table: red **High** / amber **Low** badges and the range source.
   Upload a second report with different values.
3. **Health Trends (2 min).** Open **Health Trends**, pick Hemoglobin: line
   chart with the shaded reference band, direction/range events, and a
   template explanation. Show **Correct** / **Exclude** on a report value.
   With one report it says there is not enough data. For a ready-made demo,
   run `python scripts/seed_demo_trends.py`, then sign in as
   `demo.trends@example.com` / `DemoTrends123!` (3 reports, 6 tests).
4. **AI interpretation (2 min).** Click Interpret → plain-language summary.
   Point at a finding's **Verified in report** badge and the highlighted
   quote in the text. Use the language selector + Listen button.
5. **Chat (1 min).** Ask "What was my hemoglobin?" (answered from the
   report), then "What disease do I have?" (politely declined).
6. **Doctor consent flow (2 min).** Register a doctor (pending screen shows).
   As admin, approve them. As the doctor, send an access request (Patients
   page, paste the patient ID). As the patient, open **Access & Privacy**,
   approve for 30 days, and show the audit entry. As the doctor, the patient
   now appears.
7. **Prescription safety + QR (1 min).** As the doctor, create a prescription
   with Warfarin + Aspirin → severe warning appears; acknowledge with a
   reason to save. Generate the PDF (QR inside), open the public verify link.
8. **Reminders + emergency card (1 min).** Set a follow-up date, show the
   bell icon; download the emergency card from the Profile page.
9. **Close with honesty (30 sec).** Open `docs/evaluation/results.md`:
   synthetic data, rule-based F1 ≈ 0.9, limitations listed. State clearly:
   prototype for learning, not medical advice.

## If something goes wrong during the demo

- "AI not configured": the OmniRoute key is missing — interpretation, chat
  detail answers, and scan fallback still work in offline/extractive mode;
  say so and move on.
- No patients visible to the doctor: access was not approved yet — approve it
  live in Access & Privacy (great viva moment).
- Login locked message: too many wrong passwords — wait 15 minutes or reset
  via "Forgot password".
