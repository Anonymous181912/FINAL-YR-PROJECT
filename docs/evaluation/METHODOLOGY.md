# Evaluation Methodology (synthetic data only)

## Dataset
- `backend/evaluation/dataset/reports.jsonl`: 76 fully synthetic records —
  30 generated reports (seeded RNG, seed 20260919) + 46 lab-fixture reuses
  from `backend/tests/fixtures/lab_snippets.jsonl`.
- Generated reports combine 3–4 hand-labelled lab lines (flags computed by
  hand from the reference table; the generator asserts parser agreement at
  build time and fails loudly otherwise), 1–3 affirmed entity mentions from
  the extractor's own vocabularies, 0–1 negated mentions, 1–2 medications,
  and occasional out-of-vocabulary terms (`migraine`, `tuberculosis`,
  `wheezing`) that the rule-based extractor cannot know.
- Negations use documented patterns (`negative for`, `denies`, `no evidence
  of`, `without`, `ruled out`) plus bare `No X` probes that the pattern list
  does not cover — intentionally, to measure that limitation.
- Entity spans are exact (tracked while building the text). No real patient
  data anywhere.

## Systems compared
1. **rule-based**: `RuleBasedExtractor.extract` (the production path).
   Predicted spans are recovered by case-insensitive search (the extractor
   emits no offsets); its per-line dedup means repeats count once.
2. **SciSpacy**: evaluated only if `en_core_sci_sm` loads; otherwise reported
   as skipped. When present, all its spans map to `finding` (crude, disclosed).
3. **LLM (mock)**: deterministic stand-in — gold entities minus OOV terms
   plus one fabricated finding every 5th record. Runs with no API key.
   Set `EVAL_USE_REAL_LLM=1` (not implemented in this snapshot) for live runs.

## Metrics
- **Entity P/R/F1 per type** over {disease, symptom, finding, medication,
  measurement}: a true positive needs same type, text match
  (case-insensitive, substring-tolerant) and span overlap. `organ`
  predictions are excluded (anatomy is not scored).
- **Negation accuracy** on matched pairs (predicted `negated` vs gold).
- **Lab accuracy**: flag-match rate and value-match rate (1% tolerance) of
  `parse_lab_results` against hand labels.
- **Faithfulness**: share of mock-LLM `source_quote`s that `quote_verified`
  confirms in the report text.

## Limitations (read before quoting numbers)
- Lab gold labels derive from the same reference table the parser uses, so
  lab accuracy tests *implementation correctness* (regex/unit/range logic),
  not medical validity. The table itself is educational.
- `measurement`-type F1 is ~0 because the gold schema annotates lab values
  on the separate lab axis, not as entities, while the rule extractor emits
  `measurement` entities — a schema mismatch, not a model failure.
- The mock LLM is scripted, not a model; its scores show metric behaviour,
  not LLM quality. Real-LLM evaluation needs an API key and clinician review.
- 76 short synthetic records cannot represent real report diversity (OCR
  noise, handwriting, multi-morbidity). Treat all figures as engineering
  smoke signals, never clinical evidence.
