"""Smoke-test the LLM client against whichever provider is configured.

Usage:
    python scripts/check_llm.py
"""

from app.agents.llm import LLMMessage, llm
from app.core.config import settings


def main() -> None:
    print(f"LLM_PROVIDER = {settings.llm_provider}")
    print(f"groq_model   = {settings.groq_model}")
    print(f"ollama_model = {settings.ollama_model}")
    print("-" * 50)

    resp = llm.complete(
        [
            LLMMessage("system", "You are a terse assistant. Reply in <=8 words."),
            LLMMessage("user", "Say hello and name yourself."),
        ],
        max_tokens=32,
    )
    print(f"provider used : {resp.provider} ({resp.model})")
    print(f"tokens        : in={resp.input_tokens} out={resp.output_tokens}")
    print(f"response      : {resp.text}")


if __name__ == "__main__":
    main()
