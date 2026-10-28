import os
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch


def _settings_patch(mock_settings, *, model="qwen2.5-7b-instruct", fallback="", max_tokens=800):
    mock_settings.omni_route_api_key = "test_key"
    mock_settings.omni_route_base_url = "https://api.omni-route.com/v1"
    mock_settings.omni_route_model = "qwen2.5-7b-instruct"
    mock_settings.omni_route_timeout = 60
    mock_settings.omni_route_max_tokens = 2048
    mock_settings.llm_model = model
    mock_settings.llm_fallback_model = fallback
    mock_settings.llm_max_output_tokens = max_tokens


def _http_error(status_code, message, headers=None):
    request = httpx.Request("POST", "https://api.omni-route.com/v1/chat/completions")
    response = httpx.Response(
        status_code,
        request=request,
        json={"error": {"message": message}},
        headers=headers or {},
    )
    return httpx.HTTPStatusError("provider error", request=request, response=response)


_GOOD = {
    "summary": "Test explanation",
    "key_findings": [],
    "measurements": [],
    "medical_terms": [],
    "limitations": [],
    "safety_note": "This is an explanation of the supplied report and not a diagnosis.",
}


@pytest.mark.asyncio
async def test_llm_service_interpret_report():
    os.environ["OMNIROUTE_API_KEY"] = "test_key"
    with patch("app.reports.ai.llm.settings") as mock_settings:
        _settings_patch(mock_settings)

        from app.reports.ai.llm import LLMService
        service = LLMService()

        structured_response = {
            "summary": "Test explanation",
            "key_findings": [],
            "measurements": [],
            "medical_terms": [],
            "limitations": [],
            "safety_note": "This is an explanation of the supplied report and not a diagnosis.",
        }

        with patch.object(service, "_post", return_value={
            "choices": [{"message": {"content": json.dumps(structured_response)}}]
        }) as mock_post:
            result = await service.interpret_report({"findings": ["normal"]})
            assert result.summary == "Test explanation"
            mock_post.assert_called_once()
            payload = mock_post.call_args.args[1]
            assert payload["max_tokens"] == 800
            assert payload["model"] == "qwen2.5-7b-instruct"


@pytest.mark.asyncio
async def test_429_retries_with_retry_after_then_succeeds():
    with patch("app.reports.ai.llm.settings") as mock_settings:
        _settings_patch(mock_settings)
        from app.reports.ai.llm import LLMService

        service = LLMService()
        calls = {"n": 0}

        async def fake_post(self, endpoint, payload):
            calls["n"] += 1
            if calls["n"] == 1:
                raise _http_error(
                    429,
                    "Request too large: try again in 7.5s",
                    headers={"retry-after": "7.5"},
                )
            return {"choices": [{"message": {"content": json.dumps(_GOOD)}}], "usage": {}}

        with patch.object(LLMService, "_post", new=fake_post), \
             patch("app.reports.ai.llm.asyncio.sleep", new=AsyncMock()) as sleep:
            out = await service.interpret_report({"extracted_text": "Hb 14"})
            assert out.summary == "Test explanation"
            assert calls["n"] == 2
            # Wait must respect Retry-After (7.5s), not a fixed 2s backoff.
            sleep.assert_awaited_once_with(7.5)


@pytest.mark.asyncio
async def test_429_uses_fallback_model_after_primary_exhausted():
    with patch("app.reports.ai.llm.settings") as mock_settings:
        _settings_patch(mock_settings, model="primary-model", fallback="fallback-model")
        from app.reports.ai.llm import LLMService

        service = LLMService()
        models = []

        async def fake_post(self, endpoint, payload):
            models.append(payload["model"])
            if payload["model"] == "primary-model":
                raise _http_error(429, "rate limited", headers={"retry-after": "0"})
            return {"choices": [{"message": {"content": json.dumps(_GOOD)}}], "usage": {}}

        with patch.object(LLMService, "_post", new=fake_post), \
             patch("app.reports.ai.llm.asyncio.sleep", new=AsyncMock()):
            out = await service.interpret_report({"extracted_text": "Hb 14"})
            assert out.summary == "Test explanation"
            assert models == ["primary-model", "primary-model", "primary-model", "fallback-model"]


@pytest.mark.asyncio
async def test_provider_error_is_sanitized():
    with patch("app.reports.ai.llm.settings") as mock_settings:
        _settings_patch(mock_settings, model="model", fallback="fallback")
        from app.reports.ai.llm import AI_BUSY_MESSAGE, LLMService, LLMServiceError

        service = LLMService()

        async def fake_post(self, endpoint, payload):
            raise _http_error(
                429,
                "Organization org_123 on_demand tier OTPM limit exceeded; see https://billing.example.test",
                headers={"retry-after": "0"},
            )

        with patch.object(LLMService, "_post", new=fake_post), \
             patch("app.reports.ai.llm.asyncio.sleep", new=AsyncMock()):
            try:
                await service.interpret_report({"extracted_text": "Hb 14"})
                raise AssertionError("should raise")
            except LLMServiceError as exc:
                assert exc.public_message == AI_BUSY_MESSAGE
                assert "org_123" not in exc.public_message
                assert "billing" not in exc.public_message
                assert "org_123" in str(exc)  # internal detail stays in logs/exception
