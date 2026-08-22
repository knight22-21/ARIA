"""Provider-agnostic LLM client.

One interface, pluggable backends selected via ``LLM_PROVIDER``:
  - ``groq``   → Groq cloud (default: llama-3.3-70b-versatile). Free, fast, 70B.
  - ``ollama`` → local Ollama (default: qwen2.5:7b). Offline fallback, no rate limits.

Design goals:
  - Uniform ``complete()`` / ``complete_json()`` API for all agents.
  - Retry-with-backoff on transient errors.
  - Automatic fallback Groq → Ollama when Groq is unavailable (rate limit / no key / error).
  - Token accounting surfaced on every response for the audit ledger.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMError(RuntimeError):
    """Raised when all providers/retries are exhausted."""


class LLMClient:
    """Facade over Groq + Ollama with retry and fallback."""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.llm_provider

    # ---- public API -------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Run a chat completion, trying the primary provider then falling back."""
        order = self._provider_order()
        last_err: Exception | None = None

        for prov in order:
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    if prov == "groq":
                        return self._groq(messages, max_tokens, temperature, json_mode)
                    return self._ollama(messages, max_tokens, temperature, json_mode)
                except Exception as exc:  # noqa: BLE001 — retry/fallback on any error
                    last_err = exc
                    log.warning(
                        "llm.attempt_failed",
                        provider=prov,
                        attempt=attempt,
                        error=str(exc),
                    )
                    if attempt < _MAX_RETRIES:
                        time.sleep(_BACKOFF_BASE ** attempt)
            log.warning("llm.provider_exhausted", provider=prov)

        raise LLMError(f"All LLM providers failed. Last error: {last_err}")

    def complete_json(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Completion that must return a JSON object. Parses and returns a dict."""
        resp = self.complete(
            messages, max_tokens=max_tokens, temperature=temperature, json_mode=True
        )
        return _extract_json(resp.text)

    # ---- provider order --------------------------------------------

    def _provider_order(self) -> list[str]:
        if self.provider == "ollama":
            return ["ollama"]
        # groq primary; fall back to ollama if a local model is configured
        return ["groq", "ollama"] if settings.ollama_model else ["groq"]

    # ---- backends ---------------------------------------------------

    def _groq(
        self,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> LLMResponse:
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY not set")
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        kwargs: dict[str, Any] = {
            "model": settings.groq_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            provider="groq",
            model=settings.groq_model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )

    def _ollama(
        self,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> LLMResponse:
        import ollama

        client = ollama.Client(host=settings.ollama_host)
        resp = client.chat(
            model=settings.ollama_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            format="json" if json_mode else "",
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return LLMResponse(
            text=resp["message"]["content"],
            provider="ollama",
            model=settings.ollama_model,
            input_tokens=resp.get("prompt_eval_count", 0) or 0,
            output_tokens=resp.get("eval_count", 0) or 0,
        )


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Tolerate ```json fences / surrounding prose by slicing the outermost braces.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


# Module-level singleton for convenience.
llm = LLMClient()
