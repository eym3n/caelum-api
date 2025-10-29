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
    next_node: Literal["code", "clarify"]
    reasoning: str


def router(state: BuilderState) -> BuilderState:

    SYS = SystemMessage(content=ROUTER_SYSTEM_PROMPT)

    messages = [SYS, *state.messages]

    router_response = _router_llm_.with_structured_output(RouterResponse).invoke(
        messages
    )

    return {"user_intent": router_response.next_node}
