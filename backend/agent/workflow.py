from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    name: str
    run: Callable[[dict], str]


@dataclass
class WorkflowResult:
    workflow: str
    steps: list[tuple[str, str]] = field(default_factory=list)

    def render(self) -> str:
        body = "\n".join(f"{idx}. [{name}] {output}" for idx, (name, output) in enumerate(self.steps, start=1))
        return f"Workflow `{self.workflow}` hoàn tất:\n{body}"


def _read_revenue(state: dict) -> str:
    revenue = {"2024": 100, "2025": 130}
    state["revenue"] = revenue
    return f"Doanh thu: {revenue}"


def _calc_growth(state: dict) -> str:
    revenue = state["revenue"]
    growth = (revenue["2025"] - revenue["2024"]) / revenue["2024"] * 100
    state["growth"] = growth
    return f"Tăng trưởng: {growth:.1f}%"


def _make_chart(state: dict) -> str:
    revenue = state["revenue"]
    chart = f"[chart] 2024={revenue['2024']} | 2025={revenue['2025']}"
    state["chart"] = chart
    return chart


def _write_report(state: dict) -> str:
    report = (
        f"Báo cáo: doanh thu tăng {state['growth']:.1f}%. "
        f"Biểu đồ: {state['chart']}"
    )
    state["report"] = report
    return report


WORKFLOWS: dict[str, list[WorkflowStep]] = {
    "bao-cao-doanh-thu": [
        WorkflowStep("read_revenue", _read_revenue),
        WorkflowStep("calc_growth", _calc_growth),
        WorkflowStep("make_chart", _make_chart),
        WorkflowStep("write_report", _write_report),
    ],
}


def match_workflow(message: str) -> str | None:
    text = message.strip().lower()
    if text.startswith("chạy workflow"):
        name = text.replace("chạy workflow", "", 1).strip(" :")
        return name or None
    if "báo cáo doanh thu" in text or "bao cao doanh thu" in text:
        return "bao-cao-doanh-thu"
    return None


def run_workflow(name: str) -> str:
    steps = WORKFLOWS.get(name)
    if steps is None:
        known = ", ".join(sorted(WORKFLOWS))
        return f"Không tìm thấy workflow `{name}`. Có sẵn: {known}"

    state: dict = {}
    result = WorkflowResult(workflow=name)
    for step in steps:
        output = step.run(state)
        result.steps.append((step.name, output))
    return result.render()
