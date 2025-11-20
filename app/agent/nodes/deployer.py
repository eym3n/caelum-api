"""Deployer node that handles deployment to Vercel after code changes."""

import subprocess
from pathlib import Path
from app.agent.state import BuilderState
from app.models.landing_page import LandingPageStatus
from app.utils.jobs import log_job_event
from app.utils.landing_pages import update_landing_page_status

# Resolve repository root (three levels up: /repo/app/agent/nodes/deployer.py → /repo)
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _run_with_live_logs(
    cmd: list[str], label: str, timeout: int = 300
) -> subprocess.CompletedProcess:
    """Run a shell command streaming stdout lines immediately.

    Returns a CompletedProcess surrogate with aggregated stdout for downstream parsing.
    """
    print(f"[{label}] EXEC: {' '.join(cmd)} (cwd={REPO_ROOT})")
    try:
        process = subprocess.Popen(
            cmd,
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


def deployer(state: BuilderState) -> BuilderState:
    """Deploy the project to Vercel after code changes are complete.

    This node runs after the coder finishes and deploys the generated
    Next.js project to Vercel using the deploy_to_vercel.sh script.

    If deployment fails, sets deployment_failed flag and returns error
    message so the coder can fix the issues.
    """

    log_job_event(
        state.job_id,
        node="deployer",
        message="Deploying landing page...",
        event_type="node_started",
    )

    session_id = state.session_id

    print(f"🚀 [DEPLOYER] Starting deployment for session: {session_id}")

    # Reset deployment_fixer_run flag before attempting deployment
    state.deployment_fixer_run = False

    try:
        # Run the deploy script with the session_id
        result = _run_with_live_logs(
            ["bash", str(SCRIPTS_DIR / "deploy_to_vercel.sh"), session_id],
            label="deployer",
            timeout=300,  # 5 minutes timeout for deployment
        )

        output = result.stdout or ""

        if result.returncode == 0:
            print(f"✅ [DEPLOYER] Deployment successful for session: {session_id}")
            print(f"[DEPLOYER] Output:\n{output}")

            # Construct deployment URL using Vercel's predictable format
            # Format: {session_id}.vercel.app
            deployment_url = f"https://{session_id}.vercel.app"
            print(f"[DEPLOYER] Deployment URL: {deployment_url}")

            # Update landing page status to generated
            updated_lp = update_landing_page_status(
                session_id=session_id,
                status=LandingPageStatus.GENERATED,
                deployment_url=deployment_url,
            )
            if updated_lp:
                print(f"✅ [DEPLOYER] Landing page status updated to 'generated'")

            return {
                "deployment_failed": False,
                "deployment_error": "",
                "deployment_fixer_run": False,
            }
        else:
            error_msg = f"Deployment failed with exit code {result.returncode}\n\n{output if output.strip() else '[No logs captured]'}"
            print(
                f"❌ [DEPLOYER] Deployment failed for session: {session_id} (exit code: {result.returncode})"
            )
            print(f"[DEPLOYER] Captured error log length: {len(error_msg)} chars")
            print(f"[DEPLOYER] Output:\n{output}")

            # Update landing page status to failed
            updated_lp = update_landing_page_status(
                session_id=session_id, status=LandingPageStatus.FAILED
            )
            if updated_lp:
                print(f"❌ [DEPLOYER] Landing page status updated to 'failed'")

            return {
                "deployment_failed": True,
                "deployment_error": error_msg,
                "found_error": True,
                "deployment_fixer_run": False,
            }

    except subprocess.TimeoutExpired:
        error_msg = "Deployment timed out after 5 minutes. This may indicate a network issue or the deployment process is taking too long."
        print(f"⏱️ [DEPLOYER] Deployment timed out for session: {session_id}")

        # Update landing page status to failed
        update_landing_page_status(
            session_id=session_id, status=LandingPageStatus.FAILED
        )

        return {
            "deployment_failed": True,
            "deployment_error": error_msg,
            "found_error": True,
            "deployment_fixer_run": False,
        }
    except Exception as e:
        error_msg = f"Deployment exception: {str(e)}"
        print(f"💥 [DEPLOYER] Deployment exception for session: {session_id}: {e}")

        # Update landing page status to failed
        update_landing_page_status(
            session_id=session_id, status=LandingPageStatus.FAILED
        )

        return {
            "deployment_failed": True,
            "deployment_error": error_msg,
            "found_error": True,
            "deployment_fixer_run": False,
        }
