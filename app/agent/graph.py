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
from app.agent.state import BuilderState
from app.agent.nodes.router import router
from app.agent.nodes.clarify import clarify
from app.agent.nodes.planner import planner
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


graph = StateGraph(BuilderState)


def edge_after_router(state: BuilderState) -> Literal["planner", "clarify", END]:
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


file_tools = [
    list_files,
    create_file,
    read_file,
    update_file,
    delete_file,
    remove_lines,
    insert_lines,
    update_lines,
]

coder_tools_node = ToolNode(file_tools)
clarify_tools_node = ToolNode([list_files, read_file])
planner_tools_node = ToolNode([list_files, read_file])


graph.add_node("router", router)
graph.add_node("clarify", clarify)
graph.add_node("planner", planner)
graph.add_node("coder", coder)
graph.add_node("coder_tools", coder_tools_node)
graph.add_node("clarify_tools", clarify_tools_node)
graph.add_node("planner_tools", planner_tools_node)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", edge_after_router)

# Planner can use tools to read existing files before planning
graph.add_conditional_edges("planner", edge_after_planner)
graph.add_edge("planner_tools", "planner")
graph.add_conditional_edges(
    "coder", tools_condition, {"tools": "coder_tools", "__end__": END}
)
graph.add_edge("coder_tools", "coder")

graph.add_conditional_edges(
    "clarify", tools_condition, {"tools": "clarify_tools", "__end__": END}
)
graph.add_edge("clarify_tools", "clarify")


checkpointer = MemorySaver()
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
