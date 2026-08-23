"""Local embeddings via Ollama ``nomic-embed-text`` (free, CPU).

Used by the pattern-similarity layer (few-shot retrieval / clustering). Kept
minimal for Phase 2; callers that don't need it never import Ollama.
"""

from __future__ import annotations

from app.core.config import settings


def embed(texts: list[str]) -> list[list[float]]:
    """Return an embedding vector per input text."""
    import ollama

    client = ollama.Client(host=settings.ollama_host)
    out: list[list[float]] = []
    for t in texts:
        resp = client.embeddings(model=settings.embed_model, prompt=t)
        out.append(resp["embedding"])
    return out
