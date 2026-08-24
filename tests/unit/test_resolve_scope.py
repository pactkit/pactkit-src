"""RED tests for STORY-slim-20260824dd23a0ed3b4c — unified WorkUnit scope derivation.

These tests drive the implementation of ``resolve_scope`` (the SSoT that
unions config ``write_scope`` roots + Spec ``Touches`` onto each WorkUnit
template floor) and the spec_linter rejection of pathological ``Touches``.

They MUST fail until the implementation lands (GREEN).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pactkit.config import validate_config
from pactkit.skills.spec_linter import validate_spec


def _resolve_scope(*args, **kwargs):
    """Lazy import — resolve_scope does not exist until GREEN lands.

    Tests collect and fail individually (RED, exit 1) rather than aborting
    collection (exit 2), so the ``red`` WorkUnit can honestly report
    ``story_tests.exit_code == 1``.
    """
    from pactkit.workflow_engine import resolve_scope

    return resolve_scope(*args, **kwargs)


WRITE_SCOPE = {
    "source_roots": ["frontend/src", "backend", "directus-extensions"],
    "test_roots": ["frontend/tests", "tests"],
    "docs_roots": ["docs"],
}


# ---------------------------------------------------------------------------
# Spec fixture helper — minimal spec with a Dependency Surface Touches field
# ---------------------------------------------------------------------------

_MIN_SPEC_TEMPLATE = """\
# {sid}: test story

| Field | Value |
|-------|-------|
| ID | {sid} |
| Status | Draft |
| Priority | P1 |
| Release | 2.22.0 |

## Requirements

### R1: Do the thing (MUST)

desc

## Acceptance Criteria

### AC1: Thing done (R1)

- **Given** a state
- **When** acting
- **Then** result

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | None |
| Touches | {touches} |
| Conflict risk | LOW |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | N/A | test fixture |
"""


def _write_spec(root: Path, story_id: str, touches: str) -> Path:
    spec = root / "docs/specs" / f"{story_id}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(_MIN_SPEC_TEMPLATE.format(sid=story_id, touches=touches), encoding="utf-8")
    return spec


# ---------------------------------------------------------------------------
# resolve_scope — zero regression (R7)
# ---------------------------------------------------------------------------

def test_zero_regression_no_config_no_touches(tmp_path):
    """No write_scope config + no story touches ⇒ resolve_scope adds nothing."""
    reads, writes = _resolve_scope(
        "project-act", "implementation", None, tmp_path, write_scope={},
    )
    assert reads == ()
    assert writes == ()


# ---------------------------------------------------------------------------
# resolve_scope — per-step config-root category selection (R2)
# ---------------------------------------------------------------------------

def test_implementation_includes_source_and_test_roots(tmp_path):
    _, writes = _resolve_scope(
        "project-act", "implementation", None, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "frontend/src" in writes
    assert "backend" in writes
    assert "directus-extensions" in writes
    assert "frontend/tests" in writes
    assert "tests" in writes
    assert "docs" not in writes  # docs not granted to implementation writes


def test_red_excludes_source_roots_tdd_isolation(tmp_path):
    """red writes tests only — source_roots MUST NOT be granted (TDD red isolation)."""
    _, writes = _resolve_scope(
        "project-act", "red", None, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "frontend/tests" in writes
    assert "tests" in writes
    assert "frontend/src" not in writes
    assert "backend" not in writes


def test_sync_coverage_includes_docs_only(tmp_path):
    _, writes = _resolve_scope(
        "project-act", "sync_coverage", None, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "docs" in writes
    assert "frontend/src" not in writes
    assert "frontend/tests" not in writes


def test_fix_hotfix_source_test_no_touches(tmp_path):
    _, writes = _resolve_scope(
        "project-hotfix", "fix", None, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "frontend/src" in writes
    assert "backend" in writes
    assert "frontend/tests" in writes


def test_run_only_steps_have_no_extra_writes(tmp_path):
    _, writes = _resolve_scope(
        "project-act", "story_tests", None, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert writes == ()


# ---------------------------------------------------------------------------
# resolve_scope — story.touches union (R1, R4)
# ---------------------------------------------------------------------------

def test_touches_included_for_implementation(tmp_path):
    sid = "STORY-slim-9001"
    _write_spec(tmp_path, sid, "frontend/src/app.vue, backend/api.js")
    _, writes = _resolve_scope(
        "project-act", "implementation", sid, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "frontend/src/app.vue" in writes
    assert "backend/api.js" in writes


def test_touches_union_not_intersection(tmp_path):
    """Touches outside declared config roots MUST still be included (union honors Tier-1 Spec)."""
    sid = "STORY-slim-9002"
    _write_spec(tmp_path, sid, "backend/migrations/012_add_vips.sql")
    _, writes = _resolve_scope(
        "project-act", "implementation", sid, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "backend/migrations/012_add_vips.sql" in writes


def test_dedup_overlapping_entries(tmp_path):
    sid = "STORY-slim-9003"
    # 'frontend/src' appears in both source_roots and touches — deduped to one.
    _write_spec(tmp_path, sid, "frontend/src, frontend/src/components/Foo.vue")
    _, writes = _resolve_scope(
        "project-act", "implementation", sid, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert writes.count("frontend/src") == 1


def test_reads_include_all_categories_and_touches(tmp_path):
    sid = "STORY-slim-9004"
    _write_spec(tmp_path, sid, "frontend/src/app.vue")
    reads, _ = _resolve_scope(
        "project-act", "implementation", sid, tmp_path, write_scope=WRITE_SCOPE,
    )
    assert "frontend/src" in reads       # source
    assert "frontend/tests" in reads     # test
    assert "docs" in reads               # docs
    assert "frontend/src/app.vue" in reads  # touches


# ---------------------------------------------------------------------------
# config validation (R3)
# ---------------------------------------------------------------------------

def test_write_scope_accepts_lists():
    validate_config({"write_scope": WRITE_SCOPE})  # no exception


def test_write_scope_rejects_non_list_roots():
    """validate_config warns (never raises) on non-list write_scope roots."""
    with pytest.warns(UserWarning):
        validate_config({"write_scope": {"source_roots": "frontend/src"}})


def test_resolve_scope_tolerates_malformed_write_scope(tmp_path):
    """resolve_scope MUST skip non-list / non-string root entries without crashing."""
    sid = "STORY-slim-9010"
    _write_spec(tmp_path, sid, "frontend/src/app.vue")
    malformed = {
        "source_roots": "frontend/src",   # string, not list — skipped
        "test_roots": ["tests", 42],       # 42 non-string — skipped, "tests" kept
        "docs_roots": ["docs"],
    }
    reads, writes = _resolve_scope(
        "project-act", "implementation", sid, tmp_path, write_scope=malformed,
    )
    assert "tests" in writes    # valid test_root preserved (implementation grants test)
    assert "docs" in reads       # valid docs_root preserved (reads include all categories)
    assert "frontend/src/app.vue" in writes  # touches honored


# ---------------------------------------------------------------------------
# spec_linter — pathological Touches rejection (R5)
# ---------------------------------------------------------------------------

def test_spec_linter_rejects_repo_wide_touches(tmp_path):
    sid = "STORY-slim-9005"
    spec = _write_spec(tmp_path, sid, "**")
    result = validate_spec(str(spec))
    assert not result.passed


def test_spec_linter_rejects_absolute_touches(tmp_path):
    sid = "STORY-slim-9006"
    spec = _write_spec(tmp_path, sid, "/etc/passwd")
    result = validate_spec(str(spec))
    assert not result.passed


def test_spec_linter_rejects_parent_traversal_touches(tmp_path):
    sid = "STORY-slim-9007"
    spec = _write_spec(tmp_path, sid, "../escape.py")
    result = validate_spec(str(spec))
    assert not result.passed


def test_spec_linter_accepts_valid_touches(tmp_path):
    sid = "STORY-slim-9008"
    spec = _write_spec(tmp_path, sid, "frontend/src/app.vue, backend/api.js")
    result = validate_spec(str(spec))
    assert result.passed, result.errors


# ---------------------------------------------------------------------------
# Engine integration — acquire unions resolve_scope onto template floor (R2)
# ---------------------------------------------------------------------------

def _initialize_project(root: Path, *, touches: str, write_scope: dict) -> str:
    """Set up a tmp project with write_scope config + a spec with Touches."""
    config = root / ".codex/pactkit.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    lines = ["developer: test", "write_scope:"]
    for key in ("source_roots", "test_roots", "docs_roots"):
        lines.append(f"  {key}:")
        for entry in write_scope.get(key, []):
            lines.append(f"    - {entry}")
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sid = "STORY-slim-9009"
    _write_spec(root, sid, touches)
    return sid


def test_engine_acquire_unions_config_roots_onto_reads(tmp_path):
    from pactkit.workflow_engine import WorkflowEngine

    sid = _initialize_project(
        tmp_path,
        touches="frontend/src/app.vue",
        write_scope=WRITE_SCOPE,
    )
    engine = WorkflowEngine(tmp_path)
    run = engine.start("project-act", goal="integration test", story_id=sid)
    unit = engine.acquire(run.run_id, owner="claude", idempotency_key="int-1")
    # act_preflight reads all categories + touches → frontend paths appear.
    assert "frontend/src" in unit.allowed_reads
    assert "frontend/src/app.vue" in unit.allowed_reads
