import subprocess
import sys

import pytest

from pactkit.project_root import ProjectRootNotFound, resolve_project_root


def test_resolves_nearest_initialized_ancestor(tmp_path):
    outer = tmp_path / "outer"
    inner = outer / "packages" / "app"
    (outer / ".claude").mkdir(parents=True)
    (outer / ".claude" / "pactkit.yaml").write_text("stack: python\n")
    inner.mkdir(parents=True)

    assert resolve_project_root(inner) == outer.resolve()


def test_nearest_nested_project_wins(tmp_path):
    outer = tmp_path / "outer"
    inner = outer / "packages" / "app"
    for root in (outer, inner):
        (root / ".codex").mkdir(parents=True)
        (root / ".codex" / "pactkit.yaml").write_text("stack: python\n")

    assert resolve_project_root(inner / "src") == inner.resolve()


def test_explicit_root_must_be_initialized(tmp_path):
    with pytest.raises(ProjectRootNotFound, match="not an initialized PactKit project"):
        resolve_project_root(tmp_path, explicit=tmp_path)


def test_missing_root_fails_without_creating_state(tmp_path):
    child = tmp_path / "unrelated" / "src"
    child.mkdir(parents=True)

    with pytest.raises(ProjectRootNotFound, match="project root not found"):
        resolve_project_root(child)

    assert not (child / ".pactkit").exists()


def test_single_legacy_governance_marker_identifies_a_partial_project(tmp_path):
    (tmp_path / "docs" / "specs").mkdir(parents=True)

    assert resolve_project_root(tmp_path / "docs" / "specs") == tmp_path.resolve()


def test_find_pactkit_yaml_searches_parents(tmp_path):
    from pactkit.config import find_pactkit_yaml

    root = tmp_path / "project"
    child = root / "frontend" / "src"
    (root / ".claude").mkdir(parents=True)
    config = root / ".claude" / "pactkit.yaml"
    config.write_text("stack: node\n")
    child.mkdir(parents=True)

    assert find_pactkit_yaml(child) == config


def test_context_cli_from_subdirectory_writes_only_at_project_root(tmp_path):
    root = tmp_path / "project"
    child = root / "frontend" / "src"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "pactkit.yaml").write_text("stack: node\n")
    (root / "docs" / "product" / "stories").mkdir(parents=True)
    (root / "docs" / "product" / "sprint_board.md").write_text("# Board\n")
    child.mkdir(parents=True)

    result = subprocess.run(
        [sys.executable, "-m", "pactkit.cli", "context"],
        cwd=child, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (root / ".pactkit" / "context.md").is_file()
    assert not (child / ".pactkit").exists()


def test_context_cli_outside_project_fails_without_creating_state(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "pactkit.cli", "context"],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 2
    assert "project root not found" in result.stderr.lower()
    assert not (tmp_path / ".pactkit").exists()


def test_workflow_start_outside_project_fails_without_creating_state(tmp_path):
    result = subprocess.run(
        [
            sys.executable, "-m", "pactkit.cli", "workflow", "start",
            "project-plan", "--evidence", '{"guard":"pass","input_fingerprint":"x"}',
        ],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 2
    assert not (tmp_path / ".pactkit").exists()


def test_global_project_root_option_works_from_unrelated_directory(tmp_path):
    root = tmp_path / "project"
    elsewhere = tmp_path / "elsewhere"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "pactkit.yaml").write_text("stack: python\n")
    (root / "docs" / "product" / "stories").mkdir(parents=True)
    (root / "docs" / "product" / "sprint_board.md").write_text("# Board\n")
    elsewhere.mkdir()

    result = subprocess.run(
        [sys.executable, "-m", "pactkit.cli", "-C", str(root), "context"],
        cwd=elsewhere, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (root / ".pactkit" / "context.md").is_file()
    assert not (elsewhere / ".pactkit").exists()


def test_update_from_subdirectory_passes_canonical_root_to_deployer(tmp_path, monkeypatch):
    from unittest.mock import patch

    from pactkit.cli import main

    root = tmp_path / "project"
    child = root / "frontend" / "src"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "pactkit.yaml").write_text("stack: python\n")
    child.mkdir(parents=True)
    monkeypatch.chdir(child)

    with (
        patch("sys.argv", ["pactkit", "update", "--format", "classic", "--no-git"]),
        patch("pactkit.generators.deployer.deploy") as deploy,
        patch("pactkit.config.sync_config_copies", return_value=[]),
        patch("pactkit.commit_gate.ensure_gate_channel", return_value="none") as gate,
        patch("pactkit.deps.check_deps", return_value=[]),
    ):
        main()

    assert deploy.call_args.kwargs["project_root"] == root.resolve()
    gate.assert_called_once_with(root.resolve(), "classic")
