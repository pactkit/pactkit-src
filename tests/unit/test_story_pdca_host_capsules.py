"""Host-native Sprint capsule deployment acceptance tests."""

from pactkit.generators.deployer import _deploy_commands, _deploy_rules
from pactkit.config import DEFAULT_RULE_IDS
from pactkit.profiles import get_profile


def test_classic_sprint_reads_one_managed_phase_capsule_at_a_time(tmp_path):
    profile = get_profile("classic")
    _deploy_commands(tmp_path / "skills", ["project-sprint"], profile=profile)
    _deploy_rules(tmp_path, sorted(DEFAULT_RULE_IDS), profile=profile)

    sprint = (tmp_path / "skills" / "project-sprint" / "SKILL.md").read_text()
    assert "current session" in sprint.lower()
    assert "sprint-orchestrator.md" in sprint
    assert "Plan Contract" not in sprint
    assert "Act Contract" not in sprint
    assert "Check Contract" not in sprint
    assert "Done Contract" not in sprint
    for retired in ("TeamCreate", "TaskCreate", "WorkUnit", "codex runner"):
        assert retired not in sprint
    for phase in ("plan", "act", "check", "done"):
        capsule = tmp_path / "skills" / "_rules" / "phases" / f"{phase}-contract.md"
        assert capsule.is_file()
        assert "Completion Evidence" in capsule.read_text()
