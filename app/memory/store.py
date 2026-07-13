import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "chat_memory.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def add_fact(fact: str) -> None:
    fact = fact.strip()
    if not fact:
        return
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO memories (fact) VALUES (?)",
            (fact,),
        )
        conn.commit()
    finally:
        conn.close()


def list_facts() -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT fact FROM memories ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


def clear_facts() -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM memories")
        conn.commit()
    finally:
        conn.close()


def format_memory(facts: list[str] | None = None) -> str:
    facts = list_facts() if facts is None else facts
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"Long-term memory about the user:\n{lines}"


_EXPLICIT_RE = re.compile(
    r"^(?:Nhớ rằng|Remember that)\s+(.+)$",
    flags=re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"^(?:Tên tôi là|My name is)\s+(.+)$",
    flags=re.IGNORECASE,
)
_LIKE_RE = re.compile(
    r"^(?:Tôi thích|I like)\s+(.+)$",
    flags=re.IGNORECASE,
)
_LIVE_RE = re.compile(
    r"^(?:Tôi ở|I live in)\s+(.+)$",
    flags=re.IGNORECASE,
)


def extract_and_store(message: str) -> str | None:
    """Detect memorable facts, store them, and optionally return a confirmation."""
    text = message.strip()

    match = _EXPLICIT_RE.match(text)
    if match:
        fact = match.group(1).strip(" .")
        add_fact(fact)
        return f"Đã nhớ: {fact}"

    match = _NAME_RE.match(text)
    if match:
        name = match.group(1).strip(" .")
        add_fact(f"Tên người dùng là {name}")
        return None

    match = _LIKE_RE.match(text)
    if match:
        liked = match.group(1).strip(" .")
        add_fact(f"Người dùng thích {liked}")
        return None

    match = _LIVE_RE.match(text)
    if match:
        place = match.group(1).strip(" .")
        add_fact(f"Người dùng ở {place}")
        return None

    return None
