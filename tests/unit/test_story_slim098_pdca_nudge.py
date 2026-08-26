"""STORY-slim-098: PDCA Nudge Protocol — dual-anchor deployment tests."""
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _deploy(tmp_path):
    with patch.object(Path, 'home', return_value=tmp_path), \
         patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
        from pactkit.generators.deployer import deploy
        deploy(mode='expert')


class TestR0CoreProtocolAnchor:
    """R0: Core Protocol contains PDCA Nudge anchor section."""

    def test_core_protocol_has_pdca_nudge_section(self):
        from pactkit.prompts import RULES_MODULES
        core = RULES_MODULES['core']
        assert '## PDCA Nudge' in core

    def test_pdca_nudge_references_detail_rule(self):
        from pactkit.prompts import RULES_MODULES
        core = RULES_MODULES['core']
        assert 'PDCA Nudge Protocol' in core

    def test_pdca_nudge_after_session_context(self):
        from pactkit.prompts import RULES_MODULES
        core = RULES_MODULES['core']
        session_pos = core.index('## Session Context')
        nudge_pos = core.index('## PDCA Nudge')
        visual_pos = core.index('## Visual First')
        assert session_pos < nudge_pos < visual_pos


class TestR1NudgeRuleModule:
    """R1-R4: Nudge rule module exists with required content."""

    def test_nudge_module_exists(self):
        from pactkit.prompts import RULES_MODULES
        assert 'nudge' in RULES_MODULES

    def test_nudge_has_trigger_matrix(self):
        from pactkit.prompts import RULES_MODULES
        nudge = RULES_MODULES['nudge']
        assert '/project-hotfix' in nudge
        assert '/project-plan' in nudge
        assert '/project-design' in nudge
        assert '/project-act' in nudge
        assert '/project-sprint' in nudge

    def test_nudge_has_format_template(self):
        from pactkit.prompts import RULES_MODULES
        nudge = RULES_MODULES['nudge']
        assert '💡' in nudge

    def test_nudge_has_suppression_rules(self):
        from pactkit.prompts import RULES_MODULES
        nudge = RULES_MODULES['nudge']
        assert 'PDCA' in nudge and ('suppress' in nudge.lower() or '抑制' in nudge or 'MUST NOT' in nudge)

    def test_nudge_signal_level_is_should(self):
        from pactkit.prompts import RULES_MODULES
        nudge = RULES_MODULES['nudge']
        assert 'SHOULD' in nudge


class TestNudgeRegistration:
    """Nudge rule is registered in config and deployment maps."""

    def test_valid_rules_includes_nudge(self):
        """Post-merge: nudge content is merged into pactkit.md (no standalone rule ID)."""
        from pactkit.config import VALID_RULES
        # nudge content is in pactkit.md (merged global file)
        assert 'pactkit' in VALID_RULES

    def test_rules_modules_includes_nudge(self):
        """nudge module key still exists in RULES_MODULES for inline embedding."""
        from pactkit.prompts.rules import RULES_MODULES
        assert 'nudge' in RULES_MODULES

    def test_managed_prefixes_covers_pactkit(self):
        """The Runtime Kernel remains the sole globally managed rule."""
        from pactkit.prompts.rules import RULES_MANAGED_PREFIXES
        assert 'pactkit-runtime' in RULES_MANAGED_PREFIXES


class TestAC6DeployVerification:
    """Deployment keeps Runtime minimal and loads workflow guidance by command."""

    def test_deployed_pactkit_has_pdca_nudge(self, tmp_path):
        """Runtime explicitly prevents unsolicited PDCA takeover."""
        _deploy(tmp_path)
        runtime = (tmp_path / '.claude' / 'rules' / 'pactkit-runtime.md').read_text()
        assert 'ordinary questions\nor coding into PDCA automatically' in runtime

    def test_deployed_pactkit_rule_exists(self, tmp_path):
        _deploy(tmp_path)
        runtime_file = tmp_path / '.claude' / 'rules' / 'pactkit-runtime.md'
        assert runtime_file.is_file()
        content = runtime_file.read_text()
        assert len(content.strip()) > 50

    def test_deployed_nudge_has_trigger_matrix(self, tmp_path):
        """A requested skill receives its scoped phase contract."""
        _deploy(tmp_path)
        content = (tmp_path / '.claude' / 'skills' / 'project-hotfix' / 'SKILL.md').read_text()
        assert 'hotfix-contract.md' in content
