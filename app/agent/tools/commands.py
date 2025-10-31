"""Command execution tools for running shell scripts and npm commands."""

import subprocess
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool


def _get_session_from_config(config: RunnableConfig) -> str:
    """Extract session_id from config."""
    return config.get("configurable", {}).get("session_id", "default")


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
        result = subprocess.run(
            ["bash", "scripts/init_app.sh", session_id],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        if result.returncode == 0:
            output = f"✓ Next.js app initialized successfully!\n\nProject includes:\n- TypeScript\n- Tailwind CSS\n- App Router\n- ESLint\n- src/ directory structure\n\nYou can now create and edit files in the project."
            print(f"[COMMANDS] init_nextjs_app → SUCCESS")
            return output
        else:
            error_msg = f"Error initializing Next.js app:\n{result.stderr}"
            print(f"[COMMANDS] init_nextjs_app → ERROR: {result.stderr}")
            return error_msg

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] init_nextjs_app → TIMEOUT")
        return "Error: Command timed out after 75 seconds"
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
        result = subprocess.run(
            ["bash", "scripts/install.sh", session_id],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        if result.returncode == 0:
            output = f"✓ Dependencies installed successfully!\n\n{result.stdout}"
            print(f"[COMMANDS] install_dependencies → SUCCESS")
            return output
        else:
            error_msg = f"Error installing dependencies:\n{result.stderr}"
            print(f"[COMMANDS] install_dependencies → ERROR: {result.stderr}")
            return error_msg

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] install_dependencies → TIMEOUT")
        return "Error: Command timed out after 75 seconds. Try again or the installation may still be running in the background."
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
        # Start the dev server in the background
        process = subprocess.Popen(
            ["bash", "scripts/run_app.sh", session_id],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Give it a moment to start
        try:
            stdout, stderr = process.communicate(timeout=5)
            if process.returncode and process.returncode != 0:
                error_msg = f"Error starting dev server:\n{stderr}"
                print(f"[COMMANDS] run_dev_server → ERROR: {stderr}")
                return error_msg
        except subprocess.TimeoutExpired:
            # Server is still running, which is expected
            output = "✓ Development server is starting!\n\nThe Next.js app should be available at http://localhost:3000\n\nNote: The server is running in the background."
            print(f"[COMMANDS] run_dev_server → Server started")
            return output

        output = f"✓ Development server started!\n\n{stdout}"
        print(f"[COMMANDS] run_dev_server → SUCCESS")
        return output

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
        result = subprocess.run(
            ["bash", "scripts/run_npm_command.sh", session_id, command],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        output = result.stdout if result.stdout else result.stderr

        if result.returncode == 0:
            print(f"[COMMANDS] run_npm_command → SUCCESS")
            return f"✓ Command completed successfully!\n\n{output}"
        else:
            print(f"[COMMANDS] run_npm_command → ERROR: {result.stderr}")
            return f"Error running command:\n{output}"

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] run_npm_command → TIMEOUT")
        return "Error: Command timed out after 75 seconds"
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
        result = subprocess.run(
            ["bash", "scripts/run_npx_command.sh", session_id, *command.split()],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        output = result.stdout if result.stdout else result.stderr

        if result.returncode == 0:
            print(f"[COMMANDS] run_npx_command → SUCCESS")
            return f"✓ npx command completed successfully!\n\n{output}"
        else:
            print(f"[COMMANDS] run_npx_command → ERROR: {result.stderr}")
            return f"Error running npx command:\n{output}"

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] run_npx_command → TIMEOUT")
        return "Error: npx command timed out after 75 seconds"
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
        result = subprocess.run(
            ["bash", "scripts/run_git_command.sh", session_id, *command.split()],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        output = result.stdout if result.stdout else result.stderr

        if result.returncode == 0:
            print(f"[COMMANDS] run_git_command → SUCCESS")
            return f"✓ git command completed successfully!\n\n{output}"
        else:
            print(f"[COMMANDS] run_git_command → ERROR: {result.stderr}")
            return f"Error running git command:\n{output}"

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] run_git_command → TIMEOUT")
        return "Error: git command timed out after 75 seconds"
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
        result = subprocess.run(
            ["bash", "scripts/lint_project.sh", session_id],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )

        output = result.stdout if result.stdout else result.stderr

        if result.returncode == 0:
            print(f"[COMMANDS] lint_project → SUCCESS - No issues found")
            return f"✅ Linting passed! No syntax errors or linting issues found.\n\n{output}"
        else:
            print(f"[COMMANDS] lint_project → ❌ ERRORS FOUND - Must be fixed!")
            error_count = output.count("error")
            warning_count = output.count("warning")
            return f"❌ LINTING FAILED - {error_count} error(s), {warning_count} warning(s)\n\n{output}\n\n🚨 CRITICAL: You MUST fix these errors before proceeding. Read the files mentioned in the errors, identify the issues, and fix them using update_lines or insert_lines. After fixing, run lint_project again to verify."

    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] lint_project → TIMEOUT")
        return "Error: Linting timed out after 75 seconds"
    except Exception as e:
        print(f"[COMMANDS] lint_project → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def git_log(
    limit: int, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Show recent commits (history) with a concise format.

    Args:
        limit: number of commits to show (e.g., 10)

    Returns:
        Formatted git log output or error details.
    """
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] git_log → Showing last {limit} commits for {session_id}")
    try:
        result = subprocess.run(
            [
                "bash",
                "scripts/run_git_command.sh",
                session_id,
                "log",
                f"-n",
                str(limit),
                "--pretty=format:%h %ad %an %s",
                "--date=short",
            ],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )
        output = result.stdout if result.stdout else result.stderr
        if result.returncode == 0:
            print(f"[COMMANDS] git_log → SUCCESS")
            return output
        else:
            print(f"[COMMANDS] git_log → ERROR: {result.stderr}")
            return f"Error running git log:\n{output}"
    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] git_log → TIMEOUT")
        return "Error: git log timed out after 75 seconds"
    except Exception as e:
        print(f"[COMMANDS] git_log → EXCEPTION: {e}")
        return f"Error: {str(e)}"


@tool
def git_show(
    commit: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Show details for a specific commit (message, author, files changed).

    Args:
        commit: commit hash or ref (e.g., HEAD, abc123)

    Returns:
        Commit details including stats and file list.
    """
    session_id = _get_session_from_config(config)
    print(f"[COMMANDS] git_show → Showing commit {commit} for {session_id}")
    try:
        result = subprocess.run(
            [
                "bash",
                "scripts/run_git_command.sh",
                session_id,
                "show",
                "--stat",
                "--name-status",
                "--format=fuller",
                commit,
            ],
            cwd="/Users/maystro/Documents/langgraph-app-builder/api",
            capture_output=True,
            text=True,
            timeout=75,
        )
        output = result.stdout if result.stdout else result.stderr
        if result.returncode == 0:
            print(f"[COMMANDS] git_show → SUCCESS")
            return output
        else:
            print(f"[COMMANDS] git_show → ERROR: {result.stderr}")
            return f"Error running git show:\n{output}"
    except subprocess.TimeoutExpired:
        print(f"[COMMANDS] git_show → TIMEOUT")
        return "Error: git show timed out after 75 seconds"
    except Exception as e:
        print(f"[COMMANDS] git_show → EXCEPTION: {e}")
        return f"Error: {str(e)}"

# Export all command tools
command_tools = [
    init_nextjs_app,
    install_dependencies,
    run_dev_server,
    run_npm_command,
    run_npx_command,
    run_git_command,
    git_log,
    git_show,
    lint_project,
]
