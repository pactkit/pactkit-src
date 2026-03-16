"""PactKit CLI — Spec-driven agentic DevOps toolkit.

Usage:
    pactkit init                  # Deploy PactKit configuration
    pactkit init -t /tmp/preview  # Preview to custom directory
    pactkit update                # Re-deploy (same as init, idempotent)
    pactkit version               # Show version
"""
import argparse

from pactkit import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="pactkit",
        description="PactKit — Spec-driven agentic DevOps toolkit",
    )
    subparsers = parser.add_subparsers(dest="command")

    # pactkit init
    init_parser = subparsers.add_parser("init", help="Deploy PactKit configuration")
    init_parser.add_argument(
        "-t", "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    init_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace"],
        default="classic",
        help="Output format: classic (default), plugin, or marketplace",
    )
    init_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "codex", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), codex, cursor, copilot, generic, or all",
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
        "-t", "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    update_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace"],
        default="classic",
        help="Output format: classic (default), plugin, or marketplace",
    )
    update_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "codex", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), codex, cursor, copilot, generic, or all",
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
        "-t", "--target",
        type=str,
        default=None,
        help="Custom target directory (default: ~/.claude)",
    )
    upgrade_parser.add_argument(
        "--format",
        type=str,
        choices=["classic", "plugin", "marketplace"],
        default="classic",
        help="Output format: classic (default), plugin, or marketplace",
    )
    upgrade_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "codex", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), codex, cursor, copilot, generic, or all",
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

    # pactkit version
    subparsers.add_parser("version", help="Show PactKit version")

    args = parser.parse_args()

    if args.command in ("init", "update", "upgrade"):
        from pactkit.generators.deployer import deploy
        deploy(
            target=args.target,
            format=args.format,
            agent=getattr(args, 'agent', 'claude'),
            no_git=getattr(args, 'no_git', False),
            no_external=getattr(args, 'no_external', False),
            non_interactive=getattr(args, 'non_interactive', False),
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

    elif args.command == "version":
        print(f"PactKit v{__version__}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
