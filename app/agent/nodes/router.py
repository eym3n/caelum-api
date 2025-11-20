from __future__ import annotations
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.prompts_new import ROUTER_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.models.landing_page import LandingPageStatus
from app.utils.landing_pages import update_landing_page_status

load_dotenv()

# LLM
ROUTER_SYSTEM_PROMPT = """
You coordinate the remaining specialists in the workspace. For every user message decide who should act next:

- `design` → When a new or revised design blueprint is required from the Design Planner.
- `code` → When coding work is needed (implementing sections, fixing bugs, wiring CTAs, etc.).
- `clarify` → When the request is unclear, purely informational, or needs more detail before work can continue.
- `deploy` → When the user specifically requests to deploy the landing page.

If a user's request starts with : 'This is a follow-up request', route to `code` or `clarify` only.

When a user reports an error or bug, prefer routing to `code`, do not route to `clarify`. Issues need to be investigated and fixed directly, without further discussion.

If a user's request starts with : 'Deploy the landing page', route to `deploy`.

Base the decision on the current design-blueprint status and conversation context. Keep progress moving—only send the user back to `design` when the visual foundations truly need a redesign.

Respond with one literal token: `design`, `code`, `clarify`, or `deploy`.
"""

_router_llm_ = ChatOpenAI(model="gpt-4.1-mini-2025-04-14")


# Structured Output
from pydantic import BaseModel


class RouterResponse(BaseModel):
    next_node: Literal["design", "code", "clarify", "deploy"]
    is_followup: bool
    reasoning: str


def router(state: BuilderState) -> BuilderState:

    status_lines = [
        f"Design blueprint ready: {'yes' if state.design_planner_run else 'no'}",
    ]

    context_section = "\n".join(
        ["CURRENT BUILD CONTEXT:", *("- " + line for line in status_lines)]
    )

    # No LLM call if no design blueprint yet, go to design planner
    if not state.design_planner_run:
        # Update landing page status to generating (starting design work)
        session_id = state.session_id
        if session_id:
            update_landing_page_status(
                session_id=session_id, status=LandingPageStatus.GENERATING
            )
            print(
                f"[ROUTER] Landing page status updated to 'generating' for session {session_id}"
            )

        return {
            "user_intent": "design",
            "coder_run": False,
            "is_followup": False,
        }

    SYS = SystemMessage(content=ROUTER_SYSTEM_PROMPT + "\n\n" + context_section)

    messages = [SYS, *state.messages]

    # print("Router Invoked with messages:\n", messages)

    router_response = _router_llm_.with_structured_output(RouterResponse).invoke(
        messages
    )

    print("\n\n[ROUTER] Decision:", router_response)

    next_node = router_response.next_node
    return {
        "user_intent": next_node,
        "coder_run": False,
        "is_followup": router_response.is_followup,
        "coder_first_pass_run": False,
    }
