from __future__ import annotations
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.prompts_new import ROUTER_SYSTEM_PROMPT
from app.agent.state import BuilderState

load_dotenv()

# LLM
ROUTER_SYSTEM_PROMPT = """
You coordinate the remaining specialists in the workspace. For every user message decide who should act next:

- `design` → When the user needs design-system updates, visual direction changes, or a fresh brand setup.
- `code` → When implementation work should proceed with the current design system.
- `clarify` → When the request is unclear, purely informational, or needs more detail before design or coding can continue.

Base the decision on the current design-system status and conversation context. Keep progress moving—only send the user back to design when visual foundations truly need revision.

Respond with one literal token: `design`, `code`, or `clarify`.
"""

_router_llm_ = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


# Structured Output
from pydantic import BaseModel


class RouterResponse(BaseModel):
    next_node: Literal["design", "code", "clarify"]
    reasoning: str


def router(state: BuilderState) -> BuilderState:

    status_lines = [
        f"Design system established: {'yes' if state.design_system_run else 'no'}",
    ]

    context_section = "\n".join(
        ["CURRENT BUILD CONTEXT:", *("- " + line for line in status_lines)]
    )

    SYS = SystemMessage(content=ROUTER_SYSTEM_PROMPT + "\n\n" + context_section)

    messages = [SYS, *state.messages]

    router_response = _router_llm_.with_structured_output(RouterResponse).invoke(
        messages
    )

    next_node = router_response.next_node
    return {
        "user_intent": next_node,
        "coder_run": state.coder_run,
    }
