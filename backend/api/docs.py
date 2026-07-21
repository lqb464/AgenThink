"""Docs / Knowledge API — in-process local RAG (no external service)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from backend.core.auth_deps import AuthUser, require_user
from backend.core.config import settings
from backend.rag import engine as rag_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docs", tags=["docs"])


def _user_project(user: AuthUser, project_id: str | None = None) -> str:
    """Force per-user project when JWT auth; allow override only for anonymous/legacy."""
    if user.id not in ("anonymous", "legacy"):
        return (user.rag_project_id or settings.RAG_PROJECT_ID).strip()
    pid = (project_id or "").strip() or user.rag_project_id or settings.RAG_PROJECT_ID
    return pid.strip() or "agentthink_default"


class EnsureProjectBody(BaseModel):
    project_id: str | None = None
    name: str | None = None


@router.get("/status")
async def docs_status(
    project_id: str | None = Query(default=None),
    user: AuthUser = Depends(require_user),
):
    """Local RAG is always online when the API is running."""
    pid = _user_project(user, project_id)
    return rag_engine.status(pid)


@router.get("/project")
async def get_project(
    project_id: str | None = Query(default=None),
    user: AuthUser = Depends(require_user),
):
    pid = _user_project(user, project_id)
    return rag_engine.get_project(pid)


@router.post("/project")
async def create_or_ensure_project(
    body: EnsureProjectBody,
    user: AuthUser = Depends(require_user),
):
    """Create / ensure the caller's RAG project on local disk."""
    pid = _user_project(user, body.project_id)
    name = (body.name or f"AgenThink · {user.email}").strip()
    return rag_engine.ensure_project(pid, name=name)


@router.get("/sources")
async def list_sources(
    project_id: str | None = Query(default=None),
    user: AuthUser = Depends(require_user),
):
    pid = _user_project(user, project_id)
    project = rag_engine.get_project(pid)
    return {
        "ok": True,
        "project_id": pid,
        "sources": project.get("sources") or [],
        "exists": project.get("exists", False),
    }


@router.post("/upload")
async def upload_documents(
    project_id: str = Form(default=""),
    files: list[UploadFile] = File(...),
    user: AuthUser = Depends(require_user),
):
    pid = _user_project(user, project_id or None)
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        if not content:
            continue
        payloads.append((f.filename or "upload.bin", content))
    if not payloads:
        raise HTTPException(status_code=400, detail="Empty files")

    try:
        return rag_engine.add_files(
            pid,
            payloads,
            name=f"AgenThink · {user.email}",
        )
    except Exception as exc:
        logger.exception("Local RAG upload failed")
        raise HTTPException(status_code=500, detail=str(exc)[:300]) from exc


@router.delete("/sources/{filename:path}")
async def delete_source(
    filename: str,
    project_id: str | None = Query(default=None),
    user: AuthUser = Depends(require_user),
):
    pid = _user_project(user, project_id)
    result = rag_engine.delete_source(pid, filename)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Source not found")
    return result
