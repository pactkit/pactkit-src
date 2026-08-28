"""STORY-slim-20260828897396a935ab: session context hooks (R1/R2).

Doc-verified contracts (code.claude.com/docs/en/hooks):
  - SessionStart: plain-text stdout IS injected as context, and the event
    fires on source ``compact`` — so post-compaction re-orientation comes
    free with the same hook.
  - PreCompact: stdout is NOT injected (debug log only) — useful for side
    effects.  Exit 2 would block compaction, which this module must never
    do.

SessionStart entry regenerates ``.pactkit/context.md`` from live board /
git / lessons state and prints it; PreCompact refreshes the same file so
the SessionStart(compact) injection that follows reads fresh state.
Both are aids, never gates: any internal failure degrades to a one-line
WARN and exit 0.
"""

from pathlib import Path

from pactkit.context_gen import context_output_path, generate_context
from pactkit.utils import atomic_write


def _refresh(root: Path) -> str:
    """Regenerate context.md; returns the new content."""
    text = generate_context(root)
    atomic_write(context_output_path(root), text)
    return text


def session_start_entry(root: Path) -> tuple[str, int]:
    """SessionStart hook mode: print context (stdout is injected).

    Returns (stdout_text, exit_code).  Always exit 0 — context injection
    is an aid, never a gate.
    """
    try:
        return _refresh(Path(root)), 0
    except Exception as exc:  # noqa: BLE001 - degrade, never block a session
        return f"[WARN] session-gate: context generation failed ({type(exc).__name__}) — skipped\n", 0


def pre_compact_entry(root: Path) -> tuple[str, int]:
    """PreCompact hook mode: refresh state as a side effect only.

    stdout is discarded by the harness for this event; the refresh serves
    the subsequent SessionStart(compact) injection.  Always exit 0 —
    compaction MUST NOT be blocked under any code path.
    """
    try:
        _refresh(Path(root))
        return "", 0
    except Exception as exc:  # noqa: BLE001 - compaction must never be blocked
        return f"[WARN] session-gate: pre-compact refresh failed ({type(exc).__name__})\n", 0
