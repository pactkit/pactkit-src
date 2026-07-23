"""Tests for STORY-slim-134: command frontmatter must not contain model field.

Verifies R1-R4:
- R1: commands.py frontmatter has no model field
- R2: workflows.py frontmatter has no model field
- R3: deployed plugin commands have no model field
- R4: sprint body text references to model are preserved
"""
import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _parse_frontmatter(text):
    """Extract YAML frontmatter as dict (no PyYAML dependency)."""
    match = re.search(r'---\n(.*?)\n---', text.strip(), re.DOTALL)
    assert match, f'Missing YAML frontmatter, content start: {text[:80]}'
    fm = {}
    for line in match.group(1).strip().splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


class TestNoModelInCommandsFrontmatter:
    """R1: commands.py — no model field in any command frontmatter."""

    def test_no_model_in_any_command(self):
        from pactkit.prompts import COMMANDS_CONTENT
        for filename, content in COMMANDS_CONTENT.items():
            fm = _parse_frontmatter(content)
            assert 'model' not in fm, (
                f'{filename} frontmatter still contains model: {fm["model"]!r}. '
                'Remove the model field to avoid Bedrock alias resolution issues.'
            )


class TestNoModelInWorkflowsFrontmatter:
    """R2: workflows.py — no model field in sprint/hotfix/design/debug frontmatter."""

    def test_sprint_frontmatter_no_model(self):
        from pactkit.prompts import SPRINT_PROMPT
        fm = _parse_frontmatter(SPRINT_PROMPT)
        assert 'model' not in fm, (
            f'SPRINT_PROMPT frontmatter still contains model: {fm["model"]!r}.'
        )

    def test_hotfix_frontmatter_no_model(self):
        from pactkit.prompts import HOTFIX_PROMPT
        fm = _parse_frontmatter(HOTFIX_PROMPT)
        assert 'model' not in fm, (
            f'HOTFIX_PROMPT frontmatter still contains model: {fm["model"]!r}.'
        )

    def test_design_frontmatter_no_model(self):
        from pactkit.prompts import DESIGN_PROMPT
        fm = _parse_frontmatter(DESIGN_PROMPT)
        assert 'model' not in fm, (
            f'DESIGN_PROMPT frontmatter still contains model: {fm["model"]!r}.'
        )

    def test_debug_frontmatter_no_model(self):
        from pactkit.prompts.workflows import DEBUG_PROMPT
        fm = _parse_frontmatter(DEBUG_PROMPT)
        assert 'model' not in fm, (
            f'DEBUG_PROMPT frontmatter still contains model: {fm["model"]!r}.'
        )


class TestSprintBodyModelReferencesPreserved:
    """R4: sprint body text references to model must be preserved (not frontmatter)."""

    def test_sprint_body_mentions_opus_for_plan(self):
        """Stage A body text should still reference opus for A1 Plan sub-stage."""
        from pactkit.prompts import SPRINT_PROMPT
        # Find Stage A section (body text, not frontmatter)
        a_start = SPRINT_PROMPT.find('Stage A')
        b_start = SPRINT_PROMPT.find('Stage B', a_start)
        assert a_start != -1 and b_start != -1
        stage_a = SPRINT_PROMPT[a_start:b_start]
        assert 'model: opus' in stage_a or 'model="opus"' in stage_a, (
            "Stage A body text must still reference opus for A1 — do not remove body references."
        )

    def test_sprint_body_mentions_sonnet_for_act(self):
        """Stage A body text should still reference sonnet for A2 Act sub-stage."""
        from pactkit.prompts import SPRINT_PROMPT
        a_start = SPRINT_PROMPT.find('Stage A')
        b_start = SPRINT_PROMPT.find('Stage B', a_start)
        assert a_start != -1 and b_start != -1
        stage_a = SPRINT_PROMPT[a_start:b_start]
        assert 'model: sonnet' in stage_a or 'model="sonnet"' in stage_a, (
            "Stage A body text must still reference sonnet for A2 — do not remove body references."
        )


class TestDeployedPluginCommandsNoModel:
    """R3: deployed plugin commands must not contain model field in frontmatter."""

    def test_deployed_commands_no_model(self, tmp_path):
        from unittest.mock import patch
        with patch.object(Path, 'home', return_value=tmp_path), \
             patch('pactkit.generators.deployer.Path.cwd', return_value=tmp_path):
            from pactkit.generators.deployer import deploy
            deploy(mode='expert')

        # STORY-slim-063: commands deployed as skills/{name}/SKILL.md
        skills_dir = tmp_path / '.claude' / 'skills'
        command_dirs = [d for d in skills_dir.iterdir()
                        if d.is_dir() and d.name.startswith('project-')]
        assert len(command_dirs) > 0, 'No project-* command skills found after deploy'

        for cmd_dir in command_dirs:
            skill_file = cmd_dir / 'SKILL.md'
            if not skill_file.exists():
                continue
            content = skill_file.read_text()
            fm = _parse_frontmatter(content)
            assert 'model' not in fm, (
                f'{cmd_dir.name}/SKILL.md deployed with model: {fm["model"]!r}'
            )
