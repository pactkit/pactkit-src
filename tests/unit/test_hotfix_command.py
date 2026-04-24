"""Tests for STORY-017: /project-hotfix command."""


def _prompts():
    import importlib

    import pactkit.prompts as p
    importlib.reload(p)
    return p


class TestHotfixPromptExists:
    """Scenario 1: HOTFIX_PROMPT 可导入"""

    def test_importable(self):
        p = _prompts()
        assert hasattr(p, 'HOTFIX_PROMPT')

    def test_non_empty(self):
        p = _prompts()
        assert isinstance(p.HOTFIX_PROMPT, str)
        assert len(p.HOTFIX_PROMPT) > 100

    def test_has_frontmatter(self):
        p = _prompts()
        assert p.HOTFIX_PROMPT.strip().startswith('---')

    def test_has_arguments_placeholder(self):
        p = _prompts()
        assert '$ARGUMENTS' in p.HOTFIX_PROMPT


class TestHotfixInCommandsContent:
    """Scenario 2: 已注册到 COMMANDS_CONTENT"""

    def test_registered(self):
        p = _prompts()
        assert 'project-hotfix.md' in p.COMMANDS_CONTENT

    def test_matches_prompt(self):
        p = _prompts()
        assert p.COMMANDS_CONTENT['project-hotfix.md'] == p.HOTFIX_PROMPT


class TestRoutingTableIncludesHotfix:
    """Scenario 3: 路由表包含 Hotfix"""

    def test_hotfix_in_routing(self):
        p = _prompts()
        routing = p.RULES_MODULES['routing']
        assert 'Hotfix' in routing or 'hotfix' in routing

    def test_has_role(self):
        p = _prompts()
        routing = p.RULES_MODULES['routing']
        assert 'Senior Developer' in routing

    def test_has_playbook(self):
        p = _prompts()
        routing = p.RULES_MODULES['routing']
        assert 'project-hotfix.md' in routing


class TestPlaybookContent:
    """Scenario 4: Playbook 包含核心关键词"""

    def test_has_pytest(self):
        p = _prompts()
        assert 'pytest' in p.HOTFIX_PROMPT

    def test_has_conventional_commit(self):
        p = _prompts()
        assert 'Conventional Commit' in p.HOTFIX_PROMPT or 'fix(' in p.HOTFIX_PROMPT

    def test_has_fix_scope_format(self):
        p = _prompts()
        assert 'fix(' in p.HOTFIX_PROMPT

    def test_has_phases(self):
        p = _prompts()
        for phase in ['Phase 0', 'Phase 1', 'Phase 2', 'Phase 3']:
            assert phase in p.HOTFIX_PROMPT, f"Missing {phase}"

    def test_has_allowed_tools_with_write(self):
        p = _prompts()
        lines = p.HOTFIX_PROMPT.split('\n')
        for line in lines:
            if 'allowed-tools' in line:
                assert 'Write' in line, "Hotfix needs Write tool"
                assert 'Edit' in line, "Hotfix needs Edit tool"
                break


class TestPlaybookTraceability:
    """Scenario 5: Playbook has lightweight traceability (STORY-032 update)"""

    def test_hotfix_creates_spec(self):
        """Hotfix now creates a lightweight Spec for traceability."""
        p = _prompts()
        text = p.HOTFIX_PROMPT.lower()
        assert 'spec' in text
        assert 'create' in text

    def test_hotfix_adds_board_entry(self):
        """Hotfix now adds a Board entry for traceability."""
        p = _prompts()
        assert 'add_story' in p.HOTFIX_PROMPT or 'Board' in p.HOTFIX_PROMPT

    def test_no_tdd_required(self):
        """Hotfix still does NOT require TDD."""
        p = _prompts()
        text = p.HOTFIX_PROMPT.lower()
        assert 'no tdd' in text or 'not require writing tests' in text


class TestBackwardCompatibility:
    """Scenario 6: 现有命令不受影响"""

    def test_existing_commands_present(self):
        p = _prompts()
        expected = [
            'project-plan.md', 'project-act.md', 'project-check.md',
            'project-done.md', 'project-init.md',
            'project-sprint.md', 'project-hotfix.md', 'project-design.md',
        ]
        for cmd in expected:
            assert cmd in p.COMMANDS_CONTENT, f"Missing {cmd}"

    def test_agents_unchanged(self):
        p = _prompts()
        expected_agents = [
            'system-architect', 'senior-developer', 'qa-engineer',
            'repo-maintainer', 'system-medic', 'security-auditor',
            'visual-architect', 'code-explorer',
        ]
        for agent in expected_agents:
            assert agent in p.AGENTS_EXPERT, f"Missing agent {agent}"


class TestImpactCheckPhase:
    """Scenario 8: Phase 0.5 Impact Check exists (STORY-slim-100)"""

    def test_has_phase_05(self):
        p = _prompts()
        assert 'Phase 0.5' in p.HOTFIX_PROMPT

    def test_has_impact_check_title(self):
        p = _prompts()
        assert 'Impact Check' in p.HOTFIX_PROMPT

    def test_references_mmd_files(self):
        p = _prompts()
        text = p.HOTFIX_PROMPT
        assert 'call_graph.mmd' in text or 'reverse_call_graph.mmd' in text or 'code_graph.mmd' in text

    def test_has_fan_in_threshold(self):
        p = _prompts()
        assert '3+' in p.HOTFIX_PROMPT or '3 or more' in p.HOTFIX_PROMPT

    def test_suggests_project_act(self):
        p = _prompts()
        assert '/project-act' in p.HOTFIX_PROMPT

    def test_graceful_skip_when_no_graphs(self):
        p = _prompts()
        text = p.HOTFIX_PROMPT.lower()
        assert 'skip' in text and ('no call graph' in text or 'do not exist' in text or 'not exist' in text)

    def test_non_blocking_advisory(self):
        """Impact check must not use blocking language."""
        p = _prompts()
        text = p.HOTFIX_PROMPT
        assert 'MUST STOP' not in text or text.index('Phase 0.5') > text.index('MUST STOP')
        assert 'advisory' in text.lower() or 'non-blocking' in text.lower() or 'SHOULD' in text


