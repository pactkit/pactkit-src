"""Deployment manifest — machine-readable record of what was deployed where.

STORY-slim-139 R2: every deploy (core format or adapter) writes
`.pactkit-deployed.json` into the deploy root. `pactkit doctor` later
compares these manifests against the current registry to surface
deployment drift (R3) instead of letting it drop silently.
"""

import json
from pathlib import Path

from pactkit import __version__
from pactkit.config import VALID_AGENTS, VALID_COMMANDS, VALID_SKILLS
from pactkit.profiles import get_profile, is_environment_format

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


def write_deploy_manifest(deploy_root: Path, format_name: str, config: dict | None = None) -> Path:
    """Write .pactkit-deployed.json into the deploy root. Returns its path."""
    deploy_root = Path(deploy_root)
    deploy_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "pactkit_version": __version__,
        "format": format_name,
        **expected_components(format_name, config),
    }
    path = deploy_root / MANIFEST_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
