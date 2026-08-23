"""Versioned prompt loader.

Prompts live as YAML under ``prompts/<agent>/<version>.yaml`` and are referenced
by version string so past decisions are reproducible (blueprint §10.1). Each file:

    version: "1.0.0"
    model: null            # optional per-prompt override; null = use configured provider
    max_tokens: 1200
    temperature: 0.2
    system_prompt: |
      ...
    user_prompt_template: |
      ...                   # Jinja2, rendered with per-call context
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import StrictUndefined, Template

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


@dataclass(frozen=True)
class LoadedPrompt:
    agent: str
    version: str
    system_prompt: str
    user_template: str
    model: str | None
    max_tokens: int
    temperature: float

    def render(self, **context) -> str:
        return Template(self.user_template, undefined=StrictUndefined).render(**context)


def _resolve_path(agent: str, version: str) -> Path:
    agent_dir = _PROMPTS_DIR / agent
    if version == "latest":
        candidates = sorted(agent_dir.glob("v*.yaml"))
        if not candidates:
            raise FileNotFoundError(f"no prompt files for agent '{agent}' in {agent_dir}")
        return candidates[-1]
    return agent_dir / f"{version}.yaml"


def load_prompt(agent: str, version: str = "latest") -> LoadedPrompt:
    path = _resolve_path(agent, version)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return LoadedPrompt(
        agent=agent,
        version=str(data.get("version", path.stem.lstrip("v"))),
        system_prompt=data["system_prompt"],
        user_template=data["user_prompt_template"],
        model=data.get("model"),
        max_tokens=int(data.get("max_tokens", 1200)),
        temperature=float(data.get("temperature", 0.2)),
    )
