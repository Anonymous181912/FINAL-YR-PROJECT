"""Chat with your report (Phase 4b).

Extractive grounding: the report text is split into chunks, the top chunks
for the question are retrieved with keyword scoring, and the answer is built
ONLY from those chunks. Diagnosis/treatment questions are refused with a
pointer to the doctor. No conversation is stored server-side (the client may
pass back the last turns; only the last few are used).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("healthcare_system")

MAX_HISTORY_TURNS = 6
TOP_K_CHUNKS = 3

# Refuse: diagnosis or treatment advice (point to the doctor instead).
_DIAGNOSIS_PATTERNS = [
    r"\bdiagnos\w*",
    r"\bwhat (disease|illness|condition) do i have\b",
    r"\bdo i have (cancer|diabetes|anemia|anaemia|tumor|tumour|infection)\b",
    r"\bshould i take\b",
    r"\bwhat (medicine|medication|drug|treatment|dosage|dose) should\b",
    r"\bprescribe\b",
    r"\bhow (should|do) i treat\b",
    r"\bcure\b",
    r"\bcan i stop\b.*\b(medicine|medication|drug|tablet)\b",
]
_DIAGNOSIS_RE = [re.compile(p, re.IGNORECASE) for p in _DIAGNOSIS_PATTERNS]

_REFUSAL = (
    "I can't answer diagnosis or treatment questions — only your doctor can. "
    "I can explain what is written in this report instead. "
    "This is an explanation, not a diagnosis."
)

_ABSENT = (
    "That information is not in this report. I can only answer from what the "
    "report itself contains. This is an explanation, not a diagnosis."
)

_STOPWORDS = frozenset(
    "a an the and or but of in on at to for with is are was were be been "
    "it its this that these those i you he she we they what which who whom "
    "how why when where do does did can could should would will shall may "
    "might have has had not no yes if then than so as by from into over my "
    "your his her our their me him us them report test result results value "
    "show shows shown mean means does".split()
)


def is_medical_advice_question(question: str) -> bool:
    q = question or ""
    return any(rx.search(q) for rx in _DIAGNOSIS_RE)


def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """Split into ~sentence-bounded chunks for retrieval."""
    sentences = re.split(r"(?<=[.!?\n])\s+", (text or "").strip())
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if size + len(sent) > max_chars and current:
            chunks.append(" ".join(current))
            current, size = [], 0
        current.append(sent)
        size += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c.strip()]


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def retrieve_chunks(question: str, chunks: list[str], top_k: int = TOP_K_CHUNKS) -> list[str]:
    """Keyword-overlap retrieval (rank_bm25 when installed, else fallback)."""
    if not chunks:
        return []
    try:
        from rank_bm25 import BM25Okapi

        tokenized = [[w for w in re.findall(r"[a-z0-9]+", c.lower())] for c in chunks]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(list(_keywords(question)))
        ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
        return [c for c, s in ranked[:top_k] if s > 0]
    except ImportError:
        pass
    qkeys = _keywords(question)
    if not qkeys:
        return chunks[:top_k]
    scored = []
    for chunk in chunks:
        ckeys = _keywords(chunk)
        overlap = len(qkeys & ckeys)
        scored.append((chunk, overlap))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [c for c, s in scored[:top_k] if s > 0]


async def answer_question(
    question: str,
    extracted_text: str,
    history: list[dict] | None = None,
) -> dict:
    """Answer ONLY from the report. Returns {answer, grounded, refused}."""
    history = (history or [])[-MAX_HISTORY_TURNS:]
    _ = history  # capped context; currently used only for length policy
    if is_medical_advice_question(question):
        return {"answer": _REFUSAL, "grounded": False, "refused": True,
                "sources": []}
    chunks = chunk_text(extracted_text or "")
    top = retrieve_chunks(question or "", chunks)
    if not top:
        return {"answer": _ABSENT, "grounded": False, "refused": False,
                "sources": []}

    from app.core.config import settings

    if not settings.omni_route_api_key:
        # Offline fallback: extractive answer from the retrieved chunks.
        excerpt = " ".join(top)[:1200]
        return {"answer": (
            f"From your report: {excerpt} "
            "(Automatic excerpt — connect the AI service for a fuller explanation. "
            "This is an explanation, not a diagnosis.)"),
            "grounded": True, "refused": False, "sources": top}

    from app.reports.ai.llm import LLMService

    model = settings.llm_model_chat or None
    service = LLMService(model=model)
    context = "\n---\n".join(top)
    messages = service._build_messages(
        "You answer questions using ONLY the provided report excerpts. "
        "If the answer is not in the excerpts, say exactly: "
        "'That information is not in this report.' "
        "Never diagnose, never recommend treatment; for such questions tell the "
        "user to ask their doctor. End with: 'This is an explanation, not a diagnosis.'",
        f"REPORT EXCERPTS:\n{context}\n\nQUESTION: {question}\n\nAnswer briefly, only from the excerpts.",
    )
    try:
        data = await service._post("chat/completions", {
            "model": service.model, "messages": messages,
            "max_tokens": 512, "temperature": 0.2,
        })
        try:
            usage = data.get("usage") or {}
            logger.info("LLM chat usage: model=%s total=%s", service.model, usage.get("total_tokens"))
        except Exception:
            pass
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not answer:
            answer = _ABSENT
        return {"answer": answer, "grounded": True, "refused": False, "sources": top}
    except Exception as exc:
        logger.warning(f"Report chat failed, extractive fallback: {exc}")
        excerpt = " ".join(top)[:1200]
        return {"answer": (
            f"From your report: {excerpt} "
            "(Automatic excerpt — the AI service is unreachable right now. "
            "This is an explanation, not a diagnosis.)"),
            "grounded": True, "refused": False, "sources": top}
