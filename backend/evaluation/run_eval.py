"""Evaluation runner (Phase 5): rule-based vs SciSpacy (if installed) vs LLM
(mockable, runs without an API key).

Metrics: per-entity-type precision/recall/F1 (span overlap + type + text),
negation accuracy, lab parser accuracy, LLM faithfulness (% quotes verified).

Outputs (repo-root docs/evaluation/):
  results.md, results.csv, charts/f1_by_type.png, charts/flag_confusion.png
Run: ``python backend/evaluation/run_eval.py`` (cwd = backend/ or repo root).
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.reports.ai.rule_based_extractor import RuleBasedExtractor  # noqa: E402
from app.reports.services.lab_parser import parse_lab_results  # noqa: E402
from app.reports.ai.quote_verify import quote_verified  # noqa: E402

EVAL_TYPES = ("disease", "symptom", "finding", "medication", "measurement")
OUT_DIR = os.path.join(REPO, "docs", "evaluation")
CHART_DIR = os.path.join(OUT_DIR, "charts")


def load_dataset():
    path = os.path.join(HERE, "dataset", "reports.jsonl")
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def locate_spans(text, mention):
    """All case-insensitive occurrence spans of mention in text."""
    spans = []
    low, needle = text.lower(), mention.lower()
    start = 0
    while True:
        idx = low.find(needle, start)
        if idx < 0:
            break
        spans.append((idx, idx + len(mention)))
        start = idx + 1
    return spans


def spans_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def score_entities(records, predictions):
    """predictions: {record_id: [{text, type, negated, start, end}]}."""
    per_type = {t: {"tp": 0, "fp": 0, "fn": 0} for t in EVAL_TYPES}
    neg_correct, neg_total = 0, 0
    for rec in records:
        gold = [e for e in rec.get("entities", []) if e["type"] in EVAL_TYPES]
        preds = [p for p in predictions.get(rec["id"], []) if p.get("type") in EVAL_TYPES]
        matched_pred = set()
        for g in gold:
            gspan = (g["start"], g["end"])
            hit = None
            for i, p in enumerate(preds):
                if i in matched_pred:
                    continue
                if p.get("type") != g["type"]:
                    continue
                if (p.get("text", "").lower() != g["text"].lower()
                        and p.get("text", "").lower() not in g["text"].lower()
                        and g["text"].lower() not in p.get("text", "").lower()):
                    continue
                pspan = (p.get("start", -1), p.get("end", -1))
                if pspan[0] >= 0 and not spans_overlap(pspan, gspan):
                    continue
                hit = i
                break
            if hit is None:
                per_type[g["type"]]["fn"] += 1
            else:
                matched_pred.add(hit)
                per_type[g["type"]]["tp"] += 1
                neg_total += 1
                if bool(preds[hit].get("negated", False)) == bool(g.get("negated", False)):
                    neg_correct += 1
        for i, p in enumerate(preds):
            if i not in matched_pred:
                per_type[p["type"]]["fp"] += 1
    rows = {}
    for t, c in per_type.items():
        p = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
        r = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        rows[t] = {"precision": p, "recall": r, "f1": f1, **c}
    return rows, (neg_correct / neg_total if neg_total else 0.0, neg_correct, neg_total)


def rule_based_predictions(records):
    extractor = RuleBasedExtractor()
    out = {}
    for rec in records:
        preds = []
        try:
            entities = extractor.extract(rec["text"])
        except Exception:
            entities = []
        for ent in entities:
            etype = ent.get("type")
            if etype not in EVAL_TYPES:
                continue
            text = ent.get("text", "")
            spans = locate_spans(rec["text"], text) or [(-1, -1)]
            # Rule extractor dedupes repeats: one prediction, first span.
            preds.append({"text": text, "type": etype,
                          "negated": bool(ent.get("negated", False)),
                          "start": spans[0][0], "end": spans[0][1]})
        out[rec["id"]] = preds
    return out


def scispacy_predictions(records):
    """SciSpacy pipeline if installed (model en_core_sci_sm); else skipped."""
    try:
        import spacy  # noqa
        nlp = spacy.load("en_core_sci_sm")
    except Exception as exc:
        return None, f"skipped ({type(exc).__name__}: model/pipeline unavailable)"
    out = {}
    for rec in records:
        preds = []
        try:
            doc = nlp(rec["text"])
            for ent in doc.ents:
                preds.append({"text": ent.text, "type": "finding",
                              "negated": False,
                              "start": ent.start_char, "end": ent.end_char})
        except Exception:
            pass
        out[rec["id"]] = preds
    return out, "en_core_sci_sm (all spans mapped to 'finding')"


def mock_llm_predictions(records):
    """Deterministic stand-in: gold entities minus OOV terms plus one
    fabricated finding per 5th record (exercises precision + faithfulness)."""
    oov_terms = {"migraine", "tuberculosis", "wheezing"}
    out = {}
    quotes = {}
    for n, rec in enumerate(records):
        preds, qs = [], []
        for ent in rec.get("entities", []):
            if ent["text"].lower() in oov_terms:
                continue  # mock misses out-of-vocabulary terms
            preds.append({"text": ent["text"], "type": ent["type"],
                          "negated": ent.get("negated", False),
                          "start": ent["start"], "end": ent["end"]})
            qs.append(rec["text"][ent["start"]: ent["end"]])
        if n % 5 == 0 and rec.get("entities"):
            preds.append({"text": "cachexia", "type": "disease",
                          "negated": False, "start": -1, "end": -1})
            qs.append("severe cachexia with wasting")  # fabricated: unverifiable
        out[rec["id"]] = preds
        quotes[rec["id"]] = qs
    return out, quotes


def score_labs(records):
    total, flag_ok, value_ok = 0, 0, 0
    conf = {"low": {"low": 0, "normal": 0, "high": 0, "unknown": 0},
            "normal": {"low": 0, "normal": 0, "high": 0, "unknown": 0},
            "high": {"low": 0, "normal": 0, "high": 0, "unknown": 0}}
    for rec in records:
        gold_labs = rec.get("labs", [])
        if not gold_labs:
            continue
        parsed = parse_lab_results(rec["text"], gender=rec.get("gender"))
        remaining = list(parsed)
        for gold in gold_labs:
            total += 1
            hit = None
            for p in remaining:
                if p["canonical_name"] == gold["canonical_name"]:
                    hit = p
                    break
            if hit is None:
                continue  # missed entirely: flag wrong by definition
            remaining.remove(hit)
            if hit["flag"] == gold["flag"]:
                flag_ok += 1
            if abs(hit["value"] - gold["value"]) < 0.01 * max(1, gold["value"]):
                value_ok += 1
            if gold["flag"] in conf and hit["flag"] in conf[gold["flag"]]:
                conf[gold["flag"]][hit["flag"]] += 1
    return {
        "n": total,
        "flag_accuracy": flag_ok / total if total else 0.0,
        "value_accuracy": value_ok / total if total else 0.0,
        "confusion": conf,
    }


def score_faithfulness(records, quotes):
    total, ok = 0, 0
    for rec in records:
        for quote in quotes.get(rec["id"], []):
            total += 1
            if quote_verified(quote, rec["text"]):
                ok += 1
    return ok / total if total else 0.0, ok, total


def plot_f1(per_system_rows, path):
    systems = list(per_system_rows)
    types = list(EVAL_TYPES)
    x = range(len(types))
    width = 0.8 / max(1, len(systems))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, sys_name in enumerate(systems):
        vals = [per_system_rows[sys_name][t]["f1"] for t in types]
        ax.bar([p + i * width for p in x], vals, width=width, label=sys_name)
    ax.set_xticks([p + width * (len(systems) - 1) / 2 for p in x])
    ax.set_xticklabels(types, rotation=15)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("F1")
    ax.set_title("Entity extraction F1 by type (synthetic data)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_confusion(conf, path):
    labels = ["low", "normal", "high"]
    matrix = [[conf[g].get(p, 0) for p in labels] for g in labels]
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(matrix)
    ax.set_xticks(range(3), labels)
    ax.set_yticks(range(3), labels)
    ax.set_xlabel("Predicted flag")
    ax.set_ylabel("Gold flag")
    ax.set_title("Lab flag confusion matrix (rule parser)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, matrix[i][j], ha="center", va="center",
                    color="white" if matrix[i][j] > max(max(r) for r in matrix) / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)
    records = load_dataset()

    rule_preds = rule_based_predictions(records)
    rule_rows, (rule_neg, _, _) = score_entities(records, rule_preds)

    sci_preds, sci_note = scispacy_predictions(records)
    sci_rows = None
    if sci_preds is not None:
        sci_rows, _ = score_entities(records, sci_preds)

    mock_preds, mock_quotes = mock_llm_predictions(records)
    llm_rows, (llm_neg, _, _) = score_entities(records, mock_preds)
    faith, faith_ok, faith_n = score_faithfulness(records, mock_quotes)

    lab = score_labs(records)

    per_system = {"rule-based": rule_rows, "llm-mock": llm_rows}
    if sci_rows is not None:
        per_system["scispacy"] = sci_rows

    plot_f1(per_system, os.path.join(CHART_DIR, "f1_by_type.png"))
    plot_confusion(lab["confusion"], os.path.join(CHART_DIR, "flag_confusion.png"))

    csv_path = os.path.join(OUT_DIR, "results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["system", "metric", "type", "value"])
        for sys_name, rows in per_system.items():
            for t, m in rows.items():
                for metric in ("precision", "recall", "f1"):
                    writer.writerow([sys_name, metric, t, round(m[metric], 4)])
        writer.writerow(["rule-based", "negation_accuracy", "all", round(rule_neg, 4)])
        writer.writerow(["llm-mock", "negation_accuracy", "all", round(llm_neg, 4)])
        writer.writerow(["rule-based", "lab_flag_accuracy", "all", round(lab["flag_accuracy"], 4)])
        writer.writerow(["rule-based", "lab_value_accuracy", "all", round(lab["value_accuracy"], 4)])
        writer.writerow(["llm-mock", "faithfulness", "all", round(faith, 4)])

    def rowline(rows):
        return " | ".join(f"{t}: P={rows[t]['precision']:.2f} R={rows[t]['recall']:.2f} F1={rows[t]['f1']:.2f}"
                          for t in EVAL_TYPES)

    md_path = os.path.join(OUT_DIR, "results.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# Evaluation Results (synthetic data)\n\n")
        fh.write(f"Records: {len(records)} (30 generated + {len(records) - 30} lab fixture reuses). "
                 "All data synthetic. See METHODOLOGY.md.\n\n")
        fh.write("## Entity extraction (per type P/R/F1)\n\n")
        for sys_name, rows in per_system.items():
            fh.write(f"### {sys_name}\n\n{rowline(rows)}\n\n")
        fh.write(f"SciSpacy status: {sci_note}\n\n")
        fh.write("## Negation accuracy\n\n"
                 f"rule-based: {rule_neg:.3f} · llm-mock: {llm_neg:.3f}\n\n")
        fh.write("## Lab parser accuracy\n\n"
                 f"n={lab['n']} · flag accuracy={lab['flag_accuracy']:.3f} · "
                 f"value accuracy={lab['value_accuracy']:.3f}\n\n")
        fh.write("## LLM faithfulness\n\n"
                 f"llm-mock: {faith:.3f} ({faith_ok}/{faith_n} quotes verified)\n\n")
        fh.write("## Charts\n\n![F1 by type](charts/f1_by_type.png)\n\n"
                 "![Flag confusion](charts/flag_confusion.png)\n\n")
        fh.write("_Limitations: mock LLM is a scripted stand-in, not a model; "
                 "SciSpacy needs a downloaded biomedical model; lab gold labels "
                 "derive from the same reference table (tests implementation, "
                 "not medical validity)._ \n")

    print(f"Evaluated {len(records)} records.")
    print(f"rule-based negation accuracy: {rule_neg:.3f}")
    print(f"lab flag accuracy: {lab['flag_accuracy']:.3f}")
    print(f"llm-mock faithfulness: {faith:.3f} ({faith_ok}/{faith_n})")
    print(f"Wrote {md_path}, {csv_path}, charts/")
    return {
        "n_records": len(records),
        "rule_rows": rule_rows,
        "rule_negation": rule_neg,
        "lab": lab,
        "faithfulness": faith,
        "scispacy": sci_note,
    }


if __name__ == "__main__":
    main()
