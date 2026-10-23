import httpx
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from app.schemas.ai_interpretation import LLMInterpretationResponse

logger = logging.getLogger("healthcare_system")

class LLMServiceError(Exception):
    pass


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


class LLMService:
    """
    OpenAI-compatible LLM client (OmniRoute, Groq, etc.).
    Configuration is loaded from environment variables / settings.
    """

    def __init__(self, model: str | None = None):
        self.api_key = settings.omni_route_api_key
        self.base_url = settings.omni_route_base_url
        # Phase 4e: per-feature model override (falls back to default model).
        self.model = model or settings.omni_route_model
        self.timeout = settings.omni_route_timeout
        self.max_tokens = settings.omni_route_max_tokens

        if not self.api_key:
            raise LLMServiceError("OMNIROUTE_API_KEY is not configured")

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

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async def interpret_report(self, structured_medical_data: dict, language: str = "en") -> LLMInterpretationResponse:
        language = (language or "en").lower()
        lang_instruction = (
            "Write the patient-facing fields (summary, key finding explanations, "
            "measurement explanations, medical-term explanations, limitations) in English."
            if language in ("en", "english")
            else f"Write the patient-facing fields (summary, key finding explanations, "
                 f"measurement explanations, medical-term explanations, limitations) in language code '{language}'. "
                 f"Always keep the original English medical term first in brackets, e.g. 'हीमोग्लोबिन (Hemoglobin)'. "
                 f"The finding titles themselves stay in English."
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
            f"{lang_instruction}\n\n"
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
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        try:
            data = await self._post("chat/completions", payload)
            # Phase 4e: log token usage for cost tracking (never the content).
            try:
                usage = data.get("usage") or {}
                logger.info(
                    "LLM interpret usage: model=%s prompt=%s completion=%s total=%s",
                    self.model, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens"),
                )
            except Exception:
                pass
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                raise LLMServiceError("Empty response from LLM provider")

            cleaned_content = _clean_json_content(content)
            try:
                parsed = json.loads(cleaned_content)
                result = LLMInterpretationResponse(**parsed)
                result.language = language
                return result
            except (json.JSONDecodeError, ValueError) as first_exc:
                # Phase 4e: one repair retry with the error spelled out.
                logger.warning(f"LLM JSON validation failed, retrying with repair prompt: {first_exc}")
                repair_messages = self._build_messages(
                    system_prompt,
                    "Your previous reply was not valid JSON for the required schema. "
                    f"Error: {str(first_exc)[:500]} "
                    "Reply with ONLY a corrected valid JSON object matching the schema, no other text.",
                )
                repair_payload = {**payload, "messages": repair_messages, "temperature": 0.1}
                repair_data = await self._post("chat/completions", repair_payload)
                repair_content = repair_data.get("choices", [{}])[0].get("message", {}).get("content")
                if not repair_content:
                    raise LLMServiceError("Empty response from LLM provider on repair retry")
                try:
                    repaired = LLMInterpretationResponse(**json.loads(_clean_json_content(repair_content)))
                    repaired.language = language
                    return repaired
                except (json.JSONDecodeError, ValueError) as exc:
                    raise LLMServiceError("Invalid JSON returned by LLM provider") from exc

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            detail_msg = None
            try:
                err_json = exc.response.json()
                detail_msg = err_json.get("error", {}).get("message")
            except Exception:
                detail_msg = exc.response.text[:200]

            logger.error(
                f"LLM API error (status {status_code}, model {self.model}): {detail_msg or 'Request failed'}"
            )
            raise LLMServiceError(
                f"LLM provider error ({status_code}): {detail_msg or 'Request failed'}"
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse LLM JSON response: {exc}")
            raise LLMServiceError("Invalid JSON returned by LLM provider") from exc
        except LLMServiceError:
            raise
        except Exception as exc:
            logger.error(f"LLM request failed: {exc}")
            raise LLMServiceError("LLM request failed") from exc

    async def generate_prescription_summary(self, prescription_data: dict) -> str:
        system_prompt = (
            "You are an assistant that creates patient-friendly summaries of prescriptions. "
            "DO NOT modify the doctor's instructions. "
            "Only summarize the given prescription in simple terms."
        )
        user_prompt = f"Summarize this prescription data:\n{json.dumps(prescription_data)}"
        payload = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "max_tokens": 1024,
            "temperature": 0.2,
        }

        try:
            data = await self._post("chat/completions", payload)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as exc:
            logger.error(f"Prescription summary generation failed: {exc}")
            return "Could not generate summary."