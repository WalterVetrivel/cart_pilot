"""Shared Gemini model selection for all agents.

ADK/google-genai read GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT,
GOOGLE_CLOUD_LOCATION and GOOGLE_API_KEY from the environment directly.
"""

from app.config import get_settings


def model_name() -> str:
    return get_settings().gemini_model
