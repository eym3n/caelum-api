from __future__ import annotations
import random

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from app.agent.prompts.designer import (
    DESIGNER_SYSTEM_PROMPT,
    FOLLOWUP_DESIGNER_SYSTEM_PROMPT,
    SUMMARIZE_DESIGNER_SYSTEM_PROMPT,
)
from app.agent.state import BuilderState
from app.agent.tools.commands import lint_project
from toon import encode
from app.utils.jobs import log_job_event
from app.agent.tools.files import (
    # Batch operations
    batch_create_files_internal,
    batch_read_files,
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
    # Utility
    list_files_internal,
    read_file,
    read_lines,
)

load_dotenv()

# LLM
tools = [
    # Batch file operations (ONLY USE THESE FOR FILES)
    batch_read_files,
    designer_batch_create_files,
    designer_batch_update_files,
    designer_batch_update_lines,
    # Utility
    read_file,
    read_lines,
    # Command tools
    lint_project,
]


class DesignerOutput(BaseModel):
    tailwind_config_ts_content: str = Field(
        ..., description="The content of the tailwind.config.ts file."
    )
    globals_css_content: str = Field(
        ..., description="The content of the globals.css file."
    )
    layout_tsx_content: str = Field(
        ..., description="The content of the layout.tsx file."
    )


_designer_llm_ = ChatOpenAI(model="gpt-5", reasoning_effort="low")


def designer(state: BuilderState) -> BuilderState:
    # Check if we have design_guidelines from design_planner
    design_guidelines = state.design_guidelines

    files = "\n".join(list_files_internal(state.session_id))

    if not state.is_followup:
        if (
            "globals.css" in files
            and "tailwind.config.ts" in files
            and "layout.tsx" in files
        ):
            SYS = SystemMessage(
                content=SUMMARIZE_DESIGNER_SYSTEM_PROMPT
                + f"\n\nThe following files exist in the session: {files}"
            )
        else:
            SYS = SystemMessage(
                content=DESIGNER_SYSTEM_PROMPT.replace(
                    "{guidelines}", encode(design_guidelines)
                )
                + f"\n\nThe following files exist in the session: {files}"
            )
    else:
        SYS = SystemMessage(
            content=FOLLOWUP_DESIGNER_SYSTEM_PROMPT
            + f"\n\nThe following files exist in the session: {files}"
        )

    print(f"[DESIGNER] Prompt: {SYS.content}")

    messages = [SYS, *state.messages]
    designer_response = _designer_llm_.with_structured_output(DesignerOutput).invoke(
        messages
    )

    try:
        batch_create_files_internal(
            state.session_id,
            [
                {
                    "name": "tailwind.config.ts",
                    "content": designer_response.tailwind_config_ts_content,
                },
                {
                    "name": "src/app/globals.css",
                    "content": designer_response.globals_css_content,
                },
                {
                    "name": "src/app/layout.tsx",
                    "content": designer_response.layout_tsx_content,
                },
            ],
        )
        log_job_event(
            state.job_id,
            node="designer_tools",
            message="Created files",
            event_type="node_completed",
        )

    except Exception as e:
        print(f"[DESIGNER] Error creating files: {e}")

    # Convert DesignerOutput to AIMessage for LangGraph compatibility
    designer_message = AIMessage(
        content=f"Design system implemented: tailwind.config.ts, globals.css, and layout.tsx created."
    )

    return {
        "messages": [designer_message],
        "design_system_run": True,
    }
