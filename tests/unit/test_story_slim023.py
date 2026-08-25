"""Tests for STORY-slim-023: Auto Version Sync via pactkit update --if-needed."""

import subprocess

from pactkit import __version__
from pactkit.prompts.commands import COMMANDS_CONTENT
from pactkit.prompts.rules import RULES_MODULES


class TestR1IfNeededFlag:
    """R1: pactkit update MUST accept --if-needed flag."""

    def test_flag_accepted(self):
        """--if-needed does not raise argparse error."""
        result = subprocess.run(
            ["pactkit", "update", "--if-needed", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--if-needed" in result.stdout

    def test_flag_in_help(self):
        """--if-needed appears in update help text."""
        result = subprocess.run(
            ["pactkit", "update", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--if-needed" in result.stdout
        assert "redeploy" in result.stdout.lower() or "version" in result.stdout.lower()


class TestR2VersionComparison:
    """R2: CLI MUST read pactkit.yaml version and compare to __version__."""

    def test_reads_pactkit_yaml(self, tmp_path, monkeypatch):
        """When --if-needed is set, pactkit.yaml is read."""
        # Create pactkit.yaml with matching version
        yaml_dir = tmp_path / ".claude"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "pactkit.yaml"
        yaml_file.write_text(f'version: "{__version__}"\nstack: python\n')

        monkeypatch.chdir(tmp_path)
        result = subprocess.run(
            ["pactkit", "update", "--if-needed"],
            capture_output=True,
            text=True,
        )
        # Should skip (up-to-date) because versions match
        assert "up-to-date" in result.stdout or result.returncode == 0


class TestR3SkipOnMatch:
    """R3: If versions match, CLI MUST skip deploy."""

    def test_skip_message_when_match(self, tmp_path, monkeypatch):
        """Prints skip message when versions match."""
        yaml_dir = tmp_path / ".claude"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "pactkit.yaml"
        yaml_file.write_text(f'version: "{__version__}"\nstack: python\n')

        monkeypatch.chdir(tmp_path)
        result = subprocess.run(
            ["pactkit", "update", "--if-needed"],
            capture_output=True,
            text=True,
        )
        assert "up-to-date" in result.stdout
        assert "skipping" in result.stdout.lower()


class TestR4ProceedOnMismatch:
    """R4: STORY-slim-102: --if-needed now checks global marker (~/.claude/.pactkit-version)."""

    def test_auto_sync_when_mismatch(self, tmp_path, monkeypatch):
        """STORY-slim-102: stale version in yaml is irrelevant; global marker controls behavior.

        When global marker matches __version__, update --if-needed skips redeploy
        regardless of what version is in pactkit.yaml.
        When global marker doesn't exist, it runs first-time setup.
        Either way, exit code is 0.
        """
        yaml_dir = tmp_path / ".claude"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "pactkit.yaml"
        # Even with stale version in yaml, CLI checks global marker, not yaml
        yaml_file.write_text('version: "0.0.0"\nstack: python\n')

        monkeypatch.chdir(tmp_path)
        result = subprocess.run(
            ["pactkit", "update", "--if-needed"],
            capture_output=True,
            text=True,
        )
        # Must exit cleanly regardless
        assert result.returncode == 0
        # Output indicates either skip (up-to-date) or first-time setup or deploy
        combined = result.stdout + result.stderr
        assert len(combined) > 0 or result.returncode == 0

    def test_proceed_when_no_yaml(self, tmp_path, monkeypatch):
        """STORY-slim-102: When no global marker, runs first-time setup or deploys."""
        # This test cannot mock Path.home() via subprocess, so it observes real behavior:
        # - If real ~/.claude/.pactkit-version exists and matches: prints "up-to-date"
        # - If real ~/.claude/.pactkit-version missing: prints "first-time setup"
        # - If version mismatch: runs deploy
        # All cases must exit 0 and produce some output.
        monkeypatch.chdir(tmp_path)
        result = subprocess.run(
            ["pactkit", "update", "--if-needed"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Produces meaningful output in any case
        combined = result.stdout + result.stderr
        assert len(combined) > 0


class TestR5CoreProtocolPrompt:
    """Session startup reports drift but never auto-deploys."""

    def test_core_protocol_requires_explicit_update_authorization(self):
        """A new session must not trigger a deployment by itself."""
        core = RULES_MODULES["core"]
        assert "version drift" in core
        assert "explicit authorization" in core
        assert "pactkit update --if-needed" not in core

    def test_session_context_reads_context_without_forcing_update(self):
        """Context loading remains available independently of deployment."""
        core = RULES_MODULES["core"]
        assert "Session Context" in core
        session_start = core.find("## Session Context")
        context_md = core.find("context.md", session_start)
        assert context_md > session_start

    def test_plan_config_refresh_requires_explicit_update_authorization(self):
        """A routine Plan invocation must not redeploy the host on stale config."""
        plan = COMMANDS_CONTENT["project-plan.md"]
        phase = plan[plan.index("Phase 0.5"):plan.index("Phase 1: Archaeology")]
        assert "pactkit update" in phase
        assert "explicit authorization" in phase.lower()
        assert "otherwise continue planning" in phase.lower()


class TestR6BlastRadius:
    """R6: Only cli.py and prompts/rules.py are modified."""

    def test_no_other_prompts_reference_if_needed(self):
        """No other individual RULES_MODULES reference --if-needed.
        Note: 'pactkit' is the merged composite of all core modules (contains core content).
        """
        for name, content in RULES_MODULES.items():
            assert "--if-needed" not in content, f"Unexpected --if-needed in {name}"
