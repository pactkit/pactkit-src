"""PactKit configuration — load, validate, and generate pactkit.yaml.

STORY-slim-135: CONFIG_SCHEMA is the single source of truth for every
configuration key (default, deep-merge flag, render metadata, validator).
get_default_config(), validate_config(), and the YAML renderer are all
driven by it — adding a config key = adding one registry entry.
"""

import copy
import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import yaml

# This module is intentionally imported after the standard dependencies: the
# rule registry depends only on PactKit's version module and never on config.
from pactkit.prompts.rules import RULE_DEFINITIONS, RULE_ID_ALIASES

# ---------------------------------------------------------------------------
# Valid identifiers (the registry of all known components)
# ---------------------------------------------------------------------------

VALID_AGENTS = frozenset(
    {
        "system-architect",
        "senior-developer",
        "qa-engineer",
        "repo-maintainer",
        "system-medic",
        "security-auditor",
        "visual-architect",
        "code-explorer",
        "product-designer",
    }
)

VALID_COMMANDS = frozenset(
    {
        "project-plan",
        "project-act",
        "project-check",
        "project-done",
        "project-init",
        "project-sprint",
        "project-hotfix",
        "project-design",
        "project-clarify",
        "project-release",
        "project-pr",
        "project-debug",
    }
)

VALID_SKILLS = frozenset(
    {
        # Embedded skills (auto-invoked by commands)
        "pactkit-visualize",
        "pactkit-board",
        "pactkit-scaffold",
        "pactkit-trace",
        "pactkit-draw",
        "pactkit-status",
        "pactkit-doctor",
        "pactkit-garden",
        "pactkit-review",
        "pactkit-release",
        "pactkit-analyze",
        "pactkit-audit",
        "pactkit-report",
        # PDCA commands (STORY-slim-063: migrated from commands/ to skills/)
        "project-plan",
        "project-act",
        "project-check",
        "project-done",
        "project-init",
        "project-sprint",
        "project-hotfix",
        "project-design",
        "project-clarify",
        "project-release",
        "project-pr",
        "project-debug",
    }
)

# Rules are a logical registry, not a filename convention.  Keep legacy IDs
# accepted for existing pactkit.yaml files; deployment normalizes them to the
# current ID before rendering.  This import is safe: prompts.rules depends only
# on the version module, never on config.

CURRENT_RULE_IDS = frozenset(RULE_DEFINITIONS)
LEGACY_RULE_IDS = frozenset(set(RULE_ID_ALIASES) - set(CURRENT_RULE_IDS))
VALID_RULES = CURRENT_RULE_IDS | LEGACY_RULE_IDS
# The maintainer overlay is intentionally opt-in.  It protects PactKit's own
# repository and adapter work, but must not be deployed into ordinary projects
# merely because PactKit is installed there.
DEFAULT_RULE_IDS = CURRENT_RULE_IDS - {"pactkit-maintainer"}

VALID_STACKS = frozenset({"auto", "python", "node", "go", "java"})

VALID_MODELS = frozenset({"haiku", "sonnet", "opus", "inherit"})

VALID_CI_PROVIDERS = frozenset({"github", "gitlab", "none"})

VALID_ISSUE_PROVIDERS = frozenset({"github", "none"})

VALID_E2E_TYPES = frozenset({"none", "cli", "frontend", "backend", "fullstack"})

# Commands deprecated in v1.2.0 — converted to skills (STORY-011)
DEPRECATED_COMMANDS = frozenset(
    {
        "project-trace",
        "project-draw",
        "project-status",
        "project-doctor",
        "project-review",
    }
)


# ---------------------------------------------------------------------------
# Enterprise configuration dataclasses (STORY-047)
# ---------------------------------------------------------------------------


@dataclass
class EnterpriseConfig:
    """Enterprise environment configuration flags.

    Supports air-gapped, TLS-inspected, CI/CD, and permission-restricted
    environments.  All flags default to False (standard behavior).
    """

    no_git: bool = False  # disable all git operations
    no_external: bool = False  # disable external network (MCP, gh CLI, pip install)
    non_interactive: bool = False  # non-interactive mode (CI/CD, auto-accept defaults)
    debug: bool = False  # verbose logging


@dataclass
class PactKitConfig:
    """Structured representation of pactkit.yaml configuration.

    Wraps the enterprise section as a typed EnterpriseConfig object.
    The raw dict form is still used throughout the codebase; this class
    is the typed interface for enterprise flag access.
    """

    enterprise: EnterpriseConfig = field(default_factory=EnterpriseConfig)


# ---------------------------------------------------------------------------
# Per-key validators (schema-driven; messages preserved verbatim — pinned
# by existing tests). Each returns a list of warning strings.
# ---------------------------------------------------------------------------


def _validate_stack_value(_key: str, value) -> list[str]:
    msgs = []
    if isinstance(value, list):
        for s in value:
            if s not in VALID_STACKS or s == "auto":
                msgs.append(f"Unknown stack in list: {s}. Valid: {', '.join(sorted(VALID_STACKS - {'auto'}))}")
    elif value not in VALID_STACKS:
        msgs.append(f"Unknown stack: {value}. Valid: {', '.join(sorted(VALID_STACKS))}")
    return msgs


def _make_component_list_validator(valid_set: frozenset):
    """Validator factory for agents/commands/skills/rules list keys."""

    def _validator(key: str, value) -> list[str]:
        msgs = []
        if not isinstance(value, list):
            msgs.append(f"Config key '{key}' should be a list, got {type(value).__name__}")
            return msgs
        for name in value:
            if not isinstance(name, str):
                msgs.append(f"Config key '{key}' contains non-string value: {name!r}")
            elif key == "commands" and name in DEPRECATED_COMMANDS:
                skill_name = f"pactkit-{name.removeprefix('project-')}"
                msgs.append(
                    f"Deprecated command '{name}' — converted to skill "
                    f"'{skill_name}' in v1.2.0. Remove from commands list."
                )
            elif name not in valid_set:
                msgs.append(f"Unknown {key.rstrip('s')}: {name}")
        return msgs

    return _validator


def _validate_agent_models(_key: str, value) -> list[str]:
    msgs = []
    if isinstance(value, dict):
        for agent_name, model_val in value.items():
            if agent_name not in VALID_AGENTS:
                msgs.append(f"Unknown agent in agent_models: {agent_name}")
            if model_val not in VALID_MODELS:
                msgs.append(
                    f"Invalid model '{model_val}' for agent '{agent_name}'. Valid: {', '.join(sorted(VALID_MODELS))}"
                )
    return msgs


def _validate_ci(_key: str, value) -> list[str]:
    if isinstance(value, dict):
        provider = value.get("provider", "none")
        if provider not in VALID_CI_PROVIDERS:
            return [f"Invalid CI provider '{provider}'. Valid: {', '.join(sorted(VALID_CI_PROVIDERS))}"]
    return []


def _validate_issue_tracker(_key: str, value) -> list[str]:
    if isinstance(value, dict):
        provider = value.get("provider", "none")
        if provider not in VALID_ISSUE_PROVIDERS:
            return [
                f"Invalid issue tracker provider '{provider}'. Valid: {', '.join(sorted(VALID_ISSUE_PROVIDERS))}"
            ]
    return []


def _validate_rule_scopes(_key: str, value) -> list[str]:
    msgs = []
    if isinstance(value, dict):
        for rule_id, pattern in value.items():
            if rule_id not in VALID_RULES:
                msgs.append(f"Unknown rule in rule_scopes: {rule_id}")
            if isinstance(pattern, str) and "[" in pattern and "]" not in pattern:
                msgs.append(f"Invalid glob pattern for rule '{rule_id}': {pattern}")
    return msgs


def _validate_venv(_key: str, value) -> list[str]:
    if isinstance(value, dict):
        venv_path = value.get("path")
        if venv_path is not None and not isinstance(venv_path, str):
            return [f"venv.path should be a string, got {type(venv_path).__name__}"]
    return []


def _validate_release(_key: str, value) -> list[str]:
    if isinstance(value, dict):
        github_release = value.get("github_release", False)
        if not isinstance(github_release, bool):
            return [
                f"release.github_release should be a boolean (true/false), got {type(github_release).__name__}"
            ]
    return []


def _validate_regression(_key: str, value) -> list[str]:
    msgs = []
    if isinstance(value, dict):
        strategy = value.get("strategy", "impact")
        if strategy not in ("impact", "full"):
            msgs.append(f"regression.strategy should be 'impact' or 'full', got '{strategy}'")
        max_impact = value.get("max_impact_tests", 50)
        if not isinstance(max_impact, int) or max_impact <= 0:
            msgs.append(f"regression.max_impact_tests should be a positive integer, got {max_impact!r}")
    return msgs


def _validate_check(_key: str, value) -> list[str]:
    msgs = []
    if not isinstance(value, dict):
        return msgs
    sc = value.get("security_checklist", True)
    if not isinstance(sc, bool):
        msgs.append(f"check.security_checklist should be a boolean (true/false), got {type(sc).__name__}")
    sso = value.get("security_scope_override", "none")
    if sso not in ("none", "full"):
        msgs.append(f"check.security_scope_override should be 'none' or 'full', got {sso!r}")

    pactguard = value.get("pactguard", {})
    if isinstance(pactguard, dict):
        pg_mode = pactguard.get("mode", "all")
        if pg_mode not in ("pattern", "all"):
            msgs.append(f"check.pactguard.mode should be 'pattern' or 'all', got '{pg_mode}'")

    observe = value.get("observe", {})
    if isinstance(observe, dict):
        obs_sources = observe.get("sources", "auto")
        if obs_sources not in ("auto", "chrome-devtools", "playwright", "all"):
            msgs.append(
                f"check.observe.sources should be 'auto', 'chrome-devtools', "
                f"'playwright', or 'all', got '{obs_sources}'"
            )
    return msgs


def _validate_done(_key: str, value) -> list[str]:
    if isinstance(value, dict):
        threshold = value.get("lesson_quality_threshold", 15)
        if not isinstance(threshold, int) or threshold < 0 or threshold > 25:
            return [f"done.lesson_quality_threshold should be an integer 0-25, got {threshold!r}"]
    return []


def _validate_e2e(_key: str, value) -> list[str]:
    msgs = []
    if not isinstance(value, dict):
        return msgs
    e2e_type = value.get("type", "none")
    if e2e_type not in VALID_E2E_TYPES:
        msgs.append(f"e2e.type should be one of {', '.join(sorted(VALID_E2E_TYPES))}, got '{e2e_type}'")
    e2e_blocking = value.get("blocking", False)
    if not isinstance(e2e_blocking, bool):
        msgs.append(f"e2e.blocking should be a boolean (true/false), got {type(e2e_blocking).__name__}")
    for sub in ("test_dir", "env_file", "api_spec", "compose_file"):
        sub_val = value.get(sub)
        if sub_val is not None and not isinstance(sub_val, str):
            msgs.append(f"e2e.{sub} should be a string, got {type(sub_val).__name__}")
    return msgs


_WRITE_SCOPE_ROOT_KEYS = ("source_roots", "test_roots", "docs_roots")


def _validate_write_scope(_key: str, value) -> list[str]:
    """Validate the optional write_scope section (STORY-slim-20260824dd23a0ed3b4c R3).

    Each of source_roots / test_roots / docs_roots MUST be a list of strings.
    Non-list or non-string entries produce warnings (validate_config warns,
    never raises); resolve_scope tolerates malformed entries at runtime.
    """
    msgs: list[str] = []
    if not isinstance(value, dict):
        msgs.append("Config key 'write_scope' should be a mapping")
        return msgs
    for root_key in _WRITE_SCOPE_ROOT_KEYS:
        roots = value.get(root_key)
        if roots is None:
            continue
        if not isinstance(roots, list):
            msgs.append(
                f"write_scope.{root_key} should be a list, got {type(roots).__name__}"
            )
            continue
        for entry in roots:
            if not isinstance(entry, str):
                msgs.append(f"write_scope.{root_key} contains non-string value: {entry!r}")
    return msgs


def _validate_preflight(_key: str, value) -> list[str]:
    if not isinstance(value, dict):
        return ["Config key 'preflight' should be a mapping"]
    mode = value.get("mode", "warn")
    if mode not in {"off", "warn", "enforce"}:
        return ["preflight.mode should be one of: off, warn, enforce"]
    return []


# ---------------------------------------------------------------------------
# CONFIG_SCHEMA — the single source of truth (STORY-slim-135 R1)
#
# Entry fields:
#   default      — value used when the key is absent from pactkit.yaml
#   deep_merge   — nested dict sections merge sub-keys instead of replacing
#   kind         — scalar | list | mapping (drives generic rendering)
#   comment      — section header comment for rendered yaml
#   validator    — optional fn(key, value) -> list[str] of warnings
#   optional     — not part of get_default_config(); rendered only if present
#   extra_lines  — documentation-only comment lines appended after the section
# ---------------------------------------------------------------------------

CONFIG_SCHEMA: dict[str, dict] = {
    "stack": {"default": "auto", "deep_merge": False, "kind": "scalar", "validator": _validate_stack_value},
    "root": {"default": ".", "deep_merge": False, "kind": "scalar"},
    "developer": {"default": "", "deep_merge": False, "kind": "scalar"},
    "agents": {
        "default": sorted(VALID_AGENTS),
        "deep_merge": False,
        "kind": "list",
        "comment": "# Agents — AI role definitions",
        "validator": _make_component_list_validator(VALID_AGENTS),
    },
    "commands": {
        "default": sorted(VALID_COMMANDS),
        "deep_merge": False,
        "kind": "list",
        "comment": "# Commands — PDCA playbooks",
        "validator": _make_component_list_validator(VALID_COMMANDS),
    },
    "skills": {
        "default": sorted(VALID_SKILLS),
        "deep_merge": False,
        "kind": "list",
        "comment": "# Skills — tool scripts",
        "validator": _make_component_list_validator(VALID_SKILLS),
    },
    "rules": {
        # New configs use logical registry IDs.  VALID_RULES also accepts
        # legacy identifiers solely so an existing pactkit.yaml can upgrade
        # without becoming invalid.
        "default": sorted(DEFAULT_RULE_IDS),
        "deep_merge": False,
        "kind": "list",
        "comment": "# Rules — constitution modules",
        "validator": _make_component_list_validator(VALID_RULES),
    },
    "ci": {
        "default": {"provider": "none"},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# CI/CD — set provider to github or gitlab to generate pipeline config",
        "validator": _validate_ci,
        "extra_lines": [
            "  # runner: ubuntu-latest",
            '  # language_version: "3.11"',
            '  # github_host: ""  # GHE server (empty = github.com)',
            '  # actions_ref: ""  # GHE actions prefix',
        ],
    },
    "issue_tracker": {
        "default": {"provider": "none"},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Issue Tracker — set provider to github to link stories to issues",
        "validator": _validate_issue_tracker,
    },
    "lint_blocking": {
        "default": False,
        "deep_merge": False,
        "kind": "scalar",
        "comment": "# Lint — configure lint behavior in /project-done",
    },
    "auto_fix": {"default": False, "deep_merge": False, "kind": "scalar"},
    "venv": {
        "default": {"auto_detect": True},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Virtual Environment — configure venv detection and paths",
        "validator": _validate_venv,
    },
    "release": {
        "default": {"github_release": False},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Release — configure release automation behavior",
        "validator": _validate_release,
    },
    "regression": {
        "default": {"strategy": "impact", "max_impact_tests": 50},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Regression — configure impact-based test selection strategy",
        "validator": _validate_regression,
    },
    "check": {
        "default": {
            "security_checklist": True,
            "security_scope_override": "none",
            "pactguard": {"enabled": False, "mode": "all", "ruleset": "", "blocking": False},
            "observe": {"enabled": False, "sources": "auto", "max_console": 100, "max_network": 200},
        },
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Check — configure QA verification behavior",
        "validator": _validate_check,
    },
    "done": {
        "default": {"lesson_quality_threshold": 15},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Done — configure commit and lesson quality behavior",
        "validator": _validate_done,
    },
    "e2e": {
        "default": {
            "type": "none",
            "blocking": False,
            "test_dir": "tests/e2e",
            "env_file": ".env.test",
            "api_spec": "",
            "compose_file": "docker-compose.test.yml",
        },
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# E2E Testing — configure end-to-end test strategy (none|cli|frontend|backend|fullstack)",
        "validator": _validate_e2e,
    },
    "visualize": {
        "default": {
            "scan_excludes": [
                "venv", "_venv", ".venv", ".env", "env",
                "__pycache__", ".git", ".claude",
                "tests", "docs",
                "node_modules", "site-packages", "dist", "build",
            ],
        },
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Visualize — configure directory scan exclusions and graph provider",
    },
    "command_models": {
        "default": {
            "project-act": "sonnet",
            "project-check": "sonnet",
            "project-done": "sonnet",
            "project-init": "sonnet",
            "project-release": "sonnet",
            "project-pr": "sonnet",
            "project-hotfix": "sonnet",
        },
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Command Models — override model per command for OpenCode deployment",
    },
    # Optional sections — not part of get_default_config(); rendered/validated
    # only when the user explicitly adds them (BUG-010, STORY-028).
    "agent_models": {
        "default": None,
        "deep_merge": False,
        "kind": "mapping",
        "comment": "# Agent Models — override default model per agent (inherit = use account default)",
        "validator": _validate_agent_models,
        "optional": True,
    },
    "rule_scopes": {
        "default": None,
        "deep_merge": False,
        "kind": "mapping",
        "comment": "# Rule Scopes — map rule IDs to glob patterns for context-aware scoping",
        "validator": _validate_rule_scopes,
        "optional": True,
    },
    "write_scope": {
        "default": None,
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Write Scope — declare source/test/docs roots for non-standard directory layouts",
        "validator": _validate_write_scope,
        "optional": True,
    },
    "preflight": {
        "default": {"mode": "warn"},
        "deep_merge": True,
        "kind": "mapping",
        "comment": "# Spec Preflight — off | warn | enforce (warn keeps normal editing available)",
        "validator": _validate_preflight,
        "optional": True,
    },
}

# Keys that require deep merge (derived from schema — was a hand-maintained set)
DEEP_MERGE_KEYS = frozenset(k for k, v in CONFIG_SCHEMA.items() if v["deep_merge"])


# ---------------------------------------------------------------------------
# Default config (schema-driven)
# ---------------------------------------------------------------------------


def get_default_config() -> dict:
    """Return the default config with all components enabled."""
    return {k: copy.deepcopy(v["default"]) for k, v in CONFIG_SCHEMA.items() if not v.get("optional")}


def is_pactkit_self_development_root(project_root: Path | str) -> bool:
    """Return whether *project_root* is the PactKit source repository.

    The maintainer overlay is intentionally not a user-selectable business
    default.  Detecting the actual source layout avoids enabling it merely
    because an unrelated repository happens to be named "pactkit".
    """
    root = Path(project_root).resolve()
    pyproject = root / "pyproject.toml"
    if not (root / "src" / "pactkit").is_dir() or not pyproject.is_file():
        return False
    try:
        return bool(re.search(r'(?m)^name\s*=\s*["\']pactkit["\']\s*$', pyproject.read_text(encoding="utf-8")))
    except OSError:
        return False


def activate_pactkit_maintainer_overlay(config: dict, project_root: Path | str) -> dict:
    """Add the maintainer overlay only for PactKit self-development.

    The private marker is consumed by command renderers so the overlay is
    referenced by phase skills as well as being deployed.  Callers receive a
    copy and never have their user-provided configuration mutated.
    """
    if not is_pactkit_self_development_root(project_root):
        return config
    effective = copy.deepcopy(config)
    rules = list(effective.get("rules", sorted(DEFAULT_RULE_IDS)))
    if "pactkit-maintainer" not in rules:
        rules.append("pactkit-maintainer")
    effective["rules"] = rules
    effective["_pactkit_self_development"] = True
    return effective


# ---------------------------------------------------------------------------
# Virtual environment detection (STORY-039)
# ---------------------------------------------------------------------------

# Common venv directory names in priority order
VENV_CANDIDATES = (".venv", "venv", "env")


def detect_venv(project_root: Path) -> tuple[str, str] | None:
    """Detect virtual environment directory in project root.

    Checks common venv directory names in order: .venv, venv, env.
    Returns the first directory that contains bin/python3 (Unix)
    or Scripts/python.exe (Windows).

    Args:
        project_root: Project root directory to search.

    Returns:
        Tuple of (venv_directory_name, layout) where layout is 'unix' or 'windows',
        or None if no venv found.

        BUG-021: Now returns layout information for platform-aware command generation.
    """
    for candidate in VENV_CANDIDATES:
        venv_path = project_root / candidate
        # Check Unix-style venv (bin/python3 or bin/python)
        if (venv_path / "bin" / "python3").exists():
            return (candidate, "unix")
        if (venv_path / "bin" / "python").exists():
            return (candidate, "unix")
        # Check Windows-style venv (Scripts/python.exe)
        if (venv_path / "Scripts" / "python.exe").exists():
            return (candidate, "windows")
    return None


# ---------------------------------------------------------------------------
# Locate pactkit.yaml (STORY-072: multi-path lookup)
# ---------------------------------------------------------------------------

# Search order for pactkit.yaml — auto-generated from FORMAT_PROFILES.
# Priority: OpenCode > Classic (newer environments preferred).
# To change priority or add a new format, update profiles.py — not here.
from pactkit.profiles import (  # noqa: E402, F401
    FORMAT_PROFILES,
    PACTKIT_YAML_CANDIDATES,
    VALID_FORMATS,
    get_profile,
    is_environment_format,
)

# Re-export for downstream consumers (deployer, cli, etc.)
__all__ = [
    "FORMAT_PROFILES",
    "PACTKIT_YAML_CANDIDATES",
    "VALID_FORMATS",
    "get_profile",
    "is_environment_format",
]


def find_pactkit_yaml(cwd: Path | None = None) -> Path | None:
    """Find pactkit.yaml by searching candidate paths (STORY-072, STORY-slim-005).

    Returns the first existing path, or None if not found.
    Search order is defined in profiles.PACTKIT_YAML_CANDIDATES.
    """
    if cwd is None:
        cwd = Path.cwd()
    start = Path(cwd).expanduser().resolve()
    if start.is_file():
        start = start.parent
    for directory in (start, *start.parents):
        for candidate in PACTKIT_YAML_CANDIDATES:
            p = directory / candidate
            if p.is_file():
                return p
    return None


def resolve_pactkit_yaml_dir(cwd: Path | None = None, format: str | None = None) -> Path:
    """Determine where to write pactkit.yaml based on environment (STORY-072 R2, STORY-slim-005 R6).

    When format is explicitly provided, derives path from FormatProfile (no hardcoded branches).
    When format is None, returns the first existing candidate path, defaulting to classic.
    """
    if cwd is None:
        cwd = Path.cwd()

    # Explicit format: look up from profile (no if-elif chains)
    if format and is_environment_format(format):
        return cwd / get_profile(format).pactkit_yaml_path

    # Auto-detect: first check for existing yaml files, then fall back to dir existence
    for candidate in PACTKIT_YAML_CANDIDATES:
        if (cwd / candidate).exists():
            return cwd / candidate
    # Dir-existence fallback (when yaml not yet created — e.g. first-time init)
    for candidate in PACTKIT_YAML_CANDIDATES:
        parent_dir = (cwd / candidate).parent
        if parent_dir.is_dir():
            return cwd / candidate

    # Default fallback: classic
    return cwd / get_profile("classic").pactkit_yaml_path


# ---------------------------------------------------------------------------
# Multi-copy governance (STORY-slim-135 R4)
# ---------------------------------------------------------------------------

# Canonical preference: classic (.claude) first — it is the primary
# environment for most users and the copy humans actually edit.
CANONICAL_PREFERENCE = (
    ".claude/pactkit.yaml",
    ".codex/pactkit.yaml",
    ".github/pactkit.yaml",
    ".opencode/pactkit.yaml",
)


def existing_config_copies(project_root: Path) -> list[Path]:
    """Return all pactkit.yaml copies that exist under the project root."""
    return [project_root / c for c in PACTKIT_YAML_CANDIDATES if (project_root / c).exists()]


def sync_config_copies(project_root: Path) -> list[Path]:
    """Sync all existing pactkit.yaml copies to the canonical one's content.

    Canonical = the first existing copy in CANONICAL_PREFERENCE order
    (.claude first). Key-count heuristics are NOT used: an auto-generated
    "default wall" copy has more keys but less user intent than a hand-curated
    minimal one. Only existing copies are touched — new copies are never
    created here.

    Returns the list of paths that were updated.
    """
    copies = existing_config_copies(project_root)
    if len(copies) < 2:
        return []

    def _pref(p: Path) -> int:
        rel = p.relative_to(project_root).as_posix()
        return CANONICAL_PREFERENCE.index(rel) if rel in CANONICAL_PREFERENCE else len(CANONICAL_PREFERENCE)

    canonical = min(copies, key=_pref)
    content = canonical.read_text(encoding="utf-8")

    synced = []
    for copy_path in copies:
        if copy_path == canonical:
            continue
        if copy_path.read_text(encoding="utf-8") != content:
            copy_path.write_text(content, encoding="utf-8")
            synced.append(copy_path)
    return synced


def check_config_copy_drift(project_root: Path) -> dict:
    """Detect content drift between pactkit.yaml copies.

    Returns {"drift": bool, "details": [str]} — details name the top-level
    keys whose values differ across copies (e.g. "developer").
    """
    copies = existing_config_copies(project_root)
    if len(copies) < 2:
        return {"drift": False, "details": []}

    parsed: dict[Path, dict] = {}
    for p in copies:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            data = {}
        parsed[p] = data if isinstance(data, dict) else {}

    all_keys: set[str] = set()
    for data in parsed.values():
        all_keys.update(data.keys())

    details = []
    for key in sorted(all_keys):
        values = {json.dumps(data.get(key), sort_keys=True, default=str) for data in parsed.values()}
        if len(values) > 1:
            names = ", ".join(p.relative_to(project_root).as_posix() for p in copies)
            details.append(f"key '{key}' differs across copies ({names})")

    contents = {p.read_text(encoding="utf-8") for p in copies}
    drift = len(contents) > 1
    if drift and not details:
        details.append("copies differ in formatting/comments only")
    return {"drift": drift, "details": details}


# ---------------------------------------------------------------------------
# Developer field validation (STORY-072 R7)
# ---------------------------------------------------------------------------

_DEVELOPER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$")


def _validate_developer(value: str) -> None:
    """Warn if developer field has invalid format."""
    if not value:
        return  # empty is valid (single-developer mode)
    if not _DEVELOPER_PATTERN.match(value):
        warnings.warn(
            f"Developer prefix '{value}' should be 2-20 chars of lowercase letters, "
            f"digits, and hyphens (e.g., 'alice', 'bob-01'). "
            f"Current value may cause issues with Story ID generation.",
            UserWarning,
            stacklevel=3,
        )


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------


def load_config(path: Path | str | None = None) -> dict:
    """Load pactkit.yaml from *path*, merging with defaults.

    If *path* is ``None``, searches candidate paths (STORY-072):
      1. $CWD/.claude/pactkit.yaml (Claude Code)
      2. $CWD/.opencode/pactkit.yaml (OpenCode)
      3. Returns default config if neither exists.

    Missing keys in the user file inherit from defaults.

    BUG-022: For nested dict sections (venv, ci, issue_tracker),
    performs deep merge to preserve default sub-keys when user specifies partial config.
    """
    if path is None:
        found = find_pactkit_yaml()
        if found is None:
            return get_default_config()
        path = found
    else:
        path = Path(path)

    default = get_default_config()

    if not path.exists():
        return default

    raw = path.read_text(encoding="utf-8")
    user_data = yaml.safe_load(raw)

    # Empty file or YAML that parses to None
    if not isinstance(user_data, dict):
        return default

    # Merge: user keys override defaults; missing keys inherit
    merged = dict(default)
    for key, value in user_data.items():
        if key in merged:
            # BUG-022: Deep merge for nested dict sections
            if key in DEEP_MERGE_KEYS and isinstance(merged[key], dict) and isinstance(value, dict):
                # Two-level deep merge: for sub-keys that are also dicts, merge them too
                # (e.g., check.pactguard, check.observe)
                result = {**merged[key]}
                for sub_key, sub_value in value.items():
                    if sub_key in result and isinstance(result[sub_key], dict) and isinstance(sub_value, dict):
                        result[sub_key] = {**result[sub_key], **sub_value}
                    else:
                        result[sub_key] = sub_value
                merged[key] = result
            else:
                # Shallow override for non-dict keys (strings, lists, booleans)
                merged[key] = value
        else:
            # Pass through unknown/extension keys (e.g. multi_agent, enterprise)
            merged[key] = value

    # STORY-072 R7: Validate developer field
    _validate_developer(str(merged.get("developer", "")))

    return merged


# ---------------------------------------------------------------------------
# Auto-merge new components
# ---------------------------------------------------------------------------


def auto_merge_config_file(path: Union[Path, str]) -> list[str]:
    """Auto-merge new components and backfill missing sections in pactkit.yaml.

    For each list-type key (agents, commands, skills, rules), appends items
    from the VALID_* registry that are missing from the user's list and not
    present in the ``exclude`` section.

    For non-list config sections (ci, issue_tracker, lint_blocking,
    auto_fix), backfills missing sections with defaults from
    ``get_default_config()``.  Existing user values are never overwritten.

    Modifies the YAML file in-place.  Returns a list of ``"key: item"``
    or ``"section: key"`` strings describing what was added (empty list
    when nothing changed).
    """
    path = Path(path)
    if not path.exists():
        return []

    raw = path.read_text(encoding="utf-8")
    user_data = yaml.safe_load(raw)

    if not isinstance(user_data, dict):
        return []

    exclude = user_data.get("exclude", {})
    if not isinstance(exclude, dict):
        exclude = {}

    added: list[str] = []

    # --- List-type keys: merge new items ---
    # If a list key is absent from yaml, it means "deploy all" (VALID_* default).
    # Only merge if the user explicitly provides a list (opt-in customization).
    for key, valid_set in _REGISTRY.items():
        # Rule aliases are read compatibility only.  Upgrade must never write
        # deprecated names back into a user's configuration, nor implicitly
        # enable the PactKit-maintainer overlay for ordinary projects.
        # Validation still uses VALID_RULES through _REGISTRY.
        if key == "rules":
            valid_set = DEFAULT_RULE_IDS
        user_list = user_data.get(key)
        if user_list is None:
            # Key absent = deploy all by default. No backfill needed.
            continue
        if not isinstance(user_list, list):
            continue

        excluded_items = set(exclude.get(key, []) or [])
        user_set = set(user_list)
        new_items = sorted(item for item in valid_set if item not in user_set and item not in excluded_items)

        if new_items:
            user_data[key] = user_list + new_items
            for item in new_items:
                added.append(f"{key}: {item}")

    # Non-list sections are NO LONGER backfilled (STORY-slim-126).
    # Absent key = accept default. Users keep yaml minimal.
    # Backfill only happens during `pactkit init` (scaffold).

    # STORY-slim-102: Remove stale version field from project yaml
    if "version" in user_data:
        del user_data["version"]
        added.append("removed: version (now tracked globally)")

    if added:
        _rewrite_yaml(path, user_data)

    return added


def _render_stack_line(stack) -> str:
    """Render the stack field as a YAML line (supports string or list)."""
    if isinstance(stack, list):
        if len(stack) == 1:
            return f"stack: {stack[0]}"
        items = "\n".join(f"  - {s}" for s in stack)
        return f"stack:\n{items}"
    return f"stack: {stack}"


def update_yaml_stack(yaml_path: Path, stacks: list[str]) -> None:
    """Update the stack field in an existing pactkit.yaml (STORY-slim-077).

    Loads the yaml, updates the stack field, and rewrites the file.
    Single-element lists are unwrapped to a plain string for cleaner output.
    """
    import yaml as _yaml

    data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    data["stack"] = stacks[0] if len(stacks) == 1 else stacks
    _rewrite_yaml(yaml_path, data)


# ---------------------------------------------------------------------------
# Schema-driven YAML renderer (STORY-slim-135 R3 — single renderer)
# ---------------------------------------------------------------------------

# Scalar values safe to emit unquoted in YAML flow style
_PLAIN_SCALAR_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.@/+=-]*$")


def _fmt_scalar(value) -> str:
    """Format a scalar for YAML output, preserving its parsed value.

    Plain style when safe; JSON double-quoted (valid YAML) otherwise —
    this keeps values like multi-line install_cmd intact through rewrites.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if _PLAIN_SCALAR_RE.match(s):
        return s
    return json.dumps(s, ensure_ascii=False)


def _render_value(lines: list[str], key: str, value, indent: int) -> None:
    """Recursively render a mapping/list/scalar value at the given indent."""
    pad = " " * indent
    if isinstance(value, dict):
        lines.append(f"{pad}{key}:")
        for sub_key, sub_val in value.items():
            _render_value(lines, sub_key, sub_val, indent + 2)
    elif isinstance(value, list):
        lines.append(f"{pad}{key}:")
        for item in value:
            lines.append(f"{pad}  - {_fmt_scalar(item)}")
    else:
        lines.append(f"{pad}{key}: {_fmt_scalar(value)}")


def render_config_yaml(data: dict, header_lines: list[str]) -> str:
    """Render pactkit.yaml content from *data*, driven by CONFIG_SCHEMA.

    Only sections present in *data* are rendered — absent keys stay absent
    (STORY-slim-135 R2/R3: no re-inflation of defaults). Unknown user keys
    are preserved in a trailing Custom section (BUG-023).
    """
    lines = list(header_lines)
    lines.append("")
    lines.append(_render_stack_line(data.get("stack", "auto")))
    lines.append(f"root: {data.get('root', '.')}")
    lines.append(f'developer: "{data.get("developer", "")}"')
    lines.append("")

    for key, entry in CONFIG_SCHEMA.items():
        if key in ("stack", "root", "developer"):
            continue  # already in header
        if key not in data or data[key] is None:
            continue
        value = data[key]
        comment = entry.get("comment")
        if comment:
            lines.append(comment)
        if entry["kind"] == "scalar":
            lines.append(f"{key}: {_fmt_scalar(value)}")
        else:
            _render_value(lines, key, value, 0)
        for extra in entry.get("extra_lines", []):
            lines.append(extra)
        lines.append("")

    # Exclude section (derived key, not in schema)
    exclude = data.get("exclude", {})
    if exclude and isinstance(exclude, dict):
        lines.append("# Exclude — components that should NOT be auto-added on upgrade")
        lines.append("exclude:")
        for key in ("agents", "commands", "skills", "rules"):
            items = exclude.get(key)
            if items:
                lines.append(f"  {key}:")
                for item in items:
                    lines.append(f"    - {item}")
        lines.append("")

    # BUG-023: Preserve unknown user-defined keys
    known = set(CONFIG_SCHEMA) | {"version", "exclude"}
    unknown_keys = {k: v for k, v in data.items() if k not in known}
    if unknown_keys:
        lines.append("# Custom — user-defined keys (preserved by PactKit)")
        for key in sorted(unknown_keys.keys()):
            value = unknown_keys[key]
            # Serialize using PyYAML for nested structures
            serialized = yaml.dump({key: value}, default_flow_style=False, allow_unicode=True)
            lines.append(serialized.rstrip())
        lines.append("")

    return "\n".join(lines)


_REWRITE_HEADER = [
    "# PactKit Configuration",
    "# Edit this file to customize which components are deployed.",
    "# Remove items from a list to disable them. Default: all enabled.",
]

_INIT_HEADER = [
    "# PactKit Configuration",
    "# Only override what you need — absent keys use built-in defaults.",
    "# See all options and current values: pactkit schema config",
]


def _rewrite_yaml(path: Path, data: dict) -> None:
    """Rewrite pactkit.yaml preserving the standard section layout.

    BUG-023: Preserves unknown user-defined keys in a separate section.
    STORY-slim-135: renders only sections present in *data* (no re-inflation).
    """
    content = render_config_yaml(data, _REWRITE_HEADER)

    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Validate config (schema-driven)
# ---------------------------------------------------------------------------

_REGISTRY = {
    "agents": VALID_AGENTS,
    "commands": VALID_COMMANDS,
    "skills": VALID_SKILLS,
    "rules": VALID_RULES,
}


def validate_config(config: dict) -> None:
    """Warn (never raise) about unknown component names or invalid values."""
    for key, value in config.items():
        entry = CONFIG_SCHEMA.get(key)
        if entry is None:
            continue  # enterprise / multi_agent / custom keys: accepted without warnings
        validator = entry.get("validator")
        if validator is None:
            continue
        for msg in validator(key, value):
            warnings.warn(msg)


# ---------------------------------------------------------------------------
# YAML generation (minimal — STORY-slim-135 R2)
# ---------------------------------------------------------------------------


def generate_default_yaml(stack=None) -> str:
    """Return the minimal initial config as a commented YAML string.

    STORY-slim-135 R2: only stack + developer are written. Every other key
    resolves through load_config() defaults; `pactkit schema config` lists
    all available options.

    Args:
        stack: Override stack value. If list with 1 element, unwraps to string.
               If None, uses default 'auto'.
    """
    if stack is None:
        stack = "auto"
    # Single-element list → unwrap to string for cleaner YAML
    if isinstance(stack, list) and len(stack) == 1:
        stack = stack[0]
    lines = list(_INIT_HEADER)
    lines.append("")
    lines.append(_render_stack_line(stack))
    lines.append('developer: ""')
    lines.append("")  # trailing newline
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discoverability report (STORY-slim-135 R5)
# ---------------------------------------------------------------------------


def schema_config_report(project_root: Path | None = None) -> str:
    """Render all configurable keys with default, effective value, and source."""
    root = Path(project_root) if project_root else Path.cwd()
    found = find_pactkit_yaml(root)
    user_data: dict = {}
    if found is not None:
        try:
            loaded = yaml.safe_load(found.read_text(encoding="utf-8"))
            user_data = loaded if isinstance(loaded, dict) else {}
        except yaml.YAMLError:
            user_data = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        merged = load_config(found) if found else get_default_config()

    source_label = found.relative_to(root).as_posix() if found else "(none — all defaults)"
    lines = [
        "pactkit.yaml — all configurable keys",
        f"Config file: {source_label}",
        "",
    ]
    for key, entry in CONFIG_SCHEMA.items():
        if entry.get("optional"):
            # Optional sections are always listed for discoverability (R5),
            # marked as unset unless the user added them.
            effective = user_data.get(key)
            default_label = "(optional)"
            source = source_label if key in user_data else "(optional — not set)"
        else:
            effective = merged.get(key)
            default_label = json.dumps(entry["default"], ensure_ascii=False)
            source = source_label if key in user_data else "default"
        effective_label = json.dumps(effective, ensure_ascii=False, default=str)
        if len(effective_label) > 60:
            effective_label = effective_label[:57] + "..."
        lines.append(f"{key}:")
        lines.append(f"  effective: {effective_label}")
        lines.append(f"  default:   {default_label}")
        lines.append(f"  source:    {source}")
    return "\n".join(lines)
