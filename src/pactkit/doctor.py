"""Project health diagnostics — deterministic doctor checks (STORY-slim-015 R1-R3).

Replaces prompt-based diagnostics from SKILL_DOCTOR_MD.
"""
from __future__ import annotations

import re
from pathlib import Path

# Pattern to extract item IDs from filenames and board text
_ITEM_ID_RE = re.compile(r"((?:STORY|BUG|HOTFIX)(?:-[\w]+)?-\d+)")


def check_orphaned_specs(project_root: Path) -> dict:
    """Cross-reference specs dir vs board + archive.

    Returns:
        {"orphaned": [{"id": ...}], "missing": [{"id": ...}]}
    """
    specs_dir = project_root / "docs" / "specs"
    board_path = project_root / "docs" / "product" / "sprint_board.md"
    archive_dir = project_root / "docs" / "product" / "archive"

    # Collect spec IDs from filenames
    spec_ids: set[str] = set()
    if specs_dir.is_dir():
        for f in specs_dir.iterdir():
            if f.suffix == ".md":
                m = _ITEM_ID_RE.match(f.stem)
                if m:
                    spec_ids.add(m.group(1))

    # Collect board IDs
    board_ids: set[str] = set()
    if board_path.exists():
        board_text = board_path.read_text(encoding="utf-8")
        board_ids.update(_ITEM_ID_RE.findall(board_text))

    # Collect archive IDs
    archive_ids: set[str] = set()
    if archive_dir.is_dir():
        for f in archive_dir.iterdir():
            if f.suffix == ".md":
                archive_ids.update(_ITEM_ID_RE.findall(f.read_text(encoding="utf-8")))

    all_referenced = board_ids | archive_ids

    orphaned = [{"id": sid} for sid in sorted(spec_ids - all_referenced)]
    missing = [{"id": bid} for bid in sorted(all_referenced - spec_ids)
               if _ITEM_ID_RE.match(bid)]

    return {"orphaned": orphaned, "missing": missing}


def check_config_drift(project_root: Path) -> dict:
    """Compare pactkit.yaml declared items vs deployed files.

    Only checks deployment drift when the yaml explicitly declares
    component lists (agents, commands, skills, rules). Default behavior
    (no lists) means "deploy all from VALID_* sets" — no drift possible.

    Returns:
        {"missing_deployments": [{"type": ..., "name": ...}]}
    """
    import yaml

    from pactkit.config import find_pactkit_yaml

    yaml_path = find_pactkit_yaml(project_root)
    if yaml_path is None:
        return {"missing_deployments": [], "error": "pactkit.yaml not found"}

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config_dir = yaml_path.parent  # .claude/ or .opencode/ or .codex/
    missing: list[dict] = []

    # Detect format from yaml path to get format-level excluded commands
    _format_excluded_commands: frozenset = frozenset()
    try:
        from pactkit.profiles import FORMAT_PROFILES
        dir_name = config_dir.name  # e.g. ".claude", ".opencode", ".codex"
        for prof in FORMAT_PROFILES.values():
            if prof.project_config_dir == dir_name:
                _format_excluded_commands = prof.excluded_commands
                break
    except Exception:
        pass

    # Files are deployed globally (e.g., ~/.claude/, ~/.config/opencode/, ~/.codex/),
    # not per-project. Check all known global deploy directories + project-local.
    home = Path.home()
    search_dirs = [
        home / ".claude",
        home / ".config" / "opencode",
        home / ".codex",
        config_dir,  # project-local as fallback
    ]

    def _exists_in_any(subdir: str, filename: str) -> bool:
        for base in search_dirs:
            if (base / subdir / filename).exists():
                return True
        return False

    def _dir_or_file_in_any(subdir: str, name: str) -> bool:
        for base in search_dirs:
            if (base / subdir / name).is_dir() or (base / subdir / f"{name}.md").exists():
                return True
        return False

    # Only check drift for explicitly declared lists.
    # If the key is absent, it means "deploy all" — no drift to check.
    _CHECKS = [
        ("agents", "agents", ".md"),
        ("commands", "commands", ".md"),
        ("rules", "rules", ".md"),
    ]
    for key, subdir, suffix in _CHECKS:
        declared = data.get(key)
        if not isinstance(declared, list):
            continue
        for item in declared:
            # Skip format-level excluded commands (e.g., project-sprint for opencode/codex)
            if key == "commands" and item in _format_excluded_commands:
                continue
            if not _exists_in_any(subdir, f"{item}{suffix}"):
                missing.append({"type": key.rstrip("s"), "name": item})

    # Skills: check as directory or .md file
    declared_skills = data.get("skills")
    if isinstance(declared_skills, list):
        for skill in declared_skills:
            # Skip format-level excluded commands deployed as skills
            if skill in _format_excluded_commands:
                continue
            if not _dir_or_file_in_any("skills", skill):
                missing.append({"type": "skill", "name": skill})

    return {"missing_deployments": missing}


def check_stale_graphs(
    project_root: Path,
    threshold_days: int = 7,
) -> dict:
    """Compare graph mtimes vs newest source file.

    Returns:
        {"stale": [{"file": ..., "days_behind": ...}], "missing": bool}
    """
    graph_dir = project_root / "docs" / "architecture" / "graphs"

    if not graph_dir.is_dir():
        return {"stale": [], "missing": True}

    # Find newest source file mtime
    source_dirs = ["src/"]  # Default Python
    try:
        from pactkit.config import load_config
        from pactkit.prompts.workflows import LANG_PROFILES

        cfg = load_config(project_root)
        stack = cfg.get("stack", "python")
        profile = LANG_PROFILES.get(stack, LANG_PROFILES.get("python", {}))
        source_dirs = profile.get("source_dirs", ["src/"])
    except Exception:
        pass

    newest_source_mtime = 0.0
    for sd in source_dirs:
        src_path = project_root / sd
        if src_path.is_dir():
            for f in src_path.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    newest_source_mtime = max(newest_source_mtime, f.stat().st_mtime)

    if newest_source_mtime == 0.0:
        return {"stale": [], "missing": False}

    threshold_seconds = threshold_days * 86400
    stale: list[dict] = []

    for graph in graph_dir.glob("*.mmd"):
        graph_mtime = graph.stat().st_mtime
        age_diff = newest_source_mtime - graph_mtime
        if age_diff > threshold_seconds:
            days_behind = int(age_diff / 86400)
            stale.append({"file": graph.name, "days_behind": days_behind})

    return {"stale": stale, "missing": False}


def check_hld_module_count(project_root: Path) -> dict:
    """Compare module count in system_design.mmd vs actual source files.

    Returns:
        {"source_modules": N, "hld_nodes": M, "drift": N - M}
    """
    hld_path = project_root / "docs" / "architecture" / "graphs" / "system_design.mmd"

    # Count actual .py modules (excluding __init__.py, __pycache__)
    src_dir = project_root / "src" / "pactkit"
    source_modules = 0
    if src_dir.is_dir():
        for f in src_dir.iterdir():
            if (f.suffix == ".py"
                    and f.name != "__init__.py"
                    and not f.name.startswith("__")):
                source_modules += 1

    # Count node declarations in system_design.mmd
    hld_nodes = 0
    if hld_path.exists():
        hld_text = hld_path.read_text(encoding="utf-8")
        # Count Mermaid node declarations: Identifier["label"]
        hld_nodes = len(re.findall(r'\w+\["[^"]+"\]', hld_text))

    return {
        "source_modules": source_modules,
        "hld_nodes": hld_nodes,
        "drift": source_modules - hld_nodes,
    }


# Deployment roots probed for .pactkit-deployed.json (STORY-slim-139 R3).
# {home} / {root} are substituted at scan time.
DEPLOY_PROBE_PATHS = (
    "{home}/.claude",
    "{home}/.codex",
    "{home}/.config/opencode",
    "{root}/.claude",
    "{root}/.github",
    "{root}/.codex",
    "{root}/.opencode",
)


def check_deploy_parity(project_root: Path) -> dict:
    """Compare per-format deployment manifests against the current registry.

    Returns {"drift": bool, "details": [str], "warnings": [str]}.
    Missing manifest on a deployed-looking directory -> warning (pre-2.17
    deploy), not drift. Corrupt JSON degrades to a warning (SEC-2/SEC-7).
    Profile capability exclusions (e.g. project-sprint off Claude) never
    count as drift (R5).
    """
    import json

    from pactkit.deploy_manifest import MANIFEST_NAME, expected_components

    details: list[str] = []
    warnings: list[str] = []
    seen_formats: set[str] = set()

    for template in DEPLOY_PROBE_PATHS:
        probe = Path(
            template.replace("{home}", str(Path.home())).replace("{root}", str(project_root))
        )
        manifest = probe / MANIFEST_NAME
        if not manifest.exists():
            # A directory that looks deployed but has no manifest = old version
            if probe.is_dir() and (probe / "skills").is_dir():
                warnings.append(f"{probe}: no deployment manifest — re-run `pactkit update`")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            warnings.append(f"{manifest}: unreadable ({exc}) — re-run `pactkit update`")
            continue

        fmt = data.get("format", "")
        if not fmt or fmt in seen_formats:
            continue
        seen_formats.add(fmt)

        expected = expected_components(fmt)
        for kind in ("skills", "commands", "agents"):
            deployed = set(data.get(kind, []))
            missing = sorted(set(expected[kind]) - deployed)
            for item in missing:
                details.append(
                    f"Deployed drift: {fmt} missing {kind[:-1]} '{item}' — upgrade adapter / re-run `pactkit update`"
                )

    return {"drift": bool(details), "details": details, "warnings": warnings}
