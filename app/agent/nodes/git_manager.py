from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import GIT_MANAGER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.commands import run_git_command


tools = [run_git_command]

_git_llm_ = ChatOpenAI(
    model="gpt-4.1-mini-2025-04-14",
    # Force the model to produce a tool call first
    tool_choice="required",
).bind_tools(tools)


def git_manager(state: BuilderState) -> BuilderState:
    SYS = SystemMessage(content=GIT_MANAGER_SYSTEM_PROMPT)
    # Provide a minimal, unambiguous instruction to begin the git workflow.
    # Avoid passing prior conversational content that could distract the agent.
    BEGIN = HumanMessage(
        content=(
            "Begin git sync now. Start with 'rev-parse --is-inside-work-tree'. "
            "Respond ONLY with tool calls until the final summary."
        )
    )
    messages = [SYS, BEGIN]
    response = _git_llm_.invoke(messages)
    print(f"Git Manager response: {response}")
    return {
        "messages": [response],
        "summarizer_output": response.content,
    }
