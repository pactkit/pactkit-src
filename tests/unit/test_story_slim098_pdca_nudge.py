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
        assert '11-pdca-nudge.md' in core

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
        """Post-merge: global content identified by 'pactkit' name."""
        from pactkit.prompts.rules import RULES_MANAGED_PREFIXES
        assert 'pactkit' in RULES_MANAGED_PREFIXES


class TestAC6DeployVerification:
    """AC6: Deploy produces merged pactkit.md containing nudge content."""

    def test_deployed_pactkit_has_pdca_nudge(self, tmp_path):
        """Merged pactkit.md contains nudge section."""
        _deploy(tmp_path)
        pactkit = (tmp_path / '.claude' / 'rules' / 'pactkit.md').read_text()
        assert '## PDCA Nudge' in pactkit

    def test_deployed_pactkit_rule_exists(self, tmp_path):
        _deploy(tmp_path)
        pactkit_file = tmp_path / '.claude' / 'rules' / 'pactkit.md'
        assert pactkit_file.is_file()
        content = pactkit_file.read_text()
        assert len(content.strip()) > 50

    def test_deployed_nudge_has_trigger_matrix(self, tmp_path):
        """Nudge trigger matrix is in the merged pactkit.md."""
        _deploy(tmp_path)
        content = (tmp_path / '.claude' / 'rules' / 'pactkit.md').read_text()
        assert '/project-hotfix' in content
        assert '/project-plan' in content
