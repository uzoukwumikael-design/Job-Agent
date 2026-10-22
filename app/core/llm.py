"""Thin LLM client – OpenAI, xAI, Ollama, Gemini (Google)."""

from __future__ import annotations
import json
from typing import Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings


def _openai_client():
    from openai import AsyncOpenAI
    s = get_settings()
    api_key = s.openai_api_key or s.xai_api_key or "ollama"
    base_url = s.llm_base_url
    if s.llm_provider == "xai" and not base_url:
        base_url = "https://api.x.ai/v1"
    elif s.llm_provider == "ollama" and not base_url:
        base_url = "http://localhost:11434/v1"
    # Gemini via OpenAI-compatible endpoint (Google AI Studio)
    elif s.llm_provider == "gemini" and not base_url:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_key = s.gemini_api_key or s.openai_api_key or api_key
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def _chat_gemini_native(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    model: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Native google-genai path when available; else falls through to OpenAI-compatible."""
    s = get_settings()
    api_key = s.gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        # Fall back to OpenAI-compatible client
        client = _openai_client()
        kwargs: dict[str, Any] = {
            "model": model or s.llm_model or "gemini-2.0-flash",
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    client = genai.Client(api_key=api_key)
    # Convert chat messages to Gemini contents
    system = ""
    contents = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system += content + "\n"
        elif role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part(text=content)]))
        else:
            contents.append(types.Content(role="user", parts=[types.Part(text=content)]))

    config_kwargs: dict[str, Any] = {"temperature": temperature}
    if system.strip():
        config_kwargs["system_instruction"] = system.strip()
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    model_name = model or s.llm_model or "gemini-2.0-flash"
    # google-genai is sync in some versions – run in executor if needed
    import asyncio
    loop = asyncio.get_event_loop()

    def _call():
        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

    resp = await loop.run_in_executor(None, _call)
    return (resp.text or "") if hasattr(resp, "text") else str(resp)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    response_format: Optional[dict] = None,
    model: Optional[str] = None,
) -> str:
    s = get_settings()
    json_mode = bool(response_format and response_format.get("type") == "json_object")

    if s.llm_provider == "gemini":
        return await _chat_gemini_native(
            messages, temperature=temperature, model=model, json_mode=json_mode
        )

    client = _openai_client()
    kwargs: dict[str, Any] = {
        "model": model or s.llm_model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format
    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


async def chat_json(messages: list[dict[str, str]], **kwargs) -> dict:
    raw = await chat(messages, response_format={"type": "json_object"}, **kwargs)
    # Gemini sometimes wraps JSON in markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)
