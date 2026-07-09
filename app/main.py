from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(
    title="AgenThink",
    version="0.1.0",
)

app.include_router(chat_router)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }