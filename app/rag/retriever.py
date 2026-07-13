import math
import re
from collections import Counter

from app.rag.documents import DOCUMENTS


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


_retriever = SimpleBM25(DOCUMENTS)


def retrieve(query: str, top_k: int = 2) -> list[dict]:
    hits = _retriever.score(query)[:top_k]
    return [doc for _score, doc in hits]


def format_context(docs: list[dict]) -> str:
    if not docs:
        return ""
    blocks = [f"[{doc['title']}]\n{doc['content']}" for doc in docs]
    return "Retrieved documents:\n" + "\n\n".join(blocks)
