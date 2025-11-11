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
def create_static_project(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Create (copy) a static Next.js project from the internal template.

    This simply copies the contents of the `template/` directory into the
    session's storage directory. Safe to call multiple times (idempotent via stamp file).
    No npm installs, linting, or builds are performed.
    """
    session_id = _get_session_from_config(config)
    print(
        f"[COMMANDS] create_static_project → Copying template for session {session_id}"
    )
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "copy_template.sh"), session_id],
            label="create_static_project",
            timeout=60,
        )
        if result.returncode == 0:
            print("[COMMANDS] create_static_project → SUCCESS")
            return "✓ Static project ready (template copied)."
        else:
            print(f"[COMMANDS] create_static_project → ERROR exit {result.returncode}")
            return f"Error copying template (exit {result.returncode}).\n\n" + (
                result.stdout or "(no output)"
            )
    except subprocess.TimeoutExpired:
        print("[COMMANDS] create_static_project → TIMEOUT")
        return "Error: Template copy timed out after 60 seconds"
    except Exception as e:
        print(f"[COMMANDS] create_static_project → EXCEPTION: {e}")
        return f"Error: {str(e)}"


# Removed: install_dependencies (no npm operations in static template mode)


# Removed: run_dev_server (static project; no dev server management)


# Removed: run_npm_command


# Removed: run_npx_command


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
    run_git_command,
    git_log,
    git_show,
]

# Reintroduce lint_project and check_css as stub tools (Node tooling removed).
from langchain_core.tools import tool as _tool_alias  # reuse decorator


@_tool_alias
def lint_project(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Run oxlint + CSS check via lint_project.sh script."""
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] lint_project → oxlint lint for session {session_id}")
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "lint_project.sh"), session_id],
            label="lint_project",
            timeout=180,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] lint_project → SUCCESS")
            return "✓ oxlint + CSS checks passed.\n\n" + output
        else:
            print(f"[COMMANDS] lint_project → ERROR exit {result.returncode}")
            return f"❌ Lint/CSS checks failed (exit {result.returncode}).\n\n" + output
    except subprocess.TimeoutExpired:
        print("[COMMANDS] lint_project → TIMEOUT")
        return "Error: lint timed out after 180s"
    except Exception as e:
        print(f"[COMMANDS] lint_project → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@_tool_alias
def check_css(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Run globals.css validation script."""
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] check_css → CSS check for session {session_id}")
    try:
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "css_check.sh"), session_id],
            label="check_css",
            timeout=120,
        )
        output = result.stdout or ""
        if result.returncode == 0:
            print("[COMMANDS] check_css → SUCCESS")
            return "✓ CSS check passed.\n\n" + output
        else:
            print(f"[COMMANDS] check_css → ERROR exit {result.returncode}")
            return f"❌ CSS check failed (exit {result.returncode}).\n\n" + output
    except subprocess.TimeoutExpired:
        print("[COMMANDS] check_css → TIMEOUT")
        return "Error: CSS check timed out after 120s"
    except Exception as e:
        print(f"[COMMANDS] check_css → EXCEPTION: {e}")
        return f"Error: {str(e)}"


# Update command_tools with lint & css
command_tools.extend([lint_project, check_css])
