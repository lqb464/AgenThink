"""
Tool executor for AgenThink.

Dispatches function calls from the LLM to built-in handlers.
Returns structured results that are fed back to the LLM.
"""

import logging
from dataclasses import dataclass, field

from backend.tools.schema_loader import get_tool_metadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    """Result of executing a tool."""

    tool_name: str
    success: bool = True
    text: str = ""
    error: str = ""
    images: list[str] = field(default_factory=list)  # base64 encoded images
    # Structured citations from RAG (filename + snippet) for UI source panel
    sources: list[dict] = field(default_factory=list)

    def to_llm_text(self) -> str:
        """Format result as text to feed back to the LLM."""
        if not self.success:
            return f"[Tool Error: {self.tool_name}] {self.error}"
        parts = [self.text]
        if self.images:
            parts.append(f"({len(self.images)} image(s) generated)")
        return "\n".join(parts)

    def to_sse_dict(self, arguments: dict | None = None, text_limit: int = 800) -> dict:
        """Compact payload for frontend tool_result SSE events."""
        payload: dict = {
            "tool": self.tool_name,
            "success": self.success,
            "text": (self.text if self.success else self.error)[:text_limit],
        }
        if arguments is not None:
            payload["arguments"] = arguments
        if self.sources:
            payload["sources"] = self.sources[:12]
        return payload



# ---------------------------------------------------------------------------
# Built-in tool handlers
# ---------------------------------------------------------------------------


def _handle_calculator(args: dict, **kwargs) -> ToolResult:
    expression = args.get("expression", "")
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
    except Exception as exc:
        return ToolResult(
            tool_name="calculator", success=False, error=f"Cannot evaluate '{expression}': {exc}"
        )
    return ToolResult(tool_name="calculator", text=f"{expression} = {result}")


def _handle_weather(args: dict, **kwargs) -> ToolResult:
    from backend.tools.weather import weather

    city = args.get("city", "")
    result = weather(city)
    return ToolResult(tool_name="get_weather", text=result)


def _handle_web_search(args: dict, **kwargs) -> ToolResult:
    from backend.tools.search import web_search

    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    result = web_search(query, max_results=max_results)
    # Soft-fail: clear error text for the agent, success=True so chat does not crash
    return ToolResult(tool_name="web_search", text=result)


def _handle_wikipedia(args: dict, **kwargs) -> ToolResult:
    from backend.tools.search import wikipedia_lookup

    query = args.get("query", "")
    lang = args.get("lang", "en")
    sentences = args.get("sentences", 4)
    result = wikipedia_lookup(query, lang=lang, sentences=sentences)
    return ToolResult(tool_name="wikipedia_lookup", text=result)


def _handle_arxiv(args: dict, **kwargs) -> ToolResult:
    from backend.tools.search import arxiv_search

    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    result = arxiv_search(query, max_results=max_results)
    return ToolResult(tool_name="arxiv_search", text=result)


def _handle_memory(args: dict, **kwargs) -> ToolResult:
    from backend.memory.store import add_fact

    fact = args.get("fact", "")
    add_fact(fact)
    return ToolResult(tool_name="remember_fact", text=f"Đã nhớ: {fact}")


def _handle_planning(args: dict, **kwargs) -> ToolResult:
    from backend.agent.planner import run_planning

    goal = args.get("goal", "")
    result = run_planning(goal)
    return ToolResult(tool_name="create_plan", text=result)


def _handle_autonomous(args: dict, **kwargs) -> ToolResult:
    from backend.agent.autonomous import run_autonomous

    goal = args.get("goal", "")
    result = run_autonomous(goal)
    return ToolResult(tool_name="run_autonomous", text=result)


def _handle_multi_agent(args: dict, **kwargs) -> ToolResult:
    from backend.agent.multi_agent import run_multi_agent

    task = args.get("task", "")
    result = run_multi_agent(task)
    return ToolResult(tool_name="run_multi_agent", text=result)


def _handle_workflow(args: dict, **kwargs) -> ToolResult:
    from backend.agent.workflow import run_workflow

    name = args.get("workflow_name", "")
    result = run_workflow(name)
    return ToolResult(tool_name="run_workflow", text=result)


def _handle_search_documents(args: dict, **kwargs) -> ToolResult:
    from backend.core.request_context import rag_project_or_default
    from backend.rag import engine as rag_engine

    query = args.get("query", "")
    top_k = int(args.get("top_k") or 4)
    allowed = args.get("allowed_sources")
    project_id = args.get("project_id") or rag_project_or_default()
    chunks = rag_engine.retrieve(
        project_id,
        query,
        top_k=top_k,
        allowed_sources=allowed if isinstance(allowed, list) else None,
    )
    if not chunks:
        return ToolResult(tool_name="search_documents", text="No relevant documents found.")
    lines = []
    sources: list[dict] = []
    for chunk in chunks:
        source = chunk.get("source", "Unknown")
        text = chunk.get("text", "")
        lines.append(f"[{source}]\n{text}")
        sources.append({"filename": source, "snippet": (text or "")[:280]})
    return ToolResult(
        tool_name="search_documents",
        text="Retrieved documents:\n\n" + "\n\n".join(lines),
        sources=sources,
    )


def _handle_summarize_documents(args: dict, **kwargs) -> ToolResult:
    from backend.core.request_context import rag_project_or_default
    from backend.rag import engine as rag_engine

    project_id = args.get("project_id") or rag_project_or_default()
    sources_filter = args.get("sources")
    data = rag_engine.summarize(
        project_id,
        sources=sources_filter if isinstance(sources_filter, list) else None,
    )
    src_names = data.get("sources") or []
    return ToolResult(
        tool_name="summarize_documents",
        text=f"Document summary:\n\n{data.get('markdown', '')}",
        sources=[{"filename": s, "snippet": ""} for s in src_names if isinstance(s, str)],
    )


def _handle_generate_document_report(args: dict, **kwargs) -> ToolResult:
    from backend.core.request_context import rag_project_or_default
    from backend.rag import engine as rag_engine

    project_id = args.get("project_id") or rag_project_or_default()
    sources_filter = args.get("sources")
    data = rag_engine.report(
        project_id,
        sources=sources_filter if isinstance(sources_filter, list) else None,
    )
    src_names = data.get("sources") or []
    return ToolResult(
        tool_name="generate_document_report",
        text=f"Document report:\n\n{data.get('markdown', '')}",
        sources=[{"filename": s, "snippet": ""} for s in src_names if isinstance(s, str)],
    )


def _handle_ocr_image(args: dict, **kwargs) -> ToolResult:
    images: list[bytes] | None = kwargs.get("images")
    if not images:
        return ToolResult(
            tool_name="ocr_image",
            success=False,
            error="No image attached. Upload an image with the chat message, then call ocr_image.",
        )
    from backend.tools.vision import ocr_image_bytes

    try:
        text = ocr_image_bytes(images[0], filename="upload.jpg")
        desc = args.get("image_description") or "uploaded image"
        return ToolResult(tool_name="ocr_image", text=f"OCR Result ({desc}):\n{text}")
    except Exception as exc:
        return ToolResult(tool_name="ocr_image", success=False, error=str(exc))


# Handler registry for built-in tools
_BUILTIN_HANDLERS = {
    "calculator": _handle_calculator,
    "weather": _handle_weather,
    "web_search": _handle_web_search,
    "search": _handle_web_search,  # legacy alias (fake KB removed)
    "wikipedia": _handle_wikipedia,
    "arxiv": _handle_arxiv,
    "memory": _handle_memory,
    "planning": _handle_planning,
    "autonomous": _handle_autonomous,
    "multi_agent": _handle_multi_agent,
    "workflow": _handle_workflow,
    "search_documents": _handle_search_documents,
    "summarize_documents": _handle_summarize_documents,
    "generate_document_report": _handle_generate_document_report,
    "ocr_image": _handle_ocr_image,
}


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------


async def execute_tool(
    tool_name: str,
    arguments: dict,
    images: list[bytes] | None = None,
) -> ToolResult:
    """
    Execute a tool by name with the given arguments.

    This is the main dispatcher called by the agent loop when the LLM
    returns a function_call.
    """
    metadata = get_tool_metadata(tool_name)
    if metadata is None:
        return ToolResult(tool_name=tool_name, success=False, error=f"Unknown tool: {tool_name}")

    handler_key = metadata.get("_handler")

    if handler_key and handler_key in _BUILTIN_HANDLERS:
        try:
            return _BUILTIN_HANDLERS[handler_key](arguments, images=images)
        except Exception as exc:
            logger.error("Built-in handler '%s' failed: %s", handler_key, exc)
            return ToolResult(tool_name=tool_name, success=False, error=str(exc))

    return ToolResult(tool_name=tool_name, success=False, error="No handler configured for this tool")
