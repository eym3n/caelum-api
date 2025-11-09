import logging
import os
from fastapi import FastAPI
from app.routers import agent as agent_router
from app.routers import uploads as uploads_router
from app.routers import files as files_router

from fastapi.middleware.cors import CORSMiddleware


def _configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


_configure_logging()

app = FastAPI(title="Ayor Dashboard Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agent_router.router, prefix="/v1/agent")
app.include_router(uploads_router.router, prefix="/v1/uploads")
app.include_router(files_router.router, prefix="/v1/files")


# Basic health
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    # Lazy import to keep tool deps optional outside of this endpoint
    try:
        from app.agent.tools.run_sql import test_db_connection  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"import_error: {e}"}
    return test_db_connection()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8080, reload=True, reload_dirs=["app"]
    )
