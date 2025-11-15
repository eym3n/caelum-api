from __future__ import annotations

import os
import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

try:
    from pymongo import MongoClient  # type: ignore
    from langgraph.checkpoint.mongodb import MongoDBSaver  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    MongoClient = None  # type: ignore
    MongoDBSaver = None  # type: ignore


_MONGO_CLIENT: Optional["MongoClient"] = None
_MONGO_SAVER: Optional[object] = None
_DEFAULT_SAVER: Optional[object] = None


def get_mongo_client() -> Optional["MongoClient"]:
    """
    Return a cached MongoClient if MONGODB_URI is configured and pymongo is installed.
    """
    global _MONGO_CLIENT
    if _MONGO_CLIENT is not None:
        return _MONGO_CLIENT
    uri = (
        os.getenv("MONGODB_URI")
        or os.getenv("MONGO_URI")
        or os.getenv("MONGODB_ATLAS_URI")
    )
    if not uri or MongoClient is None:
        return None
    try:
        # Keep selection timeout short so startup doesn't block for long
        _MONGO_CLIENT = MongoClient(
            uri,
            serverSelectionTimeoutMS=int(
                os.getenv("MONGODB_SELECT_TIMEOUT_MS", "3000")
            ),
        )
        # Optional connectivity check (can be disabled)
        if (
            os.getenv("MONGODB_PING_ON_BOOT", "1") in {"1", "true", "yes"}
        ) and MongoClient is not None:
            _MONGO_CLIENT.admin.command("ping")
        return _MONGO_CLIENT
    except Exception as e:
        logging.getLogger(__name__).warning(
            "Mongo unavailable, falling back to memory: %s", str(e)
        )
        _MONGO_CLIENT = None
        return None


def get_mongo_checkpointer() -> Optional[object]:
    """
    Create (and cache) a MongoDBSaver checkpointer when MongoDB is available.
    Uses env vars to configure names and TTL.
    """
    global _MONGO_SAVER
    if _MONGO_SAVER is not None:
        return _MONGO_SAVER
    client = get_mongo_client()
    if client is None or MongoDBSaver is None:
        return None

    db_name = os.getenv("MONGODB_DB", "langgraph_ckpt")
    ckpt_coll = os.getenv("MONGODB_CHECKPOINT_COLL", "checkpoints")
    writes_coll = os.getenv("MONGODB_WRITES_COLL", "writes")
    ttl_seconds = int(
        os.getenv("MONGODB_TTL_SECONDS", str(60 * 60 * 24 * 30))
    )  # 30 days

    try:
        _MONGO_SAVER = MongoDBSaver(
            client,
            db_name=db_name,
            checkpoint_collection_name=ckpt_coll,
            writes_collection_name=writes_coll,
            ttl=ttl_seconds,
        )
        # Trigger lightweight index creation/listing now to surface issues early
        try:
            _ = list(_MONGO_SAVER.checkpoint_collection.list_indexes())  # type: ignore[attr-defined]
        except Exception:
            pass
        return _MONGO_SAVER
    except Exception as e:
        logging.getLogger(__name__).warning(
            "MongoDB checkpointer not available, using memory: %s", str(e)
        )
        _MONGO_SAVER = None
        return None


def get_default_checkpointer() -> object:
    """
    Default reusable checkpointer for LangGraph.
    Prefers MongoDB persistence if configured; otherwise falls back to MemorySaver.
    """
    global _DEFAULT_SAVER
    if _DEFAULT_SAVER is not None:
        return _DEFAULT_SAVER
    mongo = get_mongo_checkpointer()
    if mongo is not None:
        _DEFAULT_SAVER = mongo
    else:
        _DEFAULT_SAVER = MemorySaver()
    return _DEFAULT_SAVER
