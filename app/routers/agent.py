from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from app.deps import get_session_id
from langchain_core.messages import HumanMessage
from app.agent.graph import agent
from app.agent.tools.files import get_session_dir, clear_session_dir
from pathlib import Path
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
    if ENV in ("local", "development", "testing"):
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
    colorPalette: dict | None = None  # expects {"raw": str}
    fonts: str | None = None
    layoutPreference: str | None = None


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


def ensure_dev_server(session_id: str, context_label: str) -> None:
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "manage_dev_server.sh"), session_id],
            WORKSPACE_ROOT,
            f"{context_label}-DEV",
            timeout=45,
        )
        if result.returncode == 0:
            print(f"[{context_label}] Dev server ensured for session {session_id}")
        else:
            print(
                f"[{context_label}] WARNING: manage_dev_server exit {result.returncode}. Raw output follows:\n{result.stdout}"  # type: ignore
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
            result = _run_with_live_logs(
                ["bash", str(SCRIPTS_DIR / "init_app.sh"), session_id],
                WORKSPACE_ROOT,
                "CHAT-init",
                timeout=300,
            )
            if result.returncode == 0:
                print(f"[CHAT] Next.js app initialized successfully")
                install_result = _run_with_live_logs(
                    [
                        "bash",
                        str(SCRIPTS_DIR / "install_base_dependencies.sh"),
                        session_id,
                    ],
                    WORKSPACE_ROOT,
                    "CHAT-install",
                    timeout=300,
                )
                if install_result.returncode == 0:
                    print(f"[CHAT] Base dependencies installed successfully")
                    app_ready = True
                else:
                    print(
                        f"[CHAT] WARNING: install_base_dependencies exit {install_result.returncode}"
                    )
            else:
                print(
                    f"[CHAT] WARNING: init_app failed exit {result.returncode}. Output captured above."
                )
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
            result = _run_with_live_logs(
                ["bash", str(SCRIPTS_DIR / "init_app.sh"), session_id],
                WORKSPACE_ROOT,
                "STREAM-init",
                timeout=300,
            )
            if result.returncode == 0:
                print(f"[STREAM] Next.js app initialized successfully")
                install_result = _run_with_live_logs(
                    [
                        "bash",
                        str(SCRIPTS_DIR / "install_base_dependencies.sh"),
                        session_id,
                    ],
                    WORKSPACE_ROOT,
                    "STREAM-install",
                    timeout=300,
                )
                if install_result.returncode == 0:
                    print(f"[STREAM] Base dependencies installed successfully")
                    app_ready = True
                else:
                    print(
                        f"[STREAM] WARNING: install_base_dependencies exit {install_result.returncode}"
                    )
            else:
                print(
                    f"[STREAM] WARNING: init_app failed exit {result.returncode}. Output captured above."
                )
        except Exception as e:
            print(f"[STREAM] WARNING: Exception during Next.js init: {e}")
    else:
        print(f"[STREAM] Continuing session: {session_id}")

    if app_ready:
        ensure_dev_server(session_id, "STREAM")

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
                    ]
                },
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
    sections: list[str] = []

    def add(title: str, lines: list[str]):
        clean = [l for l in lines if l and l.strip() and not l.strip().endswith("None")]
        if any(clean):
            sections.append(f"## {title}\n" + "\n".join(clean))

    if payload.campaign:
        add(
            "Campaign",
            [
                f"Objective: {payload.campaign.objective}",
                f"Product: {payload.campaign.productName}",
                f"Primary Offer: {payload.campaign.primaryOffer}",
            ],
        )
    if payload.audience:
        add(
            "Audience",
            [
                f"Description: {payload.audience.description}",
                f"Persona Keywords: {', '.join(payload.audience.personaKeywords or [])}",
                f"UVP: {payload.audience.uvp}",
            ],
        )
    if payload.benefits:
        add(
            "Benefits",
            [
                f"Top Benefits: {', '.join(payload.benefits.topBenefits or [])}",
                f"Features: {', '.join(payload.benefits.features or [])}",
                f"Emotional Triggers: {', '.join(payload.benefits.emotionalTriggers or [])}",
            ],
        )
    if payload.trust:
        add(
            "Trust",
            [
                f"Objections: {', '.join(payload.trust.objections or [])}",
                f"Testimonials: {', '.join(payload.trust.testimonials or [])}",
                f"Indicators: {', '.join(payload.trust.indicators or [])}",
            ],
        )
    if payload.conversion:
        add(
            "Conversion",
            [
                f"Primary CTA: {payload.conversion.primaryCTA}",
                f"Secondary CTA: {payload.conversion.secondaryCTA}",
                f"Primary KPI: {payload.conversion.primaryKPI}",
            ],
        )
    if payload.messaging:
        add(
            "Messaging",
            [
                f"Tone: {payload.messaging.tone}",
                f"SEO Keywords: {', '.join(payload.messaging.seoKeywords or [])}",
                f"Event Tracking: {', '.join(payload.messaging.eventTracking or [])}",
            ],
        )
    if payload.branding:
        add(
            "Branding",
            [
                f"Color Palette Raw: {(payload.branding.colorPalette or {}).get('raw')}",
                f"Fonts: {payload.branding.fonts}",
                f"Layout Preference: {payload.branding.layoutPreference}",
            ],
        )
    if payload.media:
        add(
            "Media",
            [
                f"Video URL: {payload.media.videoUrl}",
                f"Privacy Policy: {payload.media.privacyPolicyUrl}",
                f"Consent Text: {payload.media.consentText}",
            ],
        )
    if payload.advanced:
        add(
            "Advanced",
            [
                f"Form Fields: {', '.join(payload.advanced.formFields or [])}",
                f"Analytics rawIDs: {(payload.advanced.analytics or {}).get('rawIDs')}",
                f"Analytics gtag: {(payload.advanced.analytics or {}).get('gtag')}",
                f"Custom Prompt: {payload.advanced.customPrompt}",
            ],
        )
    if payload.assets:
        add(
            "Assets",
            [
                f"Logo: {payload.assets.logo}",
                f"Hero Image: {payload.assets.heroImage}",
                f"Secondary Images: {', '.join(payload.assets.secondaryImages or [])}",
            ],
        )
    print(f"[INIT] Flattened payload:\n" + "\n\n".join(sections))
    return "\n\n".join(sections)


@router.post("/init/stream")
async def init_stream(request: Request, session_id: str = Depends(get_session_id)):
    """Initialization stream endpoint supporting both application/json and multipart/form-data.

    Multipart format: field name 'payload' containing JSON blob.
    Optional 'session_id' key inside JSON can override header.
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
    if is_first_message:
        clear_session_dir(session_id)
        try:
            result = _run_with_live_logs(
                ["bash", str(SCRIPTS_DIR / "init_app.sh"), session_id],
                WORKSPACE_ROOT,
                "INIT-init",
                timeout=300,
            )
            if result.returncode == 0:
                install_result = _run_with_live_logs(
                    [
                        "bash",
                        str(SCRIPTS_DIR / "install_base_dependencies.sh"),
                        session_id,
                    ],
                    WORKSPACE_ROOT,
                    "INIT-install",
                    timeout=300,
                )
                app_ready = install_result.returncode == 0
        except Exception as e:
            print(f"[INIT] Exception during Next.js init: {e}")
    if app_ready:
        ensure_dev_server(session_id, "INIT")

    payload_text = _flatten_init_payload(req_payload)
    combined = "INITIAL CREATION PAYLOAD\n" + payload_text

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def event_gen():
        tool_calls_map = {}

        try:
            for event in agent.stream(
                {
                    "messages": [HumanMessage(content=combined)],
                    "init_payload": req_payload.model_dump(),
                    "init_payload_text": payload_text,
                },
                config={
                    "configurable": {"thread_id": session_id, "session_id": session_id},
                    "recursion_limit": 200,
                },
            ):
                for node, update in event.items():
                    if node in ("__start__", "__end__"):
                        continue
                    if not isinstance(update, dict):
                        continue

                    text_to_send = None

                    if "coder_output" in update:
                        text_to_send = update["coder_output"]
                    elif "clarify_response" in update:
                        text_to_send = update["clarify_response"]
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
                            c = getattr(msg, "content", "")
                            if isinstance(c, str) and c:
                                text_to_send = c

                    if text_to_send:
                        yield sse(
                            {"type": "message", "node": node, "text": text_to_send}
                        )
        except Exception as e:
            yield sse({"type": "error", "error": str(e)})
        finally:
            yield sse({"type": "done"})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


class DeployResponse(BaseModel):
    status: str
    message: str
    url: str | None = None


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
