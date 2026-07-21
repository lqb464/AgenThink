"""Filesystem project / sources / embedding index for local RAG."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from backend.core.config import settings

logger = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_project_id(project_id: str) -> str:
    cleaned = _SAFE_ID.sub("_", (project_id or "").strip()) or "default"
    return cleaned[:120]


def rag_root() -> Path:
    raw = getattr(settings, "RAG_DATA_DIR", None) or "./data/rag"
    path = Path(raw).expanduser()
    if not path.is_absolute():
        # Resolve relative to AgenThink project root (parent of backend/)
        path = Path(__file__).resolve().parents[2] / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_dir(project_id: str) -> Path:
    d = rag_root() / _safe_project_id(project_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "sources").mkdir(exist_ok=True)
    return d


def meta_path(project_id: str) -> Path:
    return project_dir(project_id) / "meta.json"


def index_path(project_id: str) -> Path:
    return project_dir(project_id) / "index.json"


def sources_dir(project_id: str) -> Path:
    return project_dir(project_id) / "sources"


def load_meta(project_id: str) -> dict[str, Any]:
    path = meta_path(project_id)
    if not path.exists():
        return {
            "project_id": project_id,
            "name": f"Project {project_id}",
            "sources": [],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load meta for %s: %s", project_id, exc)
        return {
            "project_id": project_id,
            "name": f"Project {project_id}",
            "sources": [],
        }


def save_meta(project_id: str, meta: dict[str, Any]) -> None:
    path = meta_path(project_id)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(project_id: str) -> dict[str, Any]:
    path = index_path(project_id)
    if not path.exists():
        return {"chunks": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load index for %s: %s", project_id, exc)
        return {"chunks": []}


def save_index(project_id: str, index: dict[str, Any]) -> None:
    path = index_path(project_id)
    path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def list_source_files(project_id: str) -> list[str]:
    meta = load_meta(project_id)
    sources = meta.get("sources") or []
    return [s for s in sources if isinstance(s, str)]


def write_source_file(project_id: str, filename: str, data: bytes) -> Path:
    safe_name = Path(filename).name
    dest = sources_dir(project_id) / safe_name
    dest.write_bytes(data)
    return dest


def delete_source_file(project_id: str, filename: str) -> bool:
    safe_name = Path(filename).name
    path = sources_dir(project_id) / safe_name
    if path.exists():
        path.unlink()
        return True
    return False


def remove_chunks_for_source(project_id: str, filename: str) -> None:
    index = load_index(project_id)
    chunks = [
        c
        for c in index.get("chunks") or []
        if isinstance(c, dict) and c.get("source") != filename
    ]
    save_index(project_id, {"chunks": chunks})


def clear_project(project_id: str) -> None:
    d = rag_root() / _safe_project_id(project_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
