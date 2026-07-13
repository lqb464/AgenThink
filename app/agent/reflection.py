from app.core.client import llm

MAX_REFLECTION_ROUNDS = 2


def critique(question: str, answer: str) -> tuple[bool, str]:
    """Return (is_good_enough, feedback)."""
    prompt = (
        "You are a strict reviewer. Evaluate whether the answer adequately "
        "addresses the question.\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n"
        "Reply in exactly this format:\n"
        "VERDICT: PASS or FAIL\n"
        "FEEDBACK: <short feedback>"
    )
    raw = llm.chat(prompt)
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


def reflect_until_good(question: str, draft: str, max_rounds: int = MAX_REFLECTION_ROUNDS) -> str:
    answer = draft
    for _ in range(max_rounds):
        ok, feedback = critique(question, answer)
        if ok:
            return answer
        answer = improve(question, answer, feedback)
    return answer
