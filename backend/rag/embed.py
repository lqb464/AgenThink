"""Gemini text embeddings via OpenAI-compatible API."""

from __future__ import annotations

import logging
import threading

from openai import OpenAI

from backend.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "text-embedding-004"
_lock = threading.Lock()
_key_index = 0


def _next_api_key() -> str:
    global _key_index
    keys = settings.get_gemini_api_keys()
    if not keys:
        raise RuntimeError(
            "No Gemini API keys configured for embeddings. Set GEMINI_API_KEY."
        )
    with _lock:
        key = keys[_key_index % len(keys)]
        _key_index = (_key_index + 1) % len(keys)
        return key


def _client() -> OpenAI:
    return OpenAI(api_key=_next_api_key(), base_url=settings.GEMINI_BASE_URL)


def embed_texts(texts: list[str], *, model: str | None = None) -> list[list[float]]:
    """Embed a list of texts; returns one vector per input."""
    if not texts:
        return []
    mdl = model or getattr(settings, "RAG_EMBED_MODEL", None) or _DEFAULT_MODEL
    # Gemini embedding API prefers short batches
    out: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Prefix for retrieval quality (E5-style instruction optional; Gemini ignores)
        client = _client()
        resp = client.embeddings.create(model=mdl, input=batch)
        # Ensure order by index
        ordered = sorted(resp.data, key=lambda d: d.index)
        out.extend([list(d.embedding) for d in ordered])
    return out


def embed_query(query: str, *, model: str | None = None) -> list[float]:
    vectors = embed_texts([query], model=model)
    return vectors[0] if vectors else []
