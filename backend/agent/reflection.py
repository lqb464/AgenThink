from backend.core.client import llm

MAX_REFLECTION_ROUNDS = 2


def critique(question: str, answer: str) -> tuple[bool, str]:
    """Return (is_good_enough, feedback)."""
    if not (answer or "").strip():
        return False, "Empty answer — need a concrete response."
    # Very short drafts after tool use are usually incomplete
    if len(answer.strip()) < 12:
        return False, "Answer too short — expand with the tool results."

    prompt = (
        "You are a strict reviewer. Evaluate whether the answer adequately "
        "addresses the question.\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n"
        "Reply in exactly this format:\n"
        "VERDICT: PASS or FAIL\n"
        "FEEDBACK: <short feedback>"
    )
    try:
        raw = llm.chat(prompt)
    except Exception as exc:
        # On critique failure, accept the draft rather than blocking delivery
        return True, f"Critique skipped: {exc}"

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    verdict = "FAIL"
    feedback = raw.strip()
    for line in lines:
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()
    return verdict.startswith("PASS"), feedback


def improve(question: str, answer: str, feedback: str) -> str:
    prompt = (
        f"Question: {question}\n"
        f"Previous answer: {answer}\n"
        f"Reviewer feedback: {feedback}\n"
        "Write an improved answer."
    )
    return llm.chat(prompt)


def should_reflect(question: str, *, used_tools: bool, draft: str) -> bool:
    """Whether the agent loop should run a critique pass on this draft."""
    if not (draft or "").strip():
        return False
    if used_tools:
        return True
    text = (question or "").strip()
    return len(text) >= 60


def reflect_until_good(question: str, draft: str, max_rounds: int = MAX_REFLECTION_ROUNDS) -> str:
    answer = draft
    for _ in range(max_rounds):
        ok, feedback = critique(question, answer)
        if ok:
            return answer
        answer = improve(question, answer, feedback)
    return answer
