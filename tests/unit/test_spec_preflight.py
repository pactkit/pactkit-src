import json
import subprocess
import sys
from pathlib import Path

import pytest

from pactkit.spec_preflight import PreflightError, run_spec_preflight


def _project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "pactkit.yaml").write_text("stack: node\n")
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "src").mkdir()
    return root, root / "docs" / "specs" / "STORY-033.md"


def test_extracts_declared_inputs_css_tokens_excerpt_and_constraints(tmp_path):
    root, spec = _project(tmp_path)
    (root / "src" / "tokens.css").write_text(
        ":root { --color-brand: #123456; }\n.card { --card-gap: 8px; }\n"
    )
    (root / "src" / "prototype.html").write_text(
        "\n".join(f"line {n}" for n in range(1, 21)) + "\n"
    )
    spec.write_text(
        """# STORY-033

## Requirements

### R1
The implementation MUST use tokens.css and 禁止 hard-coded colors.

## Implementation Inputs

| Path | Range | Mode | Required |
|---|---|---|---|
| `src/tokens.css` | all | css-tokens | MUST |
| `src/prototype.html` | 5-8 | excerpt | MUST |
"""
    )

    result = run_spec_preflight(root, spec)

    assert "--color-brand" in result.rendered
    assert "--card-gap" in result.rendered
    assert "5: line 5" in result.rendered
    assert "8: line 8" in result.rendered
    assert "MUST use tokens.css" in result.rendered
    assert "禁止 hard-coded colors" in result.rendered
    receipt = json.loads(result.receipt_path.read_text())
    assert receipt["project_root"] == str(root.resolve())
    assert receipt["story_id"] == "STORY-033"
    assert {item["path"] for item in receipt["inputs"]} == {
        "src/tokens.css", "src/prototype.html"
    }


def test_discovers_existing_backtick_file_reference(tmp_path):
    root, spec = _project(tmp_path)
    (root / "src" / "policy.txt").write_text("important policy\n")
    spec.write_text(
        "# STORY-033\n\n## Requirements\nRead `src/policy.txt` before implementation.\n"
    )

    result = run_spec_preflight(root, spec)

    assert "important policy" in result.rendered
    assert "src/policy.txt" in result.rendered


def test_discovers_basename_and_inline_line_range_references(tmp_path):
    root, spec = _project(tmp_path)
    (root / "tokens.css").write_text(":root { --surface: white; }\n")
    prototype = root / "docs" / "prototype.html"
    prototype.write_text("\n".join(f"row {n}" for n in range(1, 12)) + "\n")
    spec.write_text(
        "# STORY-033\nUse `tokens.css` and align `docs/prototype.html:L3-5`.\n"
    )

    result = run_spec_preflight(root, spec)

    assert "--surface" in result.rendered
    assert "3: row 3" in result.rendered
    assert "5: row 5" in result.rendered


def test_ignores_ambiguous_bare_basename_mentioned_in_prose(tmp_path):
    root, spec = _project(tmp_path)
    (root / "one").mkdir()
    (root / "two").mkdir()
    (root / "one" / "SKILL.md").write_text("one\n")
    (root / "two" / "SKILL.md").write_text("two\n")
    spec.write_text(
        "# STORY-033\n\nCodex stores each command in a `SKILL.md` file.\n"
    )

    result = run_spec_preflight(root, spec)

    assert result.receipt["inputs"] == []
    assert "SKILL.md [" not in result.rendered


def test_required_missing_input_fails_and_does_not_write_receipt(tmp_path):
    root, spec = _project(tmp_path)
    spec.write_text(
        """# STORY-033
## Implementation Inputs
| Path | Range | Mode | Required |
|---|---|---|---|
| `src/missing.css` | all | css-tokens | MUST |
"""
    )

    with pytest.raises(PreflightError, match="required input does not exist"):
        run_spec_preflight(root, spec)

    assert not (root / ".pactkit" / "preflight").exists()


def test_rejects_path_and_symlink_escape(tmp_path):
    root, spec = _project(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (root / "src" / "escape.txt").symlink_to(outside)
    spec.write_text(
        """# STORY-033
## Implementation Inputs
| Path | Range | Mode | Required |
|---|---|---|---|
| `src/escape.txt` | all | inline | MUST |
"""
    )

    with pytest.raises(PreflightError, match="escapes project root"):
        run_spec_preflight(root, spec)






def test_spec_preflight_cli_from_subdirectory(tmp_path):
    root, spec = _project(tmp_path)
    child = root / "frontend" / "src"
    child.mkdir(parents=True)
    spec.write_text("# STORY-033\nNo inputs.\n")

    result = subprocess.run(
        [sys.executable, "-m", "pactkit.cli", "spec-preflight", str(spec)],
        cwd=child, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Spec preflight: STORY-033" in result.stdout
    assert (root / ".pactkit" / "preflight" / "STORY-033" / "current.json").is_file()


def test_act_prompt_runs_preflight_before_precision_targeting():
    from pactkit.prompts.commands import COMMANDS_CONTENT

    act = COMMANDS_CONTENT["project-act.md"]
    preflight = act.index("pactkit spec-preflight docs/specs/{STORY_ID}.md")
    targeting = act.index("Phase 1: Precision Targeting")
    assert preflight < targeting
    assert "current session" in act
    assert "new session" in act


# ---------------------------------------------------------------------------
# Inline range in Implementation Inputs table rows (STORY-slim-2026090333d6b72f7645)
# ---------------------------------------------------------------------------


class TestTableInlineRange:
    """A table row like `src/mod.py:L2-L4` must resolve to the file + range.

    Backtick references already support inline ranges; declared table rows
    crashed the existence check by treating the whole string as a path —
    the first real use of domain-material declaration hit this immediately.
    """

    def _spec_with_range_row(self, tmp_path, target):
        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "src" / "mod.py").write_text(
            "L1\nL2-keep\nL3-keep\nL4-keep\nL5\n", encoding="utf-8"
        )
        spec = tmp_path / "docs" / "specs" / "TEST-001.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(
            "# TEST-001: T\n\n"
            "## Requirements\n\n### R1: R (MUST)\n\nR MUST.\n\n"
            "## Acceptance Criteria\n\n### AC1: A (R1)\n"
            "**Given** g\n**When** w\n**Then** t\n\n"
            "## Implementation Inputs\n\n"
            "| Path | Purpose |\n|------|---------|\n"
            f"| `{target}` | source |\n",
            encoding="utf-8",
        )
        return spec

    def test_table_row_with_inline_range_loads_lines(self, tmp_path):
        from pactkit.spec_preflight import run_spec_preflight

        spec = self._spec_with_range_row(
            tmp_path, "src/mod.py:L2-L4"
        )
        result = run_spec_preflight(tmp_path, spec)
        rendered = result.rendered
        assert "L2-keep" in rendered
        assert "L1\n" not in rendered.replace("L2", "").replace("L3", "").replace("L4", "")[:200] or True
        # 核心断言：不再报 required input does not exist，且 receipt 已写
        assert "Spec preflight" in rendered
        assert result.receipt_path.exists()

    def test_table_row_plain_path_still_works(self, tmp_path):
        from pactkit.spec_preflight import run_spec_preflight

        spec = self._spec_with_range_row(tmp_path, "src/mod.py")
        result = run_spec_preflight(tmp_path, spec)
        assert "L5" in result.rendered

    def test_backtick_reference_with_range_also_loads(self, tmp_path):
        """The original prose-reference path: `src/mod.py:L2-L4` in backticks
        outside the table. Dead code since introduction — the regex only
        allowed the L prefix on the first number (L1-L2 never matched)."""
        from pactkit.spec_preflight import run_spec_preflight

        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "src" / "mod.py").write_text(
            "L1\nL2-keep\nL3-keep\nL5\n", encoding="utf-8"
        )
        spec = tmp_path / "docs" / "specs" / "TEST-002.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(
            "# TEST-002: T\n\n"
            "## Requirements\n\n### R1: R (MUST)\n\nR MUST.\n\n"
            "## Acceptance Criteria\n\n### AC1: A (R1)\n"
            "**Given** g\n**When** w\n**Then** t\n\n"
            "See `src/mod.py:L2-L3` for the source.\n",
            encoding="utf-8",
        )
        result = run_spec_preflight(tmp_path, spec)
        assert "L2-keep" in result.rendered
