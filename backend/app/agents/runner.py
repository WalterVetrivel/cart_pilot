"""Run an ADK agent once and validate its structured output."""

import uuid

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

APP_NAME = "cartpilot"
_runners: dict[str, InMemoryRunner] = {}


def _runner(agent: LlmAgent) -> InMemoryRunner:
    if agent.name not in _runners:
        _runners[agent.name] = InMemoryRunner(agent=agent, app_name=APP_NAME)
    return _runners[agent.name]


async def run_structured[T: BaseModel](agent: LlmAgent, parts: list[types.Part], schema: type[T]) -> T:
    """One-shot call: fresh session, single user turn, final response parsed into `schema`."""
    runner = _runner(agent)
    user_id = f"call-{uuid.uuid4()}"
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=user_id)
    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=parts),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    finally:
        await runner.session_service.delete_session(app_name=APP_NAME, user_id=user_id, session_id=session.id)
    if not final_text:
        raise RuntimeError(f"{agent.name} returned no output")
    return schema.model_validate_json(final_text)
