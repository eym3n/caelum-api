from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from app.agent.prompts_new import CLARIFY_SYSTEM_PROMPT
from app.agent.state import BuilderState
from app.agent.tools.files import list_files, read_file, read_lines

load_dotenv()

tools = [list_files, read_file, read_lines]

_clarify_llm_ = ChatOpenAI(model="gpt-4.1").bind_tools(tools)


def clarify(state: BuilderState) -> BuilderState:
    SYS = SystemMessage(content=CLARIFY_SYSTEM_PROMPT)
    messages = [SYS, *state.messages]
    clarify_response = _clarify_llm_.invoke(messages)
    print(f"Clarify response: {clarify_response}")

    # Check for malformed function call
    finish_reason = getattr(clarify_response, "response_metadata", {}).get(
        "finish_reason"
    )
    if finish_reason == "MALFORMED_FUNCTION_CALL":
        print(
            "[CLARIFY] ⚠️  Malformed function call detected. Retrying with a simpler prompt..."
        )
        recovery_msg = HumanMessage(
            content="The previous request had an error. Please respond with clarifying questions in plain text without making tool calls."
        )
        messages.append(clarify_response)
        messages.append(recovery_msg)
        clarify_response = _clarify_llm_.invoke(messages)
        print(f"[CLARIFY] Retry response: {clarify_response}")

    # Handle both string and list content types
    response_text = ""
    if isinstance(clarify_response.content, str):
        response_text = clarify_response.content
    elif isinstance(clarify_response.content, list):
        response_text = "\n".join(
            (
                str(segment.get("text", segment))
                if isinstance(segment, dict)
                else str(segment)
            )
            for segment in clarify_response.content
            if segment
        )

    if not response_text:
        response_text = "Clarification completed."

    return {
        "messages": [clarify_response],
        "clarify_response": response_text,
    }
