import json
from pathlib import Path

import pytest
import subprocess
import sys

from pactkit.spec_preflight import (
    PreflightError,
    check_preflight_receipt,
    run_spec_preflight,
)


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

    result = run_spec_preflight(root, spec, session_id="session-1")

    assert "--color-brand" in result.rendered
    assert "--card-gap" in result.rendered
    assert "5: line 5" in result.rendered
    assert "8: line 8" in result.rendered
    assert "MUST use tokens.css" in result.rendered
    assert "禁止 hard-coded colors" in result.rendered
    receipt = json.loads(result.receipt_path.read_text())
    assert receipt["project_root"] == str(root.resolve())
    assert receipt["story_id"] == "STORY-033"
    assert receipt["session_id"] == "session-1"
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


def test_receipt_invalidates_when_spec_or_input_changes(tmp_path):
    root, spec = _project(tmp_path)
    source = root / "src" / "policy.txt"
    source.write_text("v1\n")
    spec.write_text("# STORY-033\nRead `src/policy.txt`.\n")
    run_spec_preflight(root, spec, session_id="s1")

    assert check_preflight_receipt(root, "STORY-033", session_id="s1").valid
    source.write_text("v2\n")
    stale = check_preflight_receipt(root, "STORY-033", session_id="s1")
    assert not stale.valid
    assert "input changed" in stale.reason


def test_receipt_is_session_bound_when_session_is_declared(tmp_path):
    root, spec = _project(tmp_path)
    spec.write_text("# STORY-033\nNo file inputs.\n")
    run_spec_preflight(root, spec, session_id="s1")

    result = check_preflight_receipt(root, "STORY-033", session_id="s2")
    assert not result.valid
    assert "session" in result.reason


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
