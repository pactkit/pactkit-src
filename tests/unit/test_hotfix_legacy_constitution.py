"""
HOTFIX 2026-08-26: legacy constitution double-loading.

The pre-slim-112 merged constitution (rules/pactkit.md) still sits in
users' global rules/ alongside the runtime kernel — Claude Code loads
BOTH every session, injecting two conflicting governance philosophies
(26 MUST/SHOULD vs 0). The deployer must surface it, and the on-demand
rule directory must explain itself.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pactkit.profiles import get_profile

PROFILE = get_profile("classic")


def test_legacy_constitution_presence_warns(tmp_path, capsys):
    """A superseded rules/pactkit.md on disk is reported, never silently kept."""
    from pactkit.generators.deployer import _deploy_rules

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "pactkit.md").write_text("# old merged constitution\n", encoding="utf-8")

    _deploy_rules(tmp_path, ["runtime"], profile=PROFILE)

    out = capsys.readouterr().out
    assert "superseded" in out
    assert "pactkit.md" in out


def test_legacy_constitution_retired_when_byte_identical(tmp_path):
    """A byte-identical legacy copy is retired automatically (update path)."""
    from pactkit.generators import deployer

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(parents=True)
    # Any known legacy template byte-match retires; simulate by patching the
    # legacy map for this test.
    legacy = tmp_path / "rules" / "pactkit.md"
    content = "# exact legacy template\n"
    legacy.write_text(content, encoding="utf-8")

    import unittest.mock as mock

    with mock.patch.dict(
        "pactkit.prompts.rules.LEGACY_RULE_CONTENTS",
        {"pactkit.md": content},
    ):
        _deploy_rules_local = deployer._deploy_rules
        _deploy_rules_local(tmp_path, ["runtime"], profile=PROFILE)

    assert not legacy.exists()


def test_on_demand_rules_readme_deployed(tmp_path):
    """skills/_rules/ carries a README explaining the shadow directory."""
    from pactkit.generators.deployer import _deploy_rules

    _deploy_rules(tmp_path, ["runtime"], profile=PROFILE)

    readme = tmp_path / "skills" / "_rules" / "README.md"
    assert readme.is_file()
    content = readme.read_text(encoding="utf-8")
    assert "On-Demand Rules" in content
    assert "SKILL.md" in content
    assert "pactkit update" in content
