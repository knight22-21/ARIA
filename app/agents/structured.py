"""Structured-output runner: prompt → validated Pydantic object.

Flow: render prompt → LLM (JSON mode) → parse+validate. On a validation/parse
failure, retry once with an explicit "fix the format" instruction. If it still
fails, raise ``StructuredOutputError`` so the caller can fall back to a
deterministic rule-based path (logged in the audit trail).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from app.agents.llm import LLMMessage, LLMResponse, _extract_json, llm
from app.agents.prompts import load_prompt
from app.core.logging import get_logger

log = get_logger(__name__)


class StructuredOutputError(RuntimeError):
    """Raised when the model cannot produce schema-valid output after a retry."""


def _parse[T: BaseModel](text: str, model_cls: type[T]) -> T:
    return model_cls.model_validate(_extract_json(text))


def run_structured[T: BaseModel](
    agent: str,
    model_cls: type[T],
    context: dict,
    *,
    version: str = "latest",
) -> tuple[T, LLMResponse]:
    """Run an agent prompt and return (validated_object, raw_llm_response)."""
    prompt = load_prompt(agent, version)
    messages = [
        LLMMessage("system", prompt.system_prompt),
        LLMMessage("user", prompt.render(**context)),
    ]

    resp = llm.complete(
        messages, max_tokens=prompt.max_tokens, temperature=prompt.temperature, json_mode=True
    )
    try:
        return _parse(resp.text, model_cls), resp
    except (ValidationError, json.JSONDecodeError, ValueError) as first_err:
        log.warning("structured.parse_retry", agent=agent, error=str(first_err)[:200])

    # One reformat retry with the explicit schema.
    schema = json.dumps(model_cls.model_json_schema())
    messages.append(LLMMessage("assistant", resp.text))
    messages.append(
        LLMMessage(
            "user",
            "Your previous output did not match the required schema. "
            f"Return ONLY a single valid JSON object conforming to this JSON Schema:\n{schema}",
        )
    )
    resp2 = llm.complete(messages, max_tokens=prompt.max_tokens, temperature=0.0, json_mode=True)
    try:
        return _parse(resp2.text, model_cls), resp2
    except (ValidationError, json.JSONDecodeError, ValueError) as second_err:
        raise StructuredOutputError(
            f"{agent} output failed schema validation twice: {second_err}"
        ) from second_err
