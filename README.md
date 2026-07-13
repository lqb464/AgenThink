# AgenThink

Learning project: build an AI agent step by step, from a basic chatbot to a production-ready agent.

## Levels

| Level | Commit theme | What you learn |
| ----- | ------------ | -------------- |
| 0 | Basic chatbot | LLM API call |
| 1 | Chat with history | Conversation messages |
| 2 | System prompt | Persona / identity |
| 3 | Tool calling | One external tool |
| 4 | Multiple tools | Tool routing |
| 5 | RAG | BM25 retrieval over private docs |
| 6 | Long-term memory | Persistent user facts (SQLite) |
| 7 | Planning | Plan → execute → merge |
| 8 | Reflection | Critique and retry |
| 9 | Workflow | Fixed multi-step pipelines |
| 10 | Autonomous | Goal → act → observe loop |
| 11 | Multi-agent | Research / Coder / Reviewer / Writer |
| 12 | Production | Auth, rate limit, cache, retry, tracing, cost |

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Health check: `GET /health`  
Chat: `POST /chat` with `{"message": "..."}`

Optional production env:

- `API_TOKEN` — require `Authorization: Bearer <token>`
- `RATE_LIMIT_MAX_CALLS` / `RATE_LIMIT_WINDOW_SECONDS`
- `CACHE_ENABLED`
- `ESTIMATED_COST_PER_CALL_USD`

## Try

```text
Tính 2 + 3
Thời tiết ở Hà Nội
Tìm BM25
Nội quy nghỉ phép của công ty là gì?
Nhớ rằng User thích Python
Lập kế hoạch du lịch Nhật 7 ngày
Chạy workflow bao-cao-doanh-thu
Goal: Tính thuế VAT của 7 triệu
Team: Giải thích BM25
```
