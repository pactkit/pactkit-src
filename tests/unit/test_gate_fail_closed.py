"""
STORY-slim-20260826ce35b77ce005: Gate subsystem fails closed.

Every gate that previously reported green when it verified nothing must
now fail closed: pip-audit exit contract, identity matching, config
loading paths, coverage verdicts, git collection failures, analyzer
crashes, secret pathspec, single-layer scorecard preservation.
"""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# AC1: pip-audit exit-code contract (R1)
# ===========================================================================

class _FakeProc:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


class TestPipAuditContract:
    def test_exit_1_with_vulnerabilities_reports_them(self, tmp_path, monkeypatch):
        from pactkit import audit

        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        body = json.dumps([
            {"id": "GHSA-1", "fix_versions": ["2.0"]},
            {"id": "GHSA-2", "fix_versions": []},
        ])
        monkeypatch.setattr(
            audit.subprocess, "run", lambda cmd, **kw: _FakeProc(1, body)
        )

        result = audit._check_dependency_health(tmp_path)

        assert result["vulns"] == 2
        assert result["fixable"] == 1

    def test_exit_0_clean(self, tmp_path, monkeypatch):
        from pactkit import audit

        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        monkeypatch.setattr(
            audit.subprocess, "run", lambda cmd, **kw: _FakeProc(0, "[]")
        )

        result = audit._check_dependency_health(tmp_path)

        assert result["vulns"] == 0

    def test_exit_2_is_probe_error(self, tmp_path, monkeypatch):
        from pactkit import audit

        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        monkeypatch.setattr(
            audit.subprocess, "run", lambda cmd, **kw: _FakeProc(2, "")
        )

        result = audit._check_dependency_health(tmp_path)

        assert result["vulns"] == -1
        assert "error" in result

    def test_dependency_wrapping_output_is_flattened(self, tmp_path, monkeypatch):
        from pactkit import audit

        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        body = json.dumps({"dependencies": [
            {"name": "foo", "version": "1.0", "vulns": [{"id": "GHSA-3"}]},
        ]})
        monkeypatch.setattr(
            audit.subprocess, "run", lambda cmd, **kw: _FakeProc(1, body)
        )

        result = audit._check_dependency_health(tmp_path)

        assert result["vulns"] == 1


# ===========================================================================
# AC2: word-boundary identity matching (R2)
# ===========================================================================

class TestWordBoundaryMatching:
    def _write_spec_and_case(self, tmp_path, case_text):
        spec = tmp_path / "docs" / "specs" / "STORY-X.md"
        spec.parent.mkdir(parents=True)
        musts = "\n".join(f"### R{i}: Requirement {i} (MUST)" for i in range(1, 13))
        spec.write_text(f"# STORY-X\n\n## Requirements\n\n{musts}\n", encoding="utf-8")
        case = tmp_path / "docs" / "test_cases" / "STORY-X_case.md"
        case.parent.mkdir(parents=True)
        case.write_text(case_text, encoding="utf-8")

    def test_r12_does_not_satisfy_r1_through_r11(self, tmp_path):
        from pactkit.done_verify import check_requirement_evidence

        self._write_spec_and_case(tmp_path, "## TC-01: only references R12\n\nscenario\n")

        results = check_requirement_evidence("STORY-X", tmp_path)

        passed = [r for r in results if r.status == "PASS"]
        failed = [r for r in results if r.status == "FAIL"]
        assert len(passed) == 1 and "R12" in passed[0].name
        assert len(failed) == 11

    def test_story_id_boundary_in_archive(self, tmp_path):
        from pactkit.done_verify import _archived

        archive_dir = tmp_path / "docs" / "product" / "archive"
        archive_dir.mkdir(parents=True)
        (archive_dir / "archive_202608.md").write_text(
            "STORY-slim-100 something\n", encoding="utf-8"
        )

        assert _archived(tmp_path, "STORY-slim-10") is None


# ===========================================================================
# AC3: doctor loads config from a file path (R3)
# ===========================================================================

class TestDoctorConfigPath:
    def test_stale_graphs_receives_yaml_path_not_directory(self, tmp_path, monkeypatch):
        from pactkit import doctor

        (tmp_path / "docs" / "architecture" / "graphs").mkdir(parents=True)
        received: list = []

        def recording_load_config(path):
            received.append(path)
            return {}

        monkeypatch.setattr("pactkit.config.load_config", recording_load_config)

        doctor.check_stale_graphs(tmp_path)

        assert received, "load_config was never called"
        assert all(
            not Path(arg).is_dir() for arg in received
        ), f"load_config received a directory: {received}"


# ===========================================================================
# AC4/AC5: coverage gate fails closed (R4)
# ===========================================================================

class TestCoverageGateFailClosed:
    def test_block_verdict_exits_nonzero(self, monkeypatch, tmp_path):
        from pactkit import cli

        monkeypatch.setattr(
            "pactkit.coverage_gate.check_coverage",
            lambda files, root: {"files": [], "overall": "block", "reason": "low"},
        )
        monkeypatch.setattr(
            sys, "argv",
            ["pactkit", "-C", str(PROJECT_ROOT), "coverage-gate", "src/foo.py"],
        )
        with pytest.raises(SystemExit) as excinfo:
            cli.main()
        assert excinfo.value.code == 1

    def test_dropped_source_file_surfaces_as_failure(self, tmp_path, monkeypatch):
        from pactkit import coverage_gate

        output = (
            "Name                         Stmts   Miss  Cover   Missing\n"
            "----------------------------------------------------------\n"
            "src/pactkit/foo.py              50     10    80%   11-15\n"
        )
        monkeypatch.setattr(
            coverage_gate, "_run_pytest_cov", lambda modules, root: output
        )

        result = coverage_gate.check_coverage(
            ["src/pactkit/foo.py", "src/pactkit/bar.py"], project_root=tmp_path
        )

        reported = {f["file"]: f for f in result["files"]}
        assert "src/pactkit/bar.py" in reported
        assert reported["src/pactkit/bar.py"]["status"] == "block"

    def test_uses_venv_aware_pytest_command(self, tmp_path, monkeypatch):
        from pactkit import coverage_gate

        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _FakeProc(0, "")

        monkeypatch.setattr(coverage_gate.subprocess, "run", fake_run)
        coverage_gate._run_pytest_cov(["pactkit.foo"], tmp_path)

        assert captured["cmd"][0] != "python", (
            "coverage_gate must not hardcode bare 'python'"
        )


# ===========================================================================
# AC6: git collection failure is explicit (R5)
# ===========================================================================

class TestGitCollectionFailure:
    def test_git_failure_is_not_doc_only(self, tmp_path, monkeypatch):
        from pactkit import commit_gate

        monkeypatch.setattr(commit_gate, "_git", lambda root, *args: (128, ""))

        with pytest.raises(commit_gate.GitCollectionError):
            commit_gate.collect_changed_files(tmp_path)

    def test_run_gate_blocks_on_collection_failure(self, tmp_path, monkeypatch):
        from pactkit import commit_gate

        (tmp_path / ".git").mkdir()
        monkeypatch.setattr(commit_gate, "_git", lambda root, *args: (128, ""))

        result = commit_gate.run_gate(tmp_path)

        assert result.exit_code == 1
        assert any("COLLECTION-FAILED" in line for line in result.lines)

    def test_test_only_change_is_not_doc_only(self):
        from pactkit.regression import classify_changes

        strategy, _reason = classify_changes(["tests/unit/test_foo.py"])
        assert strategy != "skip"


# ===========================================================================
# AC7: crashed analyzer is visible (R6)
# ===========================================================================

class TestAnalyzerCrashVisibility:
    def test_crashed_layer_is_reported(self, tmp_path, monkeypatch):
        from pactkit import audit

        def exploding_check(root):
            raise RuntimeError("analyzer exploded")

        monkeypatch.setattr(audit, "_check_h1", exploding_check)
        (tmp_path / "docs").mkdir()

        result = json.loads(audit.audit(tmp_path, json_only=True))

        failed = result.get("checks_failed") or []
        assert "H1" in failed, f"crashed analyzer invisible: {result.get('layers', {}).get('H1')}"
        assert result["layers"]["H1"].get("error") == "analyzer exploded"


# ===========================================================================
# AC8: single-layer probe preserves scorecard (R8)
# ===========================================================================

class TestSingleLayerScorecard:
    def test_layer_probe_does_not_overwrite_full_scorecard(self, tmp_path, monkeypatch):
        from pactkit import audit

        gov_dir = tmp_path / "docs" / "architecture" / "governance"
        gov_dir.mkdir(parents=True)
        audit_path = gov_dir / "harness_audit.json"
        original = {
            "story_id": "STORY-full", "ready": True,
            "layers": {f"H{i}": {"level": 3, "name": "Good"} for i in range(1, 8)},
        }
        audit_path.write_text(json.dumps(original), encoding="utf-8")

        monkeypatch.setattr(audit, "_check_h2", lambda root: {"level": 1, "name": "Low", "checks": {}})
        audit.audit(tmp_path, layer="H2", json_only=True)

        persisted = json.loads(audit_path.read_text(encoding="utf-8"))
        assert persisted["ready"] is True
        assert persisted["layers"]["H1"]["level"] == 3


# ===========================================================================
# AC9: secret pathspec covers key material (R7)
# ===========================================================================

class TestSecretPathspec:
    def test_key_material_is_flagged(self, tmp_path, monkeypatch):
        from pactkit import audit

        def fake_run(cmd, **kwargs):
            assert "ls-files" in cmd
            return _FakeProc(0, "id_rsa\nserver.pem\n")

        monkeypatch.setattr(audit.subprocess, "run", fake_run)

        result = audit._check_h5(tmp_path)
        assert result["checks"]["no_secrets"] is False


# ===========================================================================
# QA fix iteration: fresh-repo, all-unresolvable, probe failure, boundaries
# ===========================================================================

class TestQAFixIteration:
    def test_fresh_repo_initial_commit_is_not_blocked(self, tmp_path):
        """A repo with zero commits has no HEAD to diff against — that is a
        benign known state, not a collection failure (QA P1)."""
        import subprocess as sp

        from pactkit import commit_gate

        (tmp_path / ".git").mkdir()
        real_run = sp.run

        def fake_run(cmd, **kwargs):
            # rev-parse HEAD fails (no commits); staged + untracked succeed
            if "rev-parse" in cmd:
                return _FakeProc(1, "")
            if "ls-files" in cmd:
                return _FakeProc(0, "src/new.py\n")
            if "diff" in cmd:
                return _FakeProc(0, "src/staged.py\n")
            return real_run(cmd, **kwargs)

        import unittest.mock as mock

        with mock.patch.object(commit_gate.subprocess, "run", fake_run):
            changed = commit_gate.collect_changed_files(tmp_path)

        assert changed == ["src/new.py", "src/staged.py"]

    def test_all_unresolvable_sources_block(self, tmp_path, monkeypatch):
        from pactkit import coverage_gate

        monkeypatch.setattr(
            coverage_gate, "_run_pytest_cov", lambda modules, root: "no table parsed"
        )

        result = coverage_gate.check_coverage(
            ["src/pactkit/foo.py", "src/pactkit/bar.py"], project_root=tmp_path
        )

        assert result["overall"] == "block"
        assert all(f["status"] == "block" for f in result["files"])

    def test_probe_failure_blocks(self, tmp_path, monkeypatch):
        import subprocess

        from pactkit import coverage_gate

        def raising_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 300)

        monkeypatch.setattr(coverage_gate.subprocess, "run", raising_run)

        result = coverage_gate.check_coverage(
            ["src/pactkit/foo.py"], project_root=tmp_path
        )

        assert result["overall"] == "block"
        assert "probe failed" in result["reason"]

    def test_hyphen_suffixed_story_id_not_matched(self, tmp_path):
        from pactkit.done_verify import _archived

        archive_dir = tmp_path / "docs" / "product" / "archive"
        archive_dir.mkdir(parents=True)
        (archive_dir / "archive_202608.md").write_text(
            "STORY-slim-10-a1b2 something\n", encoding="utf-8"
        )

        assert _archived(tmp_path, "STORY-slim-10") is None

    def test_dot_slash_spelling_does_not_false_block(self, tmp_path, monkeypatch):
        from pactkit import coverage_gate

        output = (
            "Name                         Stmts   Miss  Cover   Missing\n"
            "src/pactkit/foo.py              50     10    80%   11-15\n"
        )
        monkeypatch.setattr(
            coverage_gate, "_run_pytest_cov", lambda modules, root: output
        )

        result = coverage_gate.check_coverage(
            ["./src/pactkit/foo.py"], project_root=tmp_path
        )

        assert result["overall"] == "pass", (
            f"'./' spelling must normalize: {result['files']}"
        )
