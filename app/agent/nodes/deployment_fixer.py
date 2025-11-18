"""Deployment Fixer node - specialized LLM for fixing deployment errors."""

from __future__ import annotations
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from app.agent.state import BuilderState

from app.agent.tools.files import (
    # Batch operations (ONLY USE THESE)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
    list_files_internal,
)

from app.agent.tools.commands import (
    lint_project,
)

load_dotenv()

DEPLOYMENT_FIXER_PROMPT = """You are a Deployment Debugging Specialist focused exclusively on fixing deployment errors.

🎯 YOUR MISSION:
Fix the deployment error that caused the Vercel deployment to fail. You have access to the full error log and must identify and resolve the root cause.

⚠️ CRITICAL DEPLOYMENT ERROR CONTEXT:
{deployment_error}

🔍 COMMON DEPLOYMENT ISSUES TO CHECK:

1. **Build Errors**:
   - Missing dependencies in package.json
   - TypeScript compilation errors
   - Import/export issues
   - Missing environment variables

2. **Next.js Specific**:
   - Invalid next.config.js
   - Server/client component mismatches
   - Missing 'use client' directives
   - Invalid API routes
   - **Module not found** errors for App Router pages or components

3. **Configuration Issues**:
   - Incorrect build commands
   - Wrong output directory
   - Missing public assets
   - Invalid tsconfig.json

4. **Dependency Problems**:
   - Version conflicts
   - Missing peer dependencies
   - Incorrect imports from node_modules

5. **File/Path Issues**:
   - Case sensitivity problems
   - Missing files referenced in code
   - Incorrect relative paths

📋 YOUR PROCESS:

1. **Analyze the Error**: Read the deployment error carefully.
2. **Identify Root Cause**: Determine what's causing the failure.
3. **Read Relevant Files** (ALWAYS via batch_read_files):
   - For **Next.js module-not-found errors** (e.g. `Module not found: Can't resolve '@/src/components/sections/navigation'`):
     - Read:
       - `tsconfig.json`
       - `next.config.js`
       - `src/app/page.tsx`
       - Any referenced section/component files under `src/components/sections/`.
     - Compare the alias in `tsconfig.json` (e.g. `paths: {{ "@/*": ["./src/*"] }}`) with the failing import.
       - If the import uses `@/src/...` but the alias is `@/*` → `./src/*`, then **remove the extra `src` segment** and import from `@/components/...` or the correct path.
       - If the import path points to a file that does not exist, either:
         - Create the missing file in `src/components/sections/`, or
         - Update the import to match the actual file name and path (respecting case).
   - For other errors, read only the files mentioned in the error message (configs, pages, components, etc.).
4. **Apply Fixes**:
   - Use `batch_update_files` or `batch_update_lines` to:
     - Fix incorrect import paths.
     - Align `tsconfig.json` path aliases and actual file locations.
     - Create missing section/component files when appropriate.
5. **Verify**:
   - Run `lint_project` to ensure no syntax/lint errors remain.
   - If the error was a module-not-found issue, double-check that all imports in `src/app/page.tsx` and any shared layouts are resolvable given the actual `src/` structure.

🛠️ AVAILABLE TOOLS:

File Operations (REQUIRED - use batch operations):
- batch_read_files: Read multiple files at once
- batch_create_files: Create new files if needed
- batch_update_files: Update file contents
- batch_delete_files: Remove problematic files
- batch_update_lines: Precise line-by-line updates
- list_files: See what files exist

Validation:
- lint_project: Check for linting/syntax errors after fixes

⚡ RULES:

1. ALWAYS start by reading the error message thoroughly
2. Read files before modifying them (use batch_read_files)
3. Make targeted, minimal changes to fix the specific error
4. Run lint_project after making changes
5. Explain what you're fixing in your response
6. Focus ONLY on deployment-blocking issues
7. Don't refactor or improve code unless it's causing the deployment failure

🎯 FOCUS: Your sole purpose is to make the deployment succeed. Fix what's broken, nothing more.

FILES IN SESSION:
{files_list}
"""

tools = [
    # Batch file operations (ONLY USE THESE FOR FILES)
    batch_read_files,
    batch_create_files,
    batch_update_files,
    batch_delete_files,
    batch_update_lines,
    # Utility
    list_files,
    # Command tools
    lint_project,
]


def deployment_fixer(state: BuilderState) -> BuilderState:
    """
    Specialized node for fixing deployment errors.

    Focuses exclusively on analyzing deployment failures and making
    targeted fixes to resolve the issues.
    """
    response = None  # ensure defined for exception handling
    try:
        print("\n\n[DEPLOYMENT_FIXER] 🔧 Starting deployment error analysis...")

        session_id = state.session_id
        deployment_error = state.deployment_error or "No error details available"

        print(f"[DEPLOYMENT_FIXER] Session: {session_id}")
        print(f"[DEPLOYMENT_FIXER] Error:\n{deployment_error[:200]}...")

        # Get list of files
        files = "\n".join(list_files_internal(session_id))

        # Build specialized prompt with error context
        prompt_with_context = DEPLOYMENT_FIXER_PROMPT.format(
            deployment_error=deployment_error, files_list=files
        )

        # Use GPT-5 with minimal reasoning for fast, focused fixes
        _deployment_fixer_llm_ = ChatOpenAI(
            model="gpt-5", reasoning_effort="low"
        ).bind_tools(
            tools,
            parallel_tool_calls=True,
            tool_choice="any" if not state.deployment_fixer_run else None,
        )

        SYS = SystemMessage(content=prompt_with_context)
        messages = [SYS, *state.messages]

        print("[DEPLOYMENT_FIXER] Analyzing deployment error and determining fixes...")
        response = _deployment_fixer_llm_.invoke(messages)

        print(f"\n\n[DEPLOYMENT_FIXER] Response: {response}")

        # Check if there are tool calls
        if getattr(response, "tool_calls", None):
            print(
                f"[DEPLOYMENT_FIXER] Making {len(response.tool_calls)} fix(es) to resolve deployment error"
            )
            return {
                "messages": [response],
                "deployment_fixer_run": True,
                # Keep deployment error info for context but mark as being fixed
                "deployment_failed": True,  # Still failed, but fixing
            }

        # If no tool calls, extract explanation
        output = ""
        if isinstance(response.content, str):
            output = response.content.strip()
        elif isinstance(response.content, list):
            output = "\n".join(
                (
                    str(segment.get("text", segment))
                    if isinstance(segment, dict)
                    else str(segment)
                )
                for segment in response.content
                if segment
            ).strip()

        if not output:
            output = "Deployment error analysis completed."

        print(f"[DEPLOYMENT_FIXER] {output}")

        return {
            "messages": [response],
            "deployment_fixer_run": True,
        }
    except Exception as e:
        print(f"[DEPLOYMENT_FIXER] Error: {e}")
        return {
            "messages": [response] if response is not None else state.messages,
            "deployment_fixer_run": True,
            "deployment_failed": True,
            "deployment_error": str(e),
        }
