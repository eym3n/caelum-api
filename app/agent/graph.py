from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool, BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from app.agent.nodes.coder import coder

# from app.agent.nodes.git_sync import git_sync  # Commented out for now
from app.agent.nodes.architect import architect
from app.agent.nodes.designer import designer
from app.agent.nodes.planner import planner
from app.agent.state import BuilderState
from app.agent.nodes.router import router
from app.agent.nodes.clarify import clarify
from app.agent.nodes.planner import planner
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
    run_npx_command,
    run_git_command,
    check_css,
    lint_project,
)
from app.checkpointer import get_default_checkpointer

load_dotenv()


graph = StateGraph(BuilderState)


def edge_from_start(state: BuilderState) -> Literal["designer", "architect", "router"]:
    if not state.design_system_run:
        return "designer"
    if not state.architect_system_run:
        return "architect"
    return "router"


def edge_after_router(
    state: BuilderState,
) -> Literal["planner", "clarify", "architect", END]:
    if state.user_intent == "architect":
        return "architect"
    if state.user_intent == "code":
        return "planner"
    elif state.user_intent == "clarify":
        return "clarify"
    else:
        return END


def edge_after_planner(state: BuilderState) -> Literal["planner_tools", "coder"]:
    """Route planner to tools if it called them, otherwise to coder."""
    last_message = state.messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "planner_tools"
    return "coder"


def noop(state: BuilderState) -> BuilderState:
    return {}


def edge_after_designer(state: BuilderState) -> Literal["architect", "router"]:
    if not state.architect_system_run:
        return "architect"
    return "router"


def edge_after_architect(state: BuilderState) -> Literal["planner"]:
    """After architect completes, always proceed directly to planner to avoid loops."""
    return "planner"


file_tools = [
    list_files,
    create_file,
    read_file,
    read_lines,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
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

# Coder has access to both file and command tools
coder_tools_node = ToolNode(file_tools + command_tools)
# Clarify and planner only need file reading tools
clarify_tools_node = ToolNode([list_files, read_file, read_lines])
planner_tools_node = ToolNode([list_files, read_file, read_lines])
designer_tools_node = ToolNode(file_tools + command_tools)
architect_tools_node = ToolNode([list_files, read_file, read_lines])


graph.add_node("designer", designer)
graph.add_node("designer_tools", designer_tools_node)
graph.add_node("designer_post", noop)
graph.add_node("architect", architect)
graph.add_node("architect_tools", architect_tools_node)
graph.add_node("architect_post", noop)
graph.add_node("router", router)
graph.add_node("clarify", clarify)
graph.add_node("planner", planner)
graph.add_node("coder", coder)
graph.add_node("coder_tools", coder_tools_node)
# graph.add_node("git_sync", git_sync)  # Commented out for now
graph.add_node("clarify_tools", clarify_tools_node)
graph.add_node("planner_tools", planner_tools_node)

graph.add_conditional_edges(START, edge_from_start)
graph.add_conditional_edges("router", edge_after_router)

# Planner can use tools to read existing files before planning
graph.add_conditional_edges("planner", edge_after_planner)
graph.add_edge("planner_tools", "planner")
graph.add_conditional_edges(
    "coder",
    tools_condition,
    {
        "tools": "coder_tools",
        "__end__": END,
    },  # Changed '__end__' from 'git_sync' to END
)
graph.add_edge("coder_tools", "coder")
# graph.add_edge("git_sync", END)  # Commented out for now

graph.add_conditional_edges(
    "designer",
    tools_condition,
    {"tools": "designer_tools", "__end__": "designer_post"},
)
graph.add_conditional_edges("designer_post", edge_after_designer)
graph.add_edge("designer_tools", "designer")

graph.add_conditional_edges(
    "architect",
    tools_condition,
    {"tools": "architect_tools", "__end__": "architect_post"},
)
graph.add_edge("architect_post", "planner")
graph.add_edge("architect_tools", "architect")

graph.add_conditional_edges(
    "clarify", tools_condition, {"tools": "clarify_tools", "__end__": END}
)
graph.add_edge("clarify_tools", "clarify")


checkpointer = get_default_checkpointer()
agent = graph.compile(checkpointer=checkpointer)

# if __name__ == "__main__":
#     import os

#     OUTPUT_DIR = "__out__"

#     # Empty the output directory
#     for file in os.listdir(OUTPUT_DIR):
#         os.remove(os.path.join(OUTPUT_DIR, file))

#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == "exit":
#             break
#         result = agent.invoke(
#             {"messages": [HumanMessage(content=user_input)]},
#             config={"configurable": {"thread_id": "1"}},
#         )
