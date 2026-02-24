"""STORY-016: CLAUDE.md hygiene — language matching rule & project context cleanup.

Verifies that the core protocol has a language-matching rule,
and the project .claude/CLAUDE.md is clean and instruction-focused.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


# ===========================================================================
# Scenario 1: Language matching in core protocol
# ===========================================================================

class TestLanguageMatchingRule:
    """Core protocol must contain a language-matching instruction."""

    def test_core_protocol_has_language_rule(self):
        from pactkit.prompts.rules import RULES_MODULES
        core = RULES_MODULES['core']
        assert 'language' in core.lower()

    def test_core_protocol_mentions_matching(self):
        from pactkit.prompts.rules import RULES_MODULES
        core = RULES_MODULES['core']
        # Should mention matching user's language
        assert 'match' in core.lower() or 'mirror' in core.lower() or 'respond' in core.lower()

    def test_core_protocol_mentions_chinese(self):
        """Should explicitly mention Chinese as an example."""
        from pactkit.prompts.rules import RULES_MODULES
        core = RULES_MODULES['core']
        assert 'chinese' in core.lower() or '中文' in core


# ===========================================================================
# Scenario 3: Project CLAUDE.md has no stale data
# ===========================================================================

class TestProjectClaudeMdClean:
    """Project .claude/CLAUDE.md must not have stale metrics."""

    def test_no_stale_test_count(self):
        content = (ROOT / '.claude' / 'CLAUDE.md').read_text()
        assert '909' not in content

    def test_references_context_md(self):
        content = (ROOT / '.claude' / 'CLAUDE.md').read_text()
        assert 'context.md' in content


# ===========================================================================
# Scenario 4: Project CLAUDE.md is instruction-focused
# ===========================================================================

class TestProjectClaudeMdContent:
    """Project .claude/CLAUDE.md must have architecture and dev commands."""

    def test_has_architecture_section(self):
        content = (ROOT / '.claude' / 'CLAUDE.md').read_text()
        assert 'src/pactkit/' in content or 'Architecture' in content

    def test_has_dev_commands(self):
        content = (ROOT / '.claude' / 'CLAUDE.md').read_text()
        assert 'pytest' in content or 'ruff' in content
