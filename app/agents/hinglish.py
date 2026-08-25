"""Hinglish helpers — message guidance (few-shot) + voice-script generation.

Steers the Intervention Selector to write natural code-switching Hinglish when the
merchant has ``hinglish_mode`` on, and generates a warm Hinglish voice script + SSML
preview for the GENERATE_VOICE_SCRIPT action (no call is placed).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.agents.structured import run_structured
from app.schemas.agent import VoiceScriptResult

_EXAMPLES_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "prompts"
    / "hinglish_voice"
    / "hinglish_examples.json"
)


@lru_cache
def _examples() -> dict:
    return json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))


def build_message_guidance(language: str, tier: str = "retail") -> str:
    """Return a prompt fragment steering the message language/style."""
    if language != "hinglish":
        return "Write the message in clear, warm English."
    ex = _examples()
    samples = "\n".join(f"  - {s}" for s in ex["whatsapp_examples"][:6])
    tone = ex["tone_notes"].get(tier, ex["tone_notes"]["retail"])
    return (
        "IMPORTANT — write the message in natural, warm Hinglish (Hindi + English "
        f"code-switching), NOT pure English. Tone: {tone}\n"
        f"Match the feel of these examples:\n{samples}"
    )


def generate_voice_script(
    *, tier: str, amount_inr: int, context: str, root_cause: str
) -> VoiceScriptResult:
    """LLM-generate a Hinglish call script + SSML (preview only)."""
    ex = _examples()
    examples_block = "\n".join(f"  - {s}" for s in ex["voice_script_examples"])
    result, _ = run_structured(
        "hinglish_voice",
        VoiceScriptResult,
        {
            "tier": tier,
            "amount_inr": amount_inr,
            "context": context,
            "root_cause": root_cause,
            "examples": examples_block,
        },
    )
    return result
