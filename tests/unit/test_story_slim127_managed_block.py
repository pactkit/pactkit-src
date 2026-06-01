"""Tests for STORY-slim-127: project CLAUDE.md managed-block update.

Four paths:
1. Fresh install (no CLAUDE.md exists)
2. Has markers (update only managed block)
3. Legacy PactKit template (wrap in markers)
4. User-modified (no PactKit header — append managed block)
"""

from unittest.mock import patch

import pytest

from pactkit.generators.deployer import (
    _CLAUDE_MD_END,
    _CLAUDE_MD_START,
    _generate_project_claude_md,
    _upsert_claude_md_managed_block,
)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project structure."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    # Create CLAUDE.local.md so _generate_claude_local_md_if_missing doesn't interfere
    (claude_dir / "CLAUDE.local.md").write_text("# Local\n")
    return tmp_path


@pytest.fixture
def basic_config():
    return {"stack": "python", "venv": {"auto_detect": False}}


class TestFreshInstall:
    """AC4: Fresh install creates file with markers."""

    def test_creates_file_with_markers(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        assert not claude_md.exists()

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content

    def test_at_imports_outside_managed_block(self, tmp_project, basic_config):
        """AC5: @imports appear after <!-- pactkit:end -->."""
        claude_md = tmp_project / ".claude" / "CLAUDE.md"

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        end_pos = content.index(_CLAUDE_MD_END)
        after_end = content[end_pos:]
        assert "@./docs/product/context.md" in after_end
        assert "@./.claude/CLAUDE.local.md" in after_end


class TestHasMarkers:
    """AC1: Existing user content preserved on update."""

    def test_preserves_user_content_above(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        user_content = "# My Custom Header\nSome user notes.\n\n"
        managed = f"{_CLAUDE_MD_START}\n## Old managed\n{_CLAUDE_MD_END}\n"
        imports = "\n@./docs/product/context.md\n@./.claude/CLAUDE.local.md\n"
        claude_md.write_text(user_content + managed + imports)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert "# My Custom Header" in content
        assert "Some user notes." in content
        assert "## Old managed" not in content  # replaced

    def test_preserves_user_content_below(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        managed = f"{_CLAUDE_MD_START}\n## Old managed\n{_CLAUDE_MD_END}\n"
        imports = "@./docs/product/context.md\n@./.claude/CLAUDE.local.md\n"
        user_below = "\n# My Footer\nExtra stuff\n"
        claude_md.write_text(managed + imports + user_below)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert "# My Footer" in content
        assert "Extra stuff" in content

    def test_managed_content_is_regenerated(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        managed = f"{_CLAUDE_MD_START}\n## STALE CONTENT\n{_CLAUDE_MD_END}\n"
        imports = "@./docs/product/context.md\n@./.claude/CLAUDE.local.md\n"
        claude_md.write_text(managed + imports)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert "## STALE CONTENT" not in content
        assert "## Dev Commands" in content  # new managed content


class TestLegacyTemplate:
    """AC2: Legacy CLAUDE.md migrated with markers."""

    def test_wraps_legacy_content_in_markers(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        project_name = tmp_project.name
        legacy = f"# {project_name} — Project Context\n\n## Dev Commands\n\n```bash\npytest\n```\n"
        claude_md.write_text(legacy)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content
        # Old content replaced with fresh managed content
        assert "## Dev Commands" in content


class TestUserModified:
    """AC3: User-modified legacy CLAUDE.md preserved."""

    def test_appends_managed_block(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        user_content = "# My Project\nThis is my custom CLAUDE.md.\n\nDo not touch this.\n"
        claude_md.write_text(user_content)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        # User content preserved
        assert "# My Project" in content
        assert "This is my custom CLAUDE.md." in content
        assert "Do not touch this." in content
        # Managed block appended
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content

    def test_user_content_appears_before_managed(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"
        user_content = "# My Project\nCustom content.\n"
        claude_md.write_text(user_content)

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        user_pos = content.index("# My Project")
        managed_pos = content.index(_CLAUDE_MD_START)
        assert user_pos < managed_pos


class TestCodegraphSection:
    """AC6: Codegraph section appears when .codegraph/ exists."""

    def test_codegraph_included_when_dir_exists(self, tmp_project, basic_config):
        (tmp_project / ".codegraph").mkdir()
        claude_md = tmp_project / ".claude" / "CLAUDE.md"

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert "## Code Intelligence (codegraph)" in content
        # Must be inside managed block
        start_pos = content.index(_CLAUDE_MD_START)
        end_pos = content.index(_CLAUDE_MD_END)
        codegraph_pos = content.index("## Code Intelligence (codegraph)")
        assert start_pos < codegraph_pos < end_pos

    def test_codegraph_absent_when_no_dir(self, tmp_project, basic_config):
        claude_md = tmp_project / ".claude" / "CLAUDE.md"

        with patch("pactkit.generators.deployer.Path.cwd", return_value=tmp_project):
            _generate_project_claude_md(basic_config)

        content = claude_md.read_text()
        assert "## Code Intelligence (codegraph)" not in content


class TestUpsertFunction:
    """Unit tests for _upsert_claude_md_managed_block directly."""

    def test_fresh_file(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        block = "## Managed\nContent here\n"
        _upsert_claude_md_managed_block(path, block, "tmp_path_name")
        content = path.read_text()
        assert _CLAUDE_MD_START in content
        assert _CLAUDE_MD_END in content
        assert "## Managed" in content
        assert "@./docs/product/context.md" in content

    def test_replace_existing_markers(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        old_content = f"# User\n\n{_CLAUDE_MD_START}\n## Old\n{_CLAUDE_MD_END}\n\n@./docs/product/context.md\n@./.claude/CLAUDE.local.md\n"
        path.write_text(old_content)
        block = "## New Content\n"
        _upsert_claude_md_managed_block(path, block, "test")
        content = path.read_text()
        assert "## Old" not in content
        assert "## New Content" in content
        assert "# User" in content

    def test_legacy_pactkit_header(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# test — Project Context\n\n## Dev Commands\n\n```bash\npytest\n```\n")
        block = "## Fresh\n"
        _upsert_claude_md_managed_block(path, block, "test")
        content = path.read_text()
        assert _CLAUDE_MD_START in content
        assert "## Fresh" in content

    def test_user_content_appended(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        path.write_text("# Custom Project\nMy stuff here.\n")
        block = "## Managed Section\n"
        _upsert_claude_md_managed_block(path, block, "Custom Project")
        content = path.read_text()
        assert "# Custom Project" in content
        assert "My stuff here." in content
        assert _CLAUDE_MD_START in content
