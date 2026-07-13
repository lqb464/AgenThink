from app.core.client import llm
from app.core.config import settings
from app.tools import run_tool


conversation_store: list[dict[str, str]] = []


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
    tool_hit = run_tool(message)
    if tool_hit is not None:
        _tool_name, tool_result = tool_hit
        conversation_store.append({"role": "user", "content": message})
        conversation_store.append({"role": "assistant", "content": tool_result})
        return tool_result

    prompt = _build_prompt(message)
    response = llm.chat(prompt)

    conversation_store.append({"role": "user", "content": message})
    conversation_store.append({"role": "assistant", "content": response})

    return response
