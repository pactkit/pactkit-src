"""
STORY-slim-2026082672b57c78fd67 R3: the CLI argparse surface is
byte-identical across the decomposition.

Golden snapshots were captured immediately after the sanctioned
--allow-adapter-skew unification and BEFORE any structural refactor —
they pin the user-facing contract.
"""
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_DIR = PROJECT_ROOT / "tests" / "fixtures" / "cli_help_golden"
ENV = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(PROJECT_ROOT / "src"), "HOME": "/tmp"}


def _run_help(args):
    proc = subprocess.run(
        [sys.executable, "-m", "pactkit", *args],
        capture_output=True, text=True, env=ENV, timeout=30,
    )
    assert proc.returncode == 0, f"{args}: {proc.stderr}"
    return proc.stdout


def test_root_help_matches_golden():
    assert _run_help(["--help"]) == (GOLDEN_DIR / "__root__.txt").read_text()


def test_all_subcommand_helps_match_golden():
    root_help = (GOLDEN_DIR / "__root__.txt").read_text()
    commands = re.search(r"\{([^}]+)\}", root_help).group(1).split(",")
    golden_files = {f.stem for f in GOLDEN_DIR.glob("*.txt")}
    assert set(commands) | {"__root__"} == golden_files, (
        "golden snapshot set drifted from the live command list"
    )
    mismatches = []
    for cmd in commands:
        live = _run_help([cmd, "--help"])
        golden = (GOLDEN_DIR / f"{cmd}.txt").read_text()
        if live != golden:
            mismatches.append(cmd)
    assert not mismatches, f"help surface changed for: {mismatches}"


class TestDoctorDeployRootDerivation:
    """STORY-slim-2026082672b57c78fd67 R5/AC5: doctor's project deploy
    directories derive from FORMAT_PROFILES — a new format needs no
    doctor.py edit."""

    def test_new_format_appears_without_doctor_edit(self, tmp_path, monkeypatch):
        import pactkit.doctor as doctor
        import pactkit.profiles as profiles

        class _FakeProfile:
            pactkit_yaml_path = ".trae/pactkit.yaml"

        monkeypatch.setitem(
            profiles.FORMAT_PROFILES, "trae", _FakeProfile()
        )
        # is_environment_format consults FORMAT_PROFILES
        dirs = doctor._project_deploy_dirs(tmp_path)
        assert "trae" in dirs
        assert dirs["trae"] == tmp_path / ".trae"
        # existing formats unchanged
        assert dirs["classic"] == tmp_path / ".claude"
        assert dirs["copilot"] == tmp_path / ".github"

    def test_current_formats_complete(self, tmp_path):
        import pactkit.doctor as doctor

        dirs = doctor._project_deploy_dirs(tmp_path)
        assert set(dirs) == {"classic", "opencode", "codex", "copilot"}
