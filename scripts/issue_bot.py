#!/usr/bin/env python3
"""
Autonomous Issue Fix Bot
========================
Checks GitHub open issues hourly, picks one that is suitable for auto-fixing,
spawns Kimi CLI to analyze and fix it, runs tests, and merges if passing.

Intended to be run via cron every hour:
    0 * * * * /usr/bin/env python3 /Users/leo/ws/sites_in_AOI/scripts/issue_bot.py >> ~/.local/state/issue_bot/log.txt 2>&1
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO = "Leo-zzl/sites-aoi-analysis"
WORK_DIR = "/Users/leo/ws/sites_in_AOI"
STATE_FILE = Path.home() / ".local/state/issue_bot/state.json"
LOG_FILE = Path.home() / ".local/state/issue_bot/log.txt"
KIMI_BIN = "/Users/leo/.local/bin/kimi"
GH_BIN = "/opt/homebrew/bin/gh"
MAX_STEPS = 200          # Kimi max steps per turn (very high for complex fixes)
MAX_TIME_SEC = 1800      # 30 min hard timeout for the whole Kimi session
SKIP_LABELS = {"enhancement", "question", "wontfix", "duplicate", "discussion"}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"handled_issues": [], "last_check": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def issue_already_handled(state: dict, number: int) -> bool:
    for item in state.get("handled_issues", []):
        if item.get("number") == number:
            return item.get("status") in {"merged", "in_progress", "closed", "fixed_by_other"}
    return False


def mark_issue(state: dict, number: int, status: str, **extra) -> None:
    entries = [e for e in state.get("handled_issues", []) if e.get("number") != number]
    entry = {"number": number, "status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    entry.update(extra)
    entries.append(entry)
    state["handled_issues"] = entries
    save_state(state)


def sync_issue_states(state: dict, open_numbers: set[int]) -> list[int]:
    """Check recorded issues against current open list. Update closed ones."""
    newly_closed = []
    for item in state.get("handled_issues", []):
        num = item.get("number")
        current_status = item.get("status", "")
        if num not in open_numbers and current_status not in {"closed", "fixed_by_other", "merged"}:
            item["status"] = "fixed_by_other"
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            item["closed_reason"] = "issue_no_longer_open"
            newly_closed.append(num)
    if newly_closed:
        save_state(state)
        log(f"Synced {len(newly_closed)} issues to 'fixed_by_other' (no longer open): {newly_closed}")
    return newly_closed


def record_plan(state: dict, open_issues: list[dict], target_issue: Optional[dict], action: str) -> None:
    """Record the execution plan/decision for this round."""
    plan = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "open_issue_count": len(open_issues),
        "open_issue_numbers": [i["number"] for i in open_issues],
        "target_issue": target_issue["number"] if target_issue else None,
        "target_issue_title": target_issue["title"] if target_issue else None,
        "action": action,
    }
    if "execution_plans" not in state:
        state["execution_plans"] = []
    state["execution_plans"].append(plan)
    # Keep only last 100 plans to prevent unbounded growth
    state["execution_plans"] = state["execution_plans"][-100:]
    save_state(state)

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def git(*args, cwd=WORK_DIR, check=True, capture=False):
    cmd = ["git", "-C", cwd] + list(args)
    kwargs = {"check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def ensure_clean_main() -> bool:
    """Ensure we are on main with no uncommitted changes."""
    result = git("status", "--porcelain", capture=True)
    if result.stdout.strip():
        log("ERROR: Working directory is not clean. Aborting.")
        return False
    result = git("branch", "--show-current", capture=True)
    if result.stdout.strip() != "main":
        log("ERROR: Not on main branch. Aborting.")
        return False
    return True


def create_branch(issue_number: int) -> str:
    branch = f"auto-fix/issue-{issue_number}"
    git("checkout", "-b", branch)
    log(f"Created branch: {branch}")
    return branch


def merge_branch(branch: str) -> None:
    git("checkout", "main")
    git("merge", "--no-ff", branch, "-m", f"auto: merge {branch}")
    git("push", "origin", "main")
    log(f"Merged and pushed: {branch}")


def delete_branch(branch: str) -> None:
    git("branch", "-D", branch, check=False)
    git("push", "origin", "--delete", branch, check=False)
    log(f"Deleted branch: {branch}")


def abort_branch(branch: str) -> None:
    git("checkout", "main")
    git("branch", "-D", branch, check=False)
    git("reset", "--hard", "HEAD")
    log(f"Aborted branch: {branch}")

# ---------------------------------------------------------------------------
# Issue fetching
# ---------------------------------------------------------------------------
def fetch_open_issues() -> list[dict]:
    result = subprocess.run(
        [GH_BIN, "issue", "list", "--repo", REPO, "--state", "open",
         "--limit", "10", "--json", "number,title,body,labels,author,createdAt"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def is_suitable_for_auto_fix(issue: dict) -> bool:
    labels = {lbl["name"].lower() for lbl in issue.get("labels", [])}
    if labels & SKIP_LABELS:
        log(f"Issue #{issue['number']} skipped due to labels: {labels}")
        return False
    # If it has a bug label, it's likely suitable
    if "bug" in labels:
        return True
    # If no labels, use heuristics: check title keywords
    title = issue.get("title", "").lower()
    bug_keywords = {"bug", "fix", "error", "crash", "broken", "fail", "wrong", "issue"}
    if any(kw in title for kw in bug_keywords):
        return True
    log(f"Issue #{issue['number']} not suitable for auto-fix (no bug indicators)")
    return False

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def build_prompt(issue: dict, result_file: str) -> str:
    number = issue["number"]
    title = issue["title"]
    body = issue.get("body", "")
    author = issue.get("author", {}).get("login", "unknown")
    labels = ", ".join(lbl["name"] for lbl in issue.get("labels", [])) or "none"

    prompt = textwrap.dedent(f"""\
    You are an autonomous issue-fixing agent. You have been assigned GitHub issue #{number} in repository {REPO}.

    ## Issue Details
    - **Title**: {title}
    - **Author**: {author}
    - **Labels**: {labels}
    - **Body**:
    {body or "(no body)"}

    ## Your Mission
    Fix this issue completely and autonomously. Do NOT ask the user for confirmation.

    ## Step-by-Step Instructions

    1. **Understand the issue**: Read the full issue with `gh issue view {number}` if needed.
    2. **Explore the codebase**: Find all files related to the issue. Read relevant code thoroughly.
    3. **Formulate a fix**: Plan the minimal change that resolves the issue.
    4. **Implement the fix**: Edit files using WriteFile or StrReplaceFile.
    5. **Run tests**:
       - `pytest` (Python unit/integration tests)
       - `npm test` (frontend unit tests)
       - `npm run test:e2e` (E2E tests)
       - If any test fails, STOP and report failure.
    6. **If all tests pass**:
       - `git add -A`
       - `git commit -m "fix: resolve #{number} - {title}"`
       - `git push origin HEAD`
    7. **Write result**: After completing (success or failure), write a JSON file to `{result_file}` with this exact schema:
       ```json
       {{"success": true, "summary": "brief description of what was fixed"}}
       ```
       or for failure:
       ```json
       {{"success": false, "reason": "why it failed"}}
       ```

    ## Critical Rules
    - You are on branch `auto-fix/issue-{number}`. Do NOT checkout other branches.
    - Make MINIMAL changes. Do not refactor unrelated code.
    - Follow the existing code style of the project.
    - If the issue is unclear, ambiguous, or requires design decisions beyond a simple fix, report failure with reason "ambiguous_issue".
    - If the issue requires external API keys, new dependencies, or infrastructure changes, report failure with reason "out_of_scope".
    - NEVER modify `.github/workflows/` unless the issue is specifically about CI.
    """
    )
    return prompt

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    log("=" * 60)
    log("Issue Bot started")

    state = load_state()
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    # Fetch issues
    try:
        issues = fetch_open_issues()
    except subprocess.CalledProcessError as e:
        log(f"ERROR: Failed to fetch issues: {e}")
        record_plan(state, [], None, "fetch_failed")
        return 1

    open_numbers = {i["number"] for i in issues}

    # Sync: update recorded issues that are no longer open
    sync_issue_states(state, open_numbers)

    if not issues:
        log("No open issues found. Nothing to do.")
        record_plan(state, [], None, "no_open_issues")
        return 0

    # Pick the first suitable issue
    target_issue = None
    for issue in issues:
        num = issue["number"]
        if issue_already_handled(state, num):
            log(f"Issue #{num} already handled (status in state). Skipping.")
            continue
        if is_suitable_for_auto_fix(issue):
            target_issue = issue
            break

    if target_issue is None:
        log("No suitable issues to auto-fix.")
        record_plan(state, issues, None, "no_suitable_issues")
        return 0

    number = target_issue["number"]
    title = target_issue["title"]
    log(f"Selected issue #{number}: {title}")
    mark_issue(state, number, "in_progress")

    # Ensure clean main
    if not ensure_clean_main():
        mark_issue(state, number, "failed", reason="dirty_working_tree")
        return 1

    # Pull latest main
    git("pull", "origin", "main")

    # Create branch
    branch = create_branch(number)

    # Prepare result file path
    result_fd, result_file = tempfile.mkstemp(suffix=".json", prefix="issue_bot_result_")
    os.close(result_fd)

    # Build and run Kimi prompt
    prompt = build_prompt(target_issue, result_file)
    log(f"Launching Kimi CLI for issue #{number} (timeout {MAX_TIME_SEC}s)")

    try:
        kimi_result = subprocess.run(
            [
                KIMI_BIN,
                "--work-dir", WORK_DIR,
                "--yolo",
                "--print",
                "--max-steps-per-turn", str(MAX_STEPS),
                "--prompt", prompt,
            ],
            capture_output=True,
            text=True,
            timeout=MAX_TIME_SEC,
        )
        log(f"Kimi CLI exited with code {kimi_result.returncode}")
        if kimi_result.stdout:
            # Truncate very long output
            out = kimi_result.stdout[-4000:] if len(kimi_result.stdout) > 4000 else kimi_result.stdout
            log(f"Kimi stdout:\n{out}")
        if kimi_result.stderr:
            err = kimi_result.stderr[-2000:] if len(kimi_result.stderr) > 2000 else kimi_result.stderr
            log(f"Kimi stderr:\n{err}")
    except subprocess.TimeoutExpired:
        log("ERROR: Kimi CLI timed out. Aborting branch.")
        abort_branch(branch)
        mark_issue(state, number, "failed", reason="kimi_timeout")
        record_plan(state, issues, target_issue, "kimi_timeout")
        Path(result_file).unlink(missing_ok=True)
        return 1
    except Exception as e:
        log(f"ERROR: Kimi CLI failed with exception: {e}")
        abort_branch(branch)
        mark_issue(state, number, "failed", reason=f"kimi_exception: {e}")
        record_plan(state, issues, target_issue, f"kimi_exception: {e}")
        Path(result_file).unlink(missing_ok=True)
        return 1

    # Parse result file
    success = False
    summary = ""
    if Path(result_file).exists():
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)
            success = result_data.get("success", False)
            summary = result_data.get("summary", result_data.get("reason", "unknown"))
            log(f"Result file parsed: success={success}, summary={summary}")
        except Exception as e:
            log(f"WARNING: Could not parse result file: {e}")
            # Fall back to checking git status
            diff_result = git("diff", "--stat", "main", capture=True, check=False)
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                success = True
                summary = "changes detected (result file missing)"
            else:
                success = False
                summary = "no changes detected"
    else:
        log("WARNING: Result file not found. Checking git diff...")
        diff_result = git("diff", "--stat", "main", capture=True, check=False)
        if diff_result.returncode == 0 and diff_result.stdout.strip():
            success = True
            summary = "changes detected (result file missing)"
        else:
            success = False
            summary = "no changes detected"

    # Clean up result file
    Path(result_file).unlink(missing_ok=True)

    if success:
        try:
            merge_branch(branch)
            mark_issue(state, number, "merged", summary=summary)
            record_plan(state, issues, target_issue, "merged")
            log(f"SUCCESS: Issue #{number} fixed and merged. Summary: {summary}")
        except Exception as e:
            log(f"ERROR: Merge failed: {e}")
            abort_branch(branch)
            mark_issue(state, number, "failed", reason=f"merge_failed: {e}")
            record_plan(state, issues, target_issue, f"merge_failed: {e}")
            return 1
    else:
        abort_branch(branch)
        mark_issue(state, number, "failed", reason=summary)
        record_plan(state, issues, target_issue, f"failed: {summary}")
        log(f"FAILURE: Issue #{number} not fixed. Reason: {summary}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
