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
    """List all files in the session directory, including nested folders.

    Returns relative paths from the session root (e.g., 'src/app/page.tsx', 'package.json').
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    files = []

    # Walk through all directories recursively
    for root, dirs, filenames in os.walk(session_dir):
        # Skip node_modules and .next directories
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".next", ".git"]]

        for filename in filenames:
            full_path = Path(root) / filename
            # Get relative path from session_dir
            relative_path = full_path.relative_to(session_dir)
            files.append(str(relative_path))

    print(f"[FILES] list_files → Found {len(files)} files")
    return sorted(files)


@tool
def create_file(
    name: str, content: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Create a new file in the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    Parent directories will be created automatically if they don't exist.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if file_path.exists():
        print(f"[FILES] create_file → ERROR: {name} already exists")
        return f"Error: File {name} already exists. Use update_file to modify it."

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(content)
    print(f"[FILES] create_file → Created {name} ({len(content)} chars) at {file_path}")
    return f"File {name} created successfully."


@tool
def read_file(name: str, config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Read a file from the session directory with line numbers for easy reference.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    Returns the file content with line numbers prepended to each line (1-based, e.g., '1: content').
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

    # Add 1-based line numbers to each line for easy reference
    numbered_lines = []
    for i, line in enumerate(lines, start=1):
        numbered_lines.append(f"{i}: {line}")

    result = "\n".join(numbered_lines)
    print(f"[FILES] read_file → Read {name} ({len(lines)} lines)")
    return result


@tool
def read_lines(
    name: str,
    start_line: int,
    end_line: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Read a 1-based inclusive range of lines from a file.

    Parameters
    ----------
    name: str
        Path to the file relative to the session root.
    start_line: int
        1-based line number where the range should begin (inclusive).
    end_line: int
        1-based line number where the range should end (inclusive).

    Returns the requested lines prefixed with their 1-based line numbers. Useful for
    quickly inspecting small sections without streaming the entire file.
    """

    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        print(f"[FILES] read_lines → ERROR: {name} not found")
        return f"Error: File {name} not found."

    if start_line < 1 or end_line < 1:
        print("[FILES] read_lines → ERROR: start_line/end_line must be >= 1")
        return "Error: start_line and end_line must be >= 1 (1-based indexing)."

    if start_line > end_line:
        print("[FILES] read_lines → ERROR: start_line greater than end_line")
        return "Error: start_line must be less than or equal to end_line."

    content = file_path.read_text().splitlines(keepends=False)
    total_lines = len(content)

    start_index = start_line - 1
    end_index = end_line - 1

    if start_index >= total_lines:
        print("[FILES] read_lines → ERROR: start_line out of range")
        return (
            f"Error: start_line {start_line} exceeds total line count of {total_lines}."
        )

    if end_index >= total_lines:
        print("[FILES] read_lines → ERROR: end_line out of range")
        return f"Error: end_line {end_line} exceeds total line count of {total_lines}."

    selected = []
    for offset, line in enumerate(content[start_index : end_index + 1]):
        actual_line_number = start_line + offset
        selected.append(f"{actual_line_number}: {line}")

    result = "\n".join(selected)
    print(
        f"[FILES] read_lines → Read lines {start_line}-{end_line} from {name} ({len(selected)} lines)"
    )
    return result


@tool
def update_file(
    name: str, content: str, config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Update a file in the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    """
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
    """Delete a file from the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    """
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
    """Remove lines from a file in the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        return f"Error: File {name} not found."

    lines = file_path.read_text().splitlines(keepends=True)
    # Convert 1-based indices to 0-based positions
    zero_based = {i - 1 for i in indices if i > 0}
    new_lines = [line for i, line in enumerate(lines) if i not in zero_based]
    file_path.write_text("".join(new_lines))
    return f"Lines removed successfully from {name}."


class InsertedLines(BaseModel):
    lines: list[str]
    index: int  # 1-based insertion index


class UpdatedLines(BaseModel):
    """Lines to update with their replacements (1-based, inclusive)."""

    start_index: int
    end_index: int  # inclusive
    replacement_lines: list[str]


@tool
def insert_lines(
    name: str,
    lines: list[InsertedLines],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Insert lines at specific indices in a file in the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    file_path = session_dir / name

    if not file_path.exists():
        return f"Error: File {name} not found."

    content = file_path.read_text().splitlines(keepends=True)

    # Sort by index in reverse to insert from bottom to top
    sorted_inserts = sorted(lines, key=lambda x: x.index, reverse=True)

    for insert in sorted_inserts:
        pos = max(0, insert.index - 1)
        for line_text in reversed(insert.lines):
            if not line_text.endswith("\n"):
                line_text += "\n"
            content.insert(pos, line_text)

    file_path.write_text("".join(content))
    return f"Lines inserted successfully into {name}."


@tool
def update_lines(
    name: str,
    updates: list[UpdatedLines],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Update/replace specific line ranges in a file in the session directory.

    Supports nested paths (e.g., 'src/app/page.tsx', 'components/Button.tsx').
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
        # Convert 1-based inputs to 0-based
        start0 = update.start_index - 1
        end0 = update.end_index - 1

        # Validate indices
        if start0 < 0 or end0 >= len(content):
            print(f"[FILES] update_lines → ERROR: Indices out of range")
            return f"Error: Line indices out of range (1-{len(content)})."

        if start0 > end0:
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
        del content[start0 : end0 + 1]

        # Insert replacement lines at start0
        for i, line in enumerate(replacement):
            content.insert(start0 + i, line)

    file_path.write_text("".join(content))
    print(f"[FILES] update_lines → Successfully updated {name}")
    return f"Lines updated successfully in {name}."


# ============================================================================
# BATCH OPERATIONS - Preferred for efficiency
# ============================================================================


class FileRead(BaseModel):
    """File to read."""

    name: str


class FileCreate(BaseModel):
    """File to create."""

    name: str
    content: str


class FileUpdate(BaseModel):
    """File to update."""

    name: str
    content: str


class FileDelete(BaseModel):
    """File to delete."""

    name: str


class FileLineUpdate(BaseModel):
    """File with line updates."""

    name: str
    updates: list[UpdatedLines]


@tool
def batch_read_files(
    files: list[FileRead], config: Annotated[RunnableConfig, InjectedToolArg]
) -> dict[str, str]:
    """Read multiple files in a single operation. Much more efficient than calling read_file multiple times.

    Returns a dictionary mapping file names to their content (with line numbers).
    If a file doesn't exist, its value will be an error message.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    results = {}

    print(f"[FILES] batch_read_files → Reading {len(files)} file(s)")

    for file_read in files:
        file_path = session_dir / file_read.name
        if not file_path.exists():
            results[file_read.name] = f"Error: File {file_read.name} not found."
            continue

        content = file_path.read_text()
        lines = content.splitlines(keepends=False)

        # Add 1-based line numbers
        numbered_lines = [f"{i}: {line}" for i, line in enumerate(lines, start=1)]
        results[file_read.name] = "\n".join(numbered_lines)

    print(
        f"[FILES] batch_read_files → Successfully read {len([r for r in results.values() if not r.startswith('Error')])} file(s)"
    )
    return results


@tool
def batch_create_files(
    files: list[FileCreate], config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Create multiple files in a single operation. Much more efficient than calling create_file multiple times.

    All parent directories will be created automatically.
    Returns a summary of the operation.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    created = []
    errors = []

    print(f"[FILES] batch_create_files → Creating {len(files)} file(s)")

    for file_create in files:
        file_path = session_dir / file_create.name

        if file_path.exists():
            errors.append(
                f"{file_create.name}: already exists (use batch_update_files to modify)"
            )
            continue

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_create.content)
        created.append(file_create.name)

    summary = f"Created {len(created)} file(s): {', '.join(created)}"
    if errors:
        summary += f"\nErrors: {'; '.join(errors)}"

    print(f"[FILES] batch_create_files → {summary}")
    return summary


@tool
def batch_update_files(
    files: list[FileUpdate], config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Update multiple files in a single operation. Much more efficient than calling update_file multiple times.

    Returns a summary of the operation.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    updated = []
    errors = []

    print(f"[FILES] batch_update_files → Updating {len(files)} file(s)")

    for file_update in files:
        file_path = session_dir / file_update.name

        if not file_path.exists():
            errors.append(
                f"{file_update.name}: not found (use batch_create_files to create)"
            )
            continue

        file_path.write_text(file_update.content)
        updated.append(file_update.name)

    summary = f"Updated {len(updated)} file(s): {', '.join(updated)}"
    if errors:
        summary += f"\nErrors: {'; '.join(errors)}"

    print(f"[FILES] batch_update_files → {summary}")
    return summary


@tool
def batch_delete_files(
    files: list[FileDelete], config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Delete multiple files in a single operation. Much more efficient than calling delete_file multiple times.

    Returns a summary of the operation.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    deleted = []
    errors = []

    print(f"[FILES] batch_delete_files → Deleting {len(files)} file(s)")

    for file_delete in files:
        file_path = session_dir / file_delete.name

        if not file_path.exists():
            errors.append(f"{file_delete.name}: not found")
            continue

        file_path.unlink()
        deleted.append(file_delete.name)

    summary = f"Deleted {len(deleted)} file(s): {', '.join(deleted)}"
    if errors:
        summary += f"\nErrors: {'; '.join(errors)}"

    print(f"[FILES] batch_delete_files → {summary}")
    return summary


@tool
def batch_update_lines(
    files: list[FileLineUpdate], config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Update lines in multiple files in a single operation. MUCH more efficient than calling update_lines multiple times.

    This is the PREFERRED way to make edits across multiple files. Accumulate all your changes and apply them in one batch.

    Returns a summary of the operation.
    """
    session_id = _get_session_from_config(config)
    session_dir = get_session_dir(session_id)
    updated = []
    errors = []

    print(
        f"[FILES] batch_update_lines → Updating lines in {len(files)} file(s) with {sum(len(f.updates) for f in files)} total edit(s)"
    )

    for file_update in files:
        file_path = session_dir / file_update.name

        if not file_path.exists():
            errors.append(f"{file_update.name}: not found")
            continue

        content = file_path.read_text().splitlines(keepends=True)

        # Sort by start_index in reverse to process from bottom to top
        sorted_updates = sorted(
            file_update.updates, key=lambda x: x.start_index, reverse=True
        )

        for update in sorted_updates:
            start0 = update.start_index - 1
            end0 = update.end_index - 1

            if start0 < 0 or end0 >= len(content) or start0 > end0:
                errors.append(
                    f"{file_update.name}: invalid range {update.start_index}-{update.end_index}"
                )
                continue

            replacement = []
            for line_text in update.replacement_lines:
                if not line_text.endswith("\n"):
                    line_text += "\n"
                replacement.append(line_text)

            del content[start0 : end0 + 1]
            for i, line in enumerate(replacement):
                content.insert(start0 + i, line)

        file_path.write_text("".join(content))
        updated.append(f"{file_update.name} ({len(file_update.updates)} edit(s))")

    summary = f"Updated {len(updated)} file(s): {', '.join(updated)}"
    if errors:
        summary += f"\nErrors: {'; '.join(errors)}"

    print(f"[FILES] batch_update_lines → {summary}")
    return summary
