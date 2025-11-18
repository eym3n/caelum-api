"""Background runners for LangGraph jobs.

These helpers execute the graph in the background and append job events
to MongoDB as nodes run. Frontend can poll job state via the jobs API.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from app.agent.graph import agent
from app.models.job import JobStatus
from app.utils.jobs import log_job_event, update_job_status


def _extract_message_from_update(
    update: dict[str, Any], *, node: str, tool_meta: dict[str, Any]
) -> str:
    """Best-effort extraction of a human-readable message from a node update.

    Special-cases tool nodes so we don't log huge file contents or raw tool output.
    """
    tool_name = tool_meta.get("tool_name")

    # Tool nodes: keep messages concise and NEVER include full file contents.
    if node.endswith("_tools") and tool_name:
        # Reads: don't log contents at all.
        if tool_name in {"read_file", "batch_read_files", "read_lines"}:
            return "Read file(s)."
        # Lint: short status message only.
        if tool_name == "lint_project":
            return "Lint and type checks completed."

        # For other tools (creates/updates/deletes, etc.), their own summaries are
        # already short (e.g. "Created 2 file(s): ..."). Use that, but truncate
        # just in case.
        if "messages" in update:
            try:
                msg_obj = update["messages"][-1]
                content = getattr(msg_obj, "content", "")
                if isinstance(content, str) and content:
                    return content[:400]
            except Exception:
                pass

    # Highest priority: explicit clarify/coder outputs
    if "clarify_response" in update:
        return str(update["clarify_response"]) or ""
    if "coder_output" in update:
        return str(update["coder_output"]) or ""

    # Fallback: last message content if present (truncate to keep logs light)
    if "messages" in update:
        try:
            msg = update["messages"][-1]
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content:
                return content[:400]
        except Exception:
            pass

    # Planner outputs or other lists
    if "planner_output" in update:
        todo_list = update["planner_output"]
        if isinstance(todo_list, list):
            return "\n".join(f"- {item}" for item in todo_list)
        return str(todo_list)

    # Generic stringification fallback
    return ""


def _extract_tool_metadata(update: dict[str, Any]) -> dict[str, Any]:
    """
    Extract tool-related metadata (tool name, ids, args) from an update.

    This keeps the job event `data` field rich while staying JSON-friendly.
    """
    meta: dict[str, Any] = {}

    # Many updates carry a messages array with the latest LLM/tool message last.
    msg = None
    if "messages" in update:
        try:
            msg = update["messages"][-1]
        except Exception:
            msg = None

    if msg is not None:
        tool_name = getattr(msg, "name", None)
        tool_call_id = getattr(msg, "tool_call_id", None)
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_name:
            meta["tool_name"] = tool_name
        if tool_call_id:
            meta["tool_call_id"] = tool_call_id

        # Normalize tool_calls into a JSON-serializable list of {name, args}
        if tool_calls:
            tools: list[dict[str, Any]] = []
            try:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tools.append(
                            {
                                "name": tc.get("name"),
                                "args": tc.get("args"),
                            }
                        )
                    else:
                        # Best-effort string fallback
                        tools.append({"raw": str(tc)})
                if tools:
                    meta["tool_calls"] = tools
            except Exception:
                # If anything goes wrong, fall back to stringified representation
                try:
                    meta["tool_calls"] = [str(tc) for tc in tool_calls]  # type: ignore[arg-type]
                except Exception:
                    pass

    return meta


def run_chat_job(job_id: str, session_id: str, message: str) -> None:
    """
    Execute a chat job in the background.

    Streams LangGraph events and appends them as JobEvents in MongoDB.
    """
    try:
        for event in agent.stream(
            {
                "messages": [HumanMessage(content=message)],
                "session_id": session_id,
                "job_id": job_id,
            },
            config={
                "configurable": {
                    "thread_id": session_id,
                    "session_id": session_id,  # Pass session_id to tools
                },
                "recursion_limit": 35,
            },
        ):
            for node, update in event.items():
                if node == "__start__":
                    continue

                # When the graph signals __end__, mark the job as completed and record a final event.
                if node == "__end__":
                    log_job_event(
                        job_id,
                        node="__end__",
                        message="Graph execution completed.",
                        event_type="job_completed",
                        data={"session_id": session_id},
                    )
                    update_job_status(job_id, status=JobStatus.COMPLETED)
                    continue

                if not isinstance(update, dict):
                    continue

                tool_meta = _extract_tool_metadata(update)
                has_tool_activity = bool(
                    tool_meta.get("tool_name") or tool_meta.get("tool_calls")
                )

                # For non-tool nodes, skip per-tool logs when there are tool calls.
                # The actual tool execution will be logged separately under the
                # "*_tools" node with a concise summary.
                if (not node.endswith("_tools")) and has_tool_activity:
                    continue

                msg = _extract_message_from_update(
                    update, node=node, tool_meta=tool_meta
                )
                # NOTE: we deliberately avoid storing the raw `update` object in MongoDB,
                # because it may contain non-serializable LangChain message objects.
                # Instead, we capture only JSON-friendly tool metadata and a summary message.
                log_job_event(
                    job_id,
                    node=node,
                    message=msg,
                    event_type="node",
                    data=tool_meta,
                )
    except Exception as e:
        print(f"[JOB_RUNNER] Chat job failed: {e}")
        update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))


def run_init_job(
    job_id: str,
    session_id: str,
    init_payload: dict[str, Any],
    init_payload_text: str,
) -> None:
    """
    Execute an init job in the background.

    Mirrors the behavior of the previous /init/stream endpoint but persists
    node events to the jobs collection instead of streaming SSE.
    """
    try:
        combined = "INITIAL CREATION PAYLOAD\n" + init_payload_text

        for event in agent.stream(
            {
                "messages": [HumanMessage(content=combined)],
                "init_payload": init_payload,
                "init_payload_text": init_payload_text,
                "session_id": session_id,
                "job_id": job_id,
            },
            config={
                "configurable": {"thread_id": session_id, "session_id": session_id},
                "recursion_limit": 35,
            },
        ):
            for node, update in event.items():
                if node == "__start__":
                    continue

                if node == "__end__":
                    log_job_event(
                        job_id,
                        node="__end__",
                        message="Init graph execution completed.",
                        event_type="job_completed",
                        data={"session_id": session_id},
                    )
                    update_job_status(job_id, status=JobStatus.COMPLETED)
                    continue

                if not isinstance(update, dict):
                    continue

                tool_meta = _extract_tool_metadata(update)
                has_tool_activity = bool(
                    tool_meta.get("tool_name") or tool_meta.get("tool_calls")
                )

                if (not node.endswith("_tools")) and has_tool_activity:
                    continue

                msg = _extract_message_from_update(
                    update, node=node, tool_meta=tool_meta
                )
                log_job_event(
                    job_id,
                    node=node,
                    message=msg,
                    event_type="node",
                    data=tool_meta,
                )
    except Exception as e:
        print(f"[JOB_RUNNER] Init job failed: {e}")
        update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
