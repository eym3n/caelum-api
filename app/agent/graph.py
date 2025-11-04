from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from app.agent.nodes.designer import designer
from app.agent.state import BuilderState
from app.agent.nodes.router import router
from app.agent.nodes.clarify import clarify
from app.agent.nodes.coder import coder
from app.agent.tools.files import (
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
    read_file,
    read_lines,
    update_file,
    update_lines,
    insert_lines,
)

from app.agent.tools.commands import (
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    run_npx_command,
    run_git_command,
    check_css,
    lint_project,
)
from app.checkpointer import get_default_checkpointer

load_dotenv()

print("🧱 Building agent graph...")


graph = StateGraph(BuilderState)


def edge_after_router(
    state: BuilderState,
) -> Literal["designer", "coder", "clarify", "__end__"]:
    if state.user_intent == "design":
        return "designer"
    if state.user_intent == "code":
        return "coder"
    if state.user_intent == "clarify":
        return "clarify"
    return "__end__"


def edge_after_designer(state: BuilderState) -> Literal["router"]:
    return "router"


def edge_after_architect(state: BuilderState) -> Literal["planner"]:
    """After architect completes, always proceed directly to planner to avoid loops."""
    return "planner"


file_tools = [
    # Batch operations (agents must use these)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
    read_file,
    read_lines,
    update_file,
    update_lines,
    insert_lines,
]

command_tools = [
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    run_npx_command,
    run_git_command,
    check_css,
    lint_project,
]

# Coder has access to both file and command tools (batch operations only)
coder_tools_node = ToolNode(file_tools + command_tools)
# Clarify only needs file reading (batch reads)
clarify_tools_node = ToolNode([batch_read_files, list_files])
# Designer has access to both file and command tools (batch operations only)
designer_tools_node = ToolNode(file_tools + command_tools)


graph.add_node("router", router)
graph.add_node("designer", designer)
graph.add_node("designer_tools", designer_tools_node)
graph.add_node("clarify", clarify)
graph.add_node("coder", coder)
graph.add_node("coder_tools", coder_tools_node)
graph.add_node("clarify_tools", clarify_tools_node)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", edge_after_router)

graph.add_conditional_edges(
    "designer",
    tools_condition,
    {"tools": "designer_tools", "__end__": "coder"},
)
graph.add_edge("designer_tools", "designer")


graph.add_conditional_edges(
    "coder",
    tools_condition,
    {
        "tools": "coder_tools",
        "__end__": END,
    },
)
graph.add_edge("coder_tools", "coder")

graph.add_conditional_edges(
    "clarify", tools_condition, {"tools": "clarify_tools", "__end__": END}
)
graph.add_edge("clarify_tools", "clarify")


checkpointer = get_default_checkpointer()
agent = graph.compile(checkpointer=checkpointer)
