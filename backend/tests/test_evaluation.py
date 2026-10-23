"""Phase 5 test: evaluation runs offline and produces all artefacts."""

import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_evaluation_produces_artefacts():
    import sys

    sys.path.insert(0, os.path.join(REPO, "backend"))
    from evaluation.run_eval import main

    summary = main()

    assert summary["n_records"] >= 40
    assert summary["lab"]["flag_accuracy"] >= 0.85
    assert summary["lab"]["value_accuracy"] >= 0.85
    # Rule-based should be decent on in-vocabulary synthetic terms.
    rule_f1 = [summary["rule_rows"][t]["f1"] for t in ("disease", "symptom", "finding", "medication")]
    assert sum(rule_f1) / len(rule_f1) > 0.5
    assert 0.0 <= summary["faithfulness"] <= 1.0

    base = os.path.join(REPO, "docs", "evaluation")
    for rel in ("results.md", "results.csv", "METHODOLOGY.md",
                os.path.join("charts", "f1_by_type.png"),
                os.path.join("charts", "flag_confusion.png")):
        assert os.path.exists(os.path.join(base, rel)), rel
