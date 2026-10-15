"""Checks the ADK glue end to end with a scripted model instead of Gemini."""

import asyncio

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.agents.list_parser import GeminiListParser
from app.models.schemas import ParsedList

CANNED = ParsedList.model_validate(
    {
        "items": [
            {"canonical_name": "milk", "original_text": "paal 1 litre", "quantity": 1, "unit": "l", "category": "dairy"}
        ],
        "detected_language": "ta",
    }
)


class ScriptedLlm(BaseLlm):
    model: str = "scripted"
    seen: list = []

    async def generate_content_async(self, llm_request, stream=False):
        self.seen.append(llm_request)
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text=CANNED.model_dump_json())])
        )


def test_list_parser_runs_through_adk():
    parser = GeminiListParser(["milk", "tomato"])
    llm = ScriptedLlm()
    parser.agent.model = llm

    result = asyncio.run(parser.parse("paal 1 litre", b"\x89PNG", "image/png"))

    assert result == CANNED
    request = llm.seen[0]
    sent = request.contents[-1].parts
    assert any(p.text == "paal 1 litre" for p in sent)
    assert any(p.inline_data and p.inline_data.mime_type == "image/png" for p in sent)
    assert "milk, tomato" in request.config.system_instruction
