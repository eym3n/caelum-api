from __future__ import annotations
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
import re

from app.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import list_files, read_file

load_dotenv()

tools = [list_files, read_file]

_planner_llm_ = ChatOpenAI(model="gpt-4.1").bind_tools(tools)


def planner(state: BuilderState) -> BuilderState:
    SYS = SystemMessage(content=PLANNER_SYSTEM_PROMPT)
    messages = [SYS, *state.messages]
    planner_response = _planner_llm_.invoke(messages)

    print(f"[PLANNER] Response has tool_calls: {bool(planner_response.tool_calls)}")

    # If the planner wants to call tools, return early to execute them
    if planner_response.tool_calls:
        print(f"[PLANNER] Calling {len(planner_response.tool_calls)} tool(s)")
        return {"messages": [planner_response]}

    # Extract todo list from the response content
    content = planner_response.content
    todo_list = []

    if content:
        # Parse numbered or bulleted list from content
        # Look for lines starting with numbers (1., 2., etc.) or bullets (-, *, •)
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            # Match patterns like "1. Task", "- Task", "* Task", "• Task"
            match = re.match(r"^(?:\d+\.|\-|\*|•)\s+(.+)$", line)
            if match:
                todo_list.append(match.group(1))

    # If no todo items found, use the full content as a single item
    if not todo_list and content:
        todo_list = [content]

    print(f"[PLANNER] Extracted {len(todo_list)} todo items: {todo_list}")

    return {"messages": [planner_response], "planner_output": todo_list}
