"""LLM client supporting OpenAI and Gemini."""

from __future__ import annotations

from src.config import Settings, has_llm_credentials
from src.logging_setup import configure_logging

logger = configure_logging()


class LLMError(RuntimeError):
    """Raised when the configured LLM provider cannot generate a response."""


def generate_answer(prompt: str, settings: Settings) -> str:
    """Send a prompt to the configured provider and return the text response."""
    if not has_llm_credentials(settings):
        raise LLMError(
            "No valid API key found. Copy .env.example to .env and add "
            "GEMINI_API_KEY or OPENAI_API_KEY."
        )

    try:
        if settings.llm_provider == "openai":
            return _generate_openai(prompt, settings)
        if settings.llm_provider == "gemini":
            return _generate_gemini(prompt, settings)
        raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    except LLMError:
        raise
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise LLMError(f"The language model request failed: {exc}") from exc


def _generate_openai(prompt: str, settings: Settings) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": "You are a careful enterprise knowledge assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise LLMError("OpenAI returned an empty response.")
    return content.strip()


def _generate_gemini(prompt: str, settings: Settings) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.1},
    )
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise LLMError("Gemini returned an empty response.")
    return text
