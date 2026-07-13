import re

from app.core.client import llm
from app.core.config import settings


conversation_store: list[dict[str, str]] = []


def _calculator_tool(message: str) -> str | None:
    match = re.fullmatch(r"Tính\s+(.+)", message.strip())
    if not match:
        return None

    expression = match.group(1).strip()
    try:
        result = eval(expression, {"__builtins__": {}}, {})
    except Exception:
        return None

    return f"{expression} = {result}"


def _build_prompt(message: str) -> str:
    prompt_lines = [f"System: {settings.SYSTEM_PROMPT}"]

    if conversation_store:
        history_lines = [
            f"{entry['role'].capitalize()}: {entry['content']}"
            for entry in conversation_store
        ]
        prompt_lines.append("Conversation history:")
        prompt_lines.extend(history_lines)

    prompt_lines.append(f"User: {message}")
    return "\n".join(prompt_lines)


def chat(message: str) -> str:
    calculator_result = _calculator_tool(message)
    if calculator_result is not None:
        conversation_store.append({"role": "user", "content": message})
        conversation_store.append({"role": "assistant", "content": calculator_result})
        return calculator_result

    prompt = _build_prompt(message)
    response = llm.chat(prompt)

    conversation_store.append({"role": "user", "content": message})
    conversation_store.append({"role": "assistant", "content": response})

    return response