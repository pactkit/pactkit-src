"""STORY-slim-20260828897396a935ab: secrets gate (R5).

PreToolUse gate that blocks Bash commands containing literal credential
material — the L1 "never print secrets" red line, moved into code.
Observed motivation: a plaintext password in a curl command entered a
transcript during this story's own planning session.

Env-var references ($VAR, ${VAR}) are exempt — indirection is the
sanctioned pattern for passing credentials.  Block by default (user
decision, 2026-08-28) with the ``PACTKIT_ALLOW_SECRET=1`` bypass for
legitimate local test scripts.
"""

import os
import re

SECRETS_BYPASS_ENV = "PACTKIT_ALLOW_SECRET"

# (name, pattern) for literal credential material.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern))
    for name, pattern in (
        ("aws-access-key", r"AKIA[0-9A-Z]{16}"),
        ("github-token", r"ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}"),
        ("gitlab-token", r"glpat-[A-Za-z0-9\-_]{20,}"),
        ("slack-token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
        ("api-key", r"\bsk-[A-Za-z0-9]{20,}"),
        ("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        # password= with a literal value; $VAR / ${VAR} indirection is exempt
        ("password-literal", r"(?i)(?:password|passwd|pwd)=(?!\$)\S+"),
    )
)

_BLOCK_MESSAGE = (
    "[FAIL] secrets-gate: the command contains literal credential material "
    "({names}) — secrets MUST NOT enter shell history or transcripts (L1).\n"
    "  Use env-var indirection instead (password=$DB_PASS), or for local "
    f"test scripts only: {SECRETS_BYPASS_ENV}=1."
)


def scan_command(command: str) -> list[str]:
    """Names of the credential patterns this command literally contains."""
    return [name for name, pattern in _SECRET_PATTERNS if pattern.search(command)]


def check_command(command: str, root, settings: dict | None = None) -> tuple[str, int]:
    """PreToolUse hook mode. Returns (message, exit_code); 2 = block."""
    from pactkit.commit_gate import _enforcement_settings

    if settings is None:
        settings = _enforcement_settings(root)
    if not settings.get("secrets_gate", True):
        return "", 0

    matched = scan_command(command)
    if not matched:
        return "", 0

    if os.environ.get(SECRETS_BYPASS_ENV, "") == "1":
        return "", 0  # explicit local-script bypass; not worth an audit record

    from pactkit.enforcement import FULL, record_status

    record_status(root, "secrets_gate", FULL, f"blocked: {', '.join(matched)} in '{command[:80]}'")
    return _BLOCK_MESSAGE.format(names=", ".join(matched)), 2
