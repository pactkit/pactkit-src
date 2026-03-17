"""PactKit CLI — Spec-driven agentic DevOps toolkit.

Usage:
    pactkit init                  # Deploy PactKit configuration
    pactkit init -t /tmp/preview  # Preview to custom directory
    pactkit update                # Re-deploy (same as init, idempotent)
    pactkit version               # Show version
"""

import argparse

from pactkit import __version__


def _schema_command(args) -> None:
    """Print document structure rules for the given type (STORY-slim-007 R7)."""
    from pactkit.schemas import SCHEMA_REGISTRY

    show_all = getattr(args, "all_types", False) or args.type == "--all"
    doc_type = None if show_all else args.type

    if doc_type and doc_type not in SCHEMA_REGISTRY:
        print(f"Unknown schema type: {doc_type!r}. Available: {', '.join(SCHEMA_REGISTRY)}")
        raise SystemExit(1)

    types_to_show = list(SCHEMA_REGISTRY) if show_all else [doc_type]

    for t in types_to_show:
        schema = SCHEMA_REGISTRY[t]
        print(f"\n{'─' * 60}")
        print(f"Schema: {t}  —  {schema['description']}")
        print(f"{'─' * 60}")
        for key, val in schema.items():
            if key == "description":
                continue
            if isinstance(val, (tuple, list)):
                print(f"  {key}:")
                for item in val:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {val}")

    if not show_all and not doc_type:
        print("Available schema types:", ", ".join(SCHEMA_REGISTRY))
        print("Usage: pactkit schema <type>  or  pactkit schema --all")


def main():
    parser = argparse.ArgumentParser(
        prog="pactkit",
        description="PactKit — Spec-driven agentic DevOps toolkit",
    )
    subparsers = parser.add_subparsers(dest="command")

    # pactkit init
    init_parser = subparsers.add_parser("init", help="Deploy PactKit configuration")
    init_parser.add_argument(
        "-t",
        "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    init_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace", "opencode"],
        default="classic",
        help="Output format: classic (default), plugin, marketplace, or opencode",
    )
    init_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), cursor, copilot, generic, or all",
    )
    # STORY-047: Enterprise flags
    init_parser.add_argument(
        "--no-git",
        action="store_true",
        default=False,
        help="Disable all git operations (enterprise: air-gapped environments)",
    )
    init_parser.add_argument(
        "--no-external",
        action="store_true",
        default=False,
        help="Disable external network calls — MCP, gh CLI, pip install (enterprise)",
    )
    init_parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Non-interactive mode: auto-accept defaults (CI/CD environments)",
    )

    # pactkit update (alias for init)
    update_parser = subparsers.add_parser("update", help="Re-deploy PactKit configuration")
    update_parser.add_argument(
        "-t",
        "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    update_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace", "opencode"],
        default="classic",
        help="Output format: classic (default), plugin, marketplace, or opencode",
    )
    update_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), cursor, copilot, generic, or all",
    )
    # STORY-047: Enterprise flags
    update_parser.add_argument(
        "--no-git",
        action="store_true",
        default=False,
        help="Disable all git operations (enterprise: air-gapped environments)",
    )
    update_parser.add_argument(
        "--no-external",
        action="store_true",
        default=False,
        help="Disable external network calls — MCP, gh CLI, pip install (enterprise)",
    )
    update_parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Non-interactive mode: auto-accept defaults (CI/CD environments)",
    )

    # pactkit upgrade (alias for init, migrates legacy scafpy files)
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade PactKit (migrate legacy scafpy config)")
    upgrade_parser.add_argument(
        "-t",
        "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    upgrade_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace", "opencode"],
        default="classic",
        help="Output format: classic (default), plugin, marketplace, or opencode",
    )
    # STORY-060: Enterprise flags for upgrade (parity with init/update)
    upgrade_parser.add_argument(
        "--no-git",
        action="store_true",
        default=False,
        help="Disable all git operations (enterprise: air-gapped environments)",
    )
    upgrade_parser.add_argument(
        "--no-external",
        action="store_true",
        default=False,
        help="Disable external network calls — MCP, gh CLI, pip install (enterprise)",
    )
    upgrade_parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Non-interactive mode: auto-accept defaults (CI/CD environments)",
    )

    # pactkit spec-lint
    spec_lint_parser = subparsers.add_parser("spec-lint", help="Validate spec file(s) structure")
    spec_lint_parser.add_argument("spec", nargs="?", help="Path to spec file to validate")
    spec_lint_parser.add_argument("--all", action="store_true", help="Validate all specs in specs dir")
    spec_lint_parser.add_argument(
        "--specs-dir",
        default="docs/specs",
        help="Directory containing spec files (default: docs/specs)",
    )

    # pactkit schema
    schema_parser = subparsers.add_parser("schema", help="Show document structure rules")
    schema_parser.add_argument(
        "type",
        nargs="?",
        choices=["spec", "board", "context", "lessons", "testcase", "--all"],
        help="Document type to show schema for",
    )
    schema_parser.add_argument("--all", action="store_true", dest="all_types", help="Show all schemas")

    # pactkit version
    subparsers.add_parser("version", help="Show PactKit version")

    args = parser.parse_args()

    if args.command in ("init", "update", "upgrade"):
        from pactkit.generators.deployer import deploy

        deploy(
            target=args.target,
            format=args.format,
            no_git=getattr(args, "no_git", False),
            no_external=getattr(args, "no_external", False),
            non_interactive=getattr(args, "non_interactive", False),
        )

    elif args.command == "spec-lint":
        from pactkit.skills.spec_linter import main as spec_lint_main

        argv = []
        if args.all:
            argv += ["--all", "--specs-dir", args.specs_dir]
        elif args.spec:
            argv += [args.spec]
        else:
            spec_lint_parser.print_help()
            raise SystemExit(1)
        raise SystemExit(spec_lint_main(argv))

    elif args.command == "schema":
        _schema_command(args)

    elif args.command == "version":
        print(f"PactKit v{__version__}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
