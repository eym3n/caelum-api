from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from app.deps import get_session_id
from langchain_core.messages import HumanMessage
from app.agent.graph import agent
from app.agent.tools.files import get_session_dir, clear_session_dir
from pathlib import Path
import json
import subprocess

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class ChatMessage(BaseModel):
    role: str
    content: str
    id: str | None = None
    tools_used: list[str] | None = None
    tool_response: dict | list | str | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class FileInfo(BaseModel):
    name: str
    size: int
    content: str | None = None


class FilesResponse(BaseModel):
    session_id: str
    files: list[FileInfo]


def ensure_dev_server(session_id: str, context_label: str) -> None:
    try:
        result = subprocess.run(
            ["bash", "scripts/manage_dev_server.sh", session_id],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=45,
        )
        if result.returncode == 0:
            if result.stdout.strip():
                print(f"[{context_label}] manage_dev_server → {result.stdout.strip()}")
        else:
            combined = (result.stderr or "") + ("\n" + result.stdout if result.stdout else "")
            print(
                f"[{context_label}] WARNING: manage_dev_server failed (code {result.returncode}): {combined.strip()}"
            )
    except Exception as exc:
        print(f"[{context_label}] WARNING: Exception while managing dev server: {exc}")


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, session_id: str = Depends(get_session_id)):
    # Check if this is the first message - clear session directory
    try:
        state_snapshot = agent.get_state(
            config={"configurable": {"thread_id": session_id, "recursion_limit": 50}}
        )
        is_first_message = not state_snapshot.values.get("messages", [])
    except Exception:
        is_first_message = True

    app_ready = not is_first_message

    if is_first_message:
        print(f"[CHAT] First message detected for session: {session_id}")
        clear_session_dir(session_id)
        # Initialize Next.js project
        print(f"[CHAT] Initializing Next.js app for session {session_id}")
        try:
            result = subprocess.run(
                ["bash", "scripts/init_app.sh", session_id],
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                print(f"[CHAT] Next.js app initialized successfully")
                if result.stdout:
                    print(f"[CHAT] Init output:\n{result.stdout}")

                # Install base dependencies in a separate step
                install_result = subprocess.run(
                    ["bash", "scripts/install_base_dependencies.sh", session_id],
                    cwd=str(WORKSPACE_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if install_result.returncode == 0:
                    print(f"[CHAT] Base dependencies installed successfully")
                    if install_result.stdout:
                        print(f"[CHAT] Install output:\n{install_result.stdout}")
                else:
                    print(
                        f"[CHAT] WARNING: Failed to install base dependencies: {install_result.stderr}"
                    )
                    if install_result.stdout:
                        print(f"[CHAT] Install stdout:\n{install_result.stdout}")
                app_ready = True
            else:
                print(
                    f"[CHAT] WARNING: Failed to initialize Next.js app: {result.stderr}"
                )
                if result.stdout:
                    print(f"[CHAT] Stdout:\n{result.stdout}")
        except Exception as e:
            print(f"[CHAT] WARNING: Exception during Next.js init: {e}")
    else:
        print(f"[CHAT] Continuing session: {session_id}")

    if app_ready:
        ensure_dev_server(session_id, "CHAT")

    last_text = ""
    for event in agent.stream(
        {"messages": [HumanMessage(content=req.message)]},
        config={
            "configurable": {
                "thread_id": session_id,
                "session_id": session_id,  # Pass session_id to tools
            },
            "recursion_limit": 200,
        },
    ):
        for node, update in event.items():
            if node in ("__start__", "__end__"):
                continue

            if not isinstance(update, dict):
                continue

            # Handle different node response types
            if "clarify_response" in update:
                last_text = update["clarify_response"]
            elif "coder_output" in update:
                last_text = update["coder_output"]
            elif "messages" in update:
                msg = update["messages"][-1]
                content = getattr(msg, "content", "")
                if isinstance(content, str) and content:
                    last_text = content
            elif "planner_output" in update:
                todo_list = update["planner_output"]
                if isinstance(todo_list, list):
                    last_text = "\n".join(f"- {item}" for item in todo_list)
                else:
                    last_text = str(todo_list)

    return ChatResponse(reply=last_text or "(no reply)")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, session_id: str = Depends(get_session_id)):
    # Check if this is the first message - clear session directory
    try:
        state_snapshot = agent.get_state(
            config={"configurable": {"thread_id": session_id}}
        )
        is_first_message = not state_snapshot.values.get("messages", [])
    except Exception:
        is_first_message = True

    app_ready = not is_first_message

    if is_first_message:
        print(f"[STREAM] First message detected for session: {session_id}")
        clear_session_dir(session_id)
        # Initialize Next.js project
        print(f"[STREAM] Initializing Next.js app for session {session_id}")
        try:
            result = subprocess.run(
                ["bash", "scripts/init_app.sh", session_id],
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                print(f"[STREAM] Next.js app initialized successfully")
                if result.stdout:
                    print(f"[STREAM] Init output:\n{result.stdout}")

                install_result = subprocess.run(
                    ["bash", "scripts/install_base_dependencies.sh", session_id],
                    cwd=str(WORKSPACE_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if install_result.returncode == 0:
                    print(f"[STREAM] Base dependencies installed successfully")
                    if install_result.stdout:
                        print(f"[STREAM] Install output:\n{install_result.stdout}")
                else:
                    print(
                        f"[STREAM] WARNING: Failed to install base dependencies: {install_result.stderr}"
                    )
                    if install_result.stdout:
                        print(f"[STREAM] Install stdout:\n{install_result.stdout}")
                app_ready = True
            else:
                print(
                    f"[STREAM] WARNING: Failed to initialize Next.js app: {result.stderr}"
                )
                if result.stdout:
                    print(f"[STREAM] Stdout:\n{result.stdout}")
        except Exception as e:
            print(f"[STREAM] WARNING: Exception during Next.js init: {e}")
    else:
        print(f"[STREAM] Continuing session: {session_id}")

    if app_ready:
        ensure_dev_server(session_id, "STREAM")

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def format_tool_summary(msg) -> str | None:
        """Generate a user-friendly summary for tool executions."""
        tool_name = getattr(msg, "name", None)
        if not tool_name:
            return None

        # Parse the content to extract relevant info
        content = getattr(msg, "content", "")

        # Try to get the tool call ID to look up arguments
        tool_call_id = getattr(msg, "tool_call_id", None)

        # Map tool names to friendly messages
        if tool_name == "list_files":
            # Parse the list if content is a list
            if isinstance(content, list):
                return f"Listed {len(content)} file(s)"
            return "Listed files in directory"

        elif tool_name == "create_file":
            # Content format: "File {name} created successfully."
            if (
                isinstance(content, str)
                and "File " in content
                and " created" in content
            ):
                # Extract filename
                filename = content.split("File ")[1].split(" created")[0]
                return f"Created {filename}"
            return "Created file"

        elif tool_name == "read_file":
            # For read_file, content is the actual file content
            # We need to extract the filename from somewhere
            # The content is the file content itself, not a message
            # We need to look at the previous message to get the filename
            return "Read file"

        elif tool_name == "update_file":
            # Content format: "File {name} updated successfully."
            if (
                isinstance(content, str)
                and "File " in content
                and " updated" in content
            ):
                filename = content.split("File ")[1].split(" updated")[0]
                return f"Updated {filename}"
            return "Updated file"

        elif tool_name == "delete_file":
            # Content format: "File {name} deleted successfully."
            if (
                isinstance(content, str)
                and "File " in content
                and " deleted" in content
            ):
                filename = content.split("File ")[1].split(" deleted")[0]
                return f"Deleted {filename}"
            return "Deleted file"

        elif tool_name == "insert_lines":
            # Content format: "Lines inserted successfully into {name}."
            if isinstance(content, str) and "inserted successfully into" in content:
                filename = content.split("inserted successfully into ")[1].rstrip(".")
                return f"Inserted lines into {filename}"
            return "Inserted lines"

        elif tool_name == "remove_lines":
            # Content format: "Lines removed successfully from {name}."
            if isinstance(content, str) and "removed successfully from" in content:
                filename = content.split("removed successfully from ")[1].rstrip(".")
                return f"Removed lines from {filename}"
            return "Removed lines"

        elif tool_name == "update_lines":
            # Content format: "Lines updated successfully in {name}."
            if isinstance(content, str) and "updated successfully in" in content:
                filename = content.split("updated successfully in ")[1].rstrip(".")
                return f"Updated lines in {filename}"
            return "Updated lines"

        else:
            return f"Executed {tool_name}"

    def event_gen():
        # Track tool calls to extract arguments for summaries
        tool_calls_map = {}

        try:
            for event in agent.stream(
                {"messages": [HumanMessage(content=req.message)]},
                config={
                    "configurable": {
                        "thread_id": session_id,
                        "session_id": session_id,  # Pass session_id to tools
                    },
                    "recursion_limit": 200,
                },
            ):
                for node, update in event.items():
                    if node in ("__start__", "__end__"):
                        continue

                    if not isinstance(update, dict):
                        continue

                    # Handle different node response types
                    text_to_send = None

                    # Check for clarify response
                    if "clarify_response" in update:
                        text_to_send = update["clarify_response"]

                    # Check for coder output
                    elif "coder_output" in update:
                        text_to_send = update["coder_output"]

                    # Check for messages (coder, tools, etc)
                    elif "messages" in update:
                        msg = update["messages"][-1]
                        msg_type = getattr(msg, "type", None)

                        # Track tool calls from AI messages
                        if msg_type == "ai" and hasattr(msg, "tool_calls"):
                            for tc in msg.tool_calls:
                                tool_calls_map[tc.get("id")] = tc

                        # Handle tool messages specially
                        if (
                            node
                            in (
                                "coder_tools",
                                "clarify_tools",
                                "planner_tools",
                                "designer_tools",
                                "architect_tools",
                            )
                            or msg_type == "tool"
                        ):
                            tool_name = getattr(msg, "name", None)
                            tool_call_id = getattr(msg, "tool_call_id", None)

                            # Get the original tool call to extract arguments
                            tool_call = (
                                tool_calls_map.get(tool_call_id)
                                if tool_call_id
                                else None
                            )

                            # Debug logging
                            if not tool_call and tool_call_id:
                                print(
                                    f"[STREAM] Warning: No tool_call found for ID {tool_call_id}"
                                )
                                print(
                                    f"[STREAM] Available IDs: {list(tool_calls_map.keys())}"
                                )

                            # Format summary with details from tool call arguments
                            if tool_name == "read_file":
                                if tool_call:
                                    args = tool_call.get("args", {})
                                    filename = args.get("name", "")
                                    text_to_send = (
                                        f"Read {filename}" if filename else "Read file"
                                    )
                                    print(f"[STREAM] read_file: {filename}")
                                else:
                                    text_to_send = "Read file"
                                    print(f"[STREAM] read_file: No tool_call found")

                            elif tool_name == "update_lines":
                                if tool_call:
                                    args = tool_call.get("args", {})
                                    filename = args.get("name", "")
                                    updates = args.get("updates", [])

                                    # Calculate total lines added and removed
                                    total_removed = 0
                                    total_added = 0
                                    for update in updates:
                                        start = update.get("start_index", 0)
                                        end = update.get("end_index", 0)
                                        replacement = update.get(
                                            "replacement_lines", []
                                        )

                                        lines_removed = end - start + 1
                                        lines_added = len(replacement)

                                        total_removed += lines_removed
                                        total_added += lines_added

                                    # Calculate net change
                                    net_change = total_added - total_removed
                                    if net_change > 0:
                                        change_str = f"(+{net_change})"
                                    elif net_change < 0:
                                        change_str = f"({net_change})"
                                    else:
                                        change_str = f"(±{total_added})"

                                    if filename:
                                        text_to_send = (
                                            f"Updated lines in {filename} {change_str}"
                                        )
                                    else:
                                        text_to_send = f"Updated lines {change_str}"

                                    print(
                                        f"[STREAM] update_lines: {filename} {change_str} (from {len(updates)} updates)"
                                    )
                                else:
                                    text_to_send = format_tool_summary(msg)
                                    print(
                                        f"[STREAM] update_lines: No tool_call found, using fallback"
                                    )

                            elif tool_name == "insert_lines":
                                if tool_call:
                                    args = tool_call.get("args", {})
                                    filename = args.get("name", "")
                                    lines_list = args.get("lines", [])

                                    # Count total lines being inserted
                                    total_lines = sum(
                                        len(item.get("lines", []))
                                        for item in lines_list
                                    )

                                    if filename and total_lines:
                                        text_to_send = f"Inserted {total_lines} line(s) into {filename} (+{total_lines})"
                                    else:
                                        text_to_send = (
                                            f"Inserted lines (+{total_lines})"
                                            if total_lines
                                            else "Inserted lines"
                                        )

                                    print(
                                        f"[STREAM] insert_lines: {filename} (+{total_lines})"
                                    )
                                else:
                                    text_to_send = format_tool_summary(msg)
                                    print(
                                        f"[STREAM] insert_lines: No tool_call found, using fallback"
                                    )

                            elif tool_name == "remove_lines":
                                if tool_call:
                                    args = tool_call.get("args", {})
                                    filename = args.get("name", "")
                                    indices = args.get("indices", [])
                                    num_lines = len(indices)
                                    if filename and num_lines:
                                        text_to_send = f"Removed {num_lines} line(s) from {filename} (-{num_lines})"
                                    else:
                                        text_to_send = (
                                            f"Removed {num_lines} line(s) (-{num_lines})"
                                            if num_lines
                                            else "Removed lines"
                                        )

                                    print(
                                        f"[STREAM] remove_lines: {filename} (-{num_lines})"
                                    )
                                else:
                                    text_to_send = format_tool_summary(msg)
                                    print(
                                        f"[STREAM] remove_lines: No tool_call found, using fallback"
                                    )

                            # Command tools
                            elif tool_name == "init_nextjs_app":
                                text_to_send = "Initializing Next.js app with TypeScript and Tailwind..."
                                print(f"[STREAM] init_nextjs_app")

                            elif tool_name == "install_dependencies":
                                text_to_send = "Installing npm dependencies..."
                                print(f"[STREAM] install_dependencies")

                            elif tool_name == "run_dev_server":
                                text_to_send = "Starting Next.js dev server..."
                                print(f"[STREAM] run_dev_server")

                            elif tool_name == "run_npm_command":
                                if tool_call:
                                    args = tool_call.get("args", {})
                                    command = args.get("command", "")
                                    text_to_send = f"Running npm {command}..."
                                    print(f"[STREAM] run_npm_command: {command}")
                                else:
                                    text_to_send = "Running npm command..."
                                    print(
                                        f"[STREAM] run_npm_command: No tool_call found"
                                    )

                            elif tool_name == "lint_project":
                                text_to_send = "Running ESLint to check for errors..."
                                print(f"[STREAM] lint_project")

                            else:
                                text_to_send = format_tool_summary(msg)
                        else:
                            content = getattr(msg, "content", "")
                            if isinstance(content, str) and content:
                                text_to_send = content

                    # Check for planner output
                    elif "planner_output" in update:
                        todo_list = update["planner_output"]
                        if isinstance(todo_list, list):
                            text_to_send = "\n".join(f"- {item}" for item in todo_list)
                        else:
                            text_to_send = str(todo_list)

                    if text_to_send:
                        # Clean up node names for better frontend display
                        display_node = node
                        if node in (
                            "coder_tools",
                            "clarify_tools",
                            "planner_tools",
                            "designer_tools",
                            "architect_tools",
                        ):
                            display_node = "tools"

                        yield sse(
                            {
                                "type": "message",
                                "node": display_node,
                                "text": text_to_send,
                            }
                        )
        except Exception as e:
            yield sse({"type": "error", "error": str(e)})
        finally:
            yield sse({"type": "done"})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def chat_history(session_id: str = Depends(get_session_id)):
    try:
        state = agent.get_state(config={"configurable": {"thread_id": session_id}})
        values = getattr(state, "values", None) or state  # state may already be a dict
        raw = (values.get("messages") if isinstance(values, dict) else []) or []
    except Exception:
        raw = []

    out: list[ChatMessage] = []
    for m in raw:
        role = getattr(m, "type", None) or getattr(m, "role", None) or "unknown"
        content = getattr(m, "content", "")
        msg_id = getattr(m, "id", None)
        tools_used: list[str] | None = None
        tool_response: dict | list | str | None = None

        # Tool message response
        tool_name = getattr(m, "name", None) or getattr(m, "tool", None)
        if (role == "tool" or tool_name) and content is not None:
            if tools_used is None:
                tools_used = []
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)
            tool_response = content

        # Normalize content to string for preview while retaining tool_response separately
        if not isinstance(content, str):
            try:
                content = json.dumps(content, ensure_ascii=False)
            except Exception:
                content = str(content)

        out.append(
            ChatMessage(
                role=role,
                content=content,
                id=msg_id,
                tools_used=tools_used,
                tool_response=tool_response,
            )
        )

    return ChatHistoryResponse(session_id=session_id, messages=out)


@router.post("/session/clear")
async def clear_session(session_id: str = Depends(get_session_id)):
    """Clear all files for a session."""
    try:
        clear_session_dir(session_id)
        return {"status": "success", "message": f"Session {session_id} cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/files", response_model=FilesResponse)
async def get_files(
    session_id: str = Depends(get_session_id), include_content: bool = False
):
    """Get all files for a session from the session directory."""
    session_dir = get_session_dir(session_id)
    files_list: list[FileInfo] = []

    for file_path in session_dir.iterdir():
        if file_path.is_file():
            content = None
            if include_content:
                try:
                    content = file_path.read_text()
                except Exception:
                    content = "[Binary file]"

            files_list.append(
                FileInfo(
                    name=file_path.name,
                    size=file_path.stat().st_size,
                    content=content,
                )
            )

    return FilesResponse(session_id=session_id, files=files_list)


@router.get("/files/{filename}")
async def get_file(filename: str, session_id: str = Depends(get_session_id)):
    """Get a specific file's content from the session directory."""
    session_dir = get_session_dir(session_id)
    file_path = session_dir / filename

    if not file_path.exists():
        return Response(content=f"File {filename} not found", status_code=404)

    # Determine content type based on file extension
    content_type = "text/plain"
    if filename.endswith(".html"):
        content_type = "text/html"
    elif filename.endswith(".css"):
        content_type = "text/css"
    elif filename.endswith(".js"):
        content_type = "application/javascript"
    elif filename.endswith(".json"):
        content_type = "application/json"

    return FileResponse(file_path, media_type=content_type)
