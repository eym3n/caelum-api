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
    read_lines,
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
    run_npx_command,
    run_git_command,
    git_log,
    git_show,
    check_css,
)

load_dotenv()

tools = [
    # File tools
    list_files,
    create_file,
    read_file,
    read_lines,
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
    run_npx_command,
    lint_project,
    run_git_command,
    git_log,
    git_show,
    check_css,
]

_coder_llm_ = ChatOpenAI(model="gpt-5").bind_tools(tools)


def coder(state: BuilderState) -> BuilderState:
    TODO_LIST = getattr(state, "planner_output", [])
    guidelines = state.design_guidelines.strip() if state.design_guidelines else ""
    guidelines_section = (
        "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n" + guidelines
        if guidelines
        else "\n\nCURRENT DESIGN SYSTEM GUIDELINES:\n- Design system guidelines not yet available. Coordinate with the design agent output or maintain neutral styling."
    )

    blueprint = (
        state.architecture_blueprint.strip() if state.architecture_blueprint else ""
    )
    blueprint_section = (
        "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n" + blueprint
        if blueprint
        else "\n\nCURRENT ARCHITECTURE BLUEPRINT:\n- Architecture blueprint not yet available. Coordinate with the architect agent output or confirm structure with the planner."
    )

    SYS = SystemMessage(
        content=CODER_SYSTEM_PROMPT
        + guidelines_section
        + blueprint_section
        + f"\n\nTODO List: {TODO_LIST}"
    )
    messages = [SYS, *state.messages]
    coder_response = _coder_llm_.invoke(messages)

    print(f"[CODER] {coder_response}")

    return {"messages": [coder_response], "coder_output": coder_response.content}
