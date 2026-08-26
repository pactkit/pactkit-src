"""Sprint isolation is opt-in, never a mandatory worktree."""

from pactkit.prompts import SPRINT_PROMPT


def test_sprint_does_not_require_worktree_or_merge_recovery():
    lower = SPRINT_PROMPT.lower()
    assert "worktree" not in lower
    assert "git merge" not in lower
    assert "cherry-pick" not in lower


def test_parallel_work_requires_explicit_user_choice():
    lower = SPRINT_PROMPT.lower()
    assert "explicitly requests parallel" in lower
    assert "serialized" in lower


def test_current_session_is_the_default_boundary():
    lower = SPRINT_PROMPT.lower()
    assert "current session" in lower
    assert "exactly one active phase" in lower
