import re

from app.core.client import llm


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
    return [
        f"Phân tích yêu cầu: {goal}",
        f"Liệt kê các bước thực hiện cho: {goal}",
        f"Tổng hợp kết quả cho: {goal}",
    ]


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
