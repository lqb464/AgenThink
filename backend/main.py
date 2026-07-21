from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.docs import router as docs_router
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AgenThink",
    version="1.0.0",
    description="JWT multi-user agent with tools, streaming, RAG, and OCR",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(docs_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
