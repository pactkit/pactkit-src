"""
BUG-009: pactkit update does not backfill project-level .claude/pactkit.yaml.

Tests verify that _deploy_classic() also backfills the project-level config
at $CWD/.claude/pactkit.yaml when it exists.
"""
from pathlib import Path
from unittest.mock import patch

import yaml


def _config():
    from pactkit import config
    return config


def _write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


# ===========================================================================
# AC1: Project-level config backfilled on pactkit update
# ===========================================================================
class TestAC1ProjectConfigBackfilled:
    """Project config with only stack/version/root gets backfilled."""

    def test_project_config_gets_hooks_section(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        # Global config (full)
        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        # Project config (minimal — missing hooks/ci/etc.)
        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        updated = yaml.safe_load((project_claude / 'pactkit.yaml').read_text())
        assert 'hooks' in updated

    def test_project_config_gets_ci_section(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        updated = yaml.safe_load((project_claude / 'pactkit.yaml').read_text())
        assert 'ci' in updated
        assert 'issue_tracker' in updated
        assert 'lint_blocking' in updated
        assert 'auto_fix' in updated


# ===========================================================================
# AC2: Global config still backfilled (no regression)
# ===========================================================================
class TestAC2GlobalConfigStillWorks:
    """Global config auto-merge is unchanged."""

    def test_global_config_still_auto_merged(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        # Global config missing one command
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS - {'project-design'}),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        # No project config
        project.mkdir(parents=True)

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        updated = yaml.safe_load((home_claude / 'pactkit.yaml').read_text())
        assert 'project-design' in updated['commands']


# ===========================================================================
# AC3: Non-existent project config not created
# ===========================================================================
class TestAC3NonExistentProjectConfigNotCreated:
    """Project config must not be created if it doesn't exist."""

    def test_no_project_config_not_created(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        project.mkdir(parents=True)
        # No .claude/ dir in project

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        assert not (project / '.claude' / 'pactkit.yaml').exists()

    def test_project_claude_dir_exists_but_no_yaml(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        (project / '.claude').mkdir(parents=True)
        # .claude/ dir exists but no pactkit.yaml

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        assert not (project / '.claude' / 'pactkit.yaml').exists()


# ===========================================================================
# AC4: Existing values preserved
# ===========================================================================
class TestAC4ExistingValuesPreserved:
    """Backfill must not overwrite existing user values."""

    def test_existing_ci_provider_preserved(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
            'ci': {'provider': 'github'},
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        updated = yaml.safe_load((project_claude / 'pactkit.yaml').read_text())
        assert updated['ci']['provider'] == 'github'

    def test_existing_lint_blocking_preserved(self, tmp_path):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
            'lint_blocking': True,
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        updated = yaml.safe_load((project_claude / 'pactkit.yaml').read_text())
        assert updated['lint_blocking'] is True


# ===========================================================================
# AC5: Output distinguishes global vs project config
# ===========================================================================
class TestAC5OutputDistinguishes:
    """Output must indicate project config was updated."""

    def test_project_config_output_message(self, tmp_path, capsys):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        output = capsys.readouterr().out
        assert 'project' in output.lower() or 'Project' in output

    def test_no_project_output_when_config_complete(self, tmp_path, capsys):
        from pactkit.generators.deployer import deploy

        home = tmp_path / 'home'
        project = tmp_path / 'project'

        home_claude = home / '.claude'
        home_claude.mkdir(parents=True)
        cfg = _config()
        _write_yaml(home_claude / 'pactkit.yaml', {
            'agents': sorted(cfg.VALID_AGENTS),
            'commands': sorted(cfg.VALID_COMMANDS),
            'skills': sorted(cfg.VALID_SKILLS),
            'rules': sorted(cfg.VALID_RULES),
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        # Project config already complete
        project_claude = project / '.claude'
        project_claude.mkdir(parents=True)
        _write_yaml(project_claude / 'pactkit.yaml', {
            'stack': 'python', 'version': '1.0.0', 'root': '.',
            'ci': {'provider': 'none'},
            'issue_tracker': {'provider': 'none'},
            'hooks': {'pre_commit_lint': False, 'post_test_coverage': False, 'pre_push_check': False},
            'lint_blocking': False,
            'auto_fix': False,
        })

        with patch.object(Path, 'home', return_value=home), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=project):
            deploy()

        output = capsys.readouterr().out
        # No project-level auto-added messages when already complete
        lines = [l for l in output.splitlines() if 'project' in l.lower() and 'auto' in l.lower()]
        assert len(lines) == 0
