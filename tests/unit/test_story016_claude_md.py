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
# Scenario 4: Project CLAUDE.md is instruction-focused (STORY-040 updated)
# ===========================================================================

class TestProjectClaudeMdContent:
    """Project .claude/ files have architecture and dev commands.

    STORY-040: Architecture is now in CLAUDE.local.md (user-owned),
    Dev commands are in CLAUDE.md (framework-owned).
    """

    def test_generate_claude_local_md_creates_template(self, tmp_path):
        """_generate_claude_local_md_if_missing creates a valid template (STORY-040 R3).

        Tests the generator function directly instead of reading repo state,
        which can be polluted by test-invoked deploy() side effects in CI.
        """
        from pactkit.generators.deployer import _generate_claude_local_md_if_missing
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        _generate_claude_local_md_if_missing(claude_dir)
        local_path = claude_dir / 'CLAUDE.local.md'
        assert local_path.exists()
        content = local_path.read_text()
        assert 'Project Local Instructions' in content

    def test_generate_claude_local_md_preserves_existing(self, tmp_path):
        """_generate_claude_local_md_if_missing does not overwrite existing file."""
        from pactkit.generators.deployer import _generate_claude_local_md_if_missing
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        local_path = claude_dir / 'CLAUDE.local.md'
        local_path.write_text('# My custom content\n')
        _generate_claude_local_md_if_missing(claude_dir)
        assert local_path.read_text() == '# My custom content\n'

    def test_has_dev_commands(self):
        """Dev commands should be in CLAUDE.md (framework content)."""
        content = (ROOT / '.claude' / 'CLAUDE.md').read_text()
        assert 'pytest' in content or 'ruff' in content
