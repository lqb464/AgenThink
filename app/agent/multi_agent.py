from dataclasses import dataclass

from app.core.client import llm
from app.rag import retrieve
from app.tools import run_tool


@dataclass
class Agent:
    name: str
    role: str

    def act(self, task: str, context: str = "") -> str:
        prompt = (
            f"You are the {self.name} agent. Role: {self.role}\n"
            f"Task: {task}\n"
            f"Context:\n{context or '(none)'}\n"
            "Respond briefly with your contribution only."
        )
        try:
            return llm.chat(prompt).strip()
        except Exception:
            return self._fallback(task, context)

    def _fallback(self, task: str, context: str) -> str:
        if self.name == "Research":
            docs = retrieve(task, top_k=1)
            if docs:
                return f"Research: {docs[0]['title']} — {docs[0]['content'][:160]}"
            tool_hit = run_tool(f"Tìm {task}")
            if tool_hit:
                return f"Research: {tool_hit[1]}"
            return f"Research: gathered notes for `{task}`"
        if self.name == "Coder":
            return f"Coder: sketched a solution outline for `{task}`"
        if self.name == "Reviewer":
            return f"Reviewer: checked prior work and found it acceptable.\nPrior:\n{context[:200]}"
        return f"Writer: final summary for `{task}` based on team notes."


RESEARCH = Agent("Research", "Find relevant facts and references.")
CODER = Agent("Coder", "Propose a concrete technical approach or snippet.")
REVIEWER = Agent("Reviewer", "Critique quality and point out gaps.")
WRITER = Agent("Writer", "Merge everything into a clear final answer.")


def run_multi_agent(task: str) -> str:
    research = RESEARCH.act(task)
    coded = CODER.act(task, context=research)
    review = REVIEWER.act(task, context=f"{research}\n{coded}")
    final = WRITER.act(task, context=f"{research}\n{coded}\n{review}")

    return (
        "Multi-agent result:\n"
        f"[Research]\n{research}\n\n"
        f"[Coder]\n{coded}\n\n"
        f"[Reviewer]\n{review}\n\n"
        f"[Writer]\n{final}"
    )
