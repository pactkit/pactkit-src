"""Global CLAUDE.md entrypoint deployment (extracted from deployer.py).

STORY-slim-202608264cf429c75e22: ownership-safe deployment of the small
global entrypoint, with fail-safe candidate proposals whenever the managed
block boundary cannot be proven.
"""

from pactkit import __version__
from pactkit.utils import atomic_write


def _is_pactkit_managed_global_md(content):
    """Detect if CLAUDE.md content is a PactKit-managed template (BUG-slim-089).

    Returns True if the first line starts with a PactKit generated heading.
    """
    first_line = content.split("\n", 1)[0] if content else ""
    return first_line.startswith(("# PactKit Global Constitution", "# PactKit Runtime Contract"))


def _deploy_claude_md(claude_root, enabled_rules):
    """Generate the small global Claude entrypoint.

    Only the Runtime Kernel is always loaded.  Phase and concern rules remain
    private to the active skill, preventing ordinary conversations from being
    captured by PDCA governance.

    BUG-slim-089: Read-before-write guard to preserve user-modified content.
    STORY-slim-202608264cf429c75e22 R5: an unreadable file is preserved with
    a candidate (ownership is unverifiable exactly when bytes cannot be
    read), and a managed file keeps any user content appended below the
    managed block.
    """
    claude_md_path = claude_root / "CLAUDE.md"
    new_header = f"# PactKit Runtime Contract (v{__version__})"
    runtime_import = "@~/.claude/rules/pactkit-runtime.md"
    new_content = f"{new_header}\n\n{runtime_import}\n"

    # Fresh install — no existing file
    if not claude_md_path.exists():
        atomic_write(claude_md_path, new_content)
        return

    # Read existing content
    try:
        existing = claude_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable file — ownership cannot be verified, so preserve it
        # untouched and propose the template alongside.
        _propose_claude_md_candidate(claude_md_path, new_content, "unreadable")
        return

    # User-modified content — do not touch (R1)
    if not _is_pactkit_managed_global_md(existing):
        return

    # PactKit-managed — refresh the managed block (header + runtime import)
    # while preserving any user content appended below it.
    lines = existing.split("\n")
    import_idx = next(
        (i for i, line in enumerate(lines) if line.strip() == runtime_import),
        None,
    )
    if import_idx is not None and any(line.strip() for line in lines[1:import_idx]):
        # Non-blank user content between the managed header and the import
        # line (or the import line appears only inside user content): the
        # managed block boundary is unrecognizable — fail safe.
        import_idx = None
    if import_idx is None:
        if not "\n".join(lines[1:]).strip():
            # The file is nothing but the managed header — provably free of
            # user content, so replace it as a whole (BUG-slim-089 AC2).
            if existing != new_content:
                atomic_write(claude_md_path, new_content)
            return
        _propose_claude_md_candidate(claude_md_path, new_content, "unrecognizable managed")
        return
    updated = new_content + "\n".join(lines[import_idx + 1:])
    if existing != updated:
        atomic_write(claude_md_path, updated)
    # else: idempotent — skip write (AC5)


def _propose_claude_md_candidate(claude_md_path, new_content, reason):
    """Write the new template as a .pactkit-new sibling, original untouched."""
    candidate = claude_md_path.with_suffix(claude_md_path.suffix + ".pactkit-new")
    atomic_write(candidate, new_content)
    print(
        f"  ⚠️  preserved {reason} CLAUDE.md: {claude_md_path}; "
        f"wrote candidate {candidate.name}"
    )
