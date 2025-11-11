"""Command execution tools for running shell scripts and npm commands.

Refactored to use dynamic repository root resolution with absolute script paths so
they work both locally and inside containers where CWD may differ. Adds a helper
to stream logs line-by-line for better observability.
"""

import subprocess
from pathlib import Path
import os
from typing import Annotated, Sequence

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool


def _get_session_from_config(config: RunnableConfig) -> str:
    """Extract session_id from config."""
    return config.get("configurable", {}).get("session_id", "default")


# Resolve repository root (four levels up: /repo/app/agent/tools/commands.py → /repo)
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
ENV = os.getenv("ENV", "local")
print(f"[COMMANDS] ENV={ENV} REPO_ROOT={REPO_ROOT} SCRIPTS_DIR={SCRIPTS_DIR}")


def _run_with_live_logs(
    cmd: Sequence[str], label: str, timeout: int = 180
) -> subprocess.CompletedProcess:
    """Run a shell command streaming stdout lines immediately.

    Returns a CompletedProcess surrogate with aggregated stdout for downstream parsing.
    """
    print(f"[{label}] EXEC: {' '.join(cmd)} (cwd={REPO_ROOT})")
    try:
        process = subprocess.Popen(
            list(cmd),
            cwd=str(REPO_ROOT),
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
        for line in process.stdout:  # type: ignore[attr-defined]
            if line is None:
                break
            lines.append(line)
            clean = line.rstrip("\n")
            if clean:
                print(f"[{label}] {clean}")
        ret_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"[{label}] ERROR: Timeout after {timeout}s; process killed")
        ret_code = -1
    except Exception as e:
        print(f"[{label}] ERROR: Exception while streaming: {e}")
        ret_code = -1
    stdout_all = "".join(lines)
    return subprocess.CompletedProcess(cmd, ret_code, stdout_all, None)


@tool
def init_nextjs_app(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Initialize a new Next.js application with TypeScript, Tailwind CSS, and ESLint.

    This creates a complete Next.js project structure in the session directory.
    Only call this ONCE at the start of a new project.

    Returns:
        Success message with project details or error message.
    """
    session_id = _get_session_from_config(config)

    print(
        f"[COMMANDS] init_nextjs_app → Initializing Next.js app for session {session_id}"
    )

    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "init_app.sh"), session_id],
            label="init_nextjs_app",
            timeout=240,
        )
        if result.returncode == 0:
            output = (
                "✓ Next.js app initialized successfully!\n\nProject includes:\n"
                "- TypeScript\n- Tailwind CSS\n- App Router\n- ESLint\n- src/ directory structure\n\n"
                "You can now create and edit files in the project."
            )
            print("[COMMANDS] init_nextjs_app → SUCCESS")
            return output
        else:
            print(f"[COMMANDS] init_nextjs_app → ERROR exit {result.returncode}")
            return f"Error initializing Next.js app (exit {result.returncode}).\n\n" + (
                result.stdout or "(no output)"
            )
    except subprocess.TimeoutExpired:
        print("[COMMANDS] init_nextjs_app → TIMEOUT")
        return "Error: Command timed out after 240 seconds"
    except Exception as e:
        print(f"[COMMANDS] init_nextjs_app → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def install_dependencies(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Install npm dependencies for the Next.js project.

    Run this after initializing the app or when package.json is modified.

    Returns:
        Success message or error message.
    """
    session_id = _get_session_from_config(config)

    print(f"[COMMANDS] install_dependencies → Installing for session {session_id}")

    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "install.sh"), session_id],
            label="install_dependencies",
            timeout=240,
        )
        if result.returncode == 0:
            print("[COMMANDS] install_dependencies → SUCCESS")
            return "✓ Dependencies installed successfully!\n\n" + (result.stdout or "")
        else:
            print(f"[COMMANDS] install_dependencies → ERROR exit {result.returncode}")
            return f"Error installing dependencies (exit {result.returncode}).\n\n" + (
                result.stdout or "(no output)"
            )
    except subprocess.TimeoutExpired:
        print("[COMMANDS] install_dependencies → TIMEOUT")
        return "Error: Command timed out after 240 seconds."
    except Exception as e:
        print(f"[COMMANDS] install_dependencies → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def run_dev_server(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Start the Next.js development server.

    This runs 'npm run dev' to start the development server.
    Note: The server will run in the background. Use this to test the app.

    Returns:
        Success message or error message.
    """
    session_id = _get_session_from_config(config)

    print(f"[COMMANDS] run_dev_server → Starting dev server for session {session_id}")

    try:
        process = subprocess.Popen(
            ["bash", str(SCRIPTS_DIR / "run_app.sh"), session_id],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=5)
            if process.returncode and process.returncode != 0:
                print(f"[COMMANDS] run_dev_server → ERROR exit {process.returncode}")
                return (
                    f"Error starting dev server (exit {process.returncode}).\n{stderr}"
                )
        except subprocess.TimeoutExpired:
            print("[COMMANDS] run_dev_server → Server starting (background)")
            return (
                "✓ Development server is starting!\n\n"
                "App should be available at http://localhost:3000 (once ready).\n"
                "Server runs in background."
            )
        print("[COMMANDS] run_dev_server → SUCCESS")
        return "✓ Development server started!\n\n" + (stdout or "")

    except Exception as e:
        print(f"[COMMANDS] run_dev_server → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def run_npm_command(
    command: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Run any npm command in the Next.js project directory.

    Use this to run npm scripts, install packages, or execute any npm command.

    Args:
        command: The npm command to run (e.g., "run build", "install react-icons", "list")

    Returns:
        Command output or error message.
    """
    session_id = _get_session_from_config(config)

    print(
        f"[COMMANDS] run_npm_command → Running 'npm {command}' for session {session_id}"
    )

    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "run_npm_command.sh"), session_id, command],
            label="run_npm_command",
            timeout=180,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] run_npm_command → SUCCESS")
            return "✓ Command completed successfully!\n\n" + output
        else:
            print(f"[COMMANDS] run_npm_command → ERROR exit {result.returncode}")
            return f"Error running command (exit {result.returncode}).\n\n" + output
    except subprocess.TimeoutExpired:
        print("[COMMANDS] run_npm_command → TIMEOUT")
        return "Error: Command timed out after 180 seconds"
    except Exception as e:
        print(f"[COMMANDS] run_npm_command → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def run_npx_command(
    command: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Run any npx command in the project directory.

    Ideal for installing shadcn components or executing CLI utilities.

    Args:
        command: npx command arguments (e.g., "shadcn@latest add @shadcn/ui/spotlight")

    Returns:
        Command output or error details.
    """

    session_id = _get_session_from_config(config)

    print(
        f"[COMMANDS] run_npx_command → Running 'npx {command}' for session {session_id}"
    )

    try:
        result = _run_with_live_logs(
            [
                "bash",
                str(SCRIPTS_DIR / "run_npx_command.sh"),
                session_id,
                *command.split(),
            ],
            label="run_npx_command",
            timeout=240,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] run_npx_command → SUCCESS")
            return "✓ npx command completed successfully!\n\n" + output
        else:
            print(f"[COMMANDS] run_npx_command → ERROR exit {result.returncode}")
            return f"Error running npx command (exit {result.returncode}).\n\n" + output
    except subprocess.TimeoutExpired:
        print("[COMMANDS] run_npx_command → TIMEOUT")
        return "Error: npx command timed out after 240 seconds"
    except Exception as e:
        print(f"[COMMANDS] run_npx_command → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def run_git_command(
    command: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Run a git command in the project directory for the current session.

    Args:
        command: git arguments (e.g., "status -sb", "add -A", "commit -m 'msg'")

    Returns:
        Command output or error details.
    """

    session_id = _get_session_from_config(config)

    print(
        f"[COMMANDS] run_git_command → Running 'git {command}' for session {session_id}"
    )

    try:
        result = _run_with_live_logs(
            [
                "bash",
                str(SCRIPTS_DIR / "run_git_command.sh"),
                session_id,
                *command.split(),
            ],
            label="run_git_command",
            timeout=120,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] run_git_command → SUCCESS")
            return "✓ git command completed successfully!\n\n" + output
        else:
            print(f"[COMMANDS] run_git_command → ERROR exit {result.returncode}")
            return f"Error running git command (exit {result.returncode}).\n\n" + output
    except subprocess.TimeoutExpired:
        print("[COMMANDS] run_git_command → TIMEOUT")
        return "Error: git command timed out after 120 seconds"
    except Exception as e:
        print(f"[COMMANDS] run_git_command → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def lint_project(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Run ESLint to check for syntax errors and linting issues in the Next.js project.

    ⚠️ MANDATORY: You MUST call this tool after making any code changes to verify syntax and catch errors.
    ⚠️ CRITICAL: If this tool reports errors, you MUST fix them immediately. Do NOT proceed with other tasks until all linting errors are resolved.

    This runs 'npm run lint' to check:
    - TypeScript syntax errors
    - ESLint rule violations
    - Code quality issues
    - Potential bugs

    Returns:
        Linting results with any errors or warnings found. If errors are found, you MUST fix them.
    """
    session_id = _get_session_from_config(config)

    print(f"[COMMANDS] lint_project → Linting project for session {session_id}")

    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "lint_project.sh"), session_id],
            label="lint_project",
            timeout=180,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] lint_project → SUCCESS - No issues found")
            return (
                "✅ Linting passed! No syntax errors or linting issues found.\n\n"
                + output
            )
        else:
            print("[COMMANDS] lint_project → ❌ ERRORS FOUND - Must be fixed!")
            error_count = output.count("error")
            warning_count = output.count("warning")
            return (
                f"❌ LINTING FAILED - {error_count} error(s), {warning_count} warning(s)\n\n"
                + output
                + "\n\n🚨 CRITICAL: Fix these errors before proceeding."
            )
    except subprocess.TimeoutExpired:
        print("[COMMANDS] lint_project → TIMEOUT")
        return "Error: Linting timed out after 180 seconds"
    except Exception as e:
        print(f"[COMMANDS] lint_project → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def git_log(limit: int, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Show recent commits (history) with a concise format.

    Args:
        limit: number of commits to show (e.g., 10)

    Returns:
        Formatted git log output or error details.
    """
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] git_log → Showing last {limit} commits for {session_id}")
    try:
        result = _run_with_live_logs(
            [
                "bash",
                str(SCRIPTS_DIR / "run_git_command.sh"),
                session_id,
                "log",
                "-n",
                str(limit),
                "--pretty=format:%h %ad %an %s",
                "--date=short",
            ],
            label="git_log",
            timeout=90,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] git_log → SUCCESS")
            return output
        else:
            print(f"[COMMANDS] git_log → ERROR exit {result.returncode}")
            return f"Error running git log (exit {result.returncode}).\n\n{output}"
    except subprocess.TimeoutExpired:
        print("[COMMANDS] git_log → TIMEOUT")
        return "Error: git log timed out after 90 seconds"
    except Exception as e:
        print(f"[COMMANDS] git_log → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def git_show(commit: str, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Show details for a specific commit (message, author, files changed).

    Args:
        commit: commit hash or ref (e.g., HEAD, abc123)

    Returns:
        Commit details including stats and file list.
    """
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] git_show → Showing commit {commit} for {session_id}")
    try:
        result = _run_with_live_logs(
            [
                "bash",
                str(SCRIPTS_DIR / "run_git_command.sh"),
                session_id,
                "show",
                "--stat",
                "--name-status",
                "--format=fuller",
                commit,
            ],
            label="git_show",
            timeout=120,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] git_show → SUCCESS")
            return output
        else:
            print(f"[COMMANDS] git_show → ERROR exit {result.returncode}")
            return f"Error running git show (exit {result.returncode}).\n\n{output}"
    except subprocess.TimeoutExpired:
        print("[COMMANDS] git_show → TIMEOUT")
        return "Error: git show timed out after 120 seconds"
    except Exception as e:
        print(f"[COMMANDS] git_show → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def check_css(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Type-check Tailwind CSS in globals.css using the Tailwind CLI.

    Runs a one-file compile against src/app/globals.css to catch errors like
    'Cannot apply unknown utility class'. Does not start dev server or build the app.
    """
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] check_css → Checking globals.css for session {session_id}")
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "css_check.sh"), session_id],
            label="check_css",
            timeout=120,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] check_css → SUCCESS")
            return f"✓ CSS check passed.\n\n{output}"
        else:
            print("[COMMANDS] check_css → ERROR")
            return f"❌ CSS check failed (exit {result.returncode}).\n\n{output}"
    except subprocess.TimeoutExpired:
        print("[COMMANDS] check_css → TIMEOUT")
        return "Error: CSS check timed out after 120 seconds"
    except Exception as e:
        print(f"[COMMANDS] check_css → EXCEPTION: {e}")
        return f"Error: {str(e)}"


# Export all command tools
command_tools = [
    install_dependencies,
    run_dev_server,
    run_npm_command,
    run_npx_command,
    run_git_command,
    check_css,
    git_log,
    git_show,
    lint_project,
]
