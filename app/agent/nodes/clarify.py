from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from app.agent.prompts import CLARIFY_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import list_files, read_file, read_lines

load_dotenv()

tools = [list_files, read_file, read_lines]

_clarify_llm_ = ChatOpenAI(model="gpt-4.1-mini-2025-04-14").bind_tools(tools)


def clarify(state: BuilderState) -> BuilderState:
    SYS = SystemMessage(content=CLARIFY_SYSTEM_PROMPT)
    messages = [SYS, *state.messages]
    clarify_response = _clarify_llm_.invoke(messages)
    print(f"Clarify response: {clarify_response}")
    return {
        "messages": [clarify_response],
        "clarify_response": clarify_response.content,
    }
