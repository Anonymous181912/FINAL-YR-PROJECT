import asyncio
import httpx
import json
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from app.schemas.ai_interpretation import LLMInterpretationResponse

logger = logging.getLogger("healthcare_system")

AI_BUSY_MESSAGE = "The AI service is busy, please try again in a minute."
AI_INVALID_MESSAGE = "The AI service returned an invalid response. Please try again."

_RETRY_IN_MESSAGE_RE = re.compile(r"try again in\s+([\d.]+)\s*(ms|s|m)?", re.IGNORECASE)


class LLMServiceError(Exception):
    """Internal LLM failure with a safe message for API clients."""

    def __init__(self, message: str, public_message: str | None = None):
        super().__init__(message)
        self.public_message = public_message or message


def _clean_json_content(content: str) -> str:
    """Strip markdown code fences if present around JSON response."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    """Best-effort Retry-After: header first, then provider text, then backoff."""
    headers = getattr(response, "headers", {}) or {}
    raw_header = headers.get("retry-after") or headers.get("Retry-After")
    if raw_header:
        try:
            return max(0.0, float(raw_header))
        except (TypeError, ValueError):
            try:
                when = parsedate_to_datetime(raw_header)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass

    try:
        message = (response.json().get("error") or {}).get("message") or ""
    except Exception:
        message = getattr(response, "text", "") or ""
    match = _RETRY_IN_MESSAGE_RE.search(message)
    if match:
        try:
            amount = float(match.group(1))
            unit = (match.group(2) or "s").lower()
            if unit == "ms":
                amount /= 1000.0
            elif unit == "m":
                amount *= 60.0
            return max(0.0, amount)
        except (TypeError, ValueError):
            pass
    return float(min(2 ** attempt, 10))


def _provider_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        return (exc.response.json().get("error") or {}).get("message") or exc.response.text[:200]
    except Exception:
        return exc.response.text[:200] if exc.response.text else "Request failed"


class LLMService:
    """
    OpenAI-compatible LLM client (OmniRoute, Groq, etc.).
    Configuration is loaded from environment variables / settings.
    """

    def __init__(self, model: str | None = None):
        self.api_key = settings.omni_route_api_key
        self.base_url = settings.omni_route_base_url
        # Phase 4e: per-feature model override (falls back to default model).
        configured_model = getattr(settings, "llm_model", "")
        configured_model = configured_model.strip() if isinstance(configured_model, str) else ""
        self.model = model or configured_model or settings.omni_route_model

        fallback_model = getattr(settings, "llm_fallback_model", "")
        fallback_model = fallback_model.strip() if isinstance(fallback_model, str) else ""
        self.fallback_model = fallback_model or None
        if self.fallback_model and self.fallback_model == self.model:
            self.fallback_model = None

        max_tokens = getattr(settings, "llm_max_output_tokens", 0)
        self.max_tokens = (
            max_tokens
            if isinstance(max_tokens, int) and max_tokens > 0
            else settings.omni_route_max_tokens
        )
        self.timeout = settings.omni_route_timeout

        if not self.api_key:
            raise LLMServiceError(
                "OMNIROUTE_API_KEY is not configured",
                public_message="AI interpretation service is not configured. Please contact support.",
            )

    def _get_url(self, endpoint: str) -> str:
        base = self.base_url.rstrip("/")
        # Automatically normalize if base_url is set to domain root
        if "groq.com" in base and "api.groq.com" not in base:
            base = "https://api.groq.com/openai/v1"

        endpoint_clean = endpoint.lstrip("/")
        if base.endswith("/v1") or "/v1/" in base:
            return f"{base}/{endpoint_clean}"
        return f"{base}/v1/{endpoint_clean}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _post(self, endpoint: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = self._get_url(endpoint)

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            response = await http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _chat_completion(self, payload: dict, endpoint: str = "chat/completions") -> dict:
        """Call chat/completions with 429 retry/backoff and optional fallback model.

        Public errors never include provider IDs, billing links, or raw payloads.
        """
        models: list[str] = []
        for candidate in (self.model, self.fallback_model):
            if candidate and candidate not in models:
                models.append(candidate)

        last_exc: Exception | None = None
        for model_index, model in enumerate(models):
            has_fallback = model_index < len(models) - 1
            for attempt in range(3):
                try:
                    data = await self._post(endpoint, {**payload, "model": model})
                    try:
                        usage = data.get("usage") or {}
                        logger.info(
                            "LLM usage: model=%s prompt=%s completion=%s total=%s",
                            model,
                            usage.get("prompt_tokens"),
                            usage.get("completion_tokens"),
                            usage.get("total_tokens"),
                        )
                    except Exception:
                        pass
                    return data
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    status_code = exc.response.status_code
                    if status_code == 429 and attempt < 2:
                        delay = min(_retry_after_seconds(exc.response, attempt), 15.0)
                        logger.warning(
                            "LLM rate-limited (429) on model %s; retrying in %.1fs", model, delay
                        )
                        await asyncio.sleep(delay)
                        continue

                    detail = _provider_detail(exc)
                    logger.error(
                        "LLM API error (status %s, model %s): %s",
                        status_code,
                        model,
                        detail,
                    )
                    # Auth failures affect every model; everything else may work
                    # with the fallback model.
                    if has_fallback and status_code not in (401, 403):
                        logger.warning("Trying fallback model %s", models[model_index + 1])
                        break
                    raise LLMServiceError(
                        f"LLM provider error ({status_code}, model {model}): {detail}",
                        public_message=AI_BUSY_MESSAGE,
                    ) from exc
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_exc = exc
                    if has_fallback:
                        logger.warning("Model %s unreachable; trying fallback model", model)
                        break
                    raise LLMServiceError(
                        "LLM request failed after network retries",
                        public_message=AI_BUSY_MESSAGE,
                    ) from exc
                except Exception as exc:
                    last_exc = exc
                    if has_fallback:
                        logger.warning("Model %s failed; trying fallback model", model)
                        break
                    logger.error("LLM request failed: %s", exc)
                    raise LLMServiceError(
                        "LLM request failed",
                        public_message=AI_BUSY_MESSAGE,
                    ) from exc

        if last_exc is not None:
            raise LLMServiceError(
                f"LLM request failed: {last_exc}",
                public_message=AI_BUSY_MESSAGE,
            ) from last_exc
        raise LLMServiceError("LLM request failed", public_message=AI_BUSY_MESSAGE)

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async def interpret_report(self, structured_medical_data: dict, language: str = "en") -> LLMInterpretationResponse:
        language = (language or "en").lower()
        is_english = language in ("en", "english")
        lang_instruction = (
            "Write the patient-facing fields (summary, key finding explanations, "
            "measurement explanations, medical-term explanations, limitations) in English."
            if is_english
            else f"Write the patient-facing fields (summary, key finding explanations, "
                 f"measurement explanations, medical-term explanations, limitations) in language code '{language}'. "
                 f"Always keep the original English medical term first in brackets, e.g. 'हीमोग्लोबिन (Hemoglobin)'. "
                 f"The finding titles themselves stay in English."
        )
        # Keep responses small: large outputs are the main cause of provider
        # OTPM 429s. Non-English responses are shorter to stay within budget.
        brevity = (
            "Keep the summary under 80 words. Return at most 5 key findings, 8 measurements, "
            "5 medical terms, and 3 limitations. Keep every explanation to one short sentence."
            if is_english
            else "Keep the summary under 50 words. Return at most 3 key findings, 5 measurements, "
                 "3 medical terms, and 2 limitations. Keep every explanation to one short sentence."
        )
        system_prompt = (
            "You are a medical information interpreter for patients. "
            "Your role is to explain medical report findings in simple, clear language. "
            "DO NOT provide a diagnosis, treatment recommendations, or prescribe medication. "
            "DO NOT invent clinical facts. "
            "Explain what the findings mean, what normal ranges are, and when to consult a doctor. "
            "If information is uncertain or unclear, explicitly state that. "
            "Always return valid JSON matching the requested schema."
        )
        user_prompt = (
            "Please interpret the following structured medical report data for a patient:\n\n"
            f"{json.dumps(structured_medical_data, indent=2)}\n\n"
            f"{lang_instruction}\n"
            f"{brevity}\n\n"
            "Return a JSON object with the following schema:\n"
            "{\n"
            '  "summary": "brief patient-friendly summary",\n'
            '  "key_findings": [{"finding": "...", "explanation": "...", "severity": "...", "negated": false, '
            '"source_quote": "VERBATIM quote from the extracted report text supporting this finding (copy it exactly, do not paraphrase; empty string if none applies)"}],\n'
            '  "measurements": [{"name": "...", "value": "...", "unit": "...", "explanation": "..."}],\n'
            '  "medical_terms": [{"term": "...", "simple_explanation": "..."}],\n'
            '  "limitations": ["..."],\n'
            '  "safety_note": "This is an explanation of the supplied report and not a diagnosis."\n'
            "}"
        )
        payload = {
            "messages": self._build_messages(system_prompt, user_prompt),
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        try:
            data = await self._chat_completion(payload)
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                raise LLMServiceError(
                    "Empty response from LLM provider",
                    public_message=AI_INVALID_MESSAGE,
                )

            cleaned_content = _clean_json_content(content)
            try:
                parsed = json.loads(cleaned_content)
                result = LLMInterpretationResponse(**parsed)
                result.language = language
                return result
            except (json.JSONDecodeError, ValueError) as first_exc:
                # Phase 4e: one repair retry with the error spelled out.
                logger.warning("LLM JSON validation failed, retrying with repair prompt: %s", first_exc)
                repair_messages = self._build_messages(
                    system_prompt,
                    "Your previous reply was not valid JSON for the required schema. "
                    f"Error: {str(first_exc)[:500]} "
                    "Reply with ONLY a corrected valid JSON object matching the schema, no other text.",
                )
                repair_payload = {**payload, "messages": repair_messages, "temperature": 0.1}
                repair_data = await self._chat_completion(repair_payload)
                repair_content = repair_data.get("choices", [{}])[0].get("message", {}).get("content")
                if not repair_content:
                    raise LLMServiceError(
                        "Empty response from LLM provider on repair retry",
                        public_message=AI_INVALID_MESSAGE,
                    )
                try:
                    repaired = LLMInterpretationResponse(**json.loads(_clean_json_content(repair_content)))
                    repaired.language = language
                    return repaired
                except (json.JSONDecodeError, ValueError) as exc:
                    raise LLMServiceError(
                        "Invalid JSON returned by LLM provider",
                        public_message=AI_INVALID_MESSAGE,
                    ) from exc

        except LLMServiceError:
            raise
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", exc)
            raise LLMServiceError(
                "Invalid JSON returned by LLM provider",
                public_message=AI_INVALID_MESSAGE,
            ) from exc
        except Exception as exc:
            logger.error("LLM request failed: %s", exc)
            raise LLMServiceError("LLM request failed", public_message=AI_BUSY_MESSAGE) from exc

    async def generate_prescription_summary(self, prescription_data: dict) -> str:
        system_prompt = (
            "You are an assistant that creates patient-friendly summaries of prescriptions. "
            "DO NOT modify the doctor's instructions. "
            "Only summarize the given prescription in simple terms. "
            "Keep the summary under 80 words."
        )
        user_prompt = f"Summarize this prescription data:\n{json.dumps(prescription_data)}"
        payload = {
            "messages": self._build_messages(system_prompt, user_prompt),
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
        }

        try:
            data = await self._chat_completion(payload)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as exc:
            logger.error("Prescription summary generation failed: %s", exc)
            return "Could not generate summary."
