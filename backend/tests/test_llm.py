import os
import json
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_llm_service_interpret_report():
    os.environ["OMNIROUTE_API_KEY"] = "test_key"
    with patch("app.reports.ai.llm.settings") as mock_settings:
        mock_settings.omni_route_api_key = "test_key"
        mock_settings.omni_route_base_url = "https://api.omni-route.com/v1"
        mock_settings.omni_route_model = "qwen2.5-7b-instruct"
        mock_settings.omni_route_timeout = 60
        mock_settings.omni_route_max_tokens = 2048

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
