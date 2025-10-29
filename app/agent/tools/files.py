"""File tools using disk storage with session-specific directories."""

import os
import shutil
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

OUTPUT_DIR = "__out__"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_session_dir(session_id: str = "default") -> Path:
    """Get the session-specific output directory."""
    session_dir = Path(OUTPUT_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def clear_session_dir(session_id: str):
    """Clear all files in the session directory."""
    session_dir = Path(OUTPUT_DIR) / session_id
    print(f"[FILES] Clearing session directory: {session_dir}")
    if session_dir.exists():
        files_before = list(session_dir.iterdir())
        print(f"[FILES] Found {len(files_before)} files to delete")
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"[FILES] Session directory ready: {session_dir}")


def _get_session_from_config(config: RunnableConfig) -> str:
    """Extract session_id from config."""
    session_id = config.get("configurable", {}).get("session_id", "default")
    print(f"[FILES] Using session_id: {session_id}")
    return session_id


@tool
def list_files(config: Annotated[RunnableConfig, InjectedToolArg]) -> list[str]:
    """List all files in the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    files = [f.name for f in session_dir.iterdir() if f.is_file()]
    print(f"[FILES] list_files → Found {len(files)} files: {files}")
    return files


@tool
def create_file(
    name: str, content: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Create a new file in the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if file_path.exists():
        print(f"[FILES] create_file → ERROR: {name} already exists")
        return f"Error: File {name} already exists. Use update_file to modify it."

    file_path.write_text(content)
    print(f"[FILES] create_file → Created {name} ({len(content)} chars) at {file_path}")
    return f"File {name} created successfully."


@tool
def read_file(name: str, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Read a file from the session directory with line numbers for easy reference.

    Returns the file content with line numbers prepended to each line (e.g., '1: content').
    This helps when using update_lines, insert_lines, or remove_lines tools.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        print(f"[FILES] read_file → ERROR: {name} not found")
        return f"Error: File {name} not found."

    content = file_path.read_text()
    lines = content.splitlines(keepends=False)

    # Add line numbers to each line for easy reference
    numbered_lines = []
    for i, line in enumerate(lines):
        numbered_lines.append(f"{i}: {line}")

    result = "\n".join(numbered_lines)
    print(f"[FILES] read_file → Read {name} ({len(lines)} lines)")
    return result


@tool
def update_file(
    name: str, content: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Update a file in the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        print(f"[FILES] update_file → ERROR: {name} not found")
        return f"Error: File {name} not found. Use create_file to create it."

    file_path.write_text(content)
    print(f"[FILES] update_file → Updated {name} ({len(content)} chars)")
    return f"File {name} updated successfully."


@tool
def delete_file(name: str, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Delete a file from the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        print(f"[FILES] delete_file → ERROR: {name} not found")
        return f"Error: File {name} not found."

    file_path.unlink()
    print(f"[FILES] delete_file → Deleted {name}")
    return f"File {name} deleted successfully."


@tool
def remove_lines(
    name: str, indices: list[int], config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Remove lines from a file in the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        return f"Error: File {name} not found."

    lines = file_path.read_text().splitlines(keepends=True)
    new_lines = [line for i, line in enumerate(lines) if i not in indices]
    file_path.write_text("".join(new_lines))
    return f"Lines removed successfully from {name}."


class InsertedLines(BaseModel):
    lines: list[str]
    index: int


class UpdatedLines(BaseModel):
    """Lines to update with their replacements."""

    start_index: int
    end_index: int  # inclusive
    replacement_lines: list[str]


@tool
def insert_lines(
    name: str,
    lines: list[InsertedLines],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Insert lines at specific indices in a file in the session directory."""
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        return f"Error: File {name} not found."

    content = file_path.read_text().splitlines(keepends=True)

    # Sort by index in reverse to insert from bottom to top
    sorted_inserts = sorted(lines, key=lambda x: x.index, reverse=True)

    for insert in sorted_inserts:
        for line_text in reversed(insert.lines):
            if not line_text.endswith("\n"):
                line_text += "\n"
            content.insert(insert.index, line_text)

    file_path.write_text("".join(content))
    return f"Lines inserted successfully into {name}."


@tool
def update_lines(
    name: str,
    updates: list[UpdatedLines],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Update/replace specific line ranges in a file in the session directory.

    Each update specifies a start_index, end_index (inclusive), and replacement_lines.
    The lines from start_index to end_index will be replaced with replacement_lines.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        print(f"[FILES] update_lines → ERROR: {name} not found")
        return f"Error: File {name} not found."

    content = file_path.read_text().splitlines(keepends=True)
    print(f"[FILES] update_lines → Updating {len(updates)} range(s) in {name}")

    # Sort by start_index in reverse to process from bottom to top
    # This prevents index shifting issues
    sorted_updates = sorted(updates, key=lambda x: x.start_index, reverse=True)

    for update in sorted_updates:
        # Validate indices
        if update.start_index < 0 or update.end_index >= len(content):
            print(f"[FILES] update_lines → ERROR: Indices out of range")
            return f"Error: Line indices out of range (0-{len(content)-1})."

        if update.start_index > update.end_index:
            print(f"[FILES] update_lines → ERROR: Invalid range")
            return f"Error: start_index must be <= end_index."

        # Prepare replacement lines with proper line endings
        replacement = []
        for line_text in update.replacement_lines:
            if not line_text.endswith("\n"):
                line_text += "\n"
            replacement.append(line_text)

        print(
            f"[FILES] update_lines → Replacing lines {update.start_index}-{update.end_index} with {len(replacement)} line(s)"
        )

        # Replace the line range
        # Delete lines from start_index to end_index (inclusive)
        del content[update.start_index : update.end_index + 1]

        # Insert replacement lines at start_index
        for i, line in enumerate(replacement):
            content.insert(update.start_index + i, line)

    file_path.write_text("".join(content))
    print(f"[FILES] update_lines → Successfully updated {name}")
    return f"Lines updated successfully in {name}."
