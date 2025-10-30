from langgraph.graph.message import add_messages

from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Annotated

load_dotenv()


def replace(a, b):
    return b


class BuilderState(BaseModel):
    # Core conversational stream
    messages: Annotated[list, add_messages]

    # Conditional branching
    user_intent: Annotated[str, replace]
    found_error: Annotated[bool, replace]

    # Tools
    lines_added: Annotated[int, replace]
    lines_removed: Annotated[int, replace]

    # Design System
    design_system_run: Annotated[bool, replace] = False
    design_guidelines: Annotated[str, replace] = ""

    # Architecture
    architect_system_run: Annotated[bool, replace] = False
    architect_pending: Annotated[bool, replace] = False
    architecture_blueprint: Annotated[str, replace] = ""

    # Planner
    todo_list: Annotated[list, replace]
    planner_output: Annotated[list, replace]

    # Architect
    guideline_list: Annotated[list, replace]
    architect_output: Annotated[str, replace]

    # Coder
    coder_output: Annotated[str, replace]

    # summarizer
    summarizer_output: Annotated[str, replace]

    # Clarifier
    clarify_response: Annotated[str, replace]
