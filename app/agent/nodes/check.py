from __future__ import annotations

import subprocess
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.agent.state import BuilderState


def checker_node(state: BuilderState) -> BuilderState:
    """Checks if coder agent made changes or called tools, if not loop back to coder with its output as new input."""
    coder_response = state.messages[-1]
    if "tool_calls" in coder_response.additional_kwargs:
        # Coder made tool calls, proceed normally
        return state
    else:
        # No tool calls, add a message and loop back to coder
        loop_msg = AIMessage(
            content=(
                "It seems you did not make any code changes or call any tools. "
                "Please review the project requirements and provide the necessary code updates or tool calls."
            )
        )
        state.messages.append(loop_msg)

    return state
