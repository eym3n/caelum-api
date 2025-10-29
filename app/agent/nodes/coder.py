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

from app.agent.tools.commands import (
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
)

load_dotenv()

tools = [
    # File tools
    list_files,
    create_file,
    read_file,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
    # Command tools
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    lint_project,
]

_coder_llm_ = ChatOpenAI(model="gpt-5").bind_tools(tools)


def coder(state: BuilderState) -> BuilderState:
    TODO_LIST = state.planner_output

    SYS = SystemMessage(content=CODER_SYSTEM_PROMPT + f"\nTODO List: {TODO_LIST}")
    messages = [SYS, *state.messages]
    coder_response = _coder_llm_.invoke(messages)

    return {"messages": [coder_response], "coder_output": coder_response.content}
