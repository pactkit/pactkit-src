"""STORY-slim-137: deps external dependency check and guided install."""

import pytest

from pactkit import deps
from pactkit.deps import (
    DEP_REGISTRY,
    MANUAL_HINTS,
    check_deps,
    install_deps,
    render_check_report,
)


@pytest.fixture
def root(tmp_path):
    return tmp_path


def mock_which(monkeypatch, present: set[str]):
    monkeypatch.setattr(deps.shutil, "which", lambda b: f"/usr/bin/{b}" if b in present else None)
    monkeypatch.setattr(deps, "_tool_version", lambda b: "v1.2.3")


# ---------------------------------------------------------------------------
# R1: check
# ---------------------------------------------------------------------------


class TestCheck:
    def test_status_table_mixed(self, root, monkeypatch):
        """AC1: installed shows version, missing shows platform install cmd, exit-relevant."""
        mock_which(monkeypatch, present={"codegraph", "node"})
        statuses = check_deps(platform="darwin")
        by_name = {s.name: s for s in statuses}
        assert by_name["codegraph"].installed is True
        assert by_name["codegraph"].version == "v1.2.3"
        assert by_name["gh"].installed is False
        assert by_name["gh"].install_hint == "brew install gh"

    def test_report_lists_missing_with_hint(self, root, monkeypatch):
        mock_which(monkeypatch, present=set())
        report = render_check_report(check_deps(platform="darwin"))
        assert "❌ codegraph" in report
        assert "npm install -g @colbymchenry/codegraph" in report
        assert "pactkit deps install" in report

    def test_report_all_present(self, root, monkeypatch):
        mock_which(monkeypatch, present={"node", "codegraph", "gh"})
        report = render_check_report(check_deps(platform="darwin"))
        assert "All external dependencies present." in report

    def test_unknown_platform_falls_back_to_manual_hint(self, root, monkeypatch):
        mock_which(monkeypatch, present=set())
        statuses = check_deps(platform="win32")
        gh = next(s for s in statuses if s.name == "gh")
        assert gh.install_hint == MANUAL_HINTS["gh"]  # no guessing on unknown platforms

    def test_registry_is_complete(self):
        for name, entry in DEP_REGISTRY.items():
            assert entry["detect"], name
            assert entry["purpose"], name
            assert entry["install"], name
            assert name in MANUAL_HINTS, name
            # SEC-1: install commands are argv lists, never shell strings
            for argv in entry["install"].values():
                assert isinstance(argv, list), name
                assert all(isinstance(part, str) for part in argv), name


# ---------------------------------------------------------------------------
# R2: install
# ---------------------------------------------------------------------------


class TestInstall:
    def test_install_runs_registry_command(self, root, monkeypatch):
        """AC2: --yes runs the brew command, prints it, summarizes."""
        mock_which(monkeypatch, present={"node", "codegraph"})
        ran = []
        monkeypatch.setattr(deps, "_run_install", None)  # force default off
        lines, code = install_deps(
            root, assume_yes=True, platform="darwin",
            runner=lambda argv: (ran.append(argv) or (True, "")),
        )
        assert code == 0
        assert ran == [["brew", "install", "gh"]]
        assert any("✅ gh" in ln for ln in lines)

    def test_prerequisite_ordering(self, root, monkeypatch):
        """node (no deps) installs before codegraph (needs node)."""
        mock_which(monkeypatch, present={"gh"})
        ran = []
        lines, code = install_deps(
            root, assume_yes=True, platform="darwin",
            runner=lambda argv: (ran.append(argv) or (True, "")),
        )
        assert code == 0
        assert ran[0][:2] == ["brew", "install"]  # node first
        assert ran[1][:2] == ["npm", "install"]   # codegraph second

    def test_user_decline_skips(self, root, monkeypatch):
        mock_which(monkeypatch, present={"node", "codegraph"})
        ran = []
        lines, code = install_deps(
            root, platform="darwin",
            confirm=lambda prompt: False,
            runner=lambda argv: (ran.append(argv) or (True, "")),
        )
        assert code == 0
        assert ran == []
        assert any("skipped by user" in ln for ln in lines)

    def test_failed_install_continues_and_reports(self, root, monkeypatch):
        mock_which(monkeypatch, present=set())
        outcomes = iter([(False, "brew: command failed"), (True, ""), (True, "")])
        lines, code = install_deps(
            root, assume_yes=True, platform="darwin",
            runner=lambda argv: next(outcomes),
        )
        assert code == 1
        assert any("❌ node" in ln and "brew: command failed" in ln for ln in lines)
        assert any("✅ gh" in ln for ln in lines)  # later items still attempted

    def test_no_external_refuses(self, root, monkeypatch):
        """AC3: enterprise.no_external blocks any install attempt."""
        (root / ".claude").mkdir()
        (root / ".claude" / "pactkit.yaml").write_text("enterprise:\n  no_external: true\n")
        mock_which(monkeypatch, present=set())
        ran = []
        lines, code = install_deps(
            root, assume_yes=True, platform="darwin",
            runner=lambda argv: (ran.append(argv) or (True, "")),
        )
        assert code == 1
        assert ran == []
        assert "no_external" in lines[0]

    def test_nothing_to_do(self, root, monkeypatch):
        mock_which(monkeypatch, present={"node", "codegraph", "gh"})
        lines, code = install_deps(root, assume_yes=True, platform="darwin")
        assert code == 0
        assert "nothing to do" in lines[0]

    def test_unmapped_platform_skips_with_manual_hint(self, root, monkeypatch):
        mock_which(monkeypatch, present={"node", "codegraph"})
        lines, code = install_deps(
            root, assume_yes=True, platform="win32",
            runner=lambda argv: (True, ""),
        )
        assert code == 0  # skip is not a failure
        assert any("no installer for platform" in ln for ln in lines)
