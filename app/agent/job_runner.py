"""Background runners for LangGraph jobs.

These helpers execute the graph in the background and append job events
to MongoDB as nodes run. Frontend can poll job state via the jobs API.
"""

from __future__ import annotations

from typing import Any, Tuple

from langchain_core.messages import HumanMessage

from app.agent.graph import agent
from app.models.job import JobStatus
from app.utils.jobs import log_job_event, update_job_status, pop_last_agent_message


DEFAULT_NODE_MESSAGES = {
    "router": "Planning next steps..",
    "design_planner": "Generated design blueprint",
    "design_blueprint_pdf": "Documented design blueprint into PDF",
    "generate_section": "Generated section components",
    "codegen": "Assembled page and layout",
    "followup_codegen": "Applied follow-up code updates",
    "linting": "Ran lint checks",
    "deployer": "Deployed landing page",
    "deployment_fixer": "Fixed deployment errors",
    "fix_errors": "Resolved lint failures",
    "clarify": "Clarified the request",
}


SUPPRESS_DEFAULT_NODE_LOGS = {
    "design_planner",
    "designer",
    "design_blueprint_pdf",
    "generate_section",
    "codegen",
    "followup_codegen",
    "deployment_fixer",
    "fix_errors",
    "clarify",
}


def _is_graph_end_exception(exc: Exception) -> bool:
    if not exc:
        return False
    if getattr(exc, "args", None):
        if exc.args[0] == "__end__":
            return True
    text = str(exc).strip()
    if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) >= 2:
        text = text[1:-1]
    return text == "__end__"


def _count_list_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if value is None:
        return 0
    # Treat single objects as one item
    return 1


def _final_message(job_id: str, last_message: str, default: str) -> str:
    if last_message:
        return last_message
    cached = pop_last_agent_message(job_id)
    if cached:
        return cached
    return default


def _summarize_tool_event(
    tool_name: str, tool_calls: list[dict[str, Any]]
) -> Tuple[str, dict[str, Any]]:
    """Return (message, extra_meta) for a tool execution.."""

    total_files = 0
    total_edits = 0

    for call in tool_calls:
        args = call.get("args") or {}
        files_arg = args.get("files")
        total_files += _count_list_items(files_arg)

        if isinstance(files_arg, list):
            for entry in files_arg:
                updates = (entry or {}).get("updates")
                if isinstance(updates, list):
                    total_edits += len(updates)

    normalized = tool_name.replace("designer_", "")

    if normalized.endswith("batch_create_files"):
        message = f"Created {total_files} file(s)" if total_files else "Created files"
        return message, {"file_count": total_files} if total_files else {}

    if normalized.endswith("batch_update_files"):
        message = f"Updated {total_files} file(s)" if total_files else "Updated files"
        return message, {"file_count": total_files} if total_files else {}

    if normalized.endswith("batch_delete_files"):
        message = f"Deleted {total_files} file(s)" if total_files else "Deleted files"
        return message, {"file_count": total_files} if total_files else {}

    if normalized.endswith("batch_update_lines"):
        meta: dict[str, Any] = {}
        if total_files:
            meta["file_count"] = total_files
        if total_edits:
            meta["edit_count"] = total_edits
        if total_files and total_edits:
            message = f"Updated {total_files} file(s) with {total_edits} edit(s)"
        elif total_files:
            message = f"Updated {total_files} file(s)"
        elif total_edits:
            message = f"Applied {total_edits} edit(s)"
        else:
            message = "Updated file lines"
        return message, meta

    if normalized.endswith("batch_read_files"):
        message = f"Read {total_files} file(s)" if total_files else "Read files"
        return message, {"file_count": total_files} if total_files else {}

    if normalized == "read_file":
        return "Read 1 file", {"file_count": 1}

    if normalized == "read_lines":
        return "Read file segment", {}

    if normalized == "list_files":
        return "Listed workspace files", {}

    if normalized == "lint_project":
        return "Lint and type checks completed", {}

    # Default fallback for other tools
    return f"Ran tool {tool_name}", {}


def _extract_message_from_update(
    update: dict[str, Any], *, node: str, tool_meta: dict[str, Any]
) -> str:
    """Best-effort extraction of a human-readable message from a node update.

    Special-cases tool nodes so we don't log huge file contents or raw tool output.
    """
    tool_name = tool_meta.get("tool_name")

    # Tool nodes have dedicated summaries; this branch should be unreachable.
    if node.endswith("_tools") and tool_name:
        return ""

    # Highest priority: explicit clarify/code generation outputs
    if "clarify_response" in update:
        return str(update["clarify_response"]) or ""
    if "codegen_summary" in update:
        return str(update["codegen_summary"]) or ""

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
        saw_graph_end = False
        last_meaningful_message = ""
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
                "recursion_limit": 30,
            },
        ):
            for node, update in event.items():
                if node == "__start__":
                    continue

                # When the graph signals __end__, mark the job as completed and record a final event.
                if node == "__end__":
                    final_msg = _final_message(
                        job_id, last_meaningful_message, "Graph execution completed"
                    )
                    log_job_event(
                        job_id,
                        node="__end__",
                        message=final_msg,
                        event_type="job_completed",
                        data={"session_id": session_id},
                    )
                    update_job_status(job_id, status=JobStatus.COMPLETED)
                    saw_graph_end = True
                    continue

                if not isinstance(update, dict):
                    continue

                tool_meta = _extract_tool_metadata(update)
                has_tool_activity = bool(
                    tool_meta.get("tool_name") or tool_meta.get("tool_calls")
                )

                if node.endswith("_tools") and tool_meta.get("tool_name"):
                    msg, extra_meta = _summarize_tool_event(
                        tool_meta["tool_name"], tool_meta.get("tool_calls", [])
                    )
                    if extra_meta:
                        tool_meta.update(extra_meta)
                else:
                    if has_tool_activity:
                        continue

                    msg = _extract_message_from_update(
                        update, node=node, tool_meta=tool_meta
                    )
                    default_msg = DEFAULT_NODE_MESSAGES.get(node)
                    if not msg:
                        msg = default_msg or ""
                    elif len(msg) > 240:
                        msg = msg[:240] + "…"
                        if default_msg:
                            msg = default_msg
                    elif default_msg and msg.strip().startswith("Thanks"):
                        # Replace overly conversational designer/coder chatter.
                        msg = default_msg

                if not msg:
                    msg = DEFAULT_NODE_MESSAGES.get(node, "Node activity recorded")

                default_msg = DEFAULT_NODE_MESSAGES.get(node)
                should_skip_default = (
                    default_msg
                    and msg == default_msg
                    and node in SUPPRESS_DEFAULT_NODE_LOGS
                    and not tool_meta
                )
                if should_skip_default:
                    continue

                # Track last message from core implementation nodes for final event
                if node in (
                    "codegen",
                    "followup_codegen",
                    "deployment_fixer",
                    "fix_errors",
                    "deployer",
                    "clarify",
                ):
                    last_meaningful_message = msg

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
        if not saw_graph_end:
            final_msg = _final_message(
                job_id, last_meaningful_message, "Changes applied to landing page"
            )
            log_job_event(
                job_id,
                node="__end__",
                message=final_msg,
                event_type="job_completed",
                data={"session_id": session_id},
            )
            update_job_status(job_id, status=JobStatus.COMPLETED)
    except Exception as e:
        if _is_graph_end_exception(e):
            final_msg = _final_message(
                job_id, last_meaningful_message, "Graph execution completed"
            )
            log_job_event(
                job_id,
                node="__end__",
                message=final_msg,
                event_type="job_completed",
                data={"session_id": session_id},
            )
            update_job_status(job_id, status=JobStatus.COMPLETED)
        else:
            print(f"[JOB_RUNNER] Chat job failed: {e}")
            log_job_event(
                job_id,
                node="chat_job_runner",
                message="Chat job crashed before completion.",
                event_type="error",
                data={"error": str(e)},
            )
            update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))


def run_init_job(
    job_id: str,
    session_id: str,
    init_payload: dict[str, Any],
    init_payload_text: str,
    state_overrides: dict[str, Any] | None = None,
) -> None:
    """
    Execute an init job in the background.

    Mirrors the behavior of the previous /init/stream endpoint but persists
    node events to the jobs collection instead of streaming SSE.
    """
    try:
        saw_graph_end = False
        last_meaningful_message = ""
        combined = "INITIAL CREATION PAYLOAD\n" + init_payload_text

        initial_state: dict[str, Any] = {
            "messages": [HumanMessage(content=combined)],
            "init_payload": init_payload,
            "init_payload_text": init_payload_text,
            "session_id": session_id,
            "job_id": job_id,
        }
        if state_overrides:
            initial_state.update(state_overrides)

        for event in agent.stream(
            initial_state,
            config={
                "configurable": {"thread_id": session_id, "session_id": session_id},
                "recursion_limit": 30,
            },
        ):
            for node, update in event.items():
                if node == "__start__":
                    continue

                if node == "__end__":
                    final_msg = _final_message(
                        job_id,
                        last_meaningful_message,
                        "Landing page creation completed",
                    )
                    log_job_event(
                        job_id,
                        node="__end__",
                        message=final_msg,
                        event_type="job_completed",
                        data={"session_id": session_id},
                    )
                    update_job_status(job_id, status=JobStatus.COMPLETED)
                    saw_graph_end = True
                    continue

                if not isinstance(update, dict):
                    continue

                tool_meta = _extract_tool_metadata(update)
                has_tool_activity = bool(
                    tool_meta.get("tool_name") or tool_meta.get("tool_calls")
                )

                if node.endswith("_tools") and tool_meta.get("tool_name"):
                    msg, extra_meta = _summarize_tool_event(
                        tool_meta["tool_name"], tool_meta.get("tool_calls", [])
                    )
                    if extra_meta:
                        tool_meta.update(extra_meta)
                else:
                    if has_tool_activity:
                        continue

                    msg = _extract_message_from_update(
                        update, node=node, tool_meta=tool_meta
                    )
                    default_msg = DEFAULT_NODE_MESSAGES.get(node)
                    if not msg:
                        msg = default_msg or ""
                    elif len(msg) > 240:
                        msg = msg[:240] + "…"
                        if default_msg:
                            msg = default_msg
                    elif default_msg and msg.strip().startswith("Thanks"):
                        msg = default_msg

                if not msg:
                    msg = DEFAULT_NODE_MESSAGES.get(node, "Node activity recorded")

                default_msg = DEFAULT_NODE_MESSAGES.get(node)
                should_skip_default = (
                    default_msg
                    and msg == default_msg
                    and node in SUPPRESS_DEFAULT_NODE_LOGS
                    and not tool_meta
                )
                if should_skip_default:
                    continue

                # Track last message from implementation/error-fix nodes for final event
                if node in ("codegen", "deployment_fixer", "fix_errors"):
                    last_meaningful_message = msg

                log_job_event(
                    job_id,
                    node=node,
                    message=msg,
                    event_type="node",
                    data=tool_meta,
                )
        if not saw_graph_end:
            final_msg = _final_message(
                job_id,
                last_meaningful_message,
                "Landing page creation completed",
            )
            log_job_event(
                job_id,
                node="__end__",
                message=final_msg,
                event_type="job_completed",
                data={"session_id": session_id},
            )
            update_job_status(job_id, status=JobStatus.COMPLETED)
    except Exception as e:
        if _is_graph_end_exception(e):
            final_msg = _final_message(
                job_id,
                last_meaningful_message,
                "Landing page creation completed",
            )
            log_job_event(
                job_id,
                node="__end__",
                message=final_msg,
                event_type="job_completed",
                data={"session_id": session_id},
            )
            update_job_status(job_id, status=JobStatus.COMPLETED)
        else:
            print(f"[JOB_RUNNER] Init job failed: {e}")
            log_job_event(
                job_id,
                node="init_job_runner",
                message="Init job crashed before completion.",
                event_type="error",
                data={"error": str(e)},
            )
            update_job_status(job_id, status=JobStatus.FAILED, error_message=str(e))
