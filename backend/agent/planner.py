import re

from backend.core.client import llm

_TRIVIAL_RE = re.compile(
    r"^(xin chào|chào|hello|hi|hey|cảm ơn|thanks|thank you|ok|oke|ừ|uh)\b",
    flags=re.IGNORECASE,
)

_COMPLEX_HINTS = (
    "lập kế hoạch",
    "plan",
    "goal:",
    "mục tiêu",
    "tính",
    "phân tích",
    "báo cáo",
    "du lịch",
    "travel",
    "so sánh",
    "tóm tắt",
    "research",
    "nghiên cứu",
    "wikipedia",
    "wiki",
    "arxiv",
    "tìm trên web",
    "then",
    "sau đó",
    "bước",
    "nhớ",
    "remember",
)


def _default_steps(goal: str) -> list[str]:
    lowered = goal.lower()
    if "du lịch" in lowered or "travel" in lowered:
        return [
            "Tìm điểm đến và thời điểm phù hợp",
            "Gợi ý lịch trình theo ngày",
            "Ước tính chi phí chính",
            "Tổng hợp checklist trước chuyến đi",
        ]
    if "báo cáo" in lowered or "report" in lowered:
        return [
            "Thu thập dữ liệu cần thiết",
            "Phân tích số liệu chính",
            "Viết nhận xét và kết luận",
        ]
    if "tính" in lowered or "vat" in lowered or any(ch.isdigit() for ch in goal):
        return [
            "Xác định công thức / dữ liệu cần tính",
            "Gọi công cụ calculator (hoặc tool phù hợp)",
            "Giải thích kết quả ngắn gọn",
        ]
    if "thời tiết" in lowered or "weather" in lowered:
        return [
            "Xác định địa điểm",
            "Gọi get_weather",
            "Tóm tắt thời tiết cho người dùng",
        ]
    if any(
        h in lowered
        for h in (
            "nghiên cứu",
            "research",
            "arxiv",
            "wikipedia",
            "wiki",
            "tìm trên web",
            "web search",
            "bài báo",
            "paper",
        )
    ):
        return [
            "Chọn nguồn: web_search / wikipedia_lookup / arxiv_search",
            "Gọi tool nghiên cứu và ghi nhận URL",
            "Tổng hợp câu trả lời có trích dẫn nguồn",
        ]
    return [
        f"Phân tích yêu cầu: {goal}",
        "Chọn và gọi tool phù hợp (nếu cần)",
        f"Tổng hợp kết quả cho: {goal}",
    ]


def should_plan(goal: str, *, tools_available: bool) -> bool:
    """Decide whether the agent loop should emit a light plan for this turn."""
    if not tools_available:
        return False
    text = (goal or "").strip()
    if not text or _TRIVIAL_RE.match(text):
        return False
    lowered = text.lower()
    if len(text) >= 40:
        return True
    if any(ch.isdigit() for ch in text):
        return True
    if any(hint in lowered for hint in _COMPLEX_HINTS):
        return True
    if match_plan_request(text):
        return True
    return False


def light_plan(goal: str, *, use_llm: bool = False) -> list[str]:
    """
    Build a short actionable plan for the agent loop.

    Default is heuristic (no extra LLM call) to conserve free-tier quota.
    Set use_llm=True for an LLM-authored plan.
    """
    if use_llm:
        return create_plan(goal)
    return _default_steps(goal)


def create_plan(goal: str) -> list[str]:
    """Create an ordered list of tasks for a goal."""
    prompt = (
        "Break the goal into 3 to 5 short actionable steps. "
        "Reply with one step per line, no numbering.\n"
        f"Goal: {goal}"
    )
    try:
        raw = llm.chat(prompt)
        steps = [line.strip(" -*\t") for line in raw.splitlines() if line.strip()]
        if len(steps) >= 2:
            return steps[:5]
    except Exception:
        pass
    return _default_steps(goal)


def execute_step(goal: str, step: str, prior_results: list[str]) -> str:
    context = "\n".join(prior_results) if prior_results else "(none)"
    prompt = (
        f"Goal: {goal}\n"
        f"Current step: {step}\n"
        f"Previous step results:\n{context}\n"
        "Complete only this step briefly."
    )
    return llm.chat(prompt)


def merge_results(goal: str, steps: list[str], results: list[str]) -> str:
    body = "\n".join(
        f"{idx}. {step}\n   → {result}"
        for idx, (step, result) in enumerate(zip(steps, results), start=1)
    )
    return f"Kế hoạch cho: {goal}\n\n{body}"


_PLAN_RE = re.compile(
    r"^(?:Lập kế hoạch|Plan)\s*[:\-]?\s*(.+)$",
    flags=re.IGNORECASE,
)


def match_plan_request(message: str) -> str | None:
    match = _PLAN_RE.match(message.strip())
    if not match:
        return None
    return match.group(1).strip()


def run_planning(goal: str) -> str:
    steps = create_plan(goal)
    results: list[str] = []
    for step in steps:
        result = execute_step(goal, step, results)
        results.append(result)
    return merge_results(goal, steps, results)
