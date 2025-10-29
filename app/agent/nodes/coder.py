from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI


from app.agent.prompts import CODER_SYSTEM_PROMPT
from app.agent.state import BuilderState

from app.agent.tools.files import (
    list_files,
    create_file,
    read_file,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
)

load_dotenv()

tools = [
    list_files,
    create_file,
    read_file,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
]

_coder_llm_ = ChatOpenAI(model="gpt-5-mini").bind_tools(tools)


def coder(state: BuilderState) -> BuilderState:
    TODO_LIST = state.planner_output

    SYS = SystemMessage(content=CODER_SYSTEM_PROMPT + f"\nTODO List: {TODO_LIST}")
    messages = [SYS, *state.messages]
    coder_response = _coder_llm_.invoke(messages)

    return {"messages": [coder_response], "coder_output": coder_response.content}
