"""STORY-slim-136: done-verify mechanical archive honesty gate."""

from pathlib import Path

import pytest

from pactkit.done_verify import BLOCKER_TERMS, verify_story

SID = "STORY-test-001"

SPEC_TMPL = """# {sid}: sample story

| Field | Value |
|-------|-------|
| ID | {sid} |
| Status | {status} |

## Requirements

### R1: first requirement (MUST)

Do the thing.

### R2: second requirement (MUST)

Do the other thing.

## Acceptance Criteria

### AC1: covers first (R1)

- **Given** x
- **When** y
- **Then** z

### AC2: covers second (R2)

- **Given** x
- **When** y
- **Then** z

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_sample.py` | add tests | None | Low |
"""

CASE_TMPL = """# {sid} Test Cases

## Scenario: first works (R1)

- Given x
- When y
- Then z

## Scenario: second works (AC2)

- Given x
- When y
- Then z
"""


def make_project(root: Path, status: str = "Done", board_checked: bool = True,
                 case_text: str | None = None, spec_text: str | None = None) -> Path:
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "test_cases").mkdir(parents=True)
    (root / "docs" / "product").mkdir(parents=True)
    (root / "tests" / "unit").mkdir(parents=True)

    (root / "docs" / "specs" / f"{SID}.md").write_text(
        spec_text if spec_text is not None else SPEC_TMPL.format(sid=SID, status=status)
    )
    (root / "docs" / "test_cases" / f"{SID}_case.md").write_text(
        case_text if case_text is not None else CASE_TMPL.format(sid=SID)
    )
    checkbox = "x" if board_checked else " "
    (root / "docs" / "product" / "sprint_board.md").write_text(
        "# Sprint Board\n\n## ✅ Done\n\n"
        f"### {SID}: sample story\n\n- [{checkbox}] task one\n"
    )
    (root / "tests" / "unit" / "test_sample.py").write_text("def test_sample(): pass\n")
    return root


def statuses(results):
    return {r.name.split()[1] if r.name.startswith("R") else r.name: r.status for r in results}


def find(results, prefix):
    return [r for r in results if r.name.startswith(prefix)]


# ---------------------------------------------------------------------------
# AC1: all-green story passes with exit 0
# ---------------------------------------------------------------------------


class TestAllGreen:
    def test_exit_zero_and_pass_lines(self, tmp_path):
        make_project(tmp_path)
        results, code = verify_story(SID, tmp_path)
        assert code == 0
        assert all(r.status in ("PASS", "WARN") for r in results)
        for r in find(results, "R2 evidence R"):
            assert r.status == "PASS"

    def test_render_format(self, tmp_path):
        make_project(tmp_path)
        results, _ = verify_story(SID, tmp_path)
        assert all(r.render().startswith(f"[{r.status}]") for r in results)


# ---------------------------------------------------------------------------
# AC2: P0-4 scenario — all checked but case says "RFC open"
# ---------------------------------------------------------------------------


class TestCheckboxHonesty:
    def test_open_marker_blocks_archive(self, tmp_path):
        case = CASE_TMPL.format(sid=SID) + "\n## Notes\n\nRFC open: pagination semantics unresolved\n"
        make_project(tmp_path, case_text=case)
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        honesty = find(results, "R3 honesty")[0]
        assert honesty.status == "FAIL"
        assert "_case.md:" in honesty.evidence  # line reference included

    def test_unchecked_board_skips_scan_with_warn(self, tmp_path):
        case = CASE_TMPL.format(sid=SID) + "\nTODO: unfinished\n"
        make_project(tmp_path, board_checked=False, status="In Progress", case_text=case)
        results, code = verify_story(SID, tmp_path)
        honesty = find(results, "R3 honesty")[0]
        assert honesty.status == "WARN"

    def test_blocker_terms_is_module_constant(self):
        assert "rfc open" in BLOCKER_TERMS

    def test_terms_inside_code_spans_are_not_hits(self, tmp_path):
        """A spec discussing the vocabulary (backticked) is not an open marker."""
        case = CASE_TMPL.format(sid=SID) + "\n## Notes\n\nBlocker terms include `TODO` and `FIXME` tokens.\n"
        make_project(tmp_path, case_text=case)
        results, code = verify_story(SID, tmp_path)
        assert find(results, "R3 honesty")[0].status == "PASS"
        assert code == 0


# ---------------------------------------------------------------------------
# AC3: missing test evidence blocks
# ---------------------------------------------------------------------------


class TestRequirementEvidence:
    def test_missing_case_file(self, tmp_path):
        make_project(tmp_path)
        (tmp_path / "docs" / "test_cases" / f"{SID}_case.md").unlink()
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        r2 = find(results, "R2 evidence")[0]
        assert r2.status == "FAIL"
        assert "test case missing" in r2.evidence

    def test_case_does_not_cover_r2(self, tmp_path):
        case = "## Scenario: only first (R1)\n\n- Given x\n"
        make_project(tmp_path, case_text=case)
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        r2 = find(results, "R2 evidence R2")[0]
        assert r2.status == "FAIL"
        assert "R2" in r2.evidence

    def test_missing_mapped_test_file(self, tmp_path):
        make_project(tmp_path)
        (tmp_path / "tests" / "unit" / "test_sample.py").unlink()
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        tf = find(results, "R2 test files")[0]
        assert tf.status == "FAIL"
        assert "test_sample.py" in tf.evidence

    def test_missing_spec(self, tmp_path):
        make_project(tmp_path)
        (tmp_path / "docs" / "specs" / f"{SID}.md").unlink()
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        assert "spec missing" in find(results, "R2 evidence")[0].evidence


# ---------------------------------------------------------------------------
# AC4: zero-caller component warns but does not block
# ---------------------------------------------------------------------------


class TestWiring:
    def test_orphan_symbol_warns(self, tmp_path, monkeypatch):
        make_project(tmp_path)
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "newmod.py").write_text("def orphan_helper():\n    return 1\n")
        monkeypatch.setattr("pactkit.done_verify._changed_source_files", lambda root: ["src/pkg/newmod.py"])
        monkeypatch.setattr(
            "pactkit.done_verify._new_public_symbols", lambda root, rel: ["orphan_helper"]
        )
        results, code = verify_story(SID, tmp_path)
        wiring = find(results, "R4 wiring")[0]
        assert wiring.status == "WARN"
        assert "orphan_helper" in wiring.evidence
        assert code == 0

    def test_wired_symbol_passes(self, tmp_path, monkeypatch):
        make_project(tmp_path)
        monkeypatch.setattr("pactkit.done_verify._changed_source_files", lambda root: ["src/pkg/newmod.py"])
        monkeypatch.setattr("pactkit.done_verify._new_public_symbols", lambda root, rel: ["used_helper"])
        monkeypatch.setattr("pactkit.done_verify._has_production_caller", lambda root, rel, sym: True)
        results, code = verify_story(SID, tmp_path)
        assert find(results, "R4 wiring")[0].status == "PASS"
        assert code == 0


# ---------------------------------------------------------------------------
# AC5: status-machine contradictions block
# ---------------------------------------------------------------------------


class TestStatusConsistency:
    def test_board_done_spec_draft_fails(self, tmp_path):
        make_project(tmp_path, status="Draft", board_checked=True)
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        r5 = find(results, "R5 status")[0]
        assert r5.status == "FAIL"
        assert "Draft" in r5.evidence

    def test_spec_done_board_unchecked_fails(self, tmp_path):
        make_project(tmp_path, status="Done", board_checked=False)
        results, code = verify_story(SID, tmp_path)
        assert code == 1
        assert find(results, "R5 status")[0].status == "FAIL"

    def test_consistent_done_passes(self, tmp_path):
        make_project(tmp_path, status="Done", board_checked=True)
        results, _ = verify_story(SID, tmp_path)
        assert find(results, "R5 status")[0].status == "PASS"


# ---------------------------------------------------------------------------
# SEC-1: story ID validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    @pytest.mark.parametrize("bad", ["../etc", "STORY-001; rm -rf /", "../../x", "STORY-slim-001.md"])
    def test_invalid_ids_rejected(self, tmp_path, bad):
        results, code = verify_story(bad, tmp_path)
        assert code == 1
        assert "invalid story ID" in results[0].evidence

    def test_valid_ids_accepted(self, tmp_path):
        make_project(tmp_path)
        _, code = verify_story(SID, tmp_path)
        assert code == 0


# ---------------------------------------------------------------------------
# SEC-7: a crashing check degrades to WARN, never raises
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_broken_check_becomes_warn(self, tmp_path, monkeypatch):
        make_project(tmp_path)
        monkeypatch.setattr(
            "pactkit.done_verify.check_requirement_evidence",
            lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        results, code = verify_story(SID, tmp_path)
        internal = find(results, "internal")[0]
        assert internal.status == "WARN"
        assert "boom" in internal.evidence
        assert code == 0  # WARN alone does not block
