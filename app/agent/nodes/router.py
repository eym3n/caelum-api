from __future__ import annotations
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from app.agent.prompts import ROUTER_SYSTEM_PROMPT
from app.agent.state import BuilderState

load_dotenv()

_router_llm_ = ChatOpenAI(model="gpt-4.1-mini-2025-04-14")

from pydantic import BaseModel


class RouterResponse(BaseModel):
    next_node: Literal["architect", "code", "clarify"]
    reasoning: str


def router(state: BuilderState) -> BuilderState:

    design_guidelines = state.design_guidelines.strip() if state.design_guidelines else ""
    architecture_blueprint = (
        state.architecture_blueprint.strip() if state.architecture_blueprint else ""
    )

    status_lines = [
        f"Design system established: {'yes' if state.design_system_run else 'no'}",
        f"Architecture blueprint established: {'yes' if state.architect_system_run else 'no'}",
        f"Architect pending additional pass: {'yes' if state.architect_pending else 'no'}",
    ]

    context_section = "\n".join(["CURRENT BUILD CONTEXT:", *("- " + line for line in status_lines)])

    guidelines_section = (
        "\n\nDESIGN SYSTEM SNAPSHOT:\n" + design_guidelines
        if design_guidelines
        else "\n\nDESIGN SYSTEM SNAPSHOT:\n- Not available"
    )

    architecture_section = (
        "\n\nARCHITECTURE BLUEPRINT SNAPSHOT:\n" + architecture_blueprint
        if architecture_blueprint
        else "\n\nARCHITECTURE BLUEPRINT SNAPSHOT:\n- Not available"
    )

    SYS = SystemMessage(
        content=ROUTER_SYSTEM_PROMPT
        + "\n\n"
        + context_section
        + guidelines_section
        + architecture_section
    )

    messages = [SYS, *state.messages]

    router_response = _router_llm_.with_structured_output(RouterResponse).invoke(
        messages
    )

    next_node = router_response.next_node
    return {
        "user_intent": next_node,
        "architect_pending": next_node == "architect",
    }
