from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Create a single persistent connection for the checkpointer
# check_same_thread=False is required for FastAPI (multi-threaded environment)
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)


def get_default_checkpointer():
    return SqliteSaver(conn)
