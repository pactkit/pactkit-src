import json
from pathlib import Path

from pactkit.preflight_guard import hook_entry, install_preflight_hook
from pactkit.spec_preflight import run_spec_preflight


def _root(tmp_path: Path, mode: str) -> Path:
    root = tmp_path / "project"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "pactkit.yaml").write_text(
        f"preflight:\n  mode: {mode}\n"
    )
    (root / "docs" / "specs").mkdir(parents=True)
    return root


def _payload(root: Path, *, session="s1", path="src/app.py") -> str:
    return json.dumps({
        "session_id": session,
        "cwd": str(root),
        "tool_name": "Edit",
        "tool_input": {"file_path": str(root / path)},
    })


def _bash_payload(root: Path, command: str, *, session="s1") -> str:
    return json.dumps({
        "session_id": session,
        "cwd": str(root),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    })


def test_warn_mode_never_blocks_without_act_binding(tmp_path):
    root = _root(tmp_path, "warn")
    message, code = hook_entry(_payload(root), root)
    assert code == 0
    assert "WARN" in message


def test_enforce_mode_without_explicit_act_binding_does_not_lock_editor(tmp_path):
    root = _root(tmp_path, "enforce")
    message, code = hook_entry(_payload(root), root)
    assert code == 0
    assert "not bound to an Act Story" in message


def test_enforce_blocks_stale_receipt_for_bound_story(tmp_path):
    root = _root(tmp_path, "enforce")
    (root / "src").mkdir()
    policy = root / "src" / "policy.txt"
    policy.write_text("v1")
    spec = root / "docs" / "specs" / "STORY-033.md"
    spec.write_text("# STORY-033\nRead `src/policy.txt`.\n")
    run_spec_preflight(root, spec, session_id="s1", activate=True)
    policy.write_text("v2")

    message, code = hook_entry(_payload(root), root)
    assert code == 2
    assert "input changed" in message


def test_enforce_allows_valid_receipt_for_bound_story(tmp_path):
    root = _root(tmp_path, "enforce")
    spec = root / "docs" / "specs" / "STORY-033.md"
    spec.write_text("# STORY-033\nNo inputs.\n")
    run_spec_preflight(root, spec, session_id="s1", activate=True)

    assert hook_entry(_payload(root), root) == ("", 0)
    message, code = hook_entry(_payload(root, path="src/next.py"), root)
    assert code == 0
    assert "not bound to an Act Story" in message


def test_activate_bash_command_binds_hook_session(tmp_path):
    root = _root(tmp_path, "enforce")
    spec = root / "docs" / "specs" / "STORY-033.md"
    spec.write_text("# STORY-033\nNo inputs.\n")

    message, code = hook_entry(
        _bash_payload(
            root,
            "pactkit spec-preflight docs/specs/STORY-033.md --activate",
        ),
        root,
    )
    assert (message, code) == ("", 0)
    run_spec_preflight(root, spec)  # Bash command executes after PreToolUse
    assert hook_entry(_payload(root), root) == ("", 0)


def test_docs_and_pactkit_state_are_never_blocked(tmp_path):
    root = _root(tmp_path, "enforce")
    assert hook_entry(_payload(root, path="docs/specs/STORY-033.md"), root)[1] == 0
    assert hook_entry(_payload(root, path=".pactkit/recovery.json"), root)[1] == 0


def test_hook_install_preserves_existing_settings_and_is_idempotent(tmp_path):
    root = _root(tmp_path, "warn")
    settings_path = root / ".claude" / "settings.json"
    settings_path.write_text(json.dumps({"model": "opus"}))

    install_preflight_hook(root)
    install_preflight_hook(root)

    settings = json.loads(settings_path.read_text())
    assert settings["model"] == "opus"
    entries = settings["hooks"]["PreToolUse"]
    commands = [h["command"] for e in entries for h in e["hooks"]]
    assert commands.count("pactkit preflight-guard --hook") == 1


def test_classic_gate_channel_installs_both_hooks(tmp_path):
    from pactkit.commit_gate import ensure_gate_channel

    root = _root(tmp_path, "warn")
    (root / ".git").mkdir()
    ensure_gate_channel(root, "classic")

    settings = json.loads((root / ".claude" / "settings.json").read_text())
    commands = [
        hook["command"]
        for entry in settings["hooks"]["PreToolUse"]
        for hook in entry["hooks"]
    ]
    assert "pactkit commit-gate --hook" in commands
    assert "pactkit preflight-guard --hook" in commands


def test_preflight_mode_validation():
    import pytest

    from pactkit.config import validate_config

    with pytest.warns(UserWarning, match="preflight.mode"):
        validate_config({"preflight": {"mode": "always-block"}})
