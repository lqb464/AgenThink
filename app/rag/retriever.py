"""
RAG retriever for AgenThink.

Attempts to fetch relevant document chunks from the external RAG Service
(RAnythinG). If the service is unavailable or returns an error, falls back
to the built-in SimpleBM25 retriever over the static DOCUMENTS corpus.
"""

import logging
import math
import re
from collections import Counter

import httpx

from app.core.config import settings
from app.rag.documents import DOCUMENTS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback: minimal BM25 retriever over the static DOCUMENTS corpus
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class SimpleBM25:
    """Minimal BM25 retriever for learning RAG without a vector DB."""

    def __init__(self, documents: list[dict], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.corpus = [_tokenize(f"{doc['title']} {doc['content']}") for doc in documents]
        self.doc_len = [len(tokens) for tokens in self.corpus]
        self.avgdl = sum(self.doc_len) / len(self.corpus) if self.corpus else 0.0
        self.doc_freqs: list[Counter] = [Counter(tokens) for tokens in self.corpus]
        self.df: Counter = Counter()
        for tokens in self.corpus:
            for term in set(tokens):
                self.df[term] += 1
        self.n_docs = len(self.corpus)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def score(self, query: str) -> list[tuple[float, dict]]:
        query_terms = _tokenize(query)
        scored: list[tuple[float, dict]] = []

        for idx, doc in enumerate(self.documents):
            score = 0.0
            freqs = self.doc_freqs[idx]
            dl = self.doc_len[idx]
            for term in query_terms:
                if term not in freqs:
                    continue
                tf = freqs[term]
                idf = self._idf(term)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += idf * (tf * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored


_fallback_retriever = SimpleBM25(DOCUMENTS)


def _fallback_retrieve(query: str, top_k: int) -> list[dict]:
    """Return top-k docs from the in-memory static corpus using BM25."""
    hits = _fallback_retriever.score(query)[:top_k]
    return [doc for _score, doc in hits]


# ---------------------------------------------------------------------------
# Primary: call external RAG Service
# ---------------------------------------------------------------------------

def _retrieve_from_service(query: str, top_k: int, project_id: str) -> list[dict] | None:
    """
    Call the external RAG Service's /api/external/retrieve endpoint.

    Returns a list of chunk dicts on success, or None if the call fails
    (so callers can apply the fallback strategy).
    """
    url = f"{settings.RAG_SERVICE_URL.rstrip('/')}/api/external/retrieve"
    try:
        response = httpx.post(
            url,
            json={
                "project_id": project_id,
                "query": query,
                "top_k": top_k,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        chunks = data.get("chunks", [])
        if chunks:
            # Convert service chunk format → dict compatible with format_context
            return [
                {
                    "id": chunk.get("source", "rag-service"),
                    "title": chunk.get("source", "Nguồn tài liệu"),
                    "content": chunk.get("text", ""),
                }
                for chunk in chunks
            ]
        return []
    except httpx.ConnectError:
        logger.warning("RAG Service unavailable at %s — falling back to BM25", url)
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Project not found means no documents have been uploaded yet
            logger.info(
                "RAG Service: project '%s' not found — falling back to BM25", project_id
            )
        else:
            logger.warning(
                "RAG Service returned HTTP %s — falling back to BM25",
                e.response.status_code,
            )
        return None
    except Exception as e:
        logger.warning("Error calling RAG Service: %s — falling back to BM25", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = 2) -> list[dict]:
    """
    Retrieve the most relevant document chunks for *query*.

    1. Try the external RAG Service (Hybrid Dense + BM25 + Reranking).
    2. If unavailable, fall back to the simple in-memory BM25 retriever.
    """
    project_id = settings.RAG_PROJECT_ID
    result = _retrieve_from_service(query, top_k, project_id)
    if result is not None:
        return result
    # Fallback path
    return _fallback_retrieve(query, top_k)


def format_context(docs: list[dict]) -> str:
    if not docs:
        return ""
    blocks = [f"[{doc['title']}]\n{doc['content']}" for doc in docs]
    return "Retrieved documents:\n" + "\n\n".join(blocks)
