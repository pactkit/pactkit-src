"""Project health diagnostics — deterministic doctor checks (STORY-slim-015 R1-R3).

Replaces prompt-based diagnostics from SKILL_DOCTOR_MD.
"""
from __future__ import annotations

import re
from pathlib import Path

from pactkit.id_generator import ITEM_ID_RE
from pactkit.schemas import ITEM_ID_PATTERN
from pactkit.workflow_engine import WorkflowEngine, WorkUnitError, _validate_workflow_state

_EXECUTION_MODE_RANK = {
    "portable": 0, "guided": 1, "resumable": 2, "managed": 3,
}


def resolve_rule_context(
    command: str,
    *,
    active_phase: str | None = None,
    selected_guides: tuple[str, ...] = (),
    host_format: str | None = None,
) -> dict:
    """Return a deterministic, read-only explanation of active rule semantics."""
    from pactkit.prompts.guides import GUIDE_DEFINITIONS
    from pactkit.prompts.rules import (
        COMMAND_CONDITIONAL_RULES_MAP,
        COMMAND_RULES_MAP,
        RULE_CLAUSES,
        RULE_DEFINITIONS,
        SPRINT_PHASE_SEQUENCE,
    )

    requested = tuple(COMMAND_RULES_MAP.get(command, ()))
    conditional_ids = tuple(COMMAND_CONDITIONAL_RULES_MAP.get(command, ()))
    loaded: list[dict] = []
    skipped: list[dict] = []
    warnings: list[str] = []
    for rule_id, definition in RULE_DEFINITIONS.items():
        record = {
            "id": rule_id,
            "level": definition.level,
            "trigger": definition.trigger,
            "evidence": list(definition.evidence),
        }
        if rule_id in requested:
            record["reason"] = "declared by active command"
            loaded.append(record)
        elif rule_id in conditional_ids:
            record["reason"] = "available only when its command trigger matches"
            record["load_policy"] = "conditional"
            skipped.append(record)
        else:
            record["reason"] = "not declared by active command"
            skipped.append(record)
        if (
            "active instruction artifact" in " ".join(definition.evidence)
            or definition.trigger == "when referenced by the active PactKit skill"
        ):
            warnings.append(f"generic rule metadata: {rule_id}")
        if definition.level == "hard" and definition.failure != "block_exact_action":
            warnings.append(f"illegal hard blocker: {rule_id}")

    phase = active_phase
    if phase is None and command != "project-sprint":
        phase = next(
            (rule.removeprefix("phase-") for rule in requested if rule.startswith("phase-")),
            None,
        )
    leaked = sorted(set(requested) & set(SPRINT_PHASE_SEQUENCE))
    if command == "project-sprint" and leaked:
        warnings.append("Sprint statically loads phase capsules: " + ", ".join(leaked))

    guides = []
    for filename in selected_guides:
        definition = GUIDE_DEFINITIONS.get(filename)
        if definition is None:
            warnings.append(f"unknown guide: {filename}")
            continue
        guides.append({
            "id": filename,
            "reason": definition.trigger,
            "evidence": list(definition.evidence),
        })
    if len(guides) > 3:
        warnings.append("more than three engineering guides selected")
    if host_format == "codex":
        for rule_id in requested:
            definition = RULE_DEFINITIONS.get(rule_id)
            if definition and "@~/.codex/" in definition.content:
                warnings.append(f"Codex Markdown @file dependency: {rule_id}")

    precedence = (
        "platform safety > latest user instruction > project Spec > phase "
        "contract > risk guide defaults"
    )
    return {
        "command": command,
        "active_phase": phase,
        "loaded": loaded,
        "skipped": skipped,
        "conditional_candidates": list(conditional_ids),
        "clauses": {
            clause_id: {
                "level": clause.level,
                "failure": clause.failure,
                "trigger": clause.trigger,
                "skip_when": list(clause.skip_when),
                "evidence": list(clause.evidence),
            }
            for clause_id, clause in RULE_CLAUSES.items()
        },
        "guides": guides,
        "precedence": precedence,
        "warnings": warnings,
    }


def _project_host_guarantees(
    project_root: Path, warnings: list[str], *, home: Path | None = None,
) -> dict[str, str]:
    """Read installed host guarantees and never report more than either claim.

    Deployment manifests are diagnostic inputs, not Core workflow authority.
    Still, doctor must not turn a portable host into a guided one simply
    because its legacy default is stronger than the installed contract.
    """
    import json

    roots = {
        "classic": project_root / ".claude",
        "opencode": project_root / ".opencode",
        "codex": project_root / ".codex",
        "copilot": project_root / ".github",
    }
    global_codex = (home or Path.home()) / ".codex"
    if not (roots["codex"] / ".pactkit-deployed.json").is_file():
        roots["codex"] = global_codex
    guarantees: dict[str, str] = {}
    for expected_format, root in roots.items():
        path = root / ".pactkit-deployed.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
            host = payload.get("host_capabilities")
            workflow = payload.get("workflow_continuation")
            if (
                payload.get("format") != expected_format
                or not isinstance(host, dict)
                or not isinstance(workflow, dict)
            ):
                raise ValueError
            host_mode = host.get("execution_mode")
            workflow_mode = workflow.get("guarantee_level")
            if host_mode not in _EXECUTION_MODE_RANK or workflow_mode not in _EXECUTION_MODE_RANK:
                raise ValueError
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            try:
                display_path = str(path.relative_to(project_root))
            except ValueError:
                display_path = str(path)
            warnings.append(f"corrupt host capability manifest: {display_path}")
            # The host is installed but its capability evidence is unusable.
            # Retain it at the lowest supported level so a corrupt manifest
            # cannot make doctor report the stronger no-manifest default.
            guarantees[expected_format] = "portable"
            continue
        guarantees[expected_format] = min(
            (host_mode, workflow_mode), key=_EXECUTION_MODE_RANK.__getitem__,
        )
    return guarantees


def check_legacy_engine_usage() -> dict:
    """Usage surfacing for the frozen legacy engine (deletion decision).

    Machine-local counter, read-only; absent counter returns zeroed
    usage (STORY-slim-20260826cb37edfdd4da R3/R4).
    """
    from pactkit.legacy.usage import read_legacy_usage

    usage = read_legacy_usage()
    return {
        "total": sum(int(entry.get("count", 0)) for entry in usage.values()),
        "per_command": {
            command: int(entry.get("count", 0))
            for command, entry in sorted(usage.items())
        },
        "last_seen": max(
            (entry.get("last_seen", "") for entry in usage.values()),
            default="",
        ),
    }


def check_workflow_continuation(
    project_root: Path, *, home: Path | None = None,
) -> dict:
    """Report active runs, host guarantee level, and unsafe host state."""
    import json
    from datetime import datetime, timezone

    runs_dir = project_root / ".pactkit" / "continuations" / "runs"
    hosts_dir = project_root / ".pactkit" / "continuations" / "hosts"
    active: list[dict] = []
    work_unit_runs: list[dict] = []
    warnings: list[str] = []
    run_paths = sorted(runs_dir.glob("run-*.json")) if runs_dir.is_dir() else []
    for path in run_paths:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"corrupt workflow state: {path.name}")
            continue
        if not isinstance(state, dict):
            warnings.append(f"corrupt workflow state: {path.name}")
            continue
        if state.get("status") == "in_progress":
            active.append({
                "run_id": state.get("run_id"), "workflow_id": state.get("workflow_id"),
                "step_id": state.get("step_id"),
            })
        host = state.get("host_continuation")
        # Host-continuation metadata predates WorkUnits and is advisory only.
        # A completed Core workflow is authoritative; historical Stop-hook
        # retries must not make doctor report an active hook failure.
        if isinstance(host, dict) and state.get("status") != "completed":
            _append_host_warnings(host, path.name, warnings)
    now = datetime.now(timezone.utc)
    host_paths = sorted(hosts_dir.glob("run-*.json")) if hosts_dir.is_dir() else []
    for path in host_paths:
        try:
            host = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"corrupt host lease: {path.name}")
            continue
        if not isinstance(host, dict):
            warnings.append(f"corrupt host lease: {path.name}")
            continue
        _append_host_warnings(host, path.name, warnings, now=now)
    unit_dir = project_root / ".pactkit" / "workflow-runs"
    for path in sorted(unit_dir.glob("run-*.json")) if unit_dir.is_dir() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            # WorkUnit files are recovery inputs.  Doctor must not report a
            # syntactically valid but semantically damaged run as healthy.
            _validate_workflow_state(state)
            if state["run_id"] != path.stem:
                raise WorkUnitError("invalid_workflow_state")
            WorkflowEngine(project_root)._validate_completed_finalize_journal(state)
        except (OSError, json.JSONDecodeError, WorkUnitError):
            warnings.append(f"corrupt WorkUnit state: {path.name}")
            continue
        work_unit_runs.append({
            "run_id": state.get("run_id"), "workflow_id": state.get("workflow_id"),
            "status": state.get("status"), "current_index": state.get("current_index"),
        })
    host_guarantees = _project_host_guarantees(project_root, warnings, home=home)
    # The summary describes the strongest installed capability, while
    # host_guarantees preserves every host explicitly.  With no deployment
    # evidence, default to the portable current-session model; doctor must
    # never invent a guided continuation service.
    guarantee_level = (
        max(host_guarantees.values(), key=_EXECUTION_MODE_RANK.__getitem__)
        if host_guarantees else "portable"
    )
    return {
        "finish_guard_supported": False, "auto_resume_available": False,
        "guarantee_level": guarantee_level, "host_guarantees": host_guarantees,
        "stop_hook_required": False,
        "active": active, "work_unit_runs": work_unit_runs, "warnings": warnings,
    }


def _append_host_warnings(
    host: dict, fallback: str, warnings: list[str], *, now=None,
) -> None:
    from datetime import datetime, timezone

    now = now or datetime.now(timezone.utc)
    expiry_raw = host.get("lease_expires_at")
    if expiry_raw is None:
        expiry = None
    else:
        try:
            expiry = datetime.fromisoformat(expiry_raw)
        except (TypeError, ValueError):
            warnings.append(f"corrupt host lease: {fallback}")
            return
    attempt = host.get("attempt")
    if attempt is not None and (not isinstance(attempt, int) or attempt < 0):
        warnings.append(f"corrupt host lease: {fallback}")
        return
    run_id = host.get("run_id", fallback)
    if expiry is not None and expiry <= now:
        warnings.append(f"stale host lease: {run_id}")
    if host.get("termination_reason") in {"no_progress", "attempt_limit"}:
        warnings.append(f"workflow {run_id} stopped: {host['termination_reason']}")


def check_orphaned_specs(project_root: Path) -> dict:
    """Cross-reference specs dir vs board + archive.

    Returns:
        {"orphaned": [{"id": ...}], "missing": [{"id": ...}]}
    """
    specs_dir = project_root / "docs" / "specs"
    records_dir = project_root / "docs" / "product" / "stories"
    board_path = project_root / "docs" / "product" / "sprint_board.md"
    archive_dir = project_root / "docs" / "product" / "archive"

    # Collect spec IDs from filenames
    spec_ids: set[str] = set()
    if specs_dir.is_dir():
        for f in specs_dir.iterdir():
            if f.suffix == ".md":
                if ITEM_ID_RE.fullmatch(f.stem):
                    spec_ids.add(f.stem)

    # Collect board IDs
    board_ids: set[str] = set()
    if records_dir.is_dir():
        from pactkit.governance import StoryRepository

        board_ids.update(record["id"] for record in StoryRepository(project_root).list())
    elif board_path.exists():
        board_text = board_path.read_text(encoding="utf-8")
        board_ids.update(re.findall(ITEM_ID_PATTERN, board_text))

    # Collect archive IDs
    archive_ids: set[str] = set()
    if archive_dir.is_dir():
        for f in archive_dir.iterdir():
            if f.suffix == ".md":
                archive_ids.update(re.findall(ITEM_ID_PATTERN, f.read_text(encoding="utf-8")))

    all_referenced = board_ids | archive_ids

    orphaned = [{"id": sid} for sid in sorted(spec_ids - all_referenced)]
    missing = [{"id": bid} for bid in sorted(all_referenced - spec_ids) if ITEM_ID_RE.fullmatch(bid)]

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


def check_graph_provider(project_root: Path) -> dict:
    """Return read-only diagnostics for the configured graph provider."""
    from pactkit.config import find_pactkit_yaml, load_config

    config_path = find_pactkit_yaml(project_root)
    config = load_config(config_path) if config_path else {}
    configured = config.get("visualize", {}).get("graph_provider")
    if configured != "codegraph":
        return {
            "configured": configured, "selected": "builtin_graph",
            "available": True, "fresh": True, "warnings": [],
        }
    from pactkit.graph_query import CodegraphProvider

    health = CodegraphProvider(project_root).health()
    return {"configured": configured, "selected": "codegraph", **health}


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
        from pactkit.config import find_pactkit_yaml, load_config
        from pactkit.prompts.workflows import LANG_PROFILES

        # load_config takes a file path — passing the project root directory
        # raised IsAdirectoryError that the except below silently swallowed
        # (STORY-slim-20260826ce35b77ce005 R3).
        config_path = find_pactkit_yaml(project_root) or project_root / ".claude" / "pactkit.yaml"
        if not config_path.is_file():
            print(f"  ⚠️  pactkit.yaml not found at {config_path} — defaulting source dirs to src/")
        cfg = load_config(config_path)
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

_RULE_CONFLICT_SIGNALS = {
    "unscoped STOP": re.compile(r"\bSTOP\b"),
    "forced session split": re.compile(
        r"(?:must|requires?|required(?:\s+to)?|必须).{0,24}"
        r"(?:new|separate|新).{0,12}session",
        re.IGNORECASE,
    ),
    "retired workflow protocol": re.compile(
        r"WorkUnit|EvidenceReceipt|codex runner|--owner codex", re.IGNORECASE,
    ),
}
_OPTIONAL_SESSION_SIGNAL = re.compile(
    r"(?:do\s+not|not|never|无需|不必|不需要).{0,80}"
    r"(?:require|required|must|必须)?.{0,16}(?:new|separate|新).{0,12}session"
    r"|(?:new|separate|新).{0,12}session.{0,16}(?:optional|可选)",
    re.IGNORECASE,
)


def check_rule_ownership(project_root: Path, *, home: Path | None = None) -> dict:
    """Classify deployed and local rules without modifying any file.

    Manifest hashes are the sole evidence of PactKit ownership. Untracked rule
    files under a project are project-owned; untracked files under host config
    roots are user-owned. Potential conflicts are advisory lexical signals, not
    policy failures, and never affect the doctor's exit status.
    """
    import json

    project_root = Path(project_root).resolve()
    home = Path(home or Path.home()).resolve()
    candidates = [
        ("classic", home / ".claude", "user"),
        ("codex", home / ".codex", "user"),
        ("opencode", home / ".config" / "opencode", "user"),
        ("classic", project_root / ".claude", "project"),
        ("codex", project_root / ".codex", "project"),
        ("opencode", project_root / ".opencode", "project"),
        ("copilot", project_root / ".github", "project"),
    ]
    result = {
        "pactkit_owned": [], "project_owned": [], "user_owned": [],
        "conflicts": [], "potential_conflicts": [], "warnings": [],
    }
    seen: set[Path] = set()
    for expected_format, root, local_owner in candidates:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        if resolved in seen or not root.is_dir():
            continue
        seen.add(resolved)

        managed: set[str] = set()
        manifest = root / ".pactkit-deployed.json"
        if manifest.is_file():
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("top-level JSON must be an object")
                if payload.get("format") not in (None, expected_format):
                    raise ValueError("format does not match deployment root")
                files = payload.get("files", {})
                rules = payload.get("rules", [])
                if not isinstance(files, dict) or not isinstance(rules, list):
                    raise ValueError("ownership fields are invalid")
                managed.update(
                    path for path in files
                    if isinstance(path, str) and (
                        path.startswith("rules/")
                        or path.startswith("skills/_rules/")
                        or (
                            path.startswith("skills/project-")
                            and "/references/rules/" in path
                        )
                        or (
                            path.startswith("skills/project-act/references/guides/")
                        )
                    )
                )
                managed.update(
                    item["path"] for item in rules
                    if isinstance(item, dict) and isinstance(item.get("path"), str)
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                result["warnings"].append(f"{manifest}: unreadable ownership ({exc})")

        rule_files = []
        for directory in (root / "rules", root / "skills" / "_rules"):
            if directory.is_dir():
                rule_files.extend(directory.rglob("*.md"))
        skills_root = root / "skills"
        if skills_root.is_dir():
            rule_files.extend(skills_root.glob("project-*/references/rules/*.md"))
            rule_files.extend(
                skills_root.glob("project-act/references/guides/*.md")
            )
        for path in sorted(set(rule_files)):
            relative = path.relative_to(root).as_posix()
            record = {
                "format": expected_format, "root": str(root),
                "path": relative, "owner": "pactkit" if relative in managed else local_owner,
            }
            result[f"{record['owner']}_owned"].append(record)
            candidate = path.with_suffix(path.suffix + ".pactkit-new")
            if candidate.is_file():
                result["conflicts"].append({
                    **record, "candidate": candidate.relative_to(root).as_posix(),
                })
            if record["owner"] != "pactkit":
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError as exc:
                    result["warnings"].append(f"{path}: unreadable ({exc})")
                    continue
                for line_number, line in enumerate(content.splitlines(), 1):
                    for signal, pattern in _RULE_CONFLICT_SIGNALS.items():
                        if (
                            signal == "forced session split"
                            and _OPTIONAL_SESSION_SIGNAL.search(line)
                        ):
                            continue
                        if pattern.search(line):
                            result["potential_conflicts"].append({
                                **record, "line": line_number, "signal": signal,
                            })
    return result


def check_codex_execution_capability(codex_root: Path | None = None) -> dict:
    """Read the deployed Codex current-session execution capability.

    Codex's public PactKit adapter no longer installs a runner or a Stop hook.
    This deliberately reports only capabilities that the installed manifest
    proves, so doctor cannot imply a background workflow or a session resume
    service exists.
    """
    import json

    root = codex_root or Path.home() / ".codex"
    manifest = root / ".pactkit-deployed.json"
    default = {
        "execution_mode": "portable",
        "session_execution": "native_current_session",
        "background_execution": False,
        "thread_resume": False,
        "finish_guard_supported": False,
        "guarantee_level": "portable",
        "warnings": [],
    }
    if not manifest.is_file():
        return default
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        capability = payload.get("workflow_continuation", {})
    except (OSError, json.JSONDecodeError, ValueError):
        return {**default, "warnings": ["Codex execution manifest unreadable — re-run `pactkit update`"]}
    if not isinstance(capability, dict):
        return {**default, "warnings": ["Codex execution capability is corrupt — re-run `pactkit update`"]}

    # The public Codex adapter no longer owns a runner, lifecycle hook, or
    # session-reentry service.  Old manifests must not resurrect those removed
    # capabilities in doctor output.  Keep the diagnostic non-blocking and
    # report the current public contract unconditionally.
    legacy_values = {
        "execution_mode": capability.get("execution_mode"),
        "session_execution": capability.get("session_execution"),
        "finish_guard_supported": capability.get("finish_guard_supported"),
        "guarantee_level": capability.get("guarantee_level"),
    }
    expected = {
        "execution_mode": "portable",
        "session_execution": "native_current_session",
        "finish_guard_supported": False,
        "guarantee_level": "portable",
    }
    warnings = []
    if any(value is not None and value != expected[name] for name, value in legacy_values.items()):
        warnings.append(
            "Codex execution manifest describes retired runner capabilities; "
            "using native current-session execution"
        )
    return {
        **expected,
        "background_execution": False,
        "thread_resume": False,
        "warnings": warnings,
    }


def check_codex_hook_capability(codex_root: Path | None = None) -> dict:
    """Deprecated compatibility view for callers from pre-runner releases.

    New code must use :func:`check_codex_execution_capability`.  The old hook
    fields are deliberately always false because PactKit no longer owns a
    Codex hook lifecycle.
    """
    execution = check_codex_execution_capability(codex_root)
    return {
        "installed": False,
        "trusted": False,
        "observed": False,
        "validated": False,
        "guarantee_level": execution["guarantee_level"],
        "warnings": execution["warnings"],
    }


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
        if not isinstance(data, dict):
            warnings.append(
                f"{manifest}: unreadable (top-level JSON must be an object) — "
                "re-run `pactkit update`"
            )
            continue

        fmt = data.get("format", "")
        if not fmt or fmt in seen_formats:
            continue
        seen_formats.add(fmt)

        scope = data.get("component_scope", "default")
        if scope not in ("default", "selective"):
            warnings.append(
                f"{manifest}: unknown component_scope — assuming default deployment"
            )
            scope = "default"
        expected = expected_components(fmt) if scope == "default" else {
            kind: data.get(kind) for kind in ("skills", "commands", "agents")
        }
        for kind in ("skills", "commands", "agents"):
            deployed_items = data.get(kind, [])
            if not isinstance(deployed_items, list) or not isinstance(expected[kind], list):
                warnings.append(
                    f"{manifest}: component list '{kind}' corrupt — re-run `pactkit update`"
                )
                continue
            deployed = set(deployed_items)
            missing = sorted(set(expected[kind]) - deployed)
            for item in missing:
                details.append(
                    f"Deployed drift: {fmt} missing {kind[:-1]} '{item}' — upgrade adapter / re-run `pactkit update`"
                )

        # Selective manifests declare an intentional component subset. The
        # declaration is not proof that its artifacts were written: derive
        # each selected component's canonical file and require both on-disk
        # presence and a content-hash entry below.
        declared_paths: set[str] = set()
        if scope == "selective":
            skills = data.get("skills", [])
            commands = data.get("commands", [])
            agents = data.get("agents", [])
            # The list validation above is deliberately non-fatal. Do not
            # subsequently iterate a corrupt scalar/string as a component
            # declaration and manufacture false content drift.
            skills = skills if isinstance(skills, list) else []
            commands = commands if isinstance(commands, list) else []
            agents = agents if isinstance(agents, list) else []
            for name in skills:
                if isinstance(name, str):
                    declared_paths.add(f"skills/{name}/SKILL.md")
            for name in commands:
                if not isinstance(name, str):
                    continue
                if fmt == "copilot":
                    declared_paths.add(f"prompts/{name}.prompt.md")
                else:
                    declared_paths.add(f"skills/{name}/SKILL.md")
            for name in agents:
                if isinstance(name, str):
                    declared_paths.add(f"agents/{name}.md")

        # STORY-slim-141 R2: content-level verification via per-file hashes.
        from pactkit.deploy_manifest import sha256_file

        files = data.get("files")
        if files is None:
            # R3: pre-2.18 manifest — degrade to a hint, never drift.
            warnings.append(
                f"{probe}: manifest predates content hashing — re-run `pactkit update` to enable content verification"
            )
        elif not isinstance(files, dict):
            # SEC-7: corrupt files field degrades to warning, never crashes.
            warnings.append(f"{probe}: manifest 'files' field corrupt (not a mapping) — re-run `pactkit update`")
        else:
            for rel in sorted(declared_paths):
                if not (probe / rel).is_file():
                    details.append(
                        f"Content drift: {fmt} '{rel}' missing on disk — re-run `pactkit update`"
                    )
                elif rel not in files:
                    details.append(
                        f"Content drift: {fmt} '{rel}' missing from manifest — re-run `pactkit update`"
                    )
            for rel, expected_hash in files.items():
                path = probe / rel
                if not path.is_file():
                    details.append(f"Content drift: {fmt} '{rel}' missing on disk — re-run `pactkit update`")
                    continue
                try:
                    actual = sha256_file(path)
                except OSError:
                    # SEC-7: unreadable file degrades to warning, never crashes.
                    warnings.append(f"{probe}: '{rel}' unreadable — check permissions")
                    continue
                if actual != expected_hash:
                    details.append(f"Content drift: {fmt} '{rel}' — re-run `pactkit update`")

    return {"drift": bool(details), "details": details, "warnings": warnings}


def _major_minor(v: str) -> tuple[int, ...]:
    """Extract (major, minor) tuple from a version string (STORY-slim-142)."""
    parts = []
    for chunk in v.split(".")[:2]:
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_adapter_skew() -> list[str]:
    """Warn when an installed adapter package lags behind the core version.

    STORY-slim-142 R3: the manifest's pactkit_version is stamped by core, so
    it can never reveal an outdated adapter — read package metadata directly.
    Adapters discovered via the ``pactkit.deployers`` entry-point group; a
    missing/unreadable package is skipped silently (SEC-7).
    """
    import importlib.metadata

    from pactkit import __version__

    warnings: list[str] = []
    try:
        eps = importlib.metadata.entry_points(group="pactkit.deployers")
    except Exception:
        return warnings  # SEC-7: metadata backend failure must not crash doctor
    core = _major_minor(__version__)
    for ep in eps:
        pkg = f"pactkit-{ep.name}"
        try:
            adapter_version = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            continue
        if _major_minor(adapter_version) < core:
            warnings.append(
                f"Adapter skew: {pkg} {adapter_version} < core {__version__} — "
                f"upgrade via `pipx inject pactkit {pkg}=={__version__}`"
            )
    return warnings


def check_core_metadata_divergence() -> list[str]:
    """STORY-slim-145 R6 / AC6: editable-install metadata divergence.

    Compares ``pactkit.__version__`` (source) against
    ``importlib.metadata.version("pactkit")`` (distribution). Divergence indicates
    an editable or partially upgraded install reporting one source version and
    another distribution version. PackageNotFound degrades silently (SEC-7).
    """
    import importlib.metadata

    from pactkit import __version__

    try:
        dist_version = importlib.metadata.version("pactkit")
    except importlib.metadata.PackageNotFoundError:
        return []  # SEC-7: not installed as a distribution — no divergence to report
    except Exception:
        return []  # SEC-7: metadata backend failure must not crash
    if dist_version != __version__:
        return [
            f"Core metadata divergence: source {__version__} != distribution "
            f"{dist_version} (editable/partial install) — reinstall via "
            f"`pipx install pactkit`"
        ]
    return []


def check_adapter_compat(format_name: str, allow_skew: bool = False) -> list[str]:
    """STORY-slim-145 R6 / AC5: deploy-time adapter compatibility gate.

    Blocks adapter deployment on major/minor mismatch with the core version.
    Returns a list of blocking error strings (empty = OK to deploy). An explicit
    ``allow_skew`` override skips the block. Foreign/internal formats (classic,
    plugin, marketplace) have no external adapter and always pass.
    """
    import importlib.metadata

    from pactkit import __version__

    if format_name in ("classic", "plugin", "marketplace"):
        return []
    pkg = f"pactkit-{format_name}"
    try:
        adapter_version = importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return []  # adapter not installed — not a compat error, handled elsewhere
    except Exception:
        return []  # SEC-7: metadata backend failure must not block unrelated deploy
    if _major_minor(adapter_version) != _major_minor(__version__) and not allow_skew:
        return [
            f"Adapter {pkg} {adapter_version} incompatible with core {__version__} "
            f"(major/minor mismatch) — upgrade via `pipx inject pactkit {pkg}=="
            f"{__version__}` or pass --allow-adapter-skew"
        ]
    return []
