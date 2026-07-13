from app.core.client import llm


conversation_store: list[dict[str, str]] = []


def _build_prompt(message: str) -> str:
    if not conversation_store:
        return message

    history_lines = [
        f"{entry['role'].capitalize()}: {entry['content']}"
        for entry in conversation_store
    ]
    history_block = "\n".join(history_lines)

    return f"Conversation history:\n{history_block}\nUser: {message}"


def chat(message: str) -> str:
    prompt = _build_prompt(message)
    response = llm.chat(prompt)

    conversation_store.append({"role": "user", "content": message})
    conversation_store.append({"role": "assistant", "content": response})

    return response