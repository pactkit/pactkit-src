"""Deployment manifest — machine-readable record of what was deployed where.

STORY-slim-139 R2: every deploy (core format or adapter) writes
`.pactkit-deployed.json` into the deploy root. `pactkit doctor` later
compares these manifests against the current registry to surface
deployment drift (R3) instead of letting it drop silently.
"""

import hashlib
import json
from pathlib import Path

from pactkit import __version__
from pactkit.config import VALID_AGENTS, VALID_COMMANDS, VALID_SKILLS
from pactkit.profiles import get_profile, is_environment_format
from pactkit.prompts.guides import GUIDES_DIR
from pactkit.prompts.rules import RULES_FILES, RULES_ONDEMAND_DIR

MANIFEST_NAME = ".pactkit-deployed.json"

# Skills/commands currently deployable to every format (commands deploy as
# skills since STORY-slim-063, but are tracked separately for parity checks).
ALL_PACTKIT_SKILLS = sorted(s for s in VALID_SKILLS if s.startswith("pactkit-"))


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
        "commands": sorted(set(commands)),
        "agents": sorted(set(agents)),
    }


def sha256_file(path: Path) -> str:
    """Return the lowercase hex sha256 digest of a file's raw bytes.

    Bytes-mode read avoids newline/encoding differences across platforms (R5).
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pactkit_owned_files(deploy_root: Path, components: dict) -> dict[str, str]:
    """Map relative path -> sha256 for every pactkit-owned deployed file (R1).

    Coverage = declared components' on-disk files + managed rules/guides.
    Merge-semantics files (``CLAUDE.md``, ``AGENTS.md``, ``opencode.json``,
    ``config.toml``) and meta files (``.pactkit-version``, the manifest itself)
    are never enumerated, so user additions cannot produce drift (R4).
    """
    root = Path(deploy_root)
    owned: dict[str, str] = {}

    # Skills — commands deploy as skills since STORY-slim-063.
    for name in sorted(set(components["skills"]) | set(components["commands"])):
        skill_dir = root / "skills" / name
        if skill_dir.is_dir():
            for f in sorted(skill_dir.rglob("*")):
                if f.is_file():
                    owned[f.relative_to(root).as_posix()] = sha256_file(f)

    # Agents — flat .md files.
    for name in components["agents"]:
        agent = root / "agents" / f"{name}.md"
        if agent.is_file():
            owned[agent.relative_to(root).as_posix()] = sha256_file(agent)

    # Managed rules — filename placement is format-dependent (global rules/ vs
    # on-demand skills/_rules/), so probe both locations for each managed file.
    for filename in sorted(RULES_FILES.values()):
        for cand in (root / "rules" / filename, root / "skills" / RULES_ONDEMAND_DIR / filename):
            if cand.is_file():
                owned[cand.relative_to(root).as_posix()] = sha256_file(cand)

    # Engineering guides — on-demand reference under skills/_rules/guides/.
    guides_dir = root / "skills" / RULES_ONDEMAND_DIR / GUIDES_DIR
    if guides_dir.is_dir():
        for f in sorted(guides_dir.rglob("*.md")):
            owned[f.relative_to(root).as_posix()] = sha256_file(f)

    return owned


def write_deploy_manifest(deploy_root: Path, format_name: str, config: dict | None = None) -> Path:
    """Write .pactkit-deployed.json into the deploy root. Returns its path."""
    deploy_root = Path(deploy_root)
    deploy_root.mkdir(parents=True, exist_ok=True)
    components = expected_components(format_name, config)
    payload = {
        "pactkit_version": __version__,
        "format": format_name,
        "workflow_continuation": {
            "finish_guard_supported": True,
            "auto_resume_available": False,
            "guarantee_level": "process",
        },
        **components,
        # STORY-slim-141 R1: content hashes for doctor's content-level parity.
        "files": pactkit_owned_files(deploy_root, components),
    }
    path = deploy_root / MANIFEST_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
