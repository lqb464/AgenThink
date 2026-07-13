from collections.abc import Callable

from app.tools.calculator import match_calculator
from app.tools.search import match_search
from app.tools.weather import match_weather
from app.tools.vision import match_vision
from app.tools.fashion import match_fashion

# Order matters: first matching tool wins.
TOOLS: list[tuple[str, Callable[[str], str | None]]] = [
    ("fashion", match_fashion),
    ("vision", match_vision),
    ("calculator", match_calculator),
    ("weather", match_weather),
    ("search", match_search),
]


def run_tool(message: str) -> tuple[str, str] | None:
    """Try each tool matcher. Return (tool_name, result) or None."""
    for name, matcher in TOOLS:
        result = matcher(message)
        if result is not None:
            return name, result
    return None
