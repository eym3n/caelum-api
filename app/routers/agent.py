from fastapi import (
    APIRouter,
    Depends,
    Request,
    HTTPException,
    UploadFile,
    BackgroundTasks,
)
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from app.deps import get_session_id, get_current_user
from app.models.user import User
from app.models.landing_page import LandingPageCreate, LandingPageStatus
from app.utils.landing_pages import create_landing_page, get_landing_page_by_session_id
from app.models.job import Job, JobCreate, JobType, JobStatus
from app.utils.jobs import create_job, append_job_event, update_job_status
from app.agent.job_runner import run_chat_job, run_init_job
from langchain_core.messages import HumanMessage
from app.agent.graph import agent
from app.agent.tools.files import get_session_dir, clear_session_dir
from pathlib import Path
from toon import encode
import os
import json
import subprocess
import re
from typing import Sequence

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
# Repository root (backend code lives here)
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Resolve storage root similar to shell scripts (manage_dev_server.sh, init_app.sh)
# Priority order:
# 1. Explicit OUTPUT_PATH env var
# 2. ./storage for local/development/testing
# 3. /mnt/storage for other envs
# 4. Fallback to __out__ (backward compatibility) if specified root doesn't exist
ENV = os.getenv("ENV", "local")
output_path_env = os.getenv("OUTPUT_PATH")
if output_path_env:
    STORAGE_ROOT = Path(output_path_env)
else:
    if ENV in ("local", "testing"):
        STORAGE_ROOT = REPO_ROOT / "storage"
    else:
        STORAGE_ROOT = Path("/mnt/storage")

if not STORAGE_ROOT.exists() and (REPO_ROOT / "__out__").exists():
    STORAGE_ROOT = REPO_ROOT / "__out__"

# Keep WORKSPACE_ROOT for script cwd usage (expects access to ./scripts, ./template, etc.)
WORKSPACE_ROOT = REPO_ROOT

print(
    f"[AGENT] ENV={ENV} REPO_ROOT={REPO_ROOT} STORAGE_ROOT={STORAGE_ROOT} SCRIPTS_DIR={SCRIPTS_DIR}"
)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    job_id: str | None = None


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


# =============================
# Initialization Payload Models
# =============================


class CampaignSection(BaseModel):
    objective: str | None = None
    productName: str | None = None
    primaryOffer: str | None = None


class AudienceSection(BaseModel):
    description: str | None = None
    personaKeywords: list[str] | None = None
    uvp: str | None = None


class BenefitsSection(BaseModel):
    topBenefits: list[str] | None = None
    features: list[str] | None = None
    emotionalTriggers: list[str] | None = None


class TrustSection(BaseModel):
    objections: list[str] | None = None
    testimonials: list[str] | None = None
    indicators: list[str] | None = None


class ConversionSection(BaseModel):
    primaryCTA: str | None = None
    secondaryCTA: str | None = None
    primaryKPI: str | None = None


class MessagingSection(BaseModel):
    tone: str | None = None
    seoKeywords: list[str] | None = None
    eventTracking: list[str] | None = None


class BrandingSection(BaseModel):
    theme: str | None = None  # "light" or "dark"
    colorPalette: dict | None = (
        None  # expects {"primary": str, "accent": str, "neutral": str, "raw": str}
    )
    fonts: str | None = None
    layoutPreference: str | None = None
    sections: list[str] | None = (
        None  # list of section names like ["hero", "benefits", ...]
    )
    sectionData: dict | None = (
        None  # contains faq, pricing, stats, team, testimonials, custom
    )


class MediaSection(BaseModel):
    videoUrl: str | None = None
    privacyPolicyUrl: str | None = None
    consentText: str | None = None


class AdvancedSection(BaseModel):
    formFields: list[str] | None = None
    analytics: dict | None = None  # { rawIDs: ..., gtag: ... }
    customPrompt: str | None = None


class AssetsSection(BaseModel):
    logo: str | None = None  # file ref or URL
    heroImage: str | None = None  # file ref or URL
    secondaryImages: list[str] | None = None
    favicon: str | None = None  # file ref or URL
    sectionAssets: dict | None = None  # maps section names to image URL arrays


class InitPayload(BaseModel):
    campaign: CampaignSection | None = None
    audience: AudienceSection | None = None
    benefits: BenefitsSection | None = None
    trust: TrustSection | None = None
    conversion: ConversionSection | None = None
    messaging: MessagingSection | None = None
    branding: BrandingSection | None = None
    media: MediaSection | None = None
    advanced: AdvancedSection | None = None
    assets: AssetsSection | None = None


class InitRequest(BaseModel):
    payload: InitPayload
    # Optional explicit session id override (otherwise header is used)
    session_id: str | None = None


def _run_with_live_logs(
    cmd: Sequence[str], cwd: Path, label: str, timeout: int = 300
) -> subprocess.CompletedProcess:
    """Run a command streaming stdout lines immediately to logs.

    Returns a CompletedProcess-like object with aggregated stdout/stderr for later inspection.
    """
    print(f"[{label}] EXEC: {' '.join(cmd)} (cwd={cwd})")
    try:
        process = subprocess.Popen(
            list(cmd),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        print(f"[{label}] ERROR: Failed to start process: {e}")
        raise

    lines: list[str] = []
    try:
        for line in process.stdout:  # type: ignore
            if line is None:
                break
            clean = line.rstrip("\n")
            lines.append(line)
            if clean:
                print(f"[{label}] {clean}")
        ret_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"[{label}] ERROR: Timeout after {timeout}s; process killed")
        ret_code = -1
    except Exception as e:
        print(f"[{label}] ERROR: Exception while streaming logs: {e}")
        ret_code = -1

    stdout_all = "".join(lines)
    # Build a CompletedProcess surrogate
    return subprocess.CompletedProcess(cmd, ret_code, stdout_all, None)


def _copy_static_project(session_id: str, label: str) -> bool:
    """Copy static Next.js template for session. Returns True if ready."""
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "copy_template.sh"), session_id],
            WORKSPACE_ROOT,
            f"{label}-copy",
            timeout=120,
        )
        if result.returncode == 0:
            print(f"[{label}] Static project copied for session {session_id}")
            return True
        else:
            print(f"[{label}] WARNING: copy_template exit {result.returncode}")
            return False
    except Exception as exc:
        print(f"[{label}] WARNING: Exception during template copy: {exc}")
        return False


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    session_id: str = Depends(get_session_id),
    current_user: User = Depends(get_current_user),
):
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
        print(f"[CHAT] Copying static project template for session {session_id}")
        app_ready = _copy_static_project(session_id, "CHAT")
    else:
        print(f"[CHAT] Continuing session: {session_id}")
    # No dev server management in static mode

    # Create a job record for this chat execution with the authenticated user id
    job = create_job(
        JobCreate(
            type=JobType.CHAT,
            session_id=session_id,
            user_id=current_user.id,
            title="Chat request",
            description="Asynchronous chat execution",
            initial_payload={"message": req.message},
        )
    )
    job_id = job.id if job else None

    # Kick off background execution of the graph job
    if job_id:
        background_tasks.add_task(run_chat_job, job_id, session_id, req.message)

    # Asynchronous architecture: reply is not the final graph output anymore.
    # Frontend should poll /v1/jobs/{job_id} for status and events.
    return ChatResponse(
        reply="Chat job accepted. Poll /v1/jobs/{job_id} for progress.".format(
            job_id=job_id or ""
        ),
        job_id=job_id,
    )


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
        print(f"[STREAM] Copying static project template for session {session_id}")
        app_ready = _copy_static_project(session_id, "STREAM")
    else:
        print(f"[STREAM] Continuing session: {session_id}")
    # No dev server management in static mode

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def format_tool_summary(msg) -> str | None:
        """Generate a user-friendly progressive summary for tool executions."""
        tool_name = getattr(msg, "name", None)
        if not tool_name:
            return None
        content = getattr(msg, "content", "")

        if tool_name == "list_files":
            if isinstance(content, list):
                return f"Listing {len(content)} file(s)..."
            return "Listing files..."
        elif tool_name == "create_file":
            if (
                isinstance(content, str)
                and "File " in content
                and " created" in content
            ):
                filename = content.split("File ")[1].split(" created")[0]
                return f"Creating {filename}..."
            return "Creating file..."
        elif tool_name == "read_file":
            return "Reading file..."
        elif tool_name == "update_file":
            if (
                isinstance(content, str)
                and "File " in content
                and " updated" in content
            ):
                filename = content.split("File ")[1].split(" updated")[0]
                return f"Editing {filename}..."
            return "Editing file..."
        elif tool_name == "delete_file":
            if (
                isinstance(content, str)
                and "File " in content
                and " deleted" in content
            ):
                filename = content.split("File ")[1].split(" deleted")[0]
                return f"Deleting {filename}..."
            return "Deleting file..."
        elif tool_name == "insert_lines":
            if isinstance(content, str) and "inserted successfully into" in content:
                filename = content.split("inserted successfully into ")[1].rstrip(".")
                return f"Editing {filename}..."
            return "Editing file..."
        elif tool_name == "remove_lines":
            if isinstance(content, str) and "removed successfully from" in content:
                filename = content.split("removed successfully from ")[1].rstrip(".")
                return f"Editing {filename}..."
            return "Editing file..."
        elif tool_name == "update_lines":
            if isinstance(content, str) and "updated successfully in" in content:
                filename = content.split("updated successfully in ")[1].rstrip(".")
                return f"Editing {filename}..."
            return "Editing file..."
        else:
            return "Running tool..."

    def event_gen():
        # Track tool calls to extract arguments for summaries
        tool_calls_map = {}

        try:
            for event in agent.stream(
                {
                    "messages": [
                        HumanMessage(
                            content="This is a follow-up request: user prompt:\n"
                            + req.message
                        )
                    ],
                    "session_id": session_id,
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

                        # Handle tool messages with ultra-brief summaries
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
                            tool_call = (
                                tool_calls_map.get(tool_call_id)
                                if tool_call_id
                                else None
                            )

                            def brief_tool_summary(name: str, call: dict | None) -> str:
                                args = (
                                    call.get("args", {})
                                    if isinstance(call, dict)
                                    else {}
                                )
                                # Batch counts
                                count = 0
                                if name.startswith("batch_"):
                                    files = (
                                        args.get("files") or args.get("updates") or []
                                    )
                                    if isinstance(files, list):
                                        count = len(files)
                                    # Present-progressive mapping with ellipsis for consistency
                                    simple_map = {
                                        "create_file": "Creating file...",
                                        "update_file": "Editing file...",
                                        "delete_file": "Deleting file...",
                                        "read_file": "Reading file...",
                                        "insert_lines": "Editing file...",
                                        "remove_lines": "Editing file...",
                                        "update_lines": "Editing file...",
                                        "read_lines": "Reading file...",
                                        "list_files": "Listing files...",
                                        "init_nextjs_app": "Initializing app...",
                                        "install_dependencies": "Installing dependencies...",
                                        "run_dev_server": "Starting dev server...",
                                        "run_npm_command": "Running npm command...",
                                        "run_npx_command": "Running npx command...",
                                        "run_git_command": "Running git command...",
                                        "git_log": "Viewing commit log...",
                                        "git_show": "Viewing commit...",
                                        "lint_project": "Running linter...",
                                        "check_css": "Checking CSS...",
                                    }
                                    if name == "batch_create_files":
                                        return (
                                            f"Creating {count} file(s)..."
                                            if count
                                            else "Creating files..."
                                        )
                                    if name == "batch_update_files":
                                        return (
                                            f"Editing {count} file(s)..."
                                            if count
                                            else "Editing files..."
                                        )
                                    if name == "batch_delete_files":
                                        return (
                                            f"Deleting {count} file(s)..."
                                            if count
                                            else "Deleting files..."
                                        )
                                    if name == "batch_read_files":
                                        return (
                                            f"Reading {count} file(s)..."
                                            if count
                                            else "Reading files..."
                                        )
                                    if name == "batch_update_lines":
                                        return (
                                            f"Editing {count} file(s)..."
                                            if count
                                            else "Editing files..."
                                        )
                                    return simple_map.get(name, "Running tool...")

                            # Skip streaming for read operations - user doesn't want file content
                            read_tools = {
                                "read_file",
                                "read_lines",
                                "batch_read_files",
                                "list_files",
                            }
                            if tool_name and tool_name in read_tools:
                                # Skip entirely - don't send anything for read operations
                                text_to_send = None
                            elif tool_name:
                                text_to_send = brief_tool_summary(tool_name, tool_call)
                            else:
                                text_to_send = "Ran tool"
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


# ==============================================
# Initialization Streaming Endpoint (/init/stream)
# ==============================================


def _flatten_init_payload(payload: InitPayload) -> str:
    payload = payload.model_dump(exclude_none=True)
    data = encode(payload)
    print(f"[INIT] Flattened payload: {data}")
    return data


class InitJobResponse(BaseModel):
    job_id: str
    session_id: str
    landing_page_id: str | None = None


@router.post("/init", response_model=InitJobResponse)
async def init_job(
    request: Request,
    background_tasks: BackgroundTasks,
    session_id: str = Depends(get_session_id),
    current_user: User = Depends(get_current_user),
):
    """Initialization endpoint (asynchronous).

    - Accepts JSON or multipart/form-data like the previous /init/stream
    - Creates a landing page record for the session
    - Enqueues a graph execution job and returns immediately with a job_id

    Frontend should poll `/v1/jobs/{job_id}` for progress and node outputs.
    """
    content_type = request.headers.get("content-type", "")
    raw_json: dict | None = None
    session_override: str | None = None
    try:
        if "multipart/form-data" in content_type:
            # Capture full body early for fallback extraction
            full_body_bytes = await request.body()
            form = await request.form()
            raw_payload = form.get("payload")
            if raw_payload is None:
                raise HTTPException(
                    status_code=422, detail="Missing 'payload' form part"
                )
            # Handle UploadFile vs text
            if isinstance(raw_payload, UploadFile):
                file_bytes = await raw_payload.read()
                try:
                    raw_text = file_bytes.decode("utf-8")
                except Exception:
                    raise HTTPException(
                        status_code=422,
                        detail="Unable to decode uploaded payload file as UTF-8",
                    )
            else:
                if isinstance(raw_payload, bytes):
                    raw_text = raw_payload.decode("utf-8")
                else:
                    raw_text = str(raw_payload)
            # Fallback: try to recover JSON from raw multipart body if field looks empty
            if not raw_text.strip() and full_body_bytes:
                try:
                    fb = full_body_bytes.decode("utf-8", errors="ignore")
                    start = fb.find("{")
                    end = fb.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        candidate = fb[start : end + 1]
                        if candidate.strip():
                            raw_text = candidate
                except Exception:
                    pass
            raw_text_stripped = raw_text.strip("\ufeff\n\r\t ")
            if not raw_text_stripped:
                raise HTTPException(
                    status_code=422,
                    detail="Form field 'payload' is empty after trimming.",
                )
            if raw_text_stripped == "[object Object]":
                raise HTTPException(
                    status_code=422,
                    detail="Received literal '[object Object]'. Use JSON.stringify() on the object before sending.",
                )
            try:
                parsed = json.loads(raw_text_stripped)
            except json.JSONDecodeError as e:
                # Attempt outer-quote strip fallback
                if (
                    raw_text_stripped.startswith('"')
                    and raw_text_stripped.endswith('"')
                ) or (
                    raw_text_stripped.startswith("'")
                    and raw_text_stripped.endswith("'")
                ):
                    candidate = raw_text_stripped[1:-1]
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid JSON in form field 'payload': {e}. Outer quote removal did not help.",
                        )
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid JSON in form field 'payload': {e}",
                    )
            raw_json = (
                parsed.get("payload")
                if isinstance(parsed, dict) and "payload" in parsed
                else parsed
            )
            if isinstance(parsed, dict):
                session_override = parsed.get("session_id")
        else:
            parsed = await request.json()
            raw_json = (
                parsed.get("payload")
                if isinstance(parsed, dict) and "payload" in parsed
                else parsed
            )
            if isinstance(parsed, dict):
                session_override = parsed.get("session_id")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Unable to parse request body: {e}"
        )

    if raw_json is None:
        raise HTTPException(status_code=422, detail="No JSON 'payload' provided")

    # Override session id if present in body
    if session_override:
        session_id = session_override

    # Build InitPayload pydantic model
    try:
        req_payload = InitPayload(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Payload schema error: {e}")

    # First message detection
    try:
        state_snapshot = agent.get_state(
            config={"configurable": {"thread_id": session_id}}
        )
        is_first_message = not state_snapshot.values.get("messages", [])
    except Exception:
        is_first_message = True

    app_ready = not is_first_message
    landing_page_id: str | None = None

    if is_first_message:
        clear_session_dir(session_id)
        print(f"[INIT] Copying static project template for session {session_id}")
        app_ready = _copy_static_project(session_id, "INIT")

        # Create landing page record for this session
        print(
            f"[INIT] Creating landing page record for session {session_id} and user {current_user.id}"
        )
        existing_lp = get_landing_page_by_session_id(session_id)
        if not existing_lp:
            # Convert InitPayload to dict for storage
            business_data_dict = req_payload.model_dump(exclude_none=True)
            landing_page_data = LandingPageCreate(
                session_id=session_id, business_data=business_data_dict
            )
            created_lp = create_landing_page(current_user.id, landing_page_data)
            if created_lp:
                print(f"[INIT] ✅ Landing page created: {created_lp.id}")
                landing_page_id = created_lp.id
            else:
                print(f"[INIT] ⚠️ Failed to create landing page (DB unavailable)")
        else:
            print(f"[INIT] Landing page already exists for session {session_id}")
            landing_page_id = existing_lp.id  # type: ignore[assignment]

    # No dev server management in static mode

    payload_text = _flatten_init_payload(req_payload)

    # Create a job record for this init execution
    job = create_job(
        JobCreate(
            type=JobType.INIT,
            session_id=session_id,
            user_id=current_user.id,
            title="Init request",
            description="Asynchronous init graph execution",
            initial_payload=req_payload.model_dump(),
        )
    )
    if not job:
        raise HTTPException(
            status_code=500, detail="Failed to create job for init execution"
        )

    # Run the graph in the background
    background_tasks.add_task(
        run_init_job,
        job.id,
        session_id,
        req_payload.model_dump(),
        payload_text,
    )

    return InitJobResponse(
        job_id=job.id,
        session_id=session_id,
        landing_page_id=landing_page_id,
    )


class DeployResponse(BaseModel):
    status: str
    message: str
    url: str | None = None


class KillSessionResponse(BaseModel):
    status: str
    message: str
    session_id: str


@router.delete("/sessions/{session_id}", response_model=KillSessionResponse)
async def kill_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Kill/terminate a session and clean up all associated resources.

    This endpoint will:
    - Clear all session files
    - Update landing page status to 'failed'
    - Clear LangGraph checkpoints

    Only the user who owns the session can kill it.
    """
    from app.db import get_default_checkpointer
    from app.utils.landing_pages import (
        get_landing_page_by_session_id,
        update_landing_page_status,
    )
    from app.models.landing_page import LandingPageStatus

    print(
        f"[KILL_SESSION] User {current_user.id} requesting to kill session: {session_id}"
    )

    # Verify user owns this session via landing page
    landing_page = get_landing_page_by_session_id(session_id)
    if landing_page and landing_page.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to kill this session"
        )

    try:
        # 1. Clear session files
        session_dir = get_session_dir(session_id)
        if session_dir.exists():
            clear_session_dir(session_id)
            print(f"[KILL_SESSION] Cleared session directory: {session_dir}")

        # 2. Update landing page status to failed
        if landing_page:
            update_landing_page_status(
                session_id=session_id, status=LandingPageStatus.FAILED
            )
            print(f"[KILL_SESSION] Updated landing page status to FAILED")

        # 3. Clear LangGraph checkpoints
        checkpointer = get_default_checkpointer()

        # Try to clear checkpoints if possible
        try:
            # For MemorySaver, we can access internal storage
            if hasattr(checkpointer, "storage"):
                # MemorySaver stores by (thread_id, checkpoint_ns)
                # Remove all entries for this session
                keys_to_remove = [
                    key
                    for key in checkpointer.storage.keys()
                    if key[0] == session_id  # thread_id matches session_id
                ]
                for key in keys_to_remove:
                    del checkpointer.storage[key]
                print(
                    f"[KILL_SESSION] Cleared {len(keys_to_remove)} checkpoint(s) from memory"
                )

            # For MongoDBSaver, delete from MongoDB
            elif hasattr(checkpointer, "checkpoint_collection"):
                result = checkpointer.checkpoint_collection.delete_many(
                    {"thread_id": session_id}
                )
                print(
                    f"[KILL_SESSION] Deleted {result.deleted_count} checkpoint(s) from MongoDB"
                )

                # Also clear writes collection if exists
                if hasattr(checkpointer, "writes_collection"):
                    writes_result = checkpointer.writes_collection.delete_many(
                        {"thread_id": session_id}
                    )
                    print(
                        f"[KILL_SESSION] Deleted {writes_result.deleted_count} write(s) from MongoDB"
                    )
        except Exception as checkpoint_error:
            print(
                f"[KILL_SESSION] Warning: Could not clear checkpoints: {checkpoint_error}"
            )

        print(f"[KILL_SESSION] Successfully killed session: {session_id}")

        return KillSessionResponse(
            status="success",
            message=f"Session {session_id} has been terminated and cleaned up",
            session_id=session_id,
        )

    except Exception as e:
        print(f"[KILL_SESSION] Error killing session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to kill session: {str(e)}")


@router.post("/deploy/vercel", response_model=DeployResponse)
async def deploy_to_vercel(session_id: str = Depends(get_session_id)):
    """Deploy the current session project to Vercel."""
    session_dir = get_session_dir(session_id)

    if not session_dir.exists():
        return DeployResponse(
            status="error", message=f"Session directory not found: {session_id}"
        )

    if not (session_dir / "package.json").exists():
        return DeployResponse(
            status="error", message=f"No Next.js project found in session: {session_id}"
        )

    try:
        print(f"[DEPLOY] Starting Vercel deployment for session: {session_id}")
        result = subprocess.run(
            ["bash", "scripts/deploy_to_vercel.sh", session_id],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            print(f"[DEPLOY] Deployment successful")
            if result.stdout:
                print(f"[DEPLOY] Output:\n{result.stdout}")

            # Extract deployment URL from output
            deployment_url = None
            for line in result.stdout.split("\n"):
                if "https://" in line and "vercel.app" in line:
                    url_match = re.search(r"https://[^\s]+vercel\.app", line)
                    if url_match:
                        deployment_url = url_match.group(0)
                        break

            return DeployResponse(
                status="success",
                message=f"Successfully deployed {session_id} to Vercel",
                url=deployment_url,
            )
        else:
            error_msg = result.stderr or result.stdout or "Unknown deployment error"
            print(f"[DEPLOY] Deployment failed: {error_msg}")
            return DeployResponse(
                status="error", message=f"Deployment failed: {error_msg}"
            )

    except subprocess.TimeoutExpired:
        return DeployResponse(
            status="error", message="Deployment timed out after 5 minutes"
        )
    except Exception as e:
        print(f"[DEPLOY] Exception during deployment: {e}")
        return DeployResponse(status="error", message=f"Deployment error: {str(e)}")
