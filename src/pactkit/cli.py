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

    # pactkit guard (STORY-slim-014 R1)
    subparsers.add_parser("guard", help="Check project init markers")

    # pactkit next-id (STORY-slim-014 R1)
    subparsers.add_parser("next-id", help="Generate next Story ID")

    # pactkit clean (STORY-slim-014 R1)
    clean_parser = subparsers.add_parser("clean", help="Remove temp artifacts")
    clean_parser.add_argument("--stack", default="auto", help="Language stack (default: auto)")
    clean_parser.add_argument("--dry-run", action="store_true", help="List files without deleting")

    # pactkit regression (STORY-slim-014 R1)
    regression_parser = subparsers.add_parser("regression", help="Classify changes for regression testing")
    regression_parser.add_argument("files", nargs="*", help="Changed file paths (default: git diff)")

    # pactkit context (STORY-slim-014 R1)
    subparsers.add_parser("context", help="Generate docs/product/context.md")

    # pactkit sec-scope (STORY-slim-014 R6)
    sec_scope_parser = subparsers.add_parser("sec-scope", help="Auto-detect security scope")
    sec_scope_parser.add_argument("files", nargs="*", help="Changed file paths")

    # pactkit lint-context (STORY-slim-014 R2)
    lint_ctx_parser = subparsers.add_parser("lint-context", help="Validate context.md structure")
    lint_ctx_parser.add_argument("path", nargs="?", default="docs/product/context.md", help="Path to context.md")

    # pactkit lint-lessons (STORY-slim-014 R2)
    lint_les_parser = subparsers.add_parser("lint-lessons", help="Validate lessons.md structure")
    lint_les_parser.add_argument(
        "path", nargs="?", default="docs/architecture/governance/lessons.md", help="Path to lessons.md"
    )

    # pactkit lint-testcase (STORY-slim-014 R2)
    lint_tc_parser = subparsers.add_parser("lint-testcase", help="Validate test case file structure")
    lint_tc_parser.add_argument("path", help="Path to test case file")

    # pactkit visualize --lazy (STORY-slim-014 R7)
    viz_parser = subparsers.add_parser("visualize", help="Visualize code dependency graph")
    viz_parser.add_argument("--lazy", action="store_true", help="Skip if no source changes")
    viz_parser.add_argument("--stack", default="auto", help="Language stack (default: auto)")

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

    elif args.command == "guard":
        from pathlib import Path

        from pactkit.guards import check_init_markers

        ok, missing = check_init_markers(Path.cwd())
        if ok:
            print("Guard: PASS — all init markers present")
        else:
            for m in missing:
                print(f"  ✗ {m}")
            raise SystemExit(1)

    elif args.command == "next-id":
        from pathlib import Path

        from pactkit.config import load_config
        from pactkit.id_generator import next_story_id

        cfg = load_config()
        specs_dir = Path.cwd() / "docs" / "specs"
        print(next_story_id(specs_dir=specs_dir, developer=cfg.get("developer", "")))

    elif args.command == "clean":
        from pathlib import Path

        from pactkit.cleaners import clean_artifacts

        removed = clean_artifacts(Path.cwd(), stack=args.stack, dry_run=args.dry_run)
        if removed:
            prefix = "Would remove" if args.dry_run else "Removed"
            for p in removed:
                print(f"  {prefix}: {p}")
            print(f"{prefix} {len(removed)} item(s)")
        else:
            print("Nothing to clean")

    elif args.command == "regression":
        import subprocess

        from pactkit.regression import classify_changes

        files = args.files
        if not files:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
            )
            files = [f for f in result.stdout.strip().split("\n") if f]
        strategy, reason = classify_changes(files)
        print(f"{strategy.upper()} — {reason}")
        raise SystemExit(0 if strategy == "skip" else 0)

    elif args.command == "context":
        from pathlib import Path

        from pactkit.context_gen import generate_context

        content = generate_context(Path.cwd(), command="pactkit context")
        ctx_path = Path.cwd() / "docs" / "product" / "context.md"
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text(content, encoding="utf-8")
        print(f"Generated {ctx_path}")

    elif args.command == "sec-scope":
        from pathlib import Path

        from pactkit.sec_scope import detect_security_scope, format_markdown_table

        if not args.files:
            print("Usage: pactkit sec-scope <file1> [file2 ...]")
            raise SystemExit(1)
        results = detect_security_scope(args.files, project_root=Path.cwd())
        print(format_markdown_table(results))

    elif args.command == "lint-context":
        from pathlib import Path

        from pactkit.validators import lint_context

        errors = lint_context(Path(args.path))
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            raise SystemExit(1)
        else:
            print(f"{args.path}\n  Result: PASS")

    elif args.command == "lint-lessons":
        from pathlib import Path

        from pactkit.validators import lint_lessons

        errors = lint_lessons(Path(args.path))
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            raise SystemExit(1)
        else:
            print(f"{args.path}\n  Result: PASS")

    elif args.command == "lint-testcase":
        from pathlib import Path

        from pactkit.validators import lint_testcase

        errors = lint_testcase(Path(args.path))
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            raise SystemExit(1)
        else:
            print(f"{args.path}\n  Result: PASS")

    elif args.command == "visualize":
        if args.lazy:
            from pathlib import Path

            from pactkit.lazy_visualize import should_visualize

            should_run, reason = should_visualize(Path.cwd(), stack=args.stack)
            if not should_run:
                print(reason)
                raise SystemExit(0)
            print(f"Visualize needed: {reason}")
        # Fall through to actual visualize (existing skill handles it)
        print("Run visualize skill for full graph generation")

    elif args.command == "version":
        print(f"PactKit v{__version__}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
