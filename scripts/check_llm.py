"""Smoke-test the LLM client against whichever provider is configured.

Usage:
    python scripts/check_llm.py
"""

import sys
from pathlib import Path

# Allow running as `python scripts/check_llm.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.llm import LLMMessage, llm  # noqa: E402
from app.core.config import settings  # noqa: E402


def main() -> None:
    print(f"LLM_PROVIDER = {settings.llm_provider}")
    print(f"groq_model   = {settings.groq_model}")
    print(f"ollama_model = {settings.ollama_model}")
    print("-" * 50)

    # NOTE: reasoning models (e.g. Groq gpt-oss) spend tokens on a hidden
    # reasoning pass before the final answer, so give a generous budget.
    resp = llm.complete(
        [
            LLMMessage("system", "You are a terse assistant. Reply in <=8 words."),
            LLMMessage("user", "Say hello and name yourself."),
        ],
        max_tokens=512,
    )
    print(f"provider used : {resp.provider} ({resp.model})")
    print(f"tokens        : in={resp.input_tokens} out={resp.output_tokens}")
    print(f"response      : {resp.text}")
    if resp.reasoning:
        print(f"reasoning     : {resp.reasoning[:160]}")


if __name__ == "__main__":
    main()
