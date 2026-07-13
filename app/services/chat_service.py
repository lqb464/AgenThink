from app.core.client import llm
from app.core.config import settings
from app.memory import extract_and_store, format_memory
from app.rag import format_context, retrieve
from app.tools import run_tool


conversation_store: list[dict[str, str]] = []


def _build_prompt(message: str, rag_context: str = "", memory_context: str = "") -> str:
    prompt_lines = [f"System: {settings.SYSTEM_PROMPT}"]

    if memory_context:
        prompt_lines.append(memory_context)

    if rag_context:
        prompt_lines.append(rag_context)
        prompt_lines.append(
            "Answer using the retrieved documents when relevant. "
            "If the documents do not contain the answer, say you do not know."
        )

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
    memory_ack = extract_and_store(message)
    if memory_ack is not None:
        conversation_store.append({"role": "user", "content": message})
        conversation_store.append({"role": "assistant", "content": memory_ack})
        return memory_ack

    tool_hit = run_tool(message)
    if tool_hit is not None:
        _tool_name, tool_result = tool_hit
        conversation_store.append({"role": "user", "content": message})
        conversation_store.append({"role": "assistant", "content": tool_result})
        return tool_result

    docs = retrieve(message, top_k=2)
    rag_context = format_context(docs)
    memory_context = format_memory()
    prompt = _build_prompt(
        message,
        rag_context=rag_context,
        memory_context=memory_context,
    )
    response = llm.chat(prompt)

    conversation_store.append({"role": "user", "content": message})
    conversation_store.append({"role": "assistant", "content": response})

    return response
