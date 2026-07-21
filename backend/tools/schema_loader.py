"""
Dynamic tool schema loader for AgenThink.

Loads tool definitions from JSON. Built-in tools (no remote `_service`) are
always available. Optional SearXNG health is reported separately.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)

_SCHEMAS_DIR = Path(__file__).parent / "schemas"

_OPTIONAL_HEALTH_CHECKS: dict[str, Callable[[], bool]] = {}

_health_cache: dict[str, tuple[bool, float]] = {}
_HEALTH_CACHE_TTL = 30.0


def _register_optional_health() -> None:
    if "searxng" not in _OPTIONAL_HEALTH_CHECKS:

        def _searxng() -> bool:
            if not settings.is_service_url_enabled(settings.SEARXNG_URL):
                return False
            from backend.tools.search import check_searxng_health

            return check_searxng_health()

        _OPTIONAL_HEALTH_CHECKS["searxng"] = _searxng


def _load_all_schemas() -> list[dict]:
    all_tools = []
    for schema_file in sorted(_SCHEMAS_DIR.glob("*.json")):
        try:
            with open(schema_file, encoding="utf-8") as f:
                tools = json.load(f)
            all_tools.extend(tools)
        except Exception as e:
            logger.error("Failed to load tool schema %s: %s", schema_file.name, e)
    return all_tools


def get_available_tools(check_health: bool = True) -> list[dict]:
    """Return in-process tools only (skip any leftover remote `_service` schemas)."""
    del check_health  # reserved; no remote tool health gates
    all_tools = _load_all_schemas()
    available = []

    for tool_def in all_tools:
        func = tool_def.get("function", {})
        service = func.get("_service")
        # Only built-ins: null / missing _service
        if service is None:
            available.append(tool_def)

    logger.info("Loaded %d/%d available tools", len(available), len(all_tools))
    return available


def get_tool_definitions_for_llm(check_health: bool = True) -> list[dict]:
    tools = get_available_tools(check_health=check_health)
    clean = []
    for tool_def in tools:
        clean_def = {"type": tool_def["type"]}
        func = {k: v for k, v in tool_def["function"].items() if not k.startswith("_")}
        clean_def["function"] = func
        clean.append(clean_def)
    return clean


def get_tool_metadata(tool_name: str) -> dict | None:
    for tool_def in _load_all_schemas():
        if tool_def.get("function", {}).get("name") == tool_name:
            return tool_def.get("function", {})
    return None


def get_service_statuses() -> dict[str, bool]:
    """Local RAG/OCR always ready; SearXNG optional."""
    _register_optional_health()
    statuses = {
        "rag": True,
        "docread": True,
    }
    for name, checker in _OPTIONAL_HEALTH_CHECKS.items():
        try:
            statuses[name] = bool(checker())
        except Exception:
            statuses[name] = False
    return statuses


def invalidate_health_cache() -> None:
    _health_cache.clear()
