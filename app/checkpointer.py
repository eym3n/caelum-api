from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from app.db import get_mongo_checkpointer


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
