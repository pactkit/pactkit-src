"""PactKit CLI — Spec-driven agentic DevOps toolkit.

Usage:
    pactkit init                  # Deploy PactKit configuration
    pactkit init -t /tmp/preview  # Preview to custom directory
    pactkit update                # Re-deploy (same as init, idempotent)
    pactkit version               # Show version
"""

import argparse

from pactkit import __version__
from pactkit.profiles import VALID_FORMATS


def _schema_command(args) -> None:
    """Print document structure rules for the given type (STORY-slim-007 R7)."""
    from pactkit.schemas import SCHEMA_REGISTRY

    # STORY-slim-135 R5: config discoverability report
    if getattr(args, "type", None) == "config" and not getattr(args, "all_types", False):
        from pathlib import Path

        from pactkit.config import schema_config_report

        print(schema_config_report(Path.cwd()))
        return

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
        choices=sorted(VALID_FORMATS),
        default="all",
        help="Output format: all (default, deploy all installed IDEs), or a specific format",
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
    init_parser.add_argument(
        "--allow-adapter-skew",
        action="store_true",
        default=False,
        help="Allow deploying an adapter whose major.minor differs from core (STORY-slim-145 R6)",
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
        choices=sorted(VALID_FORMATS),
        default="all",
        help="Output format: all (default, deploy all installed IDEs), or a specific format",
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
    # STORY-slim-023: Auto version sync
    update_parser.add_argument(
        "--if-needed",
        action="store_true",
        default=False,
        help="Only redeploy if installed version differs from global deploy marker",
    )
    update_parser.add_argument(
        "--allow-adapter-skew",
        action="store_true",
        default=False,
        help="Allow deploying an adapter whose major.minor differs from core (STORY-slim-145 R6)",
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
        choices=sorted(VALID_FORMATS),
        default="all",
        help="Output format: all (default, deploy all installed IDEs), or a specific format",
    )
    upgrade_parser.add_argument(
        "--agent",
        type=str,
        choices=["claude", "cursor", "copilot", "generic", "all"],
        default="claude",
        help="Target agent format: claude (default), cursor, copilot, generic, or all",
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
        choices=["spec", "board", "context", "lessons", "testcase", "config", "--all"],
        help="Document type to show schema for ('config' lists all pactkit.yaml keys)",
    )
    schema_parser.add_argument("--all", action="store_true", dest="all_types", help="Show all schemas")

    # pactkit guard (STORY-slim-014 R1, HOTFIX-slim-087)
    guard_parser = subparsers.add_parser("guard", help="Check project init markers")
    guard_parser.add_argument(
        "-C", "--project-root", type=str, default=None,
        help="Project root directory (defaults to CWD)",
    )

    # pactkit next-id (STORY-slim-014 R1)
    subparsers.add_parser("next-id", help="Generate next Story ID")

    # pactkit clean (STORY-slim-014 R1)
    clean_parser = subparsers.add_parser("clean", help="Remove temp artifacts")
    clean_parser.add_argument("--stack", default="auto", help="Language stack (default: auto)")
    clean_parser.add_argument("--dry-run", action="store_true", help="List files without deleting")

    # pactkit regression (STORY-slim-014 R1)
    regression_parser = subparsers.add_parser("regression", help="Classify changes for regression testing")
    regression_parser.add_argument("files", nargs="*", help="Changed file paths (default: git diff)")

    # pactkit context (STORY-slim-014 R1, STORY-slim-071 continuation)
    ctx_parser = subparsers.add_parser("context", help="Generate docs/product/context.md")
    ctx_parser.add_argument("--continuation", action="store_true", default=False,
                            help="Update Agent Continuation section")
    ctx_parser.add_argument("--last-command", default=None, help="Last PDCA command run")
    ctx_parser.add_argument("--phase", default=None, help="Phase reached")
    ctx_parser.add_argument("--blockers", default=None, help="Blockers or open questions")

    # pactkit sec-scope (STORY-slim-014 R6)
    sec_scope_parser = subparsers.add_parser("sec-scope", help="Auto-detect security scope")
    sec_scope_parser.add_argument("files", nargs="*", help="Changed file paths")

    # pactkit spec-graph (STORY-slim-143)
    spec_graph_parser = subparsers.add_parser(
        "spec-graph", help="Story dependency graph: execution waves + conflict matrix"
    )
    spec_graph_parser.add_argument(
        "--specs-dir", default="docs/specs", help="Directory containing spec files"
    )
    spec_graph_parser.add_argument(
        "--write-graph", action="store_true", help="Write Mermaid graph to --graph-path"
    )
    spec_graph_parser.add_argument(
        "--graph-path", default="docs/architecture/graphs/story_graph.mmd", help="Mermaid output path"
    )
    spec_graph_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON (waves + conflicts)"
    )

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

    # pactkit visualize --lazy --mode (STORY-slim-014 R7, HOTFIX-slim-023)
    viz_parser = subparsers.add_parser("visualize", help="Visualize code dependency graph")
    viz_parser.add_argument("--lazy", action="store_true", help="Skip if no source changes")
    viz_parser.add_argument("--stack", default="auto", help="Language stack (default: auto)")
    viz_parser.add_argument(
        "--mode", choices=["file", "class", "call", "module"], default=None,
        help="Graph mode (default: all three)",
    )
    # HOTFIX-slim-070: expose visualize.py args to CLI
    viz_parser.add_argument("--entry", default=None, help="Entry function for call graph BFS")
    viz_parser.add_argument("--focus", default=None, help="Focus on specific module")
    viz_parser.add_argument("--reverse", action="store_true", default=False, help="Reverse BFS: find callers of entry")
    viz_parser.add_argument("--depth", type=int, default=0, help="Limit traversal depth (0=unlimited)")
    viz_parser.add_argument("--max-nodes", type=int, default=0, help="Truncate graph to N nodes (0=unlimited)")
    viz_parser.add_argument("--sync", action="store_true", help="Force codegraph sync even if graphs are skipped")

    # pactkit sync (STORY-slim-126: codegraph sync code enforcement)
    subparsers.add_parser("sync", help="Sync codegraph index")

    # pactkit garden (STORY-slim-070)
    garden_parser = subparsers.add_parser("garden", help="Codebase quality patrol")
    garden_parser.add_argument("--json", action="store_true", default=False, help="JSON output")
    garden_parser.add_argument("--scope", default=None, help="Scan only this directory (relative path)")

    # pactkit observe (STORY-slim-073)
    observe_parser = subparsers.add_parser("observe", help="Collect runtime observability signals")
    observe_parser.add_argument("--report", action="store_true", default=False, help="Human-readable report")
    observe_parser.add_argument("--json", action="store_true", default=False, help="JSON output")

    # pactkit doctor (STORY-slim-015 R1-R3)
    subparsers.add_parser("doctor", help="Diagnose project health")

    # pactkit audit (STORY-slim-091)
    audit_parser = subparsers.add_parser("audit", help="H1-H7 AI Readiness Assessment")
    audit_parser.add_argument("--json", action="store_true", default=False, help="JSON output only")
    audit_parser.add_argument("--layer", default=None, help="Check single layer (H1-H7)")
    audit_parser.add_argument("--append", action="store_true", default=False, help="Silent update for Done integration")
    audit_parser.add_argument("--verbose", action="store_true", default=False, help="Full detail")
    audit_parser.add_argument(
        "--if-needed", dest="if_needed", action="store_true", default=False,
        help="Skip if harness_audit.json already covers the given story ID",
    )
    audit_parser.add_argument(
        "story_id", nargs="?", default=None,
        help="Story ID for --if-needed dedup (e.g. STORY-slim-014)",
    )

    # pactkit report (STORY-slim-094)
    report_parser = subparsers.add_parser("report", help="Generate unified HTML architecture dashboard")
    report_parser.add_argument("--input", default=None, help="Single .mmd file (generates individual .html)")
    report_parser.add_argument("--output", default=None, help="Output .html path (default: same name as input)")
    report_parser.add_argument(
        "--all", dest="all_mode", action="store_true", default=False,
        help="Generate unified report from all .mmd files",
    )

    # pactkit backfill-release (STORY-slim-015 R4)
    backfill_parser = subparsers.add_parser("backfill-release", help="Replace Release: TBD in completed specs")
    backfill_parser.add_argument("version", help="Version string to backfill (e.g. 2.3.0)")

    # pactkit issue-sync (STORY-slim-015 R5)
    issue_sync_parser = subparsers.add_parser("issue-sync", help="Sync GitHub issue for BUG/HOTFIX items")
    issue_sync_parser.add_argument("item_id", help="Item ID (e.g. BUG-slim-003)")

    # pactkit test-map (STORY-slim-016 R1)
    test_map_parser = subparsers.add_parser("test-map", help="Map source files to test files")
    test_map_parser.add_argument("files", nargs="*", help="Source file paths")

    # pactkit lint (STORY-slim-016 R2)
    lint_parser = subparsers.add_parser("lint", help="Run stack-aware lint")
    lint_parser.add_argument("--fix", action="store_true", help="Auto-fix lint errors")

    # pactkit lesson-append (STORY-slim-017 R1)
    lesson_parser = subparsers.add_parser("lesson-append", help="Append lesson with dedup check")
    lesson_parser.add_argument("--story", required=True, help="Story ID (e.g. STORY-017)")
    lesson_parser.add_argument("--text", required=True, help="Lesson text")
    lesson_parser.add_argument("--context", default="", help="Context (file:func)")

    # pactkit invariants-refresh (STORY-slim-017 R2)
    inv_parser = subparsers.add_parser("invariants-refresh", help="Update test count in rules.md")
    inv_parser.add_argument("--test-count", type=int, required=True, help="New test count")

    # pactkit coverage-gate (STORY-slim-017 R3)
    cov_parser = subparsers.add_parser("coverage-gate", help="Run coverage verification")
    cov_parser.add_argument("files", nargs="+", help="Changed source file paths")

    # pactkit spec-status (STORY-slim-018 R3)
    spec_status_parser = subparsers.add_parser("spec-status", help="Update Status field in a spec file")
    spec_status_parser.add_argument("spec", help="Path to spec file")
    spec_status_parser.add_argument("status", choices=["Draft", "In Progress", "Done"], help="New status value")

    # pactkit done-verify (STORY-slim-136: mechanical archive honesty gate)
    done_verify_parser = subparsers.add_parser(
        "done-verify", help="Verify archive honesty for a story (evidence chain, exit 1 on FAIL)"
    )
    done_verify_parser.add_argument("story_id", help="Story ID (e.g. STORY-slim-001)")

    # pactkit commit-gate (STORY-slim-138: pre-commit test gate)
    gate_parser = subparsers.add_parser("commit-gate", help="Pre-commit test gate (skip != pass transparency)")
    gate_parser.add_argument(
        "--hook", action="store_true",
        help="PreToolUse hook mode: read hook JSON from stdin, exit 2 blocks git commit",
    )
    gate_parser.add_argument(
        "--install-git-hook", action="store_true",
        help="Install .git/hooks/pre-commit wrapper for human commits",
    )

    # pactkit deps (STORY-slim-137: external dependency check/install)
    deps_parser = subparsers.add_parser("deps", help="Check or install external dependencies (node/codegraph/gh)")
    deps_sub = deps_parser.add_subparsers(dest="deps_action")
    deps_check = deps_sub.add_parser("check", help="Read-only dependency status report")
    deps_check.add_argument("--json", action="store_true", help="JSON output")
    deps_install = deps_sub.add_parser("install", help="Guided install of missing dependencies")
    deps_install.add_argument("--yes", action="store_true", help="Skip per-item confirmation")

    # pactkit interface-summary (STORY-slim-113)
    iface_parser = subparsers.add_parser("interface-summary", help="Output interface summary (signatures only)")
    iface_parser.add_argument("files", nargs="+", help="Source file(s) to summarize")

    # pactkit redetect-stack (STORY-slim-077)
    subparsers.add_parser("redetect-stack", help="Re-detect project stacks and update pactkit.yaml")

    # pactkit query (STORY-slim-121, STORY-slim-124: codegraph integration)
    query_parser = subparsers.add_parser(
        "query", help="Query codegraph call graph (requires graph_provider: codegraph)"
    )
    query_mode = query_parser.add_mutually_exclusive_group(required=True)
    query_mode.add_argument("--callers", metavar="FUNC", help="Fan-in: list all callers of FUNC")
    query_mode.add_argument("--callees", metavar="FUNC", help="Fan-out: list all callees of FUNC")
    query_mode.add_argument("--chain", metavar="FUNC", help="Transitive chain for FUNC")
    query_parser.add_argument(
        "--down", action="store_true",
        help="With --chain: downstream callees (default: upstream callers)",
    )
    query_parser.add_argument("--db", metavar="PATH", help="Override default .codegraph/codegraph.db path")

    # pactkit version
    subparsers.add_parser("version", help="Show PactKit version")

    args = parser.parse_args()

    # Auto-deploy on version mismatch: after pip upgrade, the next pactkit command
    # transparently syncs deployed files without requiring explicit `pactkit init`.
    if args.command and args.command not in ("init", "update", "upgrade", "version"):
        from pathlib import Path

        marker = Path.home() / ".claude" / ".pactkit-version"
        needs_deploy = not marker.exists() or marker.read_text().strip() != __version__
        if needs_deploy:
            from pactkit.generators.deployer import deploy

            print(f"PactKit {__version__} detected — auto-syncing deployed files...")
            deploy(format="all")

    if args.command in ("init", "update", "upgrade"):
        # STORY-slim-102: --if-needed checks global deploy marker, not project yaml
        if args.command == "update" and getattr(args, "if_needed", False):
            from pathlib import Path

            marker = Path.home() / ".claude" / ".pactkit-version"
            if marker.exists():
                deployed_version = marker.read_text().strip()
                if deployed_version == __version__:
                    print(f"PactKit {__version__} up-to-date — skipping redeploy")
                    raise SystemExit(0)
            else:
                print("No pactkit.yaml found. Running first-time setup...")

        from pactkit.generators.deployer import deploy

        # STORY-slim-145 R6: gate adapter compat before any managed file is
        # written (AC5). Single-format mismatch blocks before dispatch; the
        # --allow-adapter-skew override skips the block with a warning.
        if args.format not in ("all", "classic", "plugin", "marketplace"):
            _allow_skew = getattr(args, "allow_adapter_skew", False)
            _errors = _check_adapter_compat(args.format, allow_skew=_allow_skew)
            if _errors:
                for _e in _errors:
                    print(f"  ✗ {_e}")
                raise SystemExit(1)
            if _allow_skew:
                print(
                    f"  ⚠ --allow-adapter-skew: compatibility NOT verified for "
                    f"{args.format}; proceeding at your own risk."
                )

        # STORY-slim-135 R4: sync config copies BEFORE deploy reads config
        # (canonical = .claude first). Real deploys only.
        if args.target is None:
            from pathlib import Path

            from pactkit.config import sync_config_copies

            for synced in sync_config_copies(Path.cwd()):
                print(f"  -> Synced config copy: {synced}")

        deploy(
            target=args.target,
            format=args.format,
            agent=getattr(args, "agent", "claude"),
            no_git=getattr(args, "no_git", False),
            no_external=getattr(args, "no_external", False),
            non_interactive=getattr(args, "non_interactive", False),
            allow_skew=getattr(args, "allow_adapter_skew", False),
        )

        # Post-deploy housekeeping for real deploys: commit-gate channel
        # dispatch (STORY-slim-138 R4 settings hook; STORY-slim-140 R1 git-hook
        # fallback for non-Claude formats) + read-only deps summary (slim-137).
        if args.target is None:
            from pathlib import Path

            from pactkit.commit_gate import ensure_gate_channel
            from pactkit.deps import check_deps, render_check_report

            print(f"  -> commit gate: {ensure_gate_channel(Path.cwd(), args.format)}")
            report = render_check_report(check_deps())
            if "❌" in report:
                print(f"\n{report}")

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

        from pactkit.guards import check_init_markers, check_version_mismatch

        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        ok, missing = check_init_markers(project_root)
        if ok:
            print("Guard: PASS — all init markers present")
            # HOTFIX-slim-024: check version mismatch
            version_warn = check_version_mismatch(project_root)
            if version_warn:
                print(f"  ⚠️  {version_warn}")
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
        # Workflow impact — informational only (STORY-slim-038)
        try:
            from pactkit.skills.visualize import regression_workflow_impact

            wf_lines = regression_workflow_impact(".", files)
            for line in wf_lines:
                print(line)
        except Exception:
            pass  # Graceful degradation (R4)
        raise SystemExit(0 if strategy == "skip" else 0)

    elif args.command == "context":
        from pathlib import Path

        from pactkit.context_gen import generate_context

        continuation_args = None
        if args.continuation and args.last_command:
            continuation_args = {"last_command": args.last_command}
            if args.phase:
                continuation_args["phase"] = args.phase
            if args.blockers:
                continuation_args["blockers"] = args.blockers

        content = generate_context(
            Path.cwd(),
            command="pactkit context",
            continuation_args=continuation_args,
        )
        ctx_path = Path.cwd() / "docs" / "product" / "context.md"
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text(content, encoding="utf-8")
        print(f"Generated {ctx_path}")

    elif args.command == "spec-graph":
        from pactkit.spec_graph import main as spec_graph_main

        argv = ["--specs-dir", args.specs_dir, "--graph-path", args.graph_path]
        if args.write_graph:
            argv.append("--write-graph")
        if args.json:
            argv.append("--json")
        raise SystemExit(spec_graph_main(argv))

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
        from pathlib import Path

        from pactkit.lazy_visualize import codegraph_sync, run_visualize_graphs, run_visualize_single, should_visualize

        project_root = Path.cwd()
        if args.lazy:
            should_run, reason = should_visualize(project_root, stack=args.stack)
            if not should_run:
                if args.sync:
                    synced, msg = codegraph_sync(project_root)
                    if synced:
                        print(f"🔄 {msg}")
                    elif "skipped" not in msg:
                        print(f"codegraph: {msg}")
                print(reason)
                raise SystemExit(0)
            print(f"Visualize needed: {reason}")
        # HOTFIX-slim-023: support --mode for single or all modes
        if args.mode:
            run_visualize_single(
                project_root, args.mode,
                entry=args.entry, focus=args.focus, reverse=args.reverse,
                depth=args.depth, max_nodes=args.max_nodes,
            )
        else:
            run_visualize_graphs(project_root, focus=args.focus)

    elif args.command == "sync":
        from pathlib import Path

        from pactkit.lazy_visualize import codegraph_sync

        project_root = Path.cwd()
        synced, msg = codegraph_sync(project_root)
        if synced:
            print(f"🔄 {msg}")
        else:
            print(f"codegraph: {msg}")

    elif args.command == "garden":
        from pathlib import Path

        from pactkit.garden import run_garden

        root = Path.cwd()
        scope = Path(args.scope) if args.scope else None
        output, exit_code = run_garden(root, scope=scope, json_output=args.json)
        print(output)
        raise SystemExit(exit_code)

    elif args.command == "observe":
        from pactkit.observe import run_observe

        output, exit_code = run_observe(report=args.report, json_output=args.json)
        print(output)
        raise SystemExit(exit_code)

    elif args.command == "report":
        from pactkit.skills.report import generate as run_report

        # Default: --all mode (convenience entry per R7)
        all_mode = args.all_mode or (not args.input)
        output = run_report(
            input_file=args.input, output_file=args.output, all_mode=all_mode,
        )
        if output:
            print(output)

    elif args.command == "audit":
        from pactkit.audit import audit as run_audit

        output = run_audit(
            json_only=args.json, layer=args.layer, append=args.append,
            verbose=args.verbose, if_needed=args.if_needed,
            story_id=args.story_id,
        )
        if output and not args.append:
            print(output)

    elif args.command == "doctor":
        from pathlib import Path

        from pactkit.doctor import check_config_drift, check_hld_module_count, check_orphaned_specs, check_stale_graphs

        root = Path.cwd()
        has_issues = False

        # R1: Orphaned/missing specs
        spec_result = check_orphaned_specs(root)
        for item in spec_result["orphaned"]:
            print(f"  Orphaned: {item['id']} (spec exists, not on board)")
            has_issues = True
        for item in spec_result["missing"]:
            print(f"  Missing: {item['id']} (on board, no spec file)")
            has_issues = True

        # R2: Config drift
        drift_result = check_config_drift(root)
        for item in drift_result["missing_deployments"]:
            print(f"  Drift: {item['type']} '{item['name']}' configured but not deployed")
            has_issues = True

        # R3: Stale graphs
        stale_result = check_stale_graphs(root)
        if stale_result.get("missing"):
            print("  Missing: docs/architecture/graphs/ directory not found")
            has_issues = True
        for item in stale_result["stale"]:
            print(f"  Stale: {item['file']} ({item['days_behind']} days behind source)")
            has_issues = True

        # R4 (BUG-slim-006): HLD module count drift
        hld_result = check_hld_module_count(root)
        if hld_result["drift"] > 3:
            print(f"  HLD drift: {hld_result['drift']} modules not in system_design.mmd "
                  f"(source: {hld_result['source_modules']}, hld: {hld_result['hld_nodes']})")
            has_issues = True

        # STORY-slim-135 R4: pactkit.yaml multi-copy drift
        from pactkit.config import check_config_copy_drift

        copy_drift = check_config_copy_drift(root)
        if copy_drift["drift"]:
            for detail in copy_drift["details"]:
                print(f"  Config copy drift: {detail}")
            print("  → Run `pactkit update` to sync all config copies")
            has_issues = True

        # STORY-slim-137 R4: external dependency health — report-only (these
        # are optional enhancements; missing ones must not fail doctor in
        # minimal/CI environments — Spec AC6 amended 2026-08-13)
        from pactkit.deps import check_deps

        for s in check_deps():
            if not s.installed:
                print(f"  ⚠️  Optional dependency missing: {s.name} — {s.purpose}")
                print(f"    install: {s.install_hint}")

        # STORY-slim-139 R3: deployment parity across formats
        from pactkit.doctor import check_deploy_parity

        parity = check_deploy_parity(root)
        for detail in parity["details"]:
            print(f"  {detail}")
            has_issues = True
        for warning in parity["warnings"]:
            print(f"  ⚠️  {warning}")

        # STORY-slim-142 R3: adapter package version skew (report-only)
        from pactkit.doctor import check_adapter_skew

        for warning in check_adapter_skew():
            print(f"  ⚠️  {warning}")

        # STORY-slim-145 R6/AC6: core source vs distribution metadata divergence
        # (editable/partial install). Report and mark needs-attention — doctor
        # must not claim the installation is aligned when source != distribution.
        from pactkit.doctor import check_core_metadata_divergence

        for warning in check_core_metadata_divergence():
            print(f"  ⚠️  {warning}")
            has_issues = True

        if not has_issues:
            print("Health: OK")
        else:
            print("Health: NEEDS ATTENTION")
            raise SystemExit(1)

    elif args.command == "backfill-release":
        from pathlib import Path

        from pactkit.backfill import scan_and_replace_tbd

        result = scan_and_replace_tbd(Path.cwd(), args.version)
        for item in result["backfilled"]:
            print(f"  Backfilled: {item['id']} → {args.version}")
        for item in result["skipped"]:
            print(f"  Skipped: {item['id']} ({item['reason']})")
        if not result["backfilled"] and not result["skipped"]:
            print("No specs with Release: TBD found")

    elif args.command == "issue-sync":
        from pathlib import Path

        from pactkit.issue_sync import issue_sync

        result = issue_sync(args.item_id, Path.cwd())
        print(result["message"])
        if result["action"] == "error":
            raise SystemExit(1)

    elif args.command == "test-map":
        from pathlib import Path

        from pactkit.test_mapper import map_to_tests

        if not args.files:
            print("Usage: pactkit test-map <file1> [file2 ...]")
            raise SystemExit(1)
        result = map_to_tests(args.files, Path.cwd())
        for test_path in result["mapped"]:
            print(test_path)

    elif args.command == "lint":
        from pathlib import Path

        from pactkit.lint_runner import run_lint

        result = run_lint(Path.cwd(), fix=args.fix)
        if result["stdout"]:
            print(result["stdout"])
        if result["exit_code"] == 0:
            print(result["message"])
        else:
            print(result["message"])
            if result["blocking"]:
                raise SystemExit(result["exit_code"])

    elif args.command == "lesson-append":
        from pathlib import Path

        from pactkit.lessons import append_lesson

        result = append_lesson(Path.cwd(), args.story, args.text, args.context)
        import json
        print(json.dumps(result))

    elif args.command == "invariants-refresh":
        from pathlib import Path

        from pactkit.invariants import refresh_test_count

        result = refresh_test_count(Path.cwd(), args.test_count)
        import json
        print(json.dumps(result))

    elif args.command == "coverage-gate":
        from pathlib import Path

        from pactkit.coverage_gate import check_coverage

        result = check_coverage(args.files, Path.cwd())
        import json
        print(json.dumps(result, indent=2))

    elif args.command == "spec-status":
        from pathlib import Path

        from pactkit.spec_status import update_spec_status

        result = update_spec_status(Path(args.spec), args.status)
        print(result["message"])
        if result["action"] == "error":
            raise SystemExit(1)

    elif args.command == "done-verify":
        from pathlib import Path

        from pactkit.done_verify import verify_story

        results, exit_code = verify_story(args.story_id, Path.cwd())
        for r in results:
            print(r.render())
        print(f"\ndone-verify: {'FAIL' if exit_code else 'PASS'} ({args.story_id})")
        raise SystemExit(exit_code)

    elif args.command == "deps":
        import json as _json
        from dataclasses import asdict
        from pathlib import Path

        from pactkit.deps import check_deps, install_deps, render_check_report

        if args.deps_action == "install":
            lines, exit_code = install_deps(Path.cwd(), assume_yes=args.yes)
            for ln in lines:
                print(ln)
            raise SystemExit(exit_code)
        # default: check
        statuses = check_deps()
        if getattr(args, "json", False):
            print(_json.dumps([asdict(s) for s in statuses], indent=2, ensure_ascii=False))
        else:
            print(render_check_report(statuses))
        raise SystemExit(0 if all(s.installed for s in statuses) else 1)

    elif args.command == "commit-gate":
        import sys
        from pathlib import Path

        from pactkit.commit_gate import hook_entry, install_git_hook, run_gate

        if args.install_git_hook:
            print(install_git_hook(Path.cwd()))
            raise SystemExit(0)
        if args.hook:
            message, exit_code = hook_entry(sys.stdin.read(), Path.cwd())
            if message:
                print(message, file=sys.stderr)
            raise SystemExit(exit_code)
        result = run_gate(Path.cwd())
        print(result.render())
        raise SystemExit(result.exit_code)

    elif args.command == "interface-summary":
        from pathlib import Path

        from pactkit.skills.interface_summary import generate_summary

        paths = [Path(f) for f in args.files]
        print(generate_summary(paths))

    elif args.command == "redetect-stack":
        from pathlib import Path

        import yaml as _yaml

        from pactkit.cleaners import detect_stacks
        from pactkit.config import update_yaml_stack
        from pactkit.profiles import PACTKIT_YAML_CANDIDATES

        cwd = Path.cwd()
        yaml_paths = [cwd / c for c in PACTKIT_YAML_CANDIDATES if (cwd / c).exists()]
        if not yaml_paths:
            print("❌ No pactkit.yaml found. Run `pactkit init` first.")
            raise SystemExit(1)

        new_stacks = detect_stacks(cwd)
        new_display = new_stacks[0] if len(new_stacks) == 1 else new_stacks

        for yaml_path in yaml_paths:
            old_data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            old_stack = old_data.get("stack", "auto")
            update_yaml_stack(yaml_path, new_stacks)
            print(f"Stack updated: {old_stack} → {new_display}")
            print(f"  📄 {yaml_path}")

    elif args.command == "version":
        print(f"PactKit v{__version__}")

    elif args.command == "query":
        import sqlite3
        import sys
        from pathlib import Path

        from pactkit.config import load_config

        config = load_config()
        graph_provider = config.get("visualize", {}).get("graph_provider")

        if not graph_provider or graph_provider != "codegraph":
            print(
                "❌ pactkit query requires graph_provider: codegraph\n"
                "Configure in pactkit.yaml:\n"
                "  visualize:\n"
                "    graph_provider: codegraph\n"
                "Then run: codegraph init\n\n"
                "Or use grep on .mmd files directly:\n"
                "  grep \"<func>\" docs/architecture/graphs/call_graph.mmd",
                file=sys.stderr,
            )
            raise SystemExit(1)

        default_db = Path.cwd() / ".codegraph" / "codegraph.db"
        db_path = Path(args.db) if args.db else default_db

        if not db_path.exists():
            import shutil
            import subprocess
            if shutil.which("codegraph"):
                print("⚙️ codegraph.db not found — running codegraph init...",
                      file=sys.stderr)
                result = subprocess.run(
                    ["codegraph", "init", "-i"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    print(f"❌ codegraph init failed:\n{result.stderr}",
                          file=sys.stderr)
                    raise SystemExit(1)
                if not db_path.exists():
                    print("❌ codegraph init completed but db not created",
                          file=sys.stderr)
                    raise SystemExit(1)
            else:
                print(
                    f"❌ codegraph.db not found at {db_path}\n"
                    "Install codegraph: npm i -g @colbymchenry/codegraph\n"
                    "Then run: codegraph init",
                    file=sys.stderr,
                )
                raise SystemExit(1)

        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            if args.callers:
                rows = con.execute(
                    """
                    SELECT DISTINCT ns.name, ns.file_path, ns.start_line
                    FROM edges e
                    JOIN nodes ns ON e.source = ns.id
                    JOIN nodes nt ON e.target = nt.id
                    WHERE e.kind = 'calls' AND nt.name LIKE ?
                    """,
                    (f"%{args.callers}%",),
                ).fetchall()
            elif args.callees:
                rows = con.execute(
                    """
                    SELECT DISTINCT nt.name, nt.file_path, nt.start_line
                    FROM edges e
                    JOIN nodes ns ON e.source = ns.id
                    JOIN nodes nt ON e.target = nt.id
                    WHERE e.kind = 'calls' AND ns.name LIKE ?
                    """,
                    (f"%{args.callees}%",),
                ).fetchall()
            else:  # --chain
                if args.down:
                    rows = con.execute(
                        """
                        WITH RECURSIVE chain(id) AS (
                            SELECT DISTINCT e.target
                            FROM edges e JOIN nodes n ON e.source = n.id
                            WHERE e.kind = 'calls' AND n.name LIKE ?
                            UNION
                            SELECT e.target FROM edges e
                            JOIN chain c ON e.source = c.id
                            WHERE e.kind = 'calls'
                        )
                        SELECT DISTINCT n.name, n.file_path, n.start_line
                        FROM chain c JOIN nodes n ON c.id = n.id
                        """,
                        (f"%{args.chain}%",),
                    ).fetchall()
                else:
                    rows = con.execute(
                        """
                        WITH RECURSIVE chain(id) AS (
                            SELECT DISTINCT e.source
                            FROM edges e JOIN nodes n ON e.target = n.id
                            WHERE e.kind = 'calls' AND n.name LIKE ?
                            UNION
                            SELECT e.source FROM edges e
                            JOIN chain c ON e.target = c.id
                            WHERE e.kind = 'calls'
                        )
                        SELECT DISTINCT n.name, n.file_path, n.start_line
                        FROM chain c JOIN nodes n ON c.id = n.id
                        """,
                        (f"%{args.chain}%",),
                    ).fetchall()
        finally:
            con.close()

        for name, file_path, start_line in sorted(rows):
            print(f"{name} ({file_path}:{start_line})")

    else:
        parser.print_help()


def _check_adapter_compat(format_name: str, allow_skew: bool = False) -> list[str]:
    """STORY-slim-145 R6: deploy-time adapter compatibility gate (AC5).

    Thin wrapper over ``pactkit.doctor.check_adapter_compat`` so the CLI module
    can gate adapter dispatch before any managed file is written. Returns
    blocking errors (empty = OK to deploy).
    """
    from pactkit.doctor import check_adapter_compat

    return check_adapter_compat(format_name, allow_skew=allow_skew)


if __name__ == "__main__":
    main()
