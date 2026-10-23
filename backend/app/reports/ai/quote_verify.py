"""Source-quote verification (Phase 4a): check the LLM's VERBATIM quotes
against the extracted report text. Normalized substring match first, then a
fuzzy token-overlap fallback (>=0.8). Anything else -> verified=False and the
UI shows an 'unverified' badge (never silently presented as grounded)."""

from __future__ import annotations

import difflib
import re


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    # Unify common OCR/punctuation variants so trivial differences don't fail.
    for a, b in (("–", "-"), ("—", "-"), ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(a, b)
    return text


def quote_verified(quote: str | None, extracted_text: str, fuzzy_threshold: float = 0.8) -> bool:
    if not quote or not extracted_text:
        return False
    norm_quote = normalize(quote)
    if len(norm_quote) < 4:
        return False
    norm_text = normalize(extracted_text)
    if norm_quote in norm_text:
        return True
    # Fuzzy: best matching window of similar length via token overlap.
    quote_tokens = set(norm_quote.split())
    if not quote_tokens:
        return False
    words = norm_text.split()
    span = max(1, len(norm_quote.split()) + 2)
    best = 0.0
    for i in range(0, max(1, len(words) - span + 1)):
        window = set(words[i: i + span])
        overlap = len(quote_tokens & window) / len(quote_tokens)
        if overlap > best:
            best = overlap
            if best >= 1.0:
                break
    if best >= fuzzy_threshold:
        return True
    # Character-level fallback for short quotes with OCR noise.
    best_ratio = 0.0
    qlen = len(norm_quote)
    step = max(1, qlen // 4)
    for i in range(0, max(1, len(norm_text) - qlen + 1), step):
        ratio = difflib.SequenceMatcher(None, norm_quote, norm_text[i: i + qlen]).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            if best_ratio >= 0.9:
                break
    return best_ratio >= 0.9


def verify_findings(findings: list, extracted_text: str) -> list:
    """Set .verified on each finding in place; returns the list."""
    for finding in findings:
        quote = getattr(finding, "source_quote", None)
        try:
            finding.verified = quote_verified(quote, extracted_text or "")
        except Exception:
            finding.verified = False
    return findings
