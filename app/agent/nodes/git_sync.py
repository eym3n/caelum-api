from __future__ import annotations

import subprocess
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.agent.state import BuilderState


def git_sync(state: BuilderState) -> BuilderState:
    """Deterministically initialize repo if needed and commit staged changes.

    Runs scripts/git_sync.sh with the current session id and returns a short summary.
    """
    session_id = state.__dict__.get("configurable", {}).get("session_id", "default")
    # Fallback: some runners pass session via config in the graph compile; ensure robustness
    if not isinstance(session_id, str):
        session_id = "default"

    try:
        result = subprocess.run(
            ["bash", "scripts/git_sync.sh", session_id],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        if result.returncode == 0:
            msg = AIMessage(content=f"Git sync complete.\n\n{output}")
        else:
            msg = AIMessage(content=f"Git sync error:\n\n{output}")
    except subprocess.TimeoutExpired:
        msg = AIMessage(content="Git sync timed out.")
    except Exception as e:
        msg = AIMessage(content=f"Git sync exception: {e}")

    return {"messages": [msg], "summarizer_output": msg.content}


