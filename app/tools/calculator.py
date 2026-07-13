import re


def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        return f"Không tính được biểu thức '{expression}': {exc}"

    return f"{expression} = {result}"


def match_calculator(message: str) -> str | None:
    match = re.fullmatch(r"Tính\s+(.+)", message.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return calculator(match.group(1).strip())
