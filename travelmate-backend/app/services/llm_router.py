# app/services/llm_router.py
# ============================================================
#  LLM Router — Automatic Groq → Gemini fallback
#  All services call this instead of calling providers directly.
#
#  Priority chain:
#    1. Groq (llama3-70b) — primary, free
#    2. Groq (mixtral)    — secondary on rate-limit
#    3. Gemini Flash      — final fallback
# ============================================================

from app.services.llm_groq import chat_completion as groq_chat
from app.services.llm_gemini import chat_completion_gemini as gemini_chat
from app.core.logging import logger
from typing import List, Dict, Tuple


async def route_llm(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Tuple[str, str]:
    """
    Routes to the best available LLM.
    Returns (response_text, provider_name) so callers know which was used.
    """
    # ── Try Groq first ──────────────────────────────────────
    try:
        response = await groq_chat(messages, temperature, max_tokens)
        return response, "groq"

    except Exception as groq_error:
        logger.warning(f"[Router] Groq failed: {groq_error} — falling back to Gemini")

    # ── Gemini fallback ────────────────────────────────────
    try:
        response = await gemini_chat(messages, temperature, max_tokens)
        return response, "gemini"

    except Exception as gemini_error:
        logger.error(f"[Router] Gemini also failed: {gemini_error}")
        raise RuntimeError(
            "All LLM providers failed. Please check your API keys and network."
        )
