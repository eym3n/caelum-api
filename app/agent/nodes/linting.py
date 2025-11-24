from __future__ import annotations

import subprocess
from pathlib import Path

from app.agent.state import BuilderState
from app.utils.jobs import log_job_event


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def linting(state: BuilderState) -> BuilderState:
    log_job_event(
        state.job_id,
        node="linting",
        message="Running lint checks...",
        event_type="node_started",
    )

    session_id = state.session_id
    cmd = [
        "bash",
        str(SCRIPTS_DIR / "lint_project.sh"),
        session_id,
    ]

    process = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    output = (process.stdout or "") + (process.stderr or "")
    lint_failed = process.returncode != 0

    print("[LINTING] ---------------- LINT OUTPUT START ----------------")
    print(output or "(no output)")
    print("[LINTING] ----------------- LINT OUTPUT END -----------------")

    if lint_failed:
        log_job_event(
            state.job_id,
            node="linting",
            message="Linting failed.",
            event_type="error",
            data={"output": output},
        )
    else:
        log_job_event(
            state.job_id,
            node="linting",
            message="Linting passed with no errors.",
            event_type="node_completed",
        )

    return {
        "lint_output": output,
        "lint_failed": lint_failed,
    }
