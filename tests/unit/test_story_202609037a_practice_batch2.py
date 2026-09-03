"""Tests for STORY-slim-202609037a7d4be200e7: Guide Practice batch 2.

Every remaining 20 guides gains an operational Practice section (ADR-0002);
each carries >=3 content anchors as drift guards. Budget (<=50 rendered
lines) is enforced by the existing test_each_guide_under_50_lines.
"""

import pytest

from pactkit.prompts.guides import GUIDE_DEFINITIONS

# guide -> (anchors, must_have_practice)
ANCHORS = {
    # --- API 域 ---
    "api-integration.md": ("cursor", "idempotency key", "error code", "version"),
    "event-driven.md": ("at-least-once", "dead-letter", "idempotent"),
    "backwards-compatibility.md": ("deprecat", "dual-write", "enum"),
    # --- 数据域 ---
    "database.md": ("expansion", "rollback", "external call"),
    "caching.md": ("TTL", "stampede", "invalidation"),
    "data-consistency.md": ("eventual", "compensat", "optimistic"),
    # --- 并发域 ---
    "concurrency.md": ("I/O-bound", "bounded", "message passing"),
    "async-patterns.md": ("block", "cancel", "timeout"),
    "memory-management.md": ("generator", "bound", "stream"),
    "performance-antipatterns.md": ("measure", "N+1", "premature"),
    "resilience.md": ("circuit breaker", "bulkhead", "degrad"),
    "graceful-shutdown.md": ("SIGTERM", "drain", "kill"),
    # --- 质量域 ---
    "testing-strategy.md": ("pyramid", "flaky", "factory"),
    "code-review-first.md": ("correctness", "self-review", "justify"),
    "component-reuse.md": ("stdlib", "wrapper", "grep"),
    # --- 运维域 ---
    "configuration.md": ("layer", "fail-fast", "redact"),
    "operational-readiness.md": ("liveness", "readiness", "rollback"),
    "dependency-supply-chain.md": ("lockfile", "license", "transitive"),
    "write-safety.md": ("manifest", "candidate", "did not generate"),
    "ui-state-accessibility.md": ("loading", "focus", "contrast"),
}

BATCH1 = {"observability.md", "module-design.md", "error-recovery.md"}


def test_all_23_guides_have_practice_after_batch2():
    missing = [
        name for name, g in GUIDE_DEFINITIONS.items()
        if not g.practice
    ]
    assert not missing, f"guides still without Practice: {missing}"


def test_batch2_covers_exactly_20_remaining():
    with_practice = {n for n, g in GUIDE_DEFINITIONS.items() if g.practice}
    assert with_practice - BATCH1 == set(ANCHORS), (
        "batch-2 set drifted from the spec's 20 guides"
    )


@pytest.mark.parametrize("guide_name", sorted(ANCHORS))
def test_guide_practice_anchors(guide_name):
    rendered = GUIDE_DEFINITIONS[guide_name].render()
    assert "## Practice" in rendered, guide_name
    lowered = rendered.lower()
    for anchor in ANCHORS[guide_name]:
        assert anchor.lower() in lowered, f"{guide_name}: missing anchor {anchor!r}"


@pytest.mark.parametrize("guide_name", sorted(ANCHORS))
def test_guide_practice_has_table_or_redline(guide_name):
    practice = GUIDE_DEFINITIONS[guide_name].practice
    has_table = practice.count("|---") >= 1 or practice.count("|--") >= 1
    has_redline = "NEVER" in practice or "MUST" in practice or "red line" in practice.lower()
    assert has_table or has_redline, f"{guide_name}: no criteria table or red line"


@pytest.mark.parametrize("guide_name", sorted(ANCHORS))
def test_guide_practice_renders_verbatim(guide_name):
    practice = GUIDE_DEFINITIONS[guide_name].practice
    assert practice.strip() in GUIDE_DEFINITIONS[guide_name].render()
