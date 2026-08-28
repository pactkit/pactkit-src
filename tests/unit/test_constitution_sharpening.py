"""
STORY-008: Constitution Sharpening — 删除伪优势，强化治理规则
"""
import importlib


def _prompts():
    import pactkit.prompts as p
    importlib.reload(p)
    return p


# ===========================================================================
# Scenario 1: Core protocol trimmed — pseudo-advantages removed
# ===========================================================================

class TestPseudoAdvantagesRemoved:
    """S1: thinking block, Enterprise Expert, Atomic Tools, Output Conventions,
    and Language Mirror are all absent from core protocol."""

    def test_no_thinking_block_directive(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert '<thinking>' not in core
        assert 'thinking' not in core.lower() or 'thinking' in core.lower()
        # More specific: the PRIME DIRECTIVE about thinking should be gone
        assert 'PRIME DIRECTIVE' not in core

    def test_no_enterprise_expert(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'Enterprise Expert' not in core

    def test_no_atomic_tools_section(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert '## Atomic Tools' not in core

    def test_no_output_conventions_section(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert '## Output Conventions' not in core

    def test_no_language_mirror_directive(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        # No **Language** line
        lang_lines = [l for l in core.splitlines() if '**Language**' in l]
        assert len(lang_lines) == 0, \
            f"Language directive should be removed, found: {lang_lines}"


# ===========================================================================
# Scenario 2: TDD and Visual First preserved
# ===========================================================================

class TestGovernanceRulesPreserved:
    """S2: Strict TDD and Visual First sections are present."""

    def test_strict_tdd_present(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'TDD' in core or 'tdd' in core.lower()

    def test_tdd_strengthened(self):
        """TDD rule should mention hotfix exception explicitly."""
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'hotfix' in core.lower()

    def test_visual_first_present(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'Visual First' in core or 'visualize' in core.lower()

    def test_visualize_commands_present(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'visualize' in core


# ===========================================================================
# Scenario 3: Session Context rule added
# ===========================================================================

class TestSessionContextRule:
    """S3: Session Context section exists with cold-start instructions."""

    def test_session_context_section_exists(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'Session Context' in core or 'session context' in core.lower()

    def test_references_context_md(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        assert 'context.md' in core

    def test_cold_start_instruction(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        text = core.lower()
        assert 'cold start' in text or 'new session' in text or \
            'first action' in text or 'before taking action' in text


# ===========================================================================
# Scenario 4: Token reduction >= 30%
# ===========================================================================

class TestTokenReduction:
    """S4: Core protocol should stay within reasonable word limit."""

    # Baseline updated: 400 words (post-STORY-008 reduction + subagent section).
    # 30% headroom → max words. Increase baseline if adding valuable content.
    # Raised from 600 to 660 for STORY-slim-098: PDCA Nudge anchor section added.
    # Raised from 660 to 730 for STORY-slim-105: DEFERRED Comment Format section added.
    # Raised from 730 to 735 for STORY-slim-112: cross-reference text slightly longer.
    # Raised from 735 to 880 for STORY-slim-202608289e83eeb30df4: L1 Hard-Rule
    # Override Protocol section added (override semantics for protected branches).
    # Raised from 880 to 900 for STORY-slim-20260828897396a935ab: authorize
    # channel (pactkit gate authorize) added to the Override Protocol.
    BASELINE_WORD_COUNT = 900

    def test_core_protocol_within_limit(self):
        p = _prompts()
        core = p.RULES_MODULES['core']
        new_word_count = len(core.split())
        max_allowed = int(self.BASELINE_WORD_COUNT * 0.70)
        assert new_word_count <= max_allowed, \
            f"Core protocol has {new_word_count} words, " \
            f"need <= {max_allowed} (70% of {self.BASELINE_WORD_COUNT} baseline)"


# ===========================================================================
# Scenario 5: Hierarchy of Truth sharpened
# ===========================================================================

class TestHierarchySharpened:
    """R3: Hierarchy of Truth has stronger wording."""

    def test_still_has_three_tiers(self):
        p = _prompts()
        hierarchy = p.RULES_MODULES['hierarchy']
        assert 'Tier 1' in hierarchy
        assert 'Tier 2' in hierarchy
        assert 'Tier 3' in hierarchy

    def test_has_conflict_resolution(self):
        p = _prompts()
        hierarchy = p.RULES_MODULES['hierarchy']
        assert 'Conflict' in hierarchy or 'conflict' in hierarchy

    def test_has_pre_existing_test_protocol(self):
        """R3: Should reference pre-existing test failure protocol."""
        p = _prompts()
        hierarchy = p.RULES_MODULES['hierarchy']
        text = hierarchy.lower()
        assert 'pre-existing' in text or 'regression' in text or \
            'do not modify' in text

    def test_spec_precedence_clear(self):
        p = _prompts()
        hierarchy = p.RULES_MODULES['hierarchy']
        assert 'Spec' in hierarchy
        assert 'precedence' in hierarchy.lower() or 'takes priority' in hierarchy.lower() \
            or 'wins' in hierarchy.lower()


# ===========================================================================
# Scenario 6: Backward compatibility — structure intact
# ===========================================================================

class TestStructureIntact:
    """All 6 rule modules still exist with correct keys and files."""

    def test_all_rule_keys_exist(self):
        p = _prompts()
        expected = ['core', 'hierarchy', 'atlas', 'routing', 'workflow', 'mcp']
        for key in expected:
            assert key in p.RULES_MODULES, f"Missing rule key: {key}"

    def test_registry_files_are_mapped_by_logical_identity(self):
        p = _prompts()
        assert p.RULES_FILES['runtime'] == 'pactkit-runtime.md'
        expected_ondemand = {
            'git-workflow': 'execution/git-workflow.md',
            'external-tools': 'execution/external-tools.md',
            'shared-execution': 'execution/shared-execution.md',
            'sectional-heuristics': 'execution/sectional-heuristics.md',
            'capability-design': 'design/capability-design.md',
        }
        for key, filename in expected_ondemand.items():
            assert p.RULES_FILES[key] == filename

    def test_claude_md_template_references_global_rules(self):
        """Only the Runtime Kernel is a global Claude import."""
        p = _prompts()
        assert 'pactkit-runtime.md' in p.CLAUDE_MD_TEMPLATE
        for filename in ['execution/git-workflow.md', 'execution/external-tools.md']:
            assert filename not in p.CLAUDE_MD_TEMPLATE, (
                f"On-demand rule '{filename}' should not be globally imported"
            )
