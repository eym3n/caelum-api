from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from app.agent.nodes.design_planner import design_planner
from app.agent.nodes.design_blueprint_pdf import design_blueprint_pdf
from app.agent.state import BuilderState
from app.agent.nodes.router import router
from app.agent.nodes.clarify import clarify
from app.agent.nodes.generate_section import generate_section
from app.agent.nodes.codegen import codegen
from app.agent.nodes.followup_codegen import followup_codegen
from app.agent.nodes.linting import linting
from app.agent.nodes.fix_errors import fix_errors
from app.agent.nodes.deployer import deployer
from app.agent.nodes.deployment_fixer import deployment_fixer
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
) -> Literal[
    "design_planner",
    "generate_section",
    "followup_codegen",
    "clarify",
    "deployer",
    "__end__",
]:
    if state.user_intent == "design":
        return "design_planner"
    if state.user_intent == "code":
        if state.is_followup:
            return "followup_codegen"
        return "generate_section"
    if state.user_intent == "clarify":
        return "clarify"
    if state.user_intent == "deploy":
        return "deployer"
    return "__end__"


def edge_after_design_planner(state: BuilderState) -> Literal["generate_section"]:
    """After design_planner generates the blueprint, proceed to section generation."""
    return "generate_section"


file_tools = [
    # Batch operations (agents must use these)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
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

# Clarify only needs file reading (batch reads)
clarify_tools_node = ToolNode([batch_read_files, list_files])
# Deployment fixer has access to both file and command tools (batch operations only)
deployment_fixer_tools_node = ToolNode(file_tools + command_tools)
fix_errors_tools_node = ToolNode(file_tools + command_tools)
followup_codegen_tools = [
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    lint_project,
]
followup_codegen_tools_node = ToolNode(followup_codegen_tools)


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


def edge_after_linting(state: BuilderState) -> Literal["fix_errors", "deployer"]:
    if state.lint_failed:
        print("❌ Lint failed, routing to fix_errors.")
        return "fix_errors"
    print("✅ Lint passed, proceeding to deployment.")
    return "deployer"


graph.add_node("router", router)
graph.add_node("design_planner", design_planner)
graph.add_node("clarify", clarify)
graph.add_node("generate_section", generate_section)
graph.add_node("codegen", codegen)
graph.add_node("followup_codegen", followup_codegen)
graph.add_node("linting", linting)
graph.add_node("design_blueprint_pdf", design_blueprint_pdf)
graph.add_node("deployer", deployer)
graph.add_node("deployment_fixer", deployment_fixer)
graph.add_node("fix_errors", fix_errors)
graph.add_node("deployment_fixer_tools", deployment_fixer_tools_node)
graph.add_node("fix_errors_tools", fix_errors_tools_node)
graph.add_node("clarify_tools", clarify_tools_node)
graph.add_node("followup_codegen_tools", followup_codegen_tools_node)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", edge_after_router)

# Design planner hands off to section generation and documentation
graph.add_edge("design_planner", "generate_section")
graph.add_edge("design_planner", "design_blueprint_pdf")
graph.add_edge("design_blueprint_pdf", END)

graph.add_edge("generate_section", "codegen")
graph.add_edge("codegen", "linting")
graph.add_conditional_edges(
    "followup_codegen",
    tools_condition,
    {
        "tools": "followup_codegen_tools",
        "__end__": "linting",
    },
)
graph.add_edge("followup_codegen_tools", "followup_codegen")
graph.add_conditional_edges("linting", edge_after_linting)
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
    "fix_errors",
    tools_condition,
    {
        "tools": "fix_errors_tools",
        "__end__": "linting",
    },
)
graph.add_edge("fix_errors_tools", "fix_errors")

graph.add_conditional_edges(
    "clarify", tools_condition, {"tools": "clarify_tools", "__end__": END}
)
graph.add_edge("clarify_tools", "clarify")


checkpointer = get_default_checkpointer()
agent = graph.compile(checkpointer=checkpointer)
