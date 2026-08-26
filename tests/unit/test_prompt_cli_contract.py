"""
STORY-slim-20260826ac1f0bfe4148: Prompt-to-CLI contract consistency.

The instructions embedded in prompts/ must reference CLI subcommands that
actually exist — machine-enforced, so drift fails CI instead of failing
an AI assistant mid-session.
"""
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROMPTS_DIR = PROJECT_ROOT / "src" / "pactkit" / "prompts"
CLI_SOURCE = (PROJECT_ROOT / "src" / "pactkit" / "cli.py").read_text(encoding="utf-8")


def _prompt_subcommand_refs() -> set[str]:
    """Every `pactkit <subcommand>` reference in prompts source."""
    refs: set[str] = set()
    for path in PROMPTS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        refs.update(re.findall(r"`pactkit ([a-z][a-z0-9-]+)`", text))
    return refs


def _cli_subcommands() -> set[str]:
    """Every subcommand registered in cli.py's argparse parsers."""
    return set(re.findall(r"add_parser\(\s*['\"]([a-z][a-z0-9-]+)", CLI_SOURCE))


class TestPromptCliContract:
    def test_all_prompt_references_are_registered(self):
        """AC2: the current prompts tree references only real subcommands."""
        refs = _prompt_subcommand_refs()
        assert refs, "extraction found no references — pattern broken?"
        missing = refs - _cli_subcommands()
        assert not missing, f"prompts reference unregistered subcommands: {sorted(missing)}"

    def test_contract_test_catches_fabricated_subcommand(self):
        """AC1: a fabricated reference in a prompts module fails the check."""
        fabricated = PROMPTS_DIR / "_contract_fixture.py"
        fabricated.write_text(
            'X = "run `pactkit nonexistent-cmd` now"\n', encoding="utf-8"
        )
        try:
            refs = _prompt_subcommand_refs()
            missing = refs - _cli_subcommands()
            assert "nonexistent-cmd" in missing
        finally:
            fabricated.unlink()


class TestBoardAddTask:
    def test_add_task_round_trips(self, tmp_path, monkeypatch):
        """AC3: mid-story task additions have a governed path."""
        monkeypatch.chdir(tmp_path)
        from pactkit.governance import StoryRepository

        repo = StoryRepository(tmp_path)
        repo.add("STORY-100", "Title", ["first task"])

        repo.add_task("STORY-100", "QA fix iteration")

        record = repo.load("STORY-100")
        titles = [t["title"] for t in record["tasks"]]
        assert titles == ["first task", "QA fix iteration"]
        assert record["tasks"][1]["completed"] is False

    def test_add_task_to_done_story_reopens_it(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from pactkit.governance import StoryRepository

        repo = StoryRepository(tmp_path)
        repo.add("STORY-100", "Title", ["only task"])
        repo.complete_task("STORY-100", "only task")
        assert repo.load("STORY-100")["status"] == "done"

        repo.add_task("STORY-100", "follow-up task")

        record = repo.load("STORY-100")
        assert record["status"] == "in_progress"

    def test_add_task_rejects_duplicate(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from pactkit.governance import GovernanceError, StoryRepository

        repo = StoryRepository(tmp_path)
        repo.add("STORY-100", "Title", ["first task"])

        with pytest.raises(GovernanceError):
            repo.add_task("STORY-100", "first task")


class TestPreflightProseHardening:
    def _spec_with_table_and_prose(self, tmp_path, big: bool) -> Path:
        target = tmp_path / ".github" / "manifest.json"
        target.parent.mkdir(parents=True)
        target.write_text("x" * (40_000 if big else 10), encoding="utf-8")
        spec = tmp_path / "docs" / "specs" / "STORY-Y.md"
        spec.parent.mkdir(parents=True)
        # Prose mentions the bare basename; the table declares the full path.
        spec.write_text(
            "# STORY-Y\n\n"
            "## Requirements\n\n### R1: needs manifest.json (MUST)\n\n"
            "The prose mentions `manifest.json` by bare basename.\n\n"
            "## Implementation Inputs\n\n"
            "| Path | Mode | Range | Required |\n"
            "|------|------|-------|----------|\n"
            "| .github/manifest.json | all | all | SHOULD |\n",
            encoding="utf-8",
        )
        return spec

    def test_prose_basename_does_not_double_add(self, tmp_path):
        """AC4: a table-declared path wins over the prose basename."""
        from pactkit.spec_preflight import run_spec_preflight

        spec = self._spec_with_table_and_prose(tmp_path, big=False)
        result = run_spec_preflight(tmp_path, spec)

        inputs = [i["path"] for i in result.receipt["inputs"]]
        assert inputs.count(".github/manifest.json") == 1, inputs

    def test_oversized_prose_reference_warns_not_aborts(self, tmp_path):
        """AC5: an undeclared >32KB prose reference downgrades to WARN."""
        from pactkit.spec_preflight import run_spec_preflight

        target = tmp_path / ".github" / "huge.json"
        target.parent.mkdir(parents=True)
        target.write_text("x" * 40_000, encoding="utf-8")
        spec = tmp_path / "docs" / "specs" / "STORY-Z.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(
            "# STORY-Z\n\nThe prose mentions `huge.json` bare.\n", encoding="utf-8"
        )

        result = run_spec_preflight(tmp_path, spec)

        assert "WARN" in result.rendered
        assert "[WARN] skipped oversized" in result.rendered
