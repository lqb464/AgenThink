import re

# Tiny demo knowledge base for the search tool.
DOCS = [
    {
        "title": "Messi",
        "content": "Lionel Messi là cầu thủ bóng đá người Argentina, từng ghi bàn ở World Cup 2022.",
    },
    {
        "title": "BM25",
        "content": "BM25 là thuật toán xếp hạng tài liệu dựa trên tần suất từ khóa, dùng phổ biến trong search.",
    },
    {
        "title": "VAT",
        "content": "VAT (thuế giá trị gia tăng) ở Việt Nam thường là 10%.",
    },
]


def search(query: str) -> str:
    query_lower = query.lower()
    hits = [
        doc
        for doc in DOCS
        if query_lower in doc["title"].lower() or query_lower in doc["content"].lower()
    ]
    if not hits:
        return f"Không tìm thấy thông tin cho '{query}'."

    return "\n".join(f"- {doc['title']}: {doc['content']}" for doc in hits)


def match_search(message: str) -> str | None:
    match = re.fullmatch(r"(?:Tìm|Search)\s+(.+)", message.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return search(match.group(1).strip())
