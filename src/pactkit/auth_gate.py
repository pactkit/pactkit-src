"""STORY-slim-20260828897396a935ab: authorization gate (R4/R6).

PreToolUse gate that blocks external-effect commands (PR creation,
releases, package publishing, repo deletion) until the user has
authorized them.  The Runtime Contract's authorization list was pure
prompt text — this moves it into code.

Flow (user-confirmed design): block first with an ask-the-user message;
after explicit in-conversation confirmation the agent runs
``pactkit gate authorize <scope>`` (short-TTL token) and retries; the
strict human channel is ``PACTKIT_AUTHORIZED=1`` via the ``!`` prefix.

Honest threat model: the token is agent-invocable by design — this gate
prevents forgetting, not malice.  Every block and authorized allow is
recorded under gate name ``auth_gate``; the token file lives in
``.pactkit/enforcement/`` which the tamper guard already protects, so
the CLI is the single audited write path.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

AUTH_BYPASS_ENV = "PACTKIT_AUTHORIZED"
DEFAULT_AUTH_TTL_MINUTES = 30

# (scope, pattern) — subcommand-anchored so read-only variants
# (`gh pr view`, `gh release list`) never match.
_EXTERNAL_EFFECT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (scope, re.compile(pattern))
    for scope, pattern in (
        ("pr", r"\bgh\s+pr\s+create\b"),
        ("release", r"\bgh\s+release\s+(?:create|delete|upload)\b"),
        ("repo", r"\bgh\s+repo\s+(?:create|delete)\b"),
        ("publish", r"\b(?:npm|pnpm|yarn)\s+publish\b"),
        ("publish", r"\bcargo\s+publish\b"),
        ("publish", r"\btwine\s+upload\b"),
        ("publish", r"\bdocker\s+push\b"),
    )
)

KNOWN_SCOPES = ("pr", "release", "repo", "publish", "spec_edit")

_BLOCK_MESSAGE = (
    "[FAIL] auth-gate: `{command}` is an external-effect operation — user "
    "authorization required first.\n"
    "  1. Ask the user to confirm this action.\n"
    "  2. After explicit confirmation: `pactkit gate authorize {scope}` "
    "(valid {ttl} min), then retry.\n"
    "  3. Strict human channel: run it yourself via the `!` prefix with "
    f"{AUTH_BYPASS_ENV}=1."
)


def authorization_path(root: Path) -> Path:
    return root / ".pactkit" / "enforcement" / "authorization.json"


def authorize(root: Path, scope: str, ttl_minutes: int | None = None) -> str:
    """Write a short-TTL authorization token for the given scope."""
    if scope not in KNOWN_SCOPES:
        return f"auth-gate: unknown scope '{scope}' (known: {', '.join(KNOWN_SCOPES)})"
    minutes = DEFAULT_AUTH_TTL_MINUTES if ttl_minutes is None else int(ttl_minutes)
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {
        "schema_version": 1,
        "scope": scope,
        "expires_at": expires.isoformat(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    path = authorization_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return f"auth-gate: scope '{scope}' authorized for {minutes} minute(s)"


def _token_valid(root: Path, scope: str) -> bool:
    path = authorization_path(root)
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("scope") != scope:
        return False
    try:
        expires = datetime.fromisoformat(str(payload.get("expires_at")))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def match_scope(command: str) -> str | None:
    """The scope of the first external-effect rule this command matches."""
    for scope, pattern in _EXTERNAL_EFFECT_RULES:
        if pattern.search(command):
            return scope
    return None


def check_command(command: str, root: Path, settings: dict | None = None) -> tuple[str, int]:
    """PreToolUse hook mode. Returns (message, exit_code); 2 = block."""
    import os

    from pactkit.commit_gate import _enforcement_settings

    if settings is None:
        settings = _enforcement_settings(root)
    if not settings.get("auth_gate", True):
        return "", 0

    scope = match_scope(command)
    if scope is None:
        return "", 0

    from pactkit.enforcement import FULL, record_status

    if os.environ.get(AUTH_BYPASS_ENV, "") == "1":
        record_status(root, "auth_gate", FULL, f"{scope}: bypass via {AUTH_BYPASS_ENV}=1 (human channel)")
        return "", 0

    ttl = settings.get("auth_ttl_minutes", DEFAULT_AUTH_TTL_MINUTES)
    if _token_valid(root, scope):
        record_status(root, "auth_gate", FULL, f"{scope}: authorized (TTL token)")
        return "", 0

    record_status(root, "auth_gate", FULL, f"blocked {scope}: '{command[:80]}' — awaiting user authorization")
    return (
        _BLOCK_MESSAGE.format(command=command[:80], scope=scope, ttl=ttl),
        2,
    )
