"""BUG-slim-089: Global CLAUDE.md overwritten on every deploy.

Tests that _deploy_claude_md() preserves user-modified content,
updates version headers in-place, and creates fresh files on first install.
"""


class TestAC1UserModifiedPreserved:
    """AC1: User-modified global CLAUDE.md is preserved."""

    def test_user_content_not_overwritten(self, tmp_path):
        """Given CLAUDE.md with user content, deploy must not overwrite it."""
        from pactkit.generators.deployer import _deploy_claude_md

        claude_md = tmp_path / "CLAUDE.md"
        user_content = "# My Custom Instructions\n\nDo things my way.\n"
        claude_md.write_text(user_content)

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text() == user_content

    def test_user_content_with_context_ref_preserved(self, tmp_path):
        """User content that already has @./docs/product/context.md is left alone."""
        from pactkit.generators.deployer import _deploy_claude_md

        claude_md = tmp_path / "CLAUDE.md"
        user_content = "# My Setup\n\n@./docs/product/context.md\n\nMore stuff.\n"
        claude_md.write_text(user_content)

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text() == user_content


class TestAC2PactKitManagedVersionUpdate:
    """AC2: PactKit-managed CLAUDE.md version header is updated in-place."""

    def test_version_header_updated(self, tmp_path):
        """Given old-version PactKit template, deploy updates the version."""
        from pactkit import __version__
        from pactkit.generators.deployer import _deploy_claude_md

        claude_md = tmp_path / "CLAUDE.md"
        old_content = "# PactKit Global Constitution (v1.0.0 Modular)\n\n@./docs/product/context.md\n"
        claude_md.write_text(old_content)

        _deploy_claude_md(tmp_path, [])

        result = claude_md.read_text()
        assert f"# PactKit Global Constitution (v{__version__} Modular)" in result
        assert "@./docs/product/context.md" in result


class TestAC3FreshInstall:
    """AC3: Fresh install creates full template."""

    def test_creates_template_when_missing(self, tmp_path):
        """Given no CLAUDE.md, deploy creates the full PactKit template."""
        from pactkit import __version__
        from pactkit.generators.deployer import _deploy_claude_md

        claude_md = tmp_path / "CLAUDE.md"
        assert not claude_md.exists()

        _deploy_claude_md(tmp_path, [])

        result = claude_md.read_text()
        assert f"# PactKit Global Constitution (v{__version__} Modular)" in result
        assert "@./docs/product/context.md" in result


class TestAC5IdempotentRedeploy:
    """AC5: Idempotent re-deploy produces same content."""

    def test_same_version_produces_identical_content(self, tmp_path):
        """Given current-version template, re-deploy produces identical output."""
        from pactkit import __version__
        from pactkit.generators.deployer import _deploy_claude_md

        claude_md = tmp_path / "CLAUDE.md"
        template = f"# PactKit Global Constitution (v{__version__} Modular)\n\n@./docs/product/context.md\n"
        claude_md.write_text(template)

        _deploy_claude_md(tmp_path, [])

        assert claude_md.read_text() == template
