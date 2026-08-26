"""Small, non-blocking decisions used by Act, Check and Done."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeIntegrityResult:
    completion_ready: bool
    can_continue: bool
    unexpected: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceFreshnessResult:
    reusable: bool
    changed_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TestAdequacyResult:
    completion_ready: bool
    can_continue: bool
    gaps: tuple[str, ...]


def assess_scope_integrity(
    *, expected: tuple[str, ...], changed: tuple[str, ...],
) -> ScopeIntegrityResult:
    """Compare actual paths with declared files or directory prefixes."""
    unexpected = tuple(
        path for path in changed
        if not any(path == item or path.startswith(item.rstrip("/") + "/") for item in expected)
    )
    return ScopeIntegrityResult(not unexpected, True, unexpected)


def assess_evidence_freshness(
    *, evidence_inputs: dict[str, str], current_inputs: dict[str, str],
) -> EvidenceFreshnessResult:
    """Return which evidence inputs changed since verification."""
    changed = tuple(
        path for path in sorted(set(evidence_inputs) | set(current_inputs))
        if evidence_inputs.get(path) != current_inputs.get(path)
    )
    return EvidenceFreshnessResult(not changed, changed)


def assess_test_adequacy(
    *,
    behavior_assertions: bool,
    defect_reproduced: bool | None = None,
    boundary_or_failure_paths: bool = False,
    mocks_cross_core_boundary: bool = False,
    negative_control_fails: bool | None = None,
) -> TestAdequacyResult:
    """Evaluate test evidence while leaving safe repair work available.

    None means a signal is not applicable. Missing evidence prevents a
    completion claim, but deliberately never locks investigation or repair.
    """
    gaps: list[str] = []
    if not behavior_assertions:
        gaps.append("missing observable behavior assertion")
    if defect_reproduced is False:
        gaps.append("original defect is not reproduced")
    if not boundary_or_failure_paths:
        gaps.append("boundary or failure path is not covered")
    if mocks_cross_core_boundary:
        gaps.append("mock bypasses the core behavior boundary")
    if negative_control_fails is False:
        gaps.append("test still passes when the implementation is removed")
    return TestAdequacyResult(not gaps, True, tuple(gaps))
