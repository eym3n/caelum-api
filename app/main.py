import logging
import os
from fastapi import FastAPI
from app.routers import agent as agent_router
from app.routers import uploads as uploads_router
from app.routers import files as files_router
from app.routers import auth as auth_router
from app.routers import landing_pages as landing_pages_router

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


@app.on_event("startup")
async def startup_event():
    """Initialize database indexes and connections on startup."""
    from app.db import get_users_collection, get_landing_pages_collection

    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting up application...")

    # Create MongoDB indexes for users collection
    users_collection = get_users_collection()
    if users_collection is not None:
        try:
            # Create unique index on email
            users_collection.create_index("email", unique=True)
            logger.info("✅ Users collection indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create users indexes: {e}")
    else:
        logger.warning("⚠️ MongoDB not available, using fallback storage")

    # Create MongoDB indexes for landing pages collection
    landing_pages_collection = get_landing_pages_collection()
    if landing_pages_collection is not None:
        try:
            # Create index on user_id for efficient user queries
            landing_pages_collection.create_index("user_id")
            # Create unique index on session_id
            landing_pages_collection.create_index("session_id", unique=True)
            # Create index on status for filtering
            landing_pages_collection.create_index("status")
            # Create compound index for user + status queries
            landing_pages_collection.create_index([("user_id", 1), ("status", 1)])
            # Create index on created_at for sorting
            landing_pages_collection.create_index("created_at")
            logger.info("✅ Landing pages collection indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create landing pages indexes: {e}")

    logger.info("✨ Application startup complete")


app.include_router(auth_router.router, prefix="/v1/auth")
app.include_router(landing_pages_router.router, prefix="/v1/landing-pages")
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
