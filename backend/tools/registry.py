from collections.abc import Callable

from backend.tools.calculator import match_calculator
from backend.tools.search import match_search
from backend.tools.weather import match_weather
from backend.tools.vision import match_vision

# Order matters: first matching tool wins.
_CORE_TOOLS: list[tuple[str, Callable[[str], str | None]]] = [
    ("vision", match_vision),
    ("calculator", match_calculator),
    ("weather", match_weather),
    ("search", match_search),
]

# Backward-compatible export
TOOLS: list[tuple[str, Callable[[str], str | None]]] = list(_CORE_TOOLS)


def run_tool(message: str) -> tuple[str, str] | None:
    """Try each tool matcher. Return (tool_name, result) or None."""
    for name, matcher in _CORE_TOOLS:
        result = matcher(message)
        if result is not None:
            return name, result
    return None
