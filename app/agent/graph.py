from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from app.agent.nodes.design_planner import design_planner
from app.agent.nodes.designer import designer
from app.agent.state import BuilderState
from app.agent.nodes.router import router
from app.agent.nodes.clarify import clarify
from app.agent.nodes.coder import coder
from app.agent.nodes.deployer import deployer
from app.agent.nodes.deployment_fixer import deployment_fixer
from app.agent.tools.files import (
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
    # Utility
    list_files,
    read_file,
    read_lines,
    update_file,
    update_lines,
    insert_lines,
)

from app.agent.tools.commands import (
    run_git_command,
    git_log,
    git_show,
    lint_project,
)
from app.db import get_default_checkpointer

load_dotenv()

print("🧱 Building agent graph...")


graph = StateGraph(BuilderState)


def edge_after_router(
    state: BuilderState,
) -> Literal["design_planner", "coder", "clarify", "__end__"]:
    if state.user_intent == "design":
        # Route to design_planner first (it will then go to designer)
        return "design_planner"
    if state.user_intent == "code":
        return "coder"
    if state.user_intent == "clarify":
        return "clarify"
    return "__end__"


def edge_after_design_planner(state: BuilderState) -> Literal["designer"]:
    """After design_planner generates guidelines, always proceed to designer."""
    return "designer"


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
    run_git_command,
    git_log,
    git_show,
    lint_project,
]

# Coder has access to both file and command tools (batch operations only)
coder_tools_node = ToolNode(file_tools + command_tools)
# Clarify only needs file reading (batch reads)
clarify_tools_node = ToolNode([batch_read_files, list_files])
designer_file_tools = [
    # Read any files (needed to understand context)
    batch_read_files,
    read_file,
    read_lines,
    # Design-only create/update operations: restricted to globals.css, tailwind.config.ts, layout.tsx
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
]
designer_tools_node = ToolNode(designer_file_tools + command_tools)
# Deployment fixer has access to both file and command tools (batch operations only)
deployment_fixer_tools_node = ToolNode(file_tools + command_tools)


def edge_after_coder(
    state: BuilderState,
) -> Literal["deployer", "coder"]:
    coder_run = state.coder_run
    if coder_run:
        print("🔄 Coder made tool calls, proceeding to deployment.")
        return "deployer"
    else:
        print("🔄 Coder made no tool calls, routing back to coder.")
        return "coder"


def edge_after_deployer(
    state: BuilderState,
) -> Literal["deployment_fixer", "__end__"]:
    """Route to deployment_fixer if deployment failed, otherwise end."""
    if state.deployment_failed:
        print("🔄 Deployment failed, routing to deployment fixer.")
        return "deployment_fixer"
    else:
        print("✅ Deployment successful, ending workflow.")
        return "__end__"


def edge_after_deployment_fixer(
    state: BuilderState,
) -> Literal["deployer", "deployment_fixer"]:
    """Route back to deployer after fixes, or stay in fixer if no tool calls."""
    if state.deployment_fixer_run:
        print("🔄 Deployment fixer made changes, re-running deployment.")
        return "deployer"
    else:
        print("🔄 Deployment fixer analyzing, continuing...")
        return "deployment_fixer"


def noop(state: BuilderState) -> BuilderState:
    print("⏭️ No operation node reached.")
    return {}


graph.add_node("router", router)
graph.add_node("design_planner", design_planner)
graph.add_node("designer", designer)
graph.add_node("designer_tools", designer_tools_node)
graph.add_node("clarify", clarify)
graph.add_node("coder", coder)
graph.add_node("coder_tools", coder_tools_node)
graph.add_node("check", noop)
graph.add_node("deployer", deployer)
graph.add_node("deployment_fixer", deployment_fixer)
graph.add_node("deployment_fixer_tools", deployment_fixer_tools_node)
graph.add_node("clarify_tools", clarify_tools_node)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", edge_after_router)

# Design planner → designer (no tools, just structured output)
graph.add_edge("design_planner", "designer")

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
        "__end__": "check",
    },
)
graph.add_edge("coder_tools", "coder")
graph.add_conditional_edges("check", edge_after_coder)
graph.add_conditional_edges("deployer", edge_after_deployer)

# Deployment fixer workflow
graph.add_conditional_edges(
    "deployment_fixer",
    tools_condition,
    {
        "tools": "deployment_fixer_tools",
        "__end__": "deployer",  # If no tool calls, try deployment again anyway
    },
)
graph.add_edge("deployment_fixer_tools", "deployment_fixer")

graph.add_conditional_edges(
    "clarify", tools_condition, {"tools": "clarify_tools", "__end__": END}
)
graph.add_edge("clarify_tools", "clarify")


checkpointer = get_default_checkpointer()
agent = graph.compile(checkpointer=checkpointer)
