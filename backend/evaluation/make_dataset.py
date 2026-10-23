"""Synthetic evaluation dataset generator (Phase 5).

Deterministic (seeded RNG): 30 full synthetic reports (labs + entities +
negations) plus all cases from ``tests/fixtures/lab_snippets.jsonl`` reused
as lab-only records. ALL data is invented for methods evaluation — no real
patients. Run: ``python backend/evaluation/make_dataset.py`` (from repo root
or backend/). Output: ``backend/evaluation/dataset/reports.jsonl``.

Record schema:
{id, text, gender, age_years,
 entities: [{text, type, start, end, negated}],
 labs: [{canonical_name, value, flag}]}
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from app.reports.services.lab_parser import parse_lab_results  # noqa: E402

rng = random.Random(20260919)

# (line, canonical, value, flag, gender) — flags hand-computed from the
# reference table; the generator asserts parser agreement at build time.
MALE_LABS = [
    ("Hemoglobin 14.2 g/dL", "hemoglobin", 14.2, "normal"),
    ("Hemoglobin 10.1 g/dL", "hemoglobin", 10.1, "low"),
    ("WBC 12.4 x10^3/uL", "wbc", 12.4, "high"),
    ("Total Cholesterol 210 mg/dL", "total_cholesterol", 210.0, "high"),
    ("HDL 38 mg/dL", "hdl", 38.0, "low"),
    ("Creatinine 1.5 mg/dL", "creatinine", 1.5, "high"),
    ("Fasting Glucose 88 mg/dL", "fasting_glucose", 88.0, "normal"),
    ("TSH 2.1 mIU/L", "tsh", 2.1, "normal"),
    ("Sodium 138 mEq/L", "sodium", 138.0, "normal"),
    ("Potassium 5.4 mEq/L", "potassium", 5.4, "high"),
    ("ALT 30 U/L", "alt", 30.0, "normal"),
    ("Vitamin D 15 ng/mL", "vitamin_d", 15.0, "low"),
]
FEMALE_LABS = [
    ("Hemoglobin 11.0 g/dL", "hemoglobin", 11.0, "low"),
    ("HbA1c 5.2 %", "hba1c", 5.2, "normal"),
    ("Platelets 500 x10^3/uL", "platelets", 500.0, "high"),
    ("Hematocrit 38 %", "hematocrit", 38.0, "normal"),
    ("Creatinine 0.9 mg/dL", "creatinine", 0.9, "normal"),
    ("HDL 62 mg/dL", "hdl", 62.0, "normal"),
    ("Random Glucose 150 mg/dL", "random_glucose", 150.0, "high"),
    ("Triglycerides 120 mg/dL", "triglycerides", 120.0, "normal"),
    ("AST 25 U/L", "ast", 25.0, "normal"),
    ("RBC 4.6 million/uL", "rbc", 4.6, "normal"),
]
PRINTED_LABS = [
    ("Hemoglobin 9.0 g/dL (13.0 - 17.0)", "hemoglobin", 9.0, "low"),
    ("WBC 7.0 x10^3/uL (4.0 - 11.0)", "wbc", 7.0, "normal"),
]

# In-vocabulary terms (unambiguous across extractor dictionaries).
DISEASES = ["pneumonia", "diabetes", "hypertension", "asthma", "hepatitis",
            "anemia", "infection", "inflammation"]
SYMPTOMS = ["chest pain", "cough", "fever", "headache", "nausea", "fatigue",
            "dizziness", "vomiting", "shortness of breath"]
FINDINGS = ["enlarged heart", "fluid collection", "abnormal rhythm",
            "hypodensity", "hyperdensity", "enhancement", "stenosis",
            "stricture", "fibrosis", "calcification"]
MEDICATIONS = ["aspirin", "metformin", "amoxicillin", "ibuprofen",
               "paracetamol", "atorvastatin", "levothyroxine", "omeprazole"]
# Out-of-vocabulary terms (documented recall limits of the rule extractor).
OOV = [("migraine", "disease"), ("tuberculosis", "disease"), ("wheezing", "symptom")]

AFFIRMED_TEMPLATES = [
    "Findings show {t}.",
    "Patient reports {t}.",
    "{T} noted on examination.",
    "Mild {t} observed.",
    "History of {t}.",
]
# Covered by NEGATION_PATTERNS (~80%) vs bare "No X" limitation probes (~20%).
NEGATED_TEMPLATES = [
    "Negative for {t}.",
    "Patient denies {t}.",
    "No evidence of {t}.",
    "Without {t}.",
    "{T} ruled out.",
    "No {t}.",
]
MED_TEMPLATES = [
    "Currently on {t}.",
    "Prescribed {t}.",
    "Taking {t} regularly.",
]


def _add_sentence(parts, offsets, sentence, entities):
    start = sum(len(p) for p in parts)
    parts.append(sentence + "\n")
    return start


def build_report(rid, gender):
    parts: list[str] = []
    entities: list[dict] = []
    labs: list[dict] = []

    pool = MALE_LABS if gender == "male" else FEMALE_LABS
    for line, canon, value, flag in rng.sample(pool, 3):
        s = _add_sentence(parts, None, line, entities)
        labs.append({"canonical_name": canon, "value": value, "flag": flag,
                     "span": [s, s + len(line)]})
    if rng.random() < 0.4:
        line, canon, value, flag = rng.choice(PRINTED_LABS)
        s = _add_sentence(parts, None, line, entities)
        labs.append({"canonical_name": canon, "value": value, "flag": flag,
                     "span": [s, s + len(line)]})

    def mention(term, etype, negated, template):
        surface = term
        if "{T}" in template:
            surface = term.capitalize() if not term[0].isupper() else term
            sent = template.replace("{T}", surface).replace("{t}", term)
        else:
            sent = template.replace("{t}", term)
        s = _add_sentence(parts, None, sent, entities)
        idx = sent.lower().find(term.lower())
        entities.append({"text": sent[idx: idx + len(term)], "type": etype,
                         "start": s + idx, "end": s + idx + len(term),
                         "negated": negated})

    n_aff = rng.randint(1, 3)
    for term in rng.sample(DISEASES + SYMPTOMS + FINDINGS, n_aff):
        etype = ("disease" if term in DISEASES else
                 "symptom" if term in SYMPTOMS else "finding")
        mention(term, etype, False, rng.choice(AFFIRMED_TEMPLATES))
    if rng.random() < 0.75:
        term = rng.choice(DISEASES + SYMPTOMS)
        etype = "disease" if term in DISEASES else "symptom"
        mention(term, etype, True, rng.choice(NEGATED_TEMPLATES))
    for term in rng.sample(MEDICATIONS, rng.randint(1, 2)):
        mention(term, "medication", False, rng.choice(MED_TEMPLATES))
    if rng.random() < 0.25:
        term, etype = rng.choice(OOV)
        mention(term, etype, False, rng.choice(AFFIRMED_TEMPLATES))

    text = "".join(parts).strip()
    # Lab gold sanity: every hand label must appear among parser outputs
    # (multiset match — a report can mention the same test twice).
    parsed = parse_lab_results(text, gender=gender)
    remaining = list(parsed)
    for lab in labs:
        hit = None
        for p in remaining:
            if (p["canonical_name"] == lab["canonical_name"]
                    and p["flag"] == lab["flag"]
                    and abs(p["value"] - lab["value"]) < 0.01 * max(1, lab["value"])):
                hit = p
                break
        assert hit is not None, f"{rid}: gold {lab} not in parser output"
        remaining.remove(hit)
    return {"id": rid, "text": text, "gender": gender,
            "age_years": rng.randint(22, 78), "entities": entities,
            "labs": [{k: lab[k] for k in ("canonical_name", "value", "flag")}
                     for lab in labs]}


def main():
    out_dir = os.path.join(HERE, "dataset")
    os.makedirs(out_dir, exist_ok=True)
    records = []
    for i in range(30):
        gender = "male" if i % 2 == 0 else "female"
        records.append(build_report(f"syn-{i + 1:03d}", gender))
    # Reuse the Phase-1 lab fixtures as lab-only records.
    fixture = os.path.join(BACKEND, "tests", "fixtures", "lab_snippets.jsonl")
    with open(fixture, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            records.append({
                "id": f"lab-{case['id']}",
                "text": case["text"],
                "gender": case.get("gender"),
                "age_years": case.get("age_years"),
                "entities": [],
                "labs": [{"canonical_name": e["canonical_name"],
                          "value": e["value"], "flag": e["flag"]}
                         for e in case["expected"]],
            })
    # Span sanity.
    for rec in records:
        for ent in rec["entities"]:
            assert rec["text"][ent["start"]: ent["end"]] == ent["text"], rec["id"]
    out_path = os.path.join(out_dir, "reports.jsonl")
    with open(out_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
