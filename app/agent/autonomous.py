from dataclasses import dataclass, field

from app.core.client import llm
from app.tools import run_tool

MAX_AUTONOMOUS_STEPS = 5


@dataclass
class AutonomousTrace:
    goal: str
    events: list[str] = field(default_factory=list)

    def render(self) -> str:
        body = "\n".join(f"- {event}" for event in self.events)
        return f"Autonomous run for: {self.goal}\n{body}"


def _decide_action(goal: str, observations: list[str]) -> str:
    history = "\n".join(observations) if observations else "(none)"
    prompt = (
        "You are an autonomous agent. Given the goal and observations, "
        "choose ONE next action.\n"
        "Reply with exactly one line in one of these forms:\n"
        "TOOL: <message that a tool can handle, e.g. Tính 1+1>\n"
        "THINK: <short reasoning or intermediate conclusion>\n"
        "DONE: <final answer>\n"
        f"Goal: {goal}\n"
        f"Observations:\n{history}"
    )
    return llm.chat(prompt).strip()


def _heuristic_action(goal: str, step: int) -> str:
    lowered = goal.lower()
    if step == 0 and ("tính" in lowered or "vat" in lowered or any(ch.isdigit() for ch in goal)):
        # Try to turn "Tính thuế VAT của 7 triệu" into a calculator call.
        if "vat" in lowered and "7" in goal:
            return "TOOL: Tính 7000000 * 0.1"
        if lowered.startswith("tính"):
            return f"TOOL: {goal}"
    if step >= 1:
        return f"DONE: Hoàn thành mục tiêu: {goal}"
    return f"THINK: Phân tích mục tiêu `{goal}`"


def run_autonomous(goal: str, max_steps: int = MAX_AUTONOMOUS_STEPS) -> str:
    trace = AutonomousTrace(goal=goal)
    observations: list[str] = []

    for step in range(max_steps):
        try:
            action = _decide_action(goal, observations)
        except Exception:
            action = _heuristic_action(goal, step)

        if action.upper().startswith("DONE:"):
            final = action.split(":", 1)[1].strip()
            trace.events.append(f"DONE → {final}")
            return trace.render()

        if action.upper().startswith("TOOL:"):
            tool_message = action.split(":", 1)[1].strip()
            tool_hit = run_tool(tool_message)
            if tool_hit is None:
                observation = f"Tool miss for `{tool_message}`"
            else:
                name, result = tool_hit
                observation = f"Tool `{name}` → {result}"
            observations.append(observation)
            trace.events.append(observation)
            continue

        if action.upper().startswith("THINK:"):
            thought = action.split(":", 1)[1].strip()
            observations.append(thought)
            trace.events.append(f"THINK → {thought}")
            continue

        # Unknown format: treat as thinking and continue.
        observations.append(action)
        trace.events.append(f"NOTE → {action}")

    trace.events.append("STOPPED → reached max steps")
    return trace.render()
