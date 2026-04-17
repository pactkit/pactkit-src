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
        from pactkit.config import VALID_RULES
        assert '11-pdca-nudge' in VALID_RULES

    def test_rules_files_includes_nudge(self):
        from pactkit.prompts.rules import RULES_FILES
        assert 'nudge' in RULES_FILES
        assert RULES_FILES['nudge'] == '11-pdca-nudge.md'

    def test_managed_prefixes_covers_11(self):
        from pactkit.prompts.rules import RULES_MANAGED_PREFIXES
        assert any(p == '11-' for p in RULES_MANAGED_PREFIXES)


class TestAC6DeployVerification:
    """AC6: Deploy produces both anchor and detail rule."""

    def test_deployed_core_has_pdca_nudge(self, tmp_path):
        _deploy(tmp_path)
        core = (tmp_path / '.claude' / 'rules' / '01-core-protocol.md').read_text()
        assert '## PDCA Nudge' in core

    def test_deployed_nudge_rule_exists(self, tmp_path):
        _deploy(tmp_path)
        nudge_file = tmp_path / '.claude' / 'rules' / '11-pdca-nudge.md'
        assert nudge_file.is_file()
        content = nudge_file.read_text()
        assert len(content.strip()) > 50

    def test_deployed_nudge_has_trigger_matrix(self, tmp_path):
        _deploy(tmp_path)
        content = (tmp_path / '.claude' / 'rules' / '11-pdca-nudge.md').read_text()
        assert '/project-hotfix' in content
        assert '/project-plan' in content
