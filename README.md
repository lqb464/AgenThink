# AgenThink

Multi-user AI agent: chat with tool calling, streaming, JWT auth, **in-process RAG (Tri thức)**, and **Gemini vision OCR** — all inside this single repo.

## Layout

| Folder | Role |
| ------ | ---- |
| `backend/` | FastAPI API (+ `backend/Dockerfile`) |
| `frontend/` | Next.js UI (+ `frontend/Dockerfile`) |

## Features

- **Agent loop** — plan → tools → observe → reflect, with SSE progress
- **Multi-user auth** — register / login; isolated sessions + knowledge per user
- **Tri thức (RAG)** — upload PDF/DOCX/MD/TXT → chunk → Gemini embeddings → cosine retrieve
- **OCR** — Gemini multimodal extract text from uploaded images
- **Web search** — SearXNG (in Docker Compose) + Wikipedia / arXiv tools
- **Built-in tools** — calculator, weather, memory

## Quick start

```powershell
copy .env.example .env
# Set GEMINI_API_KEY and JWT_SECRET

docker compose up --build -d
```

Open [http://localhost:3000](http://localhost:3000).

| | |
| - | - |
| UI | http://localhost:3000 |
| OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/api/health |

Demo user (if seeded): `demo@local` / `change-me`.

### Dev without Docker

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
copy .env.example .env
# Set GEMINI_API_KEY and JWT_SECRET

python -m backend
# Dev reload: set RELOAD=1   or   python -m backend  with RELOAD=true
# UI: cd frontend && npm install && npm run dev
```

## Architecture

```text
Browser (:3000)  →  AgenThink API (:8000)  →  Gemini / local LLM
                         │
                         ├── Local RAG  (data/rag/{project_id}/)
                         ├── Vision OCR (Gemini multimodal)
                         └── SearXNG (:8080)  web_search
```

## Configuration

| Variable | Role |
| -------- | ---- |
| `GEMINI_*` / `OPENAI_*` | LLM + embeddings + OCR |
| `RAG_DATA_DIR` | Local knowledge store (default `./data/rag`) |
| `JWT_SECRET`, `AUTH_REQUIRED` | Auth |
| `SEARXNG_URL` | Web search (Compose sets `http://searxng:8080`; local API use `http://localhost:8080`) |

## Example prompts

```text
Tính 2 + 3
Nội quy nghỉ phép của công ty là gì?   (demo BM25 corpus if no uploads)
Tóm tắt các tài liệu trong Tri thức
OCR / đọc chữ trong ảnh vừa upload
```

Repo: https://github.com/lqb464/AgenThink
