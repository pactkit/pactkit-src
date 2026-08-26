"""Lazy Visualize — skip graph generation when no source changes (STORY-slim-014 R7).

Implements the Lazy Visualize Protocol from execution/shared-execution
(an on-demand PactKit rule):
  If source files changed OR code_graph.mmd is missing → visualize.
  Else → skip with log: "Graph up-to-date — no source changes".
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pactkit.cleaners import detect_stack
from pactkit.prompts.workflows import LANG_PROFILES

# Canonical graph output path (relative to project root)
_GRAPH_PATH = Path("docs") / "architecture" / "graphs" / "code_graph.mmd"


def codegraph_sync(project_root: Path) -> tuple[bool, str]:
    """Sync codegraph index if .codegraph/ exists and codegraph is available.

    Opt-in signal: .codegraph/ directory exists (user ran `codegraph init`).
    No pactkit.yaml config required — presence of .codegraph/ is sufficient.

    Returns:
        (synced, message) — synced=True if sync ran successfully.
    """
    codegraph_dir = project_root / ".codegraph"
    if not codegraph_dir.is_dir():
        return (False, ".codegraph/ not found — skipped")

    if not shutil.which("codegraph"):
        return (False, "codegraph not installed")

    result = subprocess.run(
        ["codegraph", "sync", str(project_root)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return (False, f"codegraph sync failed: {result.stderr.strip()}")

    output = result.stdout.strip()
    return (True, output if output else "codegraph synced")


def should_visualize(
    project_root: Path,
    stack: str = "auto",
) -> tuple[bool, str]:
    """Determine whether visualization should run.

    Logic:
    1. Detect stack (reuse cleaners.detect_stack when stack='auto').
    2. Get source_dirs and file_ext from LANG_PROFILES.
    3. Run `git diff --name-only HEAD` to get changed files.
    4. If git fails → (True, "unable to detect changes").
    5. If graph file missing → (True, "code_graph.mmd missing").
    6. If any changed file is under source_dirs with matching extension
       → (True, "source files changed: <files>").
    7. Otherwise → (False, "Graph up-to-date — no source changes").

    Args:
        project_root: Absolute path to the project root directory.
        stack: Language stack or 'auto' to auto-detect.

    Returns:
        (should_run, reason) tuple.
    """
    # Resolve stack
    resolved_stack = stack if stack != "auto" else detect_stack(project_root)
    profile = LANG_PROFILES.get(resolved_stack, LANG_PROFILES["python"])
    source_dirs: list[str] = profile["source_dirs"]
    file_ext: str = profile["file_ext"]

    # Run git diff to get changed files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        if result.returncode != 0:
            return (True, "unable to detect changes (git diff failed)")
        changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.CalledProcessError, OSError, Exception):
        return (True, "unable to detect changes (git not available)")

    # Check if graph file exists
    graph_file = project_root / _GRAPH_PATH
    graph_exists = graph_file.exists()

    # Find source file changes
    source_changes = [
        f for f in changed_files
        if f.endswith(file_ext) and any(f.startswith(d) for d in source_dirs)
    ]

    if source_changes:
        files_str = ", ".join(source_changes)
        return (True, f"source files changed: {files_str}")

    if not graph_exists:
        return (True, f"code_graph.mmd missing: {graph_file}")

    return (False, "Graph up-to-date — no source changes")


def run_visualize_single(
    project_root: Path, mode: str, *,
    entry: str | None = None, focus: str | None = None,
    reverse: bool = False, depth: int = 0, max_nodes: int = 0,
) -> None:
    """Execute visualize.py for a single graph mode (HOTFIX-slim-023, HOTFIX-slim-070)."""
    import sys

    viz_script = Path(__file__).resolve().parent / "skills" / "visualize.py"
    if not viz_script.exists():
        print(f"visualize.py not found: {viz_script}")
        return
    cmd = [sys.executable, str(viz_script), "visualize", "--mode", mode]
    if entry:
        cmd += ["--entry", entry]
    if focus:
        cmd += ["--focus", focus]
    if reverse:
        cmd.append("--reverse")
    if depth:
        cmd += ["--depth", str(depth)]
    if max_nodes:
        cmd += ["--max-nodes", str(max_nodes)]
    subprocess.run(cmd, cwd=str(project_root))
    _print_codegraph_sync(project_root)


def run_visualize_graphs(project_root: Path, *, focus: str | None = None) -> None:
    """Execute visualize.py to regenerate all graph files.

    Runs file, class, call modes. Also refreshes focus graphs if they exist.
    """
    import sys

    viz_script = Path(__file__).resolve().parent / "skills" / "visualize.py"
    if not viz_script.exists():
        return

    mode_flag = "--mode"
    for mode in ["file", "class", "call"]:
        cmd = [sys.executable, str(viz_script), "visualize", mode_flag, mode]
        if focus:
            cmd += ["--focus", focus]
        subprocess.run(cmd, cwd=str(project_root))

    # Focus graphs are user-generated on demand (--focus <target>), not auto-refreshed.
    # Removed hardcoded --focus cli refresh (HOTFIX-slim-062).
    _print_codegraph_sync(project_root)


def _print_codegraph_sync(project_root: Path) -> None:
    """Run codegraph_sync and print status feedback (R5)."""
    synced, msg = codegraph_sync(project_root)
    if synced:
        print(f"🔄 {msg}")
    elif "skipped" not in msg:
        print(f"codegraph: {msg}")
