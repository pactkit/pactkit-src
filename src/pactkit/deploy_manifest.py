"""Deployment manifest — machine-readable record of what was deployed where.

STORY-slim-139 R2: every deploy (core format or adapter) writes
`.pactkit-deployed.json` into the deploy root. `pactkit doctor` later
compares these manifests against the current registry to surface
deployment drift (R3) instead of letting it drop silently.
"""

import hashlib
import json
from pathlib import Path
from typing import Iterable

from pactkit import __version__
from pactkit.config import DEFAULT_RULE_IDS, VALID_AGENTS, VALID_COMMANDS
from pactkit.profiles import get_profile, is_environment_format
from pactkit.prompts.guides import GUIDE_DEFINITIONS, GUIDES_DIR, GUIDES_FILES
from pactkit.prompts.rules import (
    COMMAND_CONDITIONAL_RULES_MAP,
    COMMAND_RULES_MAP,
    GLOBAL_RULE_IDS,
    PHASE_CONTRACTS,
    RULE_CLAUSES,
    RULE_DEFINITIONS,
    RULES_ONDEMAND_DIR,
    SPRINT_PHASE_SEQUENCE,
    normalize_rule_id,
)
from pactkit.prompts.skills import SKILL_MANIFEST
from pactkit.protocols import CORE_PROTOCOL_VERSION
from pactkit.utils import atomic_write

MANIFEST_NAME = ".pactkit-deployed.json"

# Skills/commands currently deployable to every format (commands deploy as
# skills since STORY-slim-063, but are tracked separately for parity checks).
ALL_PACTKIT_SKILLS = sorted(entry["name"] for entry in SKILL_MANIFEST)
ALL_PORTABLE_METHODS: list[str] = []


def expected_components(format_name: str, config: dict | None = None) -> dict:
    """Expected deployment set for a format = registries − profile exclusions.

    User config may narrow skills/commands/agents lists; profile exclusions
    (e.g. project-sprint on non-Claude formats) always apply.
    """
    config = config or {}
    skills = config.get("skills", ALL_PACTKIT_SKILLS)
    commands = config.get("commands", sorted(VALID_COMMANDS))
    agents = config.get("agents", sorted(VALID_AGENTS))

    skills = [s for s in skills if s.startswith("pactkit-")]
    if is_environment_format(format_name):
        excluded = get_profile(format_name).excluded_commands
        commands = [c for c in commands if c not in excluded]

    return {
        "skills": sorted(set(skills)),
        # Portable methods are an explicit Core API, not default host skills.
        "portable_methods": ALL_PORTABLE_METHODS,
        "commands": sorted(set(commands)),
        "agents": sorted(set(agents)),
    }


def sha256_file(path: Path) -> str:
    """Return the lowercase hex sha256 digest of a file's raw bytes.

    Bytes-mode read avoids newline/encoding differences across platforms (R5).
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_previous_manifest(deploy_root: Path) -> dict:
    """Read the previous deployment manifest payload; {} when unusable.

    The manifest is advisory: a missing, corrupt, or non-dict payload yields
    no ownership proof but never blocks deployment (STORY-slim-202608264cf429c75e22 R1).
    """
    manifest_path = Path(deploy_root) / MANIFEST_NAME
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_previous_hashes(deploy_root: Path) -> dict[str, str]:
    """Ownership proof map (relative path -> sha256) from the previous manifest."""
    files = load_previous_manifest(deploy_root).get("files", {})
    if not isinstance(files, dict):
        return {}
    return {
        path: digest
        for path, digest in files.items()
        if isinstance(path, str) and isinstance(digest, str)
    }


def preserve_or_write(
    deploy_root: Path,
    destination: Path,
    content: str,
    previous_hashes: dict[str, str],
    label: str,
) -> bool:
    """Write ``content`` to ``destination`` only with ownership proof.

    Overwrite is authorized when the destination is absent, byte-identical
    to the new content, or manifest-proven unchanged since the previous
    deployment. Any other existing bytes are user-owned: the original is
    preserved untouched and the new content is proposed as a
    ``.pactkit-new`` sibling candidate. Returns True when the file was
    written in place.
    """
    destination = Path(destination)
    root = Path(deploy_root)
    try:
        relative = destination.relative_to(root).as_posix()
    except ValueError:
        relative = None
    expected_hash = previous_hashes.get(relative) if relative else None

    if destination.is_file():
        try:
            actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        except OSError:
            # Unverifiable bytes at the exact moment ownership must be
            # proven: preserve, never destroy.
            actual_hash = None
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if actual_hash is not None and (
            actual_hash == content_hash or (expected_hash and actual_hash == expected_hash)
        ):
            atomic_write(destination, content)
            return True
        candidate = destination.with_suffix(destination.suffix + ".pactkit-new")
        atomic_write(candidate, content)
        print(
            f"  ⚠️  preserved user-modified PactKit {label}: {destination}; "
            f"wrote candidate {candidate.name}"
        )
        return False
    if destination.exists():
        # A directory or special file is never ours to replace.
        print(f"  ⚠️  preserved non-file {label}: {destination}")
        return False
    atomic_write(destination, content)
    return True


def retire_disabled_skills(
    skills_dir: Path, enabled_set: set, deploy_root: Path, previous_hashes: dict[str, str],
) -> None:
    """Retire a disabled skill only when the previous manifest proves ownership.

    A directory name is not an ownership claim.  The skill directory is
    removed only when it contains exactly the registered artifacts and every
    one still matches its manifest-recorded hash; anything drifted or
    extended by the user is preserved with a warning
    (STORY-slim-202608264cf429c75e22 R8).
    """
    import shutil

    script_names = {entry["name"]: entry["script_name"] for entry in SKILL_MANIFEST}
    previous = load_previous_manifest(deploy_root).get("skills")
    if not isinstance(previous, list):
        return
    for name in previous:
        if not isinstance(name, str) or name in enabled_set:
            continue
        skill_dir = Path(skills_dir) / name
        if not skill_dir.is_dir():
            continue
        registered = [skill_dir / "SKILL.md"]
        script_name = script_names.get(name)
        if script_name:
            registered.append(skill_dir / "scripts" / script_name)
        # Registered files and their parent directories are the only entries
        # a proven-unchanged skill directory may contain; a user file — or a
        # user-created (even empty) subdirectory — blocks retirement.
        allowed = set(registered) | {artifact.parent for artifact in registered}
        try:
            entries = sorted(skill_dir.rglob("*"))
        except OSError:
            continue
        if any(entry not in allowed for entry in entries):
            print(f"  ⚠️  preserved user-modified skill directory: {skill_dir}")
            continue
        try:
            proven = all(
                previous_hashes.get(path.relative_to(deploy_root).as_posix())
                == hashlib.sha256(path.read_bytes()).hexdigest()
                for path in registered
            )
        except OSError:
            proven = False
        if proven:
            shutil.rmtree(skill_dir)
        else:
            print(f"  ⚠️  preserved user-modified skill directory: {skill_dir}")


def retire_disabled_agents(
    agents_dir: Path,
    enabled_set: set,
    managed_names: Iterable[str],
    *,
    enforce: bool,
    deploy_root: Path,
    previous_hashes: dict[str, str],
) -> None:
    """Retire managed agent files outside the enabled set, by ownership proof.

    In generation mode (``enforce=False``) the registry owns the output
    directory and deletes by name.  In deployment mode a filename alone is
    never proof: deletion requires the previous manifest to record the
    file's hash and the current bytes to still match
    (STORY-slim-202608264cf429c75e22 R3).
    """
    managed_files = {f"{name}.md" for name in managed_names}
    agents_dir = Path(agents_dir)
    if not agents_dir.exists():
        return
    for f in agents_dir.glob("*.md"):
        if f.name not in managed_files or f.stem in enabled_set:
            continue
        if not enforce:
            f.unlink()
            continue
        expected_hash = previous_hashes.get(f.relative_to(deploy_root).as_posix())
        try:
            actual_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            print(f"  ⚠️  preserved unreadable agent file: {f}")
            continue
        if expected_hash and actual_hash == expected_hash:
            f.unlink()
        else:
            print(f"  ⚠️  preserved user-owned agent file: {f}")


def pactkit_owned_files(
    deploy_root: Path, components: dict, format_name: str = "classic",
    enabled_rules: list[str] | None = None,
) -> dict[str, str]:
    """Map relative path -> sha256 for every pactkit-owned deployed file (R1).

    Coverage = declared components' on-disk files + managed rules/guides.
    Merge-semantics files (``CLAUDE.md``, ``AGENTS.md``, ``opencode.json``,
    ``config.toml``) and meta files (``.pactkit-version``, the manifest itself)
    are never enumerated, so user additions cannot produce drift (R4).
    """
    root = Path(deploy_root)
    owned: dict[str, str] = {}

    # Skills.  Commands deploy as skills in Core/Codex, but Copilot uses
    # .github/prompts/{name}.prompt.md.  The manifest must follow the real
    # adapter layout or doctor cannot detect prompt drift.
    #
    # Ownership is claimed only for registered artifacts (SKILL.md plus the
    # registry-declared script).  Enumerating a whole directory would claim
    # user files dropped inside it and authorize a later overwrite
    # (STORY-slim-202608264cf429c75e22 R4).
    skill_script = {entry["name"]: entry["script_name"] for entry in SKILL_MANIFEST}
    skill_names = set(components["skills"]) | set(components["portable_methods"])
    if format_name != "copilot":
        skill_names |= set(components["commands"])
    for name in sorted(skill_names):
        skill_dir = root / "skills" / name
        registered = [skill_dir / "SKILL.md"]
        script_name = skill_script.get(name)
        if script_name:
            registered.append(skill_dir / "scripts" / script_name)
        for artifact in registered:
            candidate = artifact.with_suffix(artifact.suffix + ".pactkit-new")
            if artifact.is_file() and not candidate.exists():
                owned[artifact.relative_to(root).as_posix()] = sha256_file(artifact)

    if format_name == "copilot":
        for name in components["commands"]:
            prompt = root / "prompts" / f"{name}.prompt.md"
            if prompt.is_file():
                owned[prompt.relative_to(root).as_posix()] = sha256_file(prompt)

    # Agents — flat .md files.
    for name in components["agents"]:
        agent = root / "agents" / f"{name}.md"
        if agent.is_file():
            owned[agent.relative_to(root).as_posix()] = sha256_file(agent)

    # Managed rules — filename placement is format-dependent (global rules/ vs
    # on-demand skills/_rules/), so probe both locations for each managed file.
    # A sibling ``.pactkit-new`` is an explicit unresolved conflict marker: the
    # original is user-preserved and must not be reclaimed by a new manifest.
    configured = RULE_DEFINITIONS if enabled_rules is None else enabled_rules
    enabled_ids = {
        normalized
        for rule_id in configured
        if (normalized := normalize_rule_id(rule_id)) is not None
    }
    for rule_id in sorted(enabled_ids):
        filename = RULE_DEFINITIONS[rule_id].filename
        candidates = (
            root / "rules" / filename,
            root / "skills" / RULES_ONDEMAND_DIR / filename,
        )
        for cand in candidates:
            candidate = cand.with_suffix(cand.suffix + ".pactkit-new")
            if cand.is_file() and not candidate.exists():
                owned[cand.relative_to(root).as_posix()] = sha256_file(cand)

    # Engineering guides — on-demand reference under skills/_rules/guides/.
    # Only record content that still matches PactKit's rendered source.  A
    # same-named, drifted file may be a user adaptation preserved by deploy;
    # listing it as owned would authorize a later overwrite.
    guides_dir = root / "skills" / RULES_ONDEMAND_DIR / GUIDES_DIR
    if guides_dir.is_dir():
        for filename, expected in GUIDES_FILES.items():
            guide = guides_dir / filename
            candidate = guide.with_suffix(guide.suffix + ".pactkit-new")
            if (
                guide.is_file()
                and not candidate.exists()
                and guide.read_text(encoding="utf-8") == expected
            ):
                owned[guide.relative_to(root).as_posix()] = sha256_file(guide)

    return owned


def pactkit_rule_ownership(
    deploy_root: Path, format_name: str = "classic",
    enabled_rules: list[str] | None = None,
    enabled_commands: list[str] | None = None,
) -> list[dict]:
    """Describe registry-owned rule artifacts without inspecting user files.

    File hashes remain the integrity evidence.  This metadata makes ownership
    explicit so update/uninstall logic never has to infer it from a filename.
    """
    root = Path(deploy_root)
    records: list[dict[str, str]] = []
    configured = RULE_DEFINITIONS if enabled_rules is None else enabled_rules
    enabled_ids = {
        normalized
        for rule_id in configured
        if (normalized := normalize_rule_id(rule_id)) is not None
    }
    command_ids = set(COMMAND_RULES_MAP if enabled_commands is None else enabled_commands)
    for rule_id in sorted(enabled_ids):
        definition = RULE_DEFINITIONS[rule_id]
        # Copilot inlines rules into prompts, so it has no standalone registry
        # artifacts to record. Codex stores only Runtime globally; conditional
        # modules are copied into each applicable command skill's references/.
        if format_name == "copilot":
            continue
        if format_name == "codex" and definition.load_policy != "global":
            for command, candidates in COMMAND_CONDITIONAL_RULES_MAP.items():
                if command not in command_ids or rule_id not in candidates:
                    continue
                relative = f"skills/{command}/references/rules/{rule_id}.md"
                path = root / relative
                candidate = path.with_suffix(path.suffix + ".pactkit-new")
                if path.is_file() and not candidate.exists():
                    records.append({
                        "id": definition.id,
                        "owner": definition.owner,
                        "path": relative,
                        "sha256": sha256_file(path),
                        "level": definition.level,
                        "scope": list(definition.scope),
                        "load_policy": definition.load_policy,
                        "failure": definition.failure,
                        "trigger": definition.trigger,
                        "skip_when": list(definition.skip_when),
                        "evidence": list(definition.evidence),
                        "override": definition.override,
                        "clauses": list(definition.clauses),
                        "legacy_ids": list(definition.legacy_ids),
                    })
            continue
        base = (
            "rules" if definition.load_policy == "global"
            else f"skills/{RULES_ONDEMAND_DIR}"
        )
        relative = f"{base}/{definition.filename}"
        path = root / relative
        candidate = path.with_suffix(path.suffix + ".pactkit-new")
        if path.is_file() and not candidate.exists():
            records.append({
                "id": definition.id,
                "owner": definition.owner,
                "path": relative,
                "sha256": sha256_file(path),
                "level": definition.level,
                "scope": list(definition.scope),
                "load_policy": definition.load_policy,
                "failure": definition.failure,
                "trigger": definition.trigger,
                "skip_when": list(definition.skip_when),
                "evidence": list(definition.evidence),
                "override": definition.override,
                "clauses": list(definition.clauses),
                "legacy_ids": list(definition.legacy_ids),
            })
    return records


def write_deploy_manifest(deploy_root: Path, format_name: str, config: dict | None = None) -> Path:
    """Write .pactkit-deployed.json into the deploy root. Returns its path."""
    deploy_root = Path(deploy_root)
    deploy_root.mkdir(parents=True, exist_ok=True)
    components = expected_components(format_name, config)
    enabled_rules = (
        config.get("rules", sorted(DEFAULT_RULE_IDS))
        if config is not None
        else sorted(DEFAULT_RULE_IDS)
    )
    # The manifest is also the durable declaration of a user's intentional
    # selective deployment.  Doctor can keep auditing default installs against
    # the current registry while avoiding false drift for a declared subset.
    default_components = expected_components(format_name)
    component_scope = (
        "default"
        if all(components[kind] == default_components[kind] for kind in components)
        else "selective"
    )
    capability_profiles = {
        "classic": ("portable", "core_profile"),
        "opencode": ("portable", "adapter_native_command_facade"),
        # Codex commands are discovered as skills and executed in the active
        # Codex conversation.  PactKit deliberately ships no App Server
        # bridge, runner, lifecycle hook, or resumable background workflow.
        "codex": ("portable", "native_codex_session"),
        # Copilot deploys prompt files for the active IDE conversation. It
        # ships no PactKit execution bridge, WorkUnit facade, or resume API,
        # so it must not claim guided/manual-resume capability.
        "copilot": ("portable", "native_current_session"),
    }
    execution_mode, verification_source = capability_profiles.get(
        format_name, ("portable", "core_profile")
    )
    host_capabilities = {
        "protocol_version": CORE_PROTOCOL_VERSION,
        "verification_source": verification_source,
        "instructions_discovery": True,
        "skills_discovery": True,
        "structured_results": False,
        "tool_execution": execution_mode == "guided",
        "approval": False,
        "lifecycle_events": False,
        "thread_resume": False,
        "turn_steer": False,
        "background_execution": False,
        "cancellation": False,
        "e2e_validated": False,
        "execution_mode": execution_mode,
        "manual_resume": execution_mode == "guided",
    }
    payload = {
        "pactkit_version": __version__,
        "format": format_name,
        "workflow_continuation": {
            # A deployment manifest records actual host capabilities.  The
            # default command model is direct current-session execution, so
            # no format gets to advertise a completion gate it does not ship.
            "finish_guard_supported": False,
            "auto_resume_available": False,
            # This is the externally reported guarantee.  It must be derived
            # from the same host capability declaration, otherwise a
            # portable-only host is incorrectly advertised as tool-guided.
            "guarantee_level": execution_mode,
            "execution_mode": execution_mode,
            "protocol_version": CORE_PROTOCOL_VERSION,
            "stop_hook_required": False,
            "e2e_validated": host_capabilities["e2e_validated"],
        },
        "host_capabilities": host_capabilities,
        "component_scope": component_scope,
        **components,
        "rule_schema_version": 2,
        "rule_loading": {
            "primary_hosts": ["classic", "codex", "opencode"],
            "compatibility_hosts": ["copilot"],
            "layout": (
                "skill_local_references" if format_name == "codex"
                else "shared_on_demand_rules"
            ),
            "global": sorted(GLOBAL_RULE_IDS),
            "command": {
                command: list(rule_ids)
                for command, rule_ids in COMMAND_RULES_MAP.items()
            },
            "conditional": {
                command: list(rule_ids)
                for command, rule_ids in COMMAND_CONDITIONAL_RULES_MAP.items()
            },
            "risk": {"source": "change_risk_profile", "max_guides": 3},
        },
        "rules": pactkit_rule_ownership(
            deploy_root, format_name, enabled_rules, components["commands"],
        ),
        "rule_clauses": {
            clause_id: {
                "level": clause.level,
                "trigger": clause.trigger,
                "skip_when": list(clause.skip_when),
                "evidence": list(clause.evidence),
                "failure": clause.failure,
                "override": clause.override,
            }
            for clause_id, clause in RULE_CLAUSES.items()
        },
        "phase_contracts": {
            command: {
                "phase": contract.phase,
                "entry": contract.entry,
                "inputs": list(contract.inputs),
                "outputs": list(contract.outputs),
                "invariants": list(contract.invariants),
                "completion_evidence": list(contract.completion_evidence),
                "failure_semantics": contract.failure_semantics,
                "allowed_next": list(contract.allowed_next),
                "external_effects": list(contract.external_effects),
            }
            for command, contract in PHASE_CONTRACTS.items()
        },
        "guides": {
            filename: {
                "trigger": guide.trigger,
                "questions": list(guide.questions),
                "safe_invariants": list(guide.safe_invariants),
                "defaults": list(guide.defaults),
                "alternatives": list(guide.alternatives),
                "evidence": list(guide.evidence),
                "non_applicable": list(guide.non_applicable),
            }
            for filename, guide in GUIDE_DEFINITIONS.items()
        },
        "sprint_capsules": {
            "strategy": (
                "skill_local_references" if format_name == "codex"
                else "managed_phase_references"
            ),
            "sequence": list(SPRINT_PHASE_SEQUENCE),
            "single_active_phase": True,
        },
        # STORY-slim-141 R1: content hashes for doctor's content-level parity.
        "files": pactkit_owned_files(
            deploy_root, components, format_name,
            enabled_rules,
        ),
    }
    path = deploy_root / MANIFEST_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
