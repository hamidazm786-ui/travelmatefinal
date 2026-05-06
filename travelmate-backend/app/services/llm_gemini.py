# app/services/llm_gemini.py
# ============================================================
#  Google Gemini Service — Fallback LLM
#  Activated automatically when Groq fails or is unavailable.
# ============================================================

import google.generativeai as genai
from app.core.config import get_settings
from app.core.logging import logger
from typing import List, Dict, Optional

settings = get_settings()

_gemini_model = None


def get_gemini_model():
    global _gemini_model
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    if _gemini_model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel(settings.gemini_model)
    return _gemini_model


def _build_gemini_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Gemini doesn't use the same roles format as OpenAI.
    We flatten the conversation into a single prompt string.
    """
    parts = []
    for msg in messages:
        role = msg["role"].upper()
        if role == "SYSTEM":
            parts.append(f"[SYSTEM INSTRUCTIONS]\n{msg['content']}\n")
        elif role == "USER":
            parts.append(f"[USER]\n{msg['content']}\n")
        elif role == "ASSISTANT":
            parts.append(f"[ASSISTANT]\n{msg['content']}\n")
    parts.append("[ASSISTANT]\n")  # cue the model to respond
    return "\n".join(parts)


async def chat_completion_gemini(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """
    Fallback chat completion via Google Gemini.
    Called automatically by llm_router when Groq fails.
    """
    model = get_gemini_model()
    prompt = _build_gemini_prompt(messages)

    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    try:
        logger.info(f"[Gemini] Calling model={settings.gemini_model}")
        response = model.generate_content(prompt, generation_config=generation_config)
        content = response.text
        logger.info(f"[Gemini] Success — {len(content)} chars returned")
        return content

    except Exception as e:
        logger.error(f"[Gemini] Error: {e}")
        raise
