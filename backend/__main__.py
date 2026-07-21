"""Run: python -m backend"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
