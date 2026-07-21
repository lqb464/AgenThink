"""In-process RAG engine: ensure / upload / retrieve / summarize / report."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from backend.core.config import settings
from backend.rag.chunk import chunk_text
from backend.rag.embed import embed_query, embed_texts
from backend.rag.parse import parse_bytes, supported_extension
from backend.rag import store

logger = logging.getLogger(__name__)


def ensure_project(project_id: str, name: str | None = None) -> dict[str, Any]:
    """Create project dirs + meta if missing; return project snapshot."""
    store.project_dir(project_id)
    meta = store.load_meta(project_id)
    if name and name.strip():
        meta["name"] = name.strip()
    meta["project_id"] = project_id
    sources = store.list_source_files(project_id)
    meta["sources"] = sources
    store.save_meta(project_id, meta)
    index = store.load_index(project_id)
    chunks = index.get("chunks") or []
    return {
        "ok": True,
        "exists": True,
        "project_id": project_id,
        "name": meta.get("name") or f"Project {project_id}",
        "sources": sources,
        "stats": {"documents": len(sources), "chunks": len(chunks)},
        "indexed": bool(chunks),
    }


def get_project(project_id: str) -> dict[str, Any]:
    store.project_dir(project_id)
    meta = store.load_meta(project_id)
    sources = store.list_source_files(project_id)
    index = store.load_index(project_id)
    chunks = index.get("chunks") or []
    exists = bool(sources) or store.meta_path(project_id).exists()
    return {
        "ok": True,
        "exists": exists,
        "project_id": project_id,
        "name": meta.get("name") or f"Project {project_id}",
        "sources": sources,
        "stats": {"documents": len(sources), "chunks": len(chunks)},
        "indexed": bool(chunks),
    }


def status(project_id: str) -> dict[str, Any]:
    """Always online for local RAG."""
    project = get_project(project_id)
    return {
        "online": True,
        "default_project_id": project_id,
        "project_id": project_id,
        "project": project,
        "studio_url": None,
        "error": None,
    }


def add_files(
    project_id: str,
    files: list[tuple[str, bytes]],
    *,
    name: str | None = None,
) -> dict[str, Any]:
    """
    Persist files, parse, chunk, embed, merge into index.
    *files* is a list of (filename, bytes).
    """
    from pathlib import Path

    ensure_project(project_id, name=name)
    added: list[str] = []
    errors: list[str] = []
    new_chunks: list[dict[str, Any]] = []
    replaced_sources: set[str] = set()

    for filename, data in files:
        if not filename or not data:
            continue
        if not supported_extension(filename):
            errors.append(f"{filename}: unsupported type")
            continue
        try:
            text = parse_bytes(filename, data)
            pieces = chunk_text(text)
            if not pieces:
                errors.append(f"{filename}: empty after parse")
                continue
            safe = Path(filename).name
            store.write_source_file(project_id, safe, data)
            replaced_sources.add(safe)
            vectors = embed_texts(pieces)
            for text_piece, vec in zip(pieces, vectors, strict=True):
                new_chunks.append(
                    {
                        "source": safe,
                        "text": text_piece,
                        "embedding": vec,
                    }
                )
            added.append(safe)
        except Exception as exc:
            logger.exception("Failed to index %s", filename)
            errors.append(f"{filename}: {exc}")

    if new_chunks or replaced_sources:
        index = store.load_index(project_id)
        existing = [
            c
            for c in (index.get("chunks") or [])
            if isinstance(c, dict) and c.get("source") not in replaced_sources
        ]
        existing.extend(new_chunks)
        store.save_index(project_id, {"chunks": existing})

    sources = [p.name for p in sorted(store.sources_dir(project_id).iterdir()) if p.is_file()]
    meta = store.load_meta(project_id)
    meta["sources"] = sources
    store.save_meta(project_id, meta)

    index = store.load_index(project_id)
    result: dict[str, Any] = {
        "ok": True,
        "project_id": project_id,
        "added": added,
        "sources": sources,
        "stats": {
            "documents": len(sources),
            "chunks": len(index.get("chunks") or []),
        },
    }
    if errors:
        result["error"] = "; ".join(errors)
    return result


def delete_source(project_id: str, filename: str) -> dict[str, Any]:
    from pathlib import Path

    safe = Path(filename).name
    removed = store.delete_source_file(project_id, safe)
    store.remove_chunks_for_source(project_id, safe)
    meta = store.load_meta(project_id)
    sources = [p.name for p in sorted(store.sources_dir(project_id).iterdir()) if p.is_file()]
    meta["sources"] = sources
    store.save_meta(project_id, meta)
    if not removed and safe not in sources:
        return {
            "ok": False,
            "error": "Source not found",
            "project_id": project_id,
            "sources": sources,
        }
    return {"ok": True, "project_id": project_id, "sources": sources, "deleted": safe}


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def retrieve(
    project_id: str,
    query: str,
    *,
    top_k: int = 4,
    allowed_sources: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Return chunks as {source, text} ranked by cosine similarity.
    Falls back to BM25 demo corpus when project has no indexed chunks.
    """
    index = store.load_index(project_id)
    chunks = [c for c in (index.get("chunks") or []) if isinstance(c, dict)]
    if allowed_sources:
        allow = set(allowed_sources)
        chunks = [c for c in chunks if c.get("source") in allow]

    if not chunks:
        from backend.rag.retriever import _fallback_retrieve

        docs = _fallback_retrieve(query, top_k)
        return [
            {"source": d.get("title") or d.get("id") or "demo", "text": d.get("content") or ""}
            for d in docs
        ]

    try:
        qvec = np.array(embed_query(query), dtype=np.float32)
    except Exception as exc:
        logger.warning("Embedding failed, BM25 fallback: %s", exc)
        from backend.rag.retriever import _fallback_retrieve

        docs = _fallback_retrieve(query, top_k)
        return [
            {"source": d.get("title") or d.get("id") or "demo", "text": d.get("content") or ""}
            for d in docs
        ]

    scored: list[tuple[float, dict]] = []
    for c in chunks:
        emb = c.get("embedding")
        if not emb:
            continue
        score = _cosine_sim(qvec, np.array(emb, dtype=np.float32))
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[dict[str, str]] = []
    for score, c in scored[: max(1, top_k)]:
        if score <= 0:
            continue
        results.append({"source": str(c.get("source") or "unknown"), "text": str(c.get("text") or "")})
    if not results and scored:
        # return top anyway
        for _score, c in scored[: max(1, top_k)]:
            results.append(
                {"source": str(c.get("source") or "unknown"), "text": str(c.get("text") or "")}
            )
    return results


def _llm_markdown(prompt: str) -> str:
    from backend.core.client import get_llm_provider

    provider = get_llm_provider()
    full = (
        "You are a helpful research assistant. Write clear Markdown. "
        "Respond in Vietnamese unless the sources are English-only.\n\n"
        f"{prompt}"
    )
    return provider.chat(full)


def _gather_source_texts(
    project_id: str,
    sources: list[str] | None,
) -> tuple[str, list[str]]:
    index = store.load_index(project_id)
    chunks = [c for c in (index.get("chunks") or []) if isinstance(c, dict)]
    if sources:
        allow = set(sources)
        chunks = [c for c in chunks if c.get("source") in allow]
    used = sorted({str(c.get("source")) for c in chunks if c.get("source")})
    if not chunks:
        return "", used
    # Cap context size
    parts: list[str] = []
    total = 0
    for c in chunks:
        block = f"[{c.get('source')}]\n{c.get('text')}"
        if total + len(block) > 24000:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts), used


def summarize(project_id: str, sources: list[str] | None = None) -> dict[str, Any]:
    context, used = _gather_source_texts(project_id, sources)
    if not context:
        return {
            "markdown": "Chưa có tài liệu nào trong Tri thức để tóm tắt. Hãy upload PDF/DOCX/MD trước.",
            "sources": used,
        }
    prompt = (
        "Tóm tắt các tài liệu sau một cách ngắn gọn, có cấu trúc (bullet/heading).\n"
        "Trích dẫn tên file nguồn khi phù hợp.\n\n"
        f"{context}"
    )
    md = _llm_markdown(prompt)
    return {"markdown": md, "sources": used}


def report(project_id: str, sources: list[str] | None = None) -> dict[str, Any]:
    context, used = _gather_source_texts(project_id, sources)
    if not context:
        return {
            "markdown": "Chưa có tài liệu nào để lập báo cáo. Hãy upload vào Tri thức trước.",
            "sources": used,
        }
    prompt = (
        "Viết báo cáo nghiên cứu/Markdown chi tiết dựa trên các nguồn sau:\n"
        "- Mở đầu / bối cảnh\n"
        "- Các điểm chính\n"
        "- Kết luận\n"
        "Trích dẫn filename nguồn trong từng mục.\n\n"
        f"{context}"
    )
    md = _llm_markdown(prompt)
    return {"markdown": md, "sources": used}
