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


def _run_deploy_command(args, project_root):
    """Shared init/update/upgrade execution path (STORY-slim-2026082672b57c78fd67 R3)."""
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

        for synced in sync_config_copies(project_root):
            print(f"  -> Synced config copy: {synced}")

    deploy(
        target=args.target,
        format=args.format,
        project_root=project_root,
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

        print(f"  -> commit gate: {ensure_gate_channel(project_root, args.format)}")
        report = render_check_report(check_deps())
        if "❌" in report:
            print(f"\n{report}")


def main():
    parser = argparse.ArgumentParser(
        prog="pactkit",
        description="PactKit — Spec-driven agentic DevOps toolkit",
    )
    parser.add_argument(
        "-C", "--project-root", default=None,
        help="Initialized PactKit project root (otherwise discovered from CWD)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # pactkit init
    def _add_deploy_args(parser, *, if_needed=False):
        """Shared init/update/upgrade arguments — one source, no drift
        (STORY-slim-2026082672b57c78fd67 R3)."""
        parser.add_argument(
            "-t", "--target", type=str, default=None,
            help="Custom target directory (default: ~/.claude)",
        )
        parser.add_argument(
            "--format", type=str, choices=sorted(VALID_FORMATS), default="all",
            help="Output format: all (default, deploy all installed IDEs), or a specific format",
        )
        parser.add_argument(
            "--agent", type=str,
            choices=["claude", "cursor", "copilot", "generic", "all"], default="claude",
            help="Target agent format: claude (default), cursor, copilot, generic, or all",
        )
        parser.add_argument(
            "--no-git", action="store_true", default=False,
            help="Disable all git operations (enterprise: air-gapped environments)",
        )
        parser.add_argument(
            "--no-external", action="store_true", default=False,
            help="Disable external network calls — MCP, gh CLI, pip install (enterprise)",
        )
        parser.add_argument(
            "--non-interactive", action="store_true", default=False,
            help="Non-interactive mode: auto-accept defaults (CI/CD environments)",
        )
        if if_needed:
            # Registration order matches the historical surface (golden-pinned).
            parser.add_argument(
                "--if-needed", action="store_true", default=False,
                help="Only redeploy if installed version differs from global deploy marker",
            )
        parser.add_argument(
            "--allow-adapter-skew", action="store_true", default=False,
            help="Allow deploying an adapter whose major.minor differs from core (STORY-slim-145 R6)",
        )

    _add_deploy_args(subparsers.add_parser("init", help="Deploy PactKit configuration"))
    _add_deploy_args(
        subparsers.add_parser("update", help="Re-deploy PactKit configuration"),
        if_needed=True,
    )
    _add_deploy_args(
        subparsers.add_parser(
            "upgrade", help="Upgrade PactKit (migrate legacy scafpy config)"
        )
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

    preflight_parser = subparsers.add_parser(
        "spec-preflight", help="Load Spec implementation inputs and write a verified receipt"
    )
    preflight_parser.add_argument("spec", help="Path to the Story Spec")

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
        "-C", "--project-root", dest="command_project_root", default=None,
        help="Initialized PactKit project root",
    )

    id_parser = subparsers.add_parser(
        "generate-id", help="Generate a decentralized time-prefixed item ID",
    )
    id_parser.add_argument(
        "--type", choices=["story", "hotfix", "bug"], default="story",
    )

    # pactkit clean (STORY-slim-014 R1)
    clean_parser = subparsers.add_parser("clean", help="Remove temp artifacts")
    clean_parser.add_argument("--stack", default="auto", help="Language stack (default: auto)")
    clean_parser.add_argument("--dry-run", action="store_true", help="List files without deleting")

    # pactkit regression (STORY-slim-014 R1)
    regression_parser = subparsers.add_parser("regression", help="Classify changes for regression testing")
    regression_parser.add_argument("files", nargs="*", help="Changed file paths (default: git diff)")

    # pactkit context (STORY-slim-014 R1, STORY-slim-071 continuation)
    ctx_parser = subparsers.add_parser("context", help="Generate local .pactkit/context.md")
    ctx_parser.add_argument("--continuation", action="store_true", default=False,
                            help="Update Agent Continuation section")
    ctx_parser.add_argument("--last-command", default=None, help="Last PDCA command run")
    ctx_parser.add_argument("--phase", default=None, help="Phase reached")
    ctx_parser.add_argument("--blockers", default=None, help="Blockers or open questions")
    ctx_parser.add_argument("--stdout", action="store_true", default=False, help="Print without writing cache")

    board_parser = subparsers.add_parser("board", help="Manage sharded Story records and Board projection")
    board_actions = board_parser.add_subparsers(dest="board_action", required=True)
    board_add = board_actions.add_parser("add", help="Create one Story record")
    board_add.add_argument("story_id")
    board_add.add_argument("title")
    board_add.add_argument("tasks", help="Pipe-separated task titles")
    board_add.add_argument("--run-id")
    board_add.add_argument("--workflow-id", default="project-plan")
    board_add.add_argument("--standalone", action="store_true", default=False)
    board_task = board_actions.add_parser("complete-task", help="Complete one Story task")
    board_task.add_argument("story_id")
    board_task.add_argument("task", help="Exact task ID or title")
    board_move = board_actions.add_parser("move", help="Change one Story workflow status")
    board_move.add_argument("story_id")
    board_move.add_argument("status", choices=["backlog", "in_progress", "done", "archived"])
    board_actions.add_parser("list", help="List Story records")
    board_render = board_actions.add_parser("render", help="Render the Board projection")
    board_render.add_argument("--output", default="docs/product/sprint_board.md")
    board_render.add_argument("--check", action="store_true", default=False)

    governance_parser = subparsers.add_parser("governance", help="Governance records and migrations")
    governance_actions = governance_parser.add_subparsers(dest="governance_action", required=True)
    governance_migrate = governance_actions.add_parser("migrate", help="Migrate legacy aggregate files")
    governance_migrate.add_argument("--apply", action="store_true", default=False)

    # STORY-slim-146: checkpoint writes are explicit; resume is read-only.
    continuation_parser = subparsers.add_parser(
        "continuation", help="Manage verifiable resumable Act checkpoints"
    )
    continuation_actions = continuation_parser.add_subparsers(
        dest="continuation_action", required=True
    )
    checkpoint_parser = continuation_actions.add_parser(
        "checkpoint", help="Write an explicit Act checkpoint"
    )
    checkpoint_parser.add_argument("story_id", help="Story ID, e.g. STORY-slim-146")
    checkpoint_parser.add_argument("--step", required=True, help="Safe boundary step ID")
    checkpoint_parser.add_argument("--evidence", required=True, help="JSON evidence object or @path")
    checkpoint_parser.add_argument(
        "--status", default="in_progress", choices=["in_progress", "blocked", "completed"]
    )
    checkpoint_parser.add_argument("--phase", default="", help="Human-readable Act phase")
    checkpoint_parser.add_argument("--blocker", default="", help="Sanitized blocker handoff")
    checkpoint_parser.add_argument(
        "--blocker-kind",
        choices=["user_input", "authorization", "external_state"],
    )
    checkpoint_parser.add_argument(
        "--fresh", action="store_true", default=False,
        help="Archive a completed checkpoint and begin a separate preflight cycle",
    )
    for action in ("status", "verify", "resume"):
        action_parser = continuation_actions.add_parser(action, help=f"Read-only continuation {action}")
        action_parser.add_argument("story_id", help="Story ID, e.g. STORY-slim-146")
    events_parser = continuation_actions.add_parser(
        "events", help="List a run's append-only event stream"
    )
    events_parser.add_argument("story_id", help="Story ID, e.g. STORY-slim-146")
    deny_parser = continuation_actions.add_parser(
        "deny", help="Record an explicit authorization denial (audit event)"
    )
    deny_parser.add_argument("story_id", help="Story ID, e.g. STORY-slim-146")
    deny_parser.add_argument("--reason", required=True, help="Sanitized denial reason")

    # STORY-slim-147: workflow-neutral continuation API.  The legacy
    # ``continuation`` command above remains the stable project-act facade.
    workflow_parser = subparsers.add_parser(
        "workflow", help="Manage registered, verifiable workflow runs"
    )
    workflow_actions = workflow_parser.add_subparsers(dest="workflow_action", required=True)
    workflow_start = workflow_actions.add_parser("start", help="Start a workflow run")
    workflow_start.add_argument("workflow_id", help="Registered workflow, e.g. project-plan")
    workflow_start.add_argument("--evidence", required=True, help="JSON evidence object or @path")
    workflow_bind = workflow_actions.add_parser("bind", help="Bind a run to a Story")
    workflow_bind.add_argument("identifier", help="Opaque run ID")
    workflow_bind.add_argument("story_id", help="Story ID")
    workflow_checkpoint = workflow_actions.add_parser("checkpoint", help="Write a workflow checkpoint")
    workflow_checkpoint.add_argument("identifier", help="Run ID or bound Story ID")
    workflow_checkpoint.add_argument("--step", required=True, help="Registered workflow step")
    workflow_checkpoint.add_argument("--evidence", required=True, help="JSON evidence object or @path")
    workflow_checkpoint.add_argument(
        "--status", default="in_progress", choices=["in_progress", "blocked", "completed"]
    )
    workflow_checkpoint.add_argument("--blocker", default="", help="Sanitized blocker handoff")
    workflow_checkpoint.add_argument(
        "--blocker-kind", choices=["user_input", "authorization", "external_state"],
        help="Machine-readable external blocker category",
    )
    for action in ("status", "verify", "resume", "finish-guard"):
        workflow_read = workflow_actions.add_parser(action, help=f"Read-only workflow {action}")
        workflow_read.add_argument("identifier", help="Run ID or bound Story ID")
        workflow_read.add_argument("--json", action="store_true", default=False)
        if action == "finish-guard":
            workflow_read.add_argument(
                "--auto-resume-available", action="store_true", default=False,
                help="Host has both completion-hook and session re-entry support",
            )
    workflow_revalidate = workflow_actions.add_parser(
        "revalidate-artifacts",
        help="Deterministically revalidate drifted artifacts and audit new fingerprints",
    )
    workflow_revalidate.add_argument("identifier", help="Run ID or bound Story ID")
    workflow_revalidate.add_argument("--json", action="store_true", default=False)
    workflow_registry = workflow_actions.add_parser("registry", help="Audit reliability registry")
    workflow_registry.add_argument("--json", action="store_true", default=False)
    workflow_contract = workflow_actions.add_parser(
        "contract", help="Print the executable lifecycle contract for a workflow"
    )
    workflow_contract.add_argument("workflow_id", help="Registered project command")
    workflow_contract.add_argument("--json", action="store_true", default=False)

    work_unit_parser = subparsers.add_parser(
        "work-unit", help="Execute host-neutral leased workflow units"
    )
    work_unit_actions = work_unit_parser.add_subparsers(
        dest="work_unit_action", required=True
    )
    from pactkit.workflow_engine import WORKFLOW_UNITS

    unit_start = work_unit_actions.add_parser("start", help="Start a WorkUnit workflow")
    unit_start.add_argument("workflow_id", choices=sorted(WORKFLOW_UNITS))
    unit_start.add_argument("--goal", required=True)
    unit_start.add_argument("--story-id")
    unit_acquire = work_unit_actions.add_parser("acquire", help="Lease the current WorkUnit")
    unit_acquire.add_argument("run_id")
    unit_acquire.add_argument("--owner", required=True)
    unit_acquire.add_argument("--idempotency-key", required=True)
    unit_renew = work_unit_actions.add_parser("renew", help="Renew a WorkUnit lease")
    unit_renew.add_argument("unit_id")
    unit_renew.add_argument("--owner", required=True)
    unit_reject = work_unit_actions.add_parser("reject", help="Reject and retry a WorkUnit")
    unit_reject.add_argument("unit_id")
    unit_reject.add_argument("--owner", required=True)
    unit_reject.add_argument("--reason-code", required=True)
    unit_retry = work_unit_actions.add_parser("retry", help="Lease a rejected/expired WorkUnit again")
    unit_retry.add_argument("unit_id")
    unit_retry.add_argument("--owner", required=True)
    unit_retry.add_argument("--idempotency-key", required=True)
    unit_expire = work_unit_actions.add_parser("expire", help="Expire an elapsed WorkUnit lease")
    unit_expire.add_argument("unit_id")
    unit_expire.add_argument("--owner", required=True)
    unit_submit = work_unit_actions.add_parser("submit", help="Submit a candidate EvidenceReceipt")
    unit_submit.add_argument("unit_id")
    unit_submit.add_argument("--owner", required=True)
    unit_submit.add_argument("--idempotency-key", required=True)
    unit_submit.add_argument("--receipt", required=True, help="Receipt JSON or @path")
    unit_attempt = work_unit_actions.add_parser("attempt-terminal", help="Record a host turn terminal")
    unit_attempt.add_argument("run_id")
    unit_attempt.add_argument("--unit-id", required=True)
    unit_attempt.add_argument("--unit-version", type=int, required=True)
    unit_attempt.add_argument("--owner", required=True)
    unit_attempt.add_argument("--host", required=True)
    unit_attempt.add_argument("--status", required=True)
    unit_attempt.add_argument("--session")
    unit_attempt.add_argument("--thread")
    unit_attempt.add_argument("--turn")
    unit_status = work_unit_actions.add_parser("status", help="Read authoritative WorkUnit state")
    unit_status.add_argument("run_id")
    unit_resume = work_unit_actions.add_parser(
        "resume", help="Read the unique active WorkUnit run bound to a Story"
    )
    unit_resume.add_argument("story_id")
    unit_bind = work_unit_actions.add_parser(
        "bind-story", help="Bind the Story allocated by the leased identity WorkUnit"
    )
    unit_bind.add_argument("run_id")
    unit_bind.add_argument("story_id")
    unit_bind.add_argument("--owner", required=True)
    unit_bind.add_argument("--idempotency-key", required=True)
    unit_finalize = work_unit_actions.add_parser("finalize-plan", help="Journaled Plan finalization")
    unit_finalize.add_argument("run_id")
    unit_finalize.add_argument("story_id")
    unit_finalize.add_argument("--title", required=True)
    unit_finalize.add_argument("--tasks", required=True, help="Pipe-separated tasks")
    unit_finalize.add_argument("--idempotency-key", required=True)
    unit_finalize_workflow = work_unit_actions.add_parser(
        "finalize-workflow", help="Journaled non-Plan workflow finalization"
    )
    unit_finalize_workflow.add_argument("run_id")
    unit_finalize_workflow.add_argument("--owner", required=True)
    unit_finalize_workflow.add_argument("--receipt", required=True, help="Receipt JSON or @path")
    unit_finalize_workflow.add_argument("--idempotency-key", required=True)

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
    lint_ctx_parser.add_argument("path", nargs="?", default=".pactkit/context.md", help="Path to context.md")

    # pactkit lint-lessons (STORY-slim-014 R2)
    lint_les_parser = subparsers.add_parser("lint-lessons", help="Validate lessons.md structure")
    lint_les_parser.add_argument(
        "path", nargs="?", default="docs/architecture/governance/lessons.md", help="Path to lessons.md"
    )

    # pactkit lint-testcase (STORY-slim-014 R2)
    lint_tc_parser = subparsers.add_parser("lint-testcase", help="Validate test case file structure")
    lint_tc_parser.add_argument("path", help="Path to test case file")

    # pactkit lint-adr (STORY-slim-2026090333d6b72f7645)
    lint_adr_parser = subparsers.add_parser("lint-adr", help="Validate ADR file structure")
    lint_adr_parser.add_argument("path", help="Path to ADR file")

    # pactkit guide show (STORY-slim-20260903a4ef6915ed62 telemetry choke point)
    guide_parser = subparsers.add_parser("guide", help="Guide operations")
    guide_sub = guide_parser.add_subparsers(dest="guide_cmd")
    show_p = guide_sub.add_parser("show", help="Print a deployed engineering guide")
    show_p.add_argument("name", help="Guide name (e.g. caching)")

    # pactkit accept-candidates (STORY-slim-20260903a24e1ece0d7f)
    accept_parser = subparsers.add_parser(
        "accept-candidates",
        help="Accept .pactkit-new deployment candidates and record ownership digests",
    )
    accept_parser.add_argument(
        "--root", default=None,
        help="Deploy root to scan (default: all known deploy roots)",
    )

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

    # pactkit stats (STORY-slim-20260827024e71df170f R2)
    stats_parser = subparsers.add_parser(
        "stats", help="Aggregate run friction metrics from event streams"
    )
    stats_parser.add_argument(
        "--format", default="human", choices=["human", "json"],
        help="Output format (human table or machine-readable JSON)",
    )

    # pactkit doctor (STORY-slim-015 R1-R3)
    doctor_parser = subparsers.add_parser("doctor", help="Diagnose project health")
    doctor_parser.add_argument(
        "--json", action="store_true", default=False,
        help="Emit machine-readable JSON diagnostics (STORY-slim-20260827024e71df170f R3)",
    )

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
    gate_parser.add_argument(
        "--push-gate", action="store_true",
        help="Protected-branch push gate: block direct pushes to main/master "
        "(pre-push hook entry point; exit 1 blocks)",
    )

    # pactkit gate (STORY-slim-20260828897396a935ab: session hooks + authorize)
    gate_parser = subparsers.add_parser(
        "gate",
        help="Session context hooks + external-effect authorization tokens",
    )
    gate_parser.add_argument(
        "--hook", choices=["session-start", "pre-compact"],
        help="Hook mode: read hook JSON context from stdin (SessionStart/PreCompact)",
    )
    gate_parser.add_argument(
        "scope", nargs="*", default=None,
        help="Authorize a scope (pr|release|repo|publish|spec_edit) for the TTL window. "
        "Both `pactkit gate authorize <scope>` and `pactkit gate <scope>` work.",
    )
    gate_parser.add_argument(
        "--ttl-minutes", type=int, default=None,
        help="Authorization TTL in minutes (default 30)",
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
    query_parser = subparsers.add_parser("query", help="Query the configured static-analysis provider")
    query_mode = query_parser.add_mutually_exclusive_group(required=True)
    query_mode.add_argument("--callers", metavar="FUNC", help="Fan-in: list all callers of FUNC")
    query_mode.add_argument("--callees", metavar="FUNC", help="Fan-out: list all callees of FUNC")
    query_mode.add_argument("--chain", metavar="FUNC", help="Transitive chain for FUNC")
    query_mode.add_argument("--explore", metavar="QUERY", help="Explore relevant symbols and paths")
    query_mode.add_argument("--impact", metavar="SYMBOL", help="Analyze affected code")
    query_parser.add_argument(
        "--down", action="store_true",
        help="With --chain: downstream callees (default: upstream callers)",
    )
    query_parser.add_argument("--db", metavar="PATH", help="Override default .codegraph/codegraph.db path")
    query_parser.add_argument("--json", action="store_true", default=False, help="Structured result")
    query_parser.add_argument("--explain", action="store_true", default=False, help="Show provider decision")
    query_parser.add_argument(
        "--allow-fallback", action="store_true", default=False,
        help="Explicitly allow Codegraph to fall back to the built-in graph",
    )

    # pactkit version
    subparsers.add_parser("version", help="Show PactKit version")

    args = parser.parse_args()

    project_root = None
    rootless_commands = {"init", "version", "schema"}
    rootless_invocation = (
        args.command == "workflow"
        and getattr(args, "workflow_action", None) in {"registry", "contract"}
    )
    if args.command and args.command not in rootless_commands:
        from pathlib import Path

        from pactkit.project_root import ProjectRootNotFound, resolve_project_root

        try:
            explicit_root = getattr(args, "command_project_root", None) or args.project_root
            project_root = resolve_project_root(Path.cwd(), explicit=explicit_root)
        except ProjectRootNotFound as exc:
            if rootless_invocation or args.command in {
                "update", "upgrade", "lesson-append", "redetect-stack",
            }:
                project_root = Path.cwd().resolve()
            else:
                parser.error(str(exc))
    elif args.command == "init":
        from pathlib import Path

        project_root = Path.cwd().resolve()

    if args.command in ("init", "update", "upgrade"):
        _run_deploy_command(args, project_root)
    elif args.command == "spec-preflight":
        from pactkit.spec_preflight import PreflightError, run_spec_preflight

        try:
            result = run_spec_preflight(project_root, args.spec)
        except PreflightError as exc:
            parser.error(str(exc))
        print(result.rendered, end="")
        print(f"Receipt: {result.receipt_path}")

    elif args.command == "spec-lint":
        from pactkit.skills.spec_linter import main as spec_lint_main

        argv = []
        if args.all:
            specs_dir = Path(args.specs_dir)
            if not specs_dir.is_absolute():
                specs_dir = project_root / specs_dir
            argv += ["--all", "--specs-dir", str(specs_dir)]
        elif args.spec:
            spec = Path(args.spec)
            if not spec.is_absolute():
                spec = project_root / spec
            argv += [str(spec)]
        else:
            spec_lint_parser.print_help()
            raise SystemExit(1)
        raise SystemExit(spec_lint_main(argv))

    elif args.command == "schema":
        _schema_command(args)

    elif args.command == "guard":
        from pathlib import Path

        from pactkit.guards import check_init_markers, check_version_mismatch

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

    elif args.command == "generate-id":
        from pathlib import Path

        from pactkit.config import load_config
        from pactkit.id_generator import generate_item_id

        cfg = load_config()
        specs_dir = project_root / "docs" / "specs"
        print(generate_item_id(
            specs_dir=specs_dir, developer=cfg.get("developer", ""),
            item_type=args.type.upper(),
        ))

    elif args.command == "clean":
        from pathlib import Path

        from pactkit.cleaners import clean_artifacts, scrub_enforcement_records

        if not args.dry_run:
            scrubbed = scrub_enforcement_records(project_root)
            if scrubbed:
                print(f"   -> Redacted credentials in {scrubbed} enforcement record(s)")
        removed = clean_artifacts(project_root, stack=args.stack, dry_run=args.dry_run)
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

            wf_lines = regression_workflow_impact(str(project_root), files)
            for line in wf_lines:
                print(line)
        except Exception:
            pass  # Graceful degradation (R4)
        raise SystemExit(0 if strategy == "skip" else 0)

    elif args.command == "context":
        from pathlib import Path

        from pactkit.context_gen import context_output_path, generate_context

        continuation_args = None
        if args.continuation and args.last_command:
            continuation_args = {"last_command": args.last_command}
            if args.phase:
                continuation_args["phase"] = args.phase
            if args.blockers:
                continuation_args["blockers"] = args.blockers

        content = generate_context(
            project_root,
            command="pactkit context",
            continuation_args=continuation_args,
        )
        if args.stdout:
            print(content, end="")
        else:
            from pactkit.utils import atomic_write

            ctx_path = context_output_path(project_root)
            atomic_write(ctx_path, content)
            print(f"Generated {ctx_path}")

    elif args.command == "board":
        import json
        from pathlib import Path

        from pactkit.governance import BoardRenderer, GovernanceError, StoryRepository
        from pactkit.utils import atomic_write

        repository = StoryRepository(project_root)
        renderer = BoardRenderer(repository)
        try:
            if args.board_action == "add":
                repository = StoryRepository(
                    project_root, run_id=args.run_id, workflow_id=args.workflow_id,
                    standalone=args.standalone or not args.run_id,
                )
                result = repository.add(
                    args.story_id, args.title,
                    [task.strip() for task in args.tasks.split("|") if task.strip()],
                )
            elif args.board_action == "complete-task":
                result = repository.complete_task(args.story_id, args.task)
            elif args.board_action == "move":
                result = repository.move(args.story_id, args.status)
            elif args.board_action == "list":
                result = repository.list()
            else:
                output = Path(args.output)
                if not output.is_absolute():
                    output = project_root / output
                if args.check:
                    if not renderer.check(output):
                        print(f"Board projection drift: {output}")
                        raise SystemExit(1)
                    print(f"Board projection current: {output}")
                    return
                atomic_write(output, renderer.render())
                result = {"rendered": str(output)}
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except GovernanceError as exc:
            print(f"Governance error: {exc}")
            raise SystemExit(1)

    elif args.command == "governance":
        import json
        from pathlib import Path

        from pactkit.governance import GovernanceError, GovernanceMigrator

        try:
            result = GovernanceMigrator(project_root).migrate(dry_run=not args.apply)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except GovernanceError as exc:
            print(f"Governance migration error: {exc}")
            raise SystemExit(1)

    elif args.command == "continuation":
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("continuation")

        import json
        from pathlib import Path

        from pactkit.continuation import ContinuationError, ContinuationStore

        store = ContinuationStore(project_root)
        try:
            if args.continuation_action == "checkpoint":
                raw_evidence = args.evidence
                if raw_evidence.startswith("@"):
                    raw_evidence = Path(raw_evidence[1:]).read_text(encoding="utf-8")
                result = store.checkpoint(
                    args.story_id,
                    step_id=args.step,
                    evidence=json.loads(raw_evidence),
                    status=args.status,
                    phase=args.phase,
                    blocker=args.blocker,
                    blocker_kind=args.blocker_kind,
                    fresh=args.fresh,
                )
            elif args.continuation_action == "status":
                result = store.status(args.story_id)
            elif args.continuation_action == "events":
                from pactkit.run_events import read_events, story_events_path

                store._validate_story_id(args.story_id)
                events, corrupt = read_events(story_events_path(project_root, args.story_id))
                if not events and not corrupt:
                    print(f"no events recorded for {args.story_id}")
                    raise SystemExit(0)
                for event in events:
                    detail = json.dumps(event.get("detail"), ensure_ascii=False)
                    print(
                        f"{event.get('ts')} {event.get('event')} "
                        f"step={event.get('step_id')} status={event.get('status')} {detail}"
                    )
                if corrupt:
                    print(f"[WARN] {corrupt} corrupt event line(s) skipped")
                raise SystemExit(0)
            elif args.continuation_action == "deny":
                result = store.deny(args.story_id, args.reason)
            else:
                result = store.resume(args.story_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if result.get("decision") == "blocked":
                raise SystemExit(1)
        except (ContinuationError, OSError, json.JSONDecodeError) as exc:
            print(f"Continuation error: {exc}")
            raise SystemExit(1)

    elif args.command == "workflow":
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("workflow")

        import json
        from pathlib import Path

        from pactkit.continuation import ContinuationEngine, ContinuationError
        from pactkit.workflow_registry import (
            EXECUTION_RELIABILITY_REGISTRY,
            get_workflow,
            validate_registry,
        )

        def _workflow_evidence(raw: str) -> dict:
            if raw.startswith("@"):
                raw = Path(raw[1:]).read_text(encoding="utf-8")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ContinuationError("workflow evidence must be a JSON object")
            return value

        try:
            if args.workflow_action == "registry":
                errors = validate_registry()
                payload = {
                    "valid": not errors,
                    "errors": errors,
                    "entries": {
                        name: {
                            "entry_type": item.entry_type,
                            "category": item.category,
                            "recovery": item.recovery,
                            "persistence": item.persistence,
                            "completion": item.completion,
                            "manual_operations": list(item.manual_operations),
                        }
                        for name, item in sorted(EXECUTION_RELIABILITY_REGISTRY.items())
                    },
                }
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                if errors:
                    raise SystemExit(1)
            elif args.workflow_action == "contract":
                definition = get_workflow(args.workflow_id)
                manual = EXECUTION_RELIABILITY_REGISTRY[args.workflow_id].manual_operations
                payload = {
                    "workflow_id": definition.name,
                    "steps": list(definition.steps),
                    "start_evidence_requirements": list(
                        definition.start_evidence_requirements
                    ),
                    "completion_evidence_requirements": list(
                        definition.completion_evidence_requirements
                    ),
                    "start": (
                        f"pactkit workflow start {definition.name} "
                        "--evidence @<evidence.json>"
                    ),
                    "resume": "pactkit workflow resume <run-id>",
                    "checkpoint": (
                        "pactkit workflow checkpoint <run-id> --step <next-step> "
                        "--evidence @<evidence.json>"
                    ),
                    "finish_guard": "pactkit workflow finish-guard <run-id> --json",
                    "manual_operations": list(manual),
                }
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                engine = ContinuationEngine(project_root)
                if args.workflow_action == "start":
                    result = engine.start(args.workflow_id, evidence=_workflow_evidence(args.evidence))
                    import os

                    session_id = os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_THREAD_ID")
                    if session_id:
                        engine.bind_host_session(result["run_id"], session_id=session_id)
                        result = engine.read(result["run_id"])
                elif args.workflow_action == "bind":
                    result = engine.bind_story(args.identifier, args.story_id)
                elif args.workflow_action == "checkpoint":
                    result = engine.checkpoint(
                        args.identifier, step_id=args.step,
                        evidence=_workflow_evidence(args.evidence), status=args.status,
                        blocker=args.blocker, blocker_kind=args.blocker_kind,
                    )
                elif args.workflow_action == "status":
                    result = engine.read(args.identifier)
                elif args.workflow_action == "finish-guard":
                    result = engine.finish_guard(
                        args.identifier,
                        auto_resume_available=args.auto_resume_available,
                    )
                elif args.workflow_action == "revalidate-artifacts":
                    result = engine.revalidate_artifacts(args.identifier)
                else:
                    result = engine.resume(args.identifier)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                if args.workflow_action == "finish-guard":
                    if result.get("exit_code"):
                        raise SystemExit(result["exit_code"])
                elif result.get("decision") == "blocked":
                    raise SystemExit(1)
        except (ContinuationError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Workflow error: {exc}")
            raise SystemExit(1)

    elif args.command == "work-unit":
        from pactkit.legacy.usage import record_legacy_usage

        record_legacy_usage("work-unit")

        import json
        from dataclasses import asdict
        from pathlib import Path

        from pactkit.workflow_engine import (
            EvidenceReceipt,
            PlanFinalizer,
            WorkflowEngine,
            WorkflowFinalizer,
            WorkUnitError,
        )

        def _unit_json(raw: str) -> dict:
            if raw.startswith("@"):
                raw = Path(raw[1:]).read_text(encoding="utf-8")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise WorkUnitError("receipt_must_be_object")
            return value

        try:
            engine = WorkflowEngine(project_root)
            if args.work_unit_action == "start":
                result = asdict(engine.start(
                    args.workflow_id, goal=args.goal, story_id=args.story_id,
                ))
            elif args.work_unit_action == "acquire":
                result = asdict(engine.acquire(
                    args.run_id, owner=args.owner,
                    idempotency_key=args.idempotency_key,
                ))
            elif args.work_unit_action == "renew":
                result = asdict(engine.renew(args.unit_id, owner=args.owner))
            elif args.work_unit_action == "reject":
                result = asdict(engine.reject(
                    args.unit_id, owner=args.owner, reason_code=args.reason_code,
                ))
            elif args.work_unit_action == "retry":
                result = asdict(engine.retry(
                    args.unit_id, owner=args.owner,
                    idempotency_key=args.idempotency_key,
                ))
            elif args.work_unit_action == "expire":
                result = engine.expire(args.unit_id, owner=args.owner)
            elif args.work_unit_action == "submit":
                result = asdict(engine.submit(
                    args.unit_id, EvidenceReceipt(**_unit_json(args.receipt)),
                    owner=args.owner, idempotency_key=args.idempotency_key,
                ))
            elif args.work_unit_action == "attempt-terminal":
                result = engine.record_turn_terminal(
                    args.run_id, unit_id=args.unit_id, unit_version=args.unit_version,
                    owner=args.owner, host=args.host, status=args.status,
                    session=args.session, thread=args.thread, turn=args.turn,
                )
            elif args.work_unit_action == "finalize-plan":
                result = PlanFinalizer(project_root, engine).finalize(
                    args.run_id, story_id=args.story_id, title=args.title,
                    tasks=[item.strip() for item in args.tasks.split("|") if item.strip()],
                    idempotency_key=args.idempotency_key,
                )
            elif args.work_unit_action == "finalize-workflow":
                result = WorkflowFinalizer(project_root, engine).finalize(
                    args.run_id, EvidenceReceipt(**_unit_json(args.receipt)),
                    owner=args.owner, idempotency_key=args.idempotency_key,
                )
            elif args.work_unit_action == "resume":
                result = engine.resume(args.story_id)
            elif args.work_unit_action == "bind-story":
                result = asdict(engine.bind_story(
                    args.run_id, story_id=args.story_id, owner=args.owner,
                    idempotency_key=args.idempotency_key,
                ))
            else:
                result = engine.status(args.run_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except (WorkUnitError, OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"WorkUnit error: {exc}")
            raise SystemExit(1)

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
        results = detect_security_scope(args.files, project_root=project_root)
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

    elif args.command == "lint-adr":
        from pathlib import Path

        from pactkit.validators import lint_adr

        errors = lint_adr(Path(args.path))
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            raise SystemExit(1)
        else:
            print(f"{args.path}\n  Result: PASS")

    elif args.command == "guide":
        if args.guide_cmd == "show":
            from pactkit.rule_diagnostics import default_deploy_roots

            raise SystemExit(_run_guide_show(
                args.name,
                deploy_roots=default_deploy_roots(project_root),
                project_root=project_root,
            ))

    elif args.command == "accept-candidates":
        from pathlib import Path as _P

        from pactkit.accept_candidates import accept_candidates, default_roots

        roots = [_P(args.root)] if args.root else default_roots()
        total = 0
        for root in roots:
            n = accept_candidates(root)
            if n:
                print(f"{root}: accepted {n} candidate(s)")
            total += n
        print(f"Accepted {total} candidate(s)")

    elif args.command == "visualize":
        from pathlib import Path

        from pactkit.lazy_visualize import codegraph_sync, run_visualize_graphs, run_visualize_single, should_visualize

        if args.lazy:
            should_run, reason = should_visualize(project_root, stack=args.stack)
            if not should_run:
                # HOTFIX 2026-09-03: sync unconditionally — the old code only
                # synced with an explicit --sync flag, so `pactkit visualize
                # --lazy` (what Act Phase 4 runs) never touched the codegraph
                # db and it went silently stale after every source change.
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
        # HOTFIX 2026-09-03: graphs regenerated — sync the codegraph index too
        # (run_visualize_graphs never did; the Act Phase 4 doc promise
        # "codegraph sync is handled automatically" was never wired here).
        synced, msg = codegraph_sync(project_root)
        if synced:
            print(f"🔄 {msg}")

    elif args.command == "sync":
        from pathlib import Path

        from pactkit.lazy_visualize import codegraph_sync

        synced, msg = codegraph_sync(project_root)
        if synced:
            print(f"🔄 {msg}")
        else:
            print(f"codegraph: {msg}")

    elif args.command == "garden":
        from pathlib import Path

        from pactkit.garden import run_garden

        root = project_root
        scope = Path(args.scope) if args.scope else None
        output, exit_code = run_garden(root, scope=scope, json_output=args.json)
        print(output)
        raise SystemExit(exit_code)

    elif args.command == "observe":
        from pactkit.observe import run_observe

        output, exit_code = run_observe(report=args.report, json_output=args.json)
        print(output)
        raise SystemExit(exit_code)

    elif args.command == "stats":
        import json as json_module

        from pactkit.run_stats import (
            collect_gate_telemetry,
            collect_runs,
            json_report,
            render_report,
        )

        runs = collect_runs(project_root)
        telemetry = collect_gate_telemetry(project_root)
        from pactkit.run_stats import rule_telemetry_summary

        rules = rule_telemetry_summary(project_root)
        if args.format == "json":
            print(json_module.dumps(json_report(runs, telemetry, rules), indent=2, ensure_ascii=False))
        else:
            print(render_report(runs, telemetry))
        raise SystemExit(0)

    elif args.command == "report":
        from pactkit.skills.report import generate as run_report

        # Default: --all mode (convenience entry per R7)
        all_mode = args.all_mode or (not args.input)
        output = run_report(
            target=project_root, input_file=args.input, output_file=args.output, all_mode=all_mode,
        )
        if output:
            print(output)

    elif args.command == "audit":
        from pactkit.audit import audit as run_audit

        output = run_audit(
            target=project_root, json_only=args.json, layer=args.layer, append=args.append,
            verbose=args.verbose, if_needed=args.if_needed,
            story_id=args.story_id,
        )
        if output and not args.append:
            print(output)

    elif args.command == "doctor":
        from pathlib import Path

        from pactkit.doctor import (
            check_config_drift,
            check_graph_provider,
            check_hld_module_count,
            check_legacy_engine_usage,
            check_orphaned_specs,
            check_rule_health,
            check_rule_ownership,
            check_stale_graphs,
            check_workflow_continuation,
        )
        from pactkit.enforcement import assess as assess_enforcement

        root = project_root

        if args.json:
            # Machine-readable diagnostics (STORY-slim-20260827024e71df170f R3):
            # enforcement completeness is the contract; the other structured
            # checks ride along so automation has one doctor surface.
            import json as json_module

            from pactkit.doctor import (
                check_codex_execution_capability,
                check_codex_hook_capability,
                check_deploy_parity,
            )

            enforcement = assess_enforcement(root)
            payload = {
                "enforcement": enforcement,
                "legacy_engine_usage": check_legacy_engine_usage(),
                "orphaned_specs": check_orphaned_specs(root),
                "config_drift": check_config_drift(root),
                "graph_provider": check_graph_provider(root),
                "deploy_parity": check_deploy_parity(root),
                "codex_execution": check_codex_execution_capability(),
                "codex_hooks": check_codex_hook_capability(root),
                "workflow_continuation": check_workflow_continuation(root),
                "rule_health": check_rule_health(root),
                "issues": False,
            }
            print(json_module.dumps(payload, indent=2, ensure_ascii=False))
            raise SystemExit(0)

        has_issues = False

        # Frozen legacy engine usage — informs the deletion decision
        # (STORY-slim-20260826cb37edfdd4da R3).
        legacy_usage = check_legacy_engine_usage()
        if legacy_usage["total"]:
            detail = ", ".join(
                f"{cmd}: {count}"
                for cmd, count in legacy_usage["per_command"].items()
            )
            print(
                f"  Legacy engine: {legacy_usage['total']} explicit invocation(s) "
                f"since {legacy_usage['last_seen']} ({detail}) — deletion candidate"
            )

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

        graph = check_graph_provider(root)
        rule_health = check_rule_health(root)
        for warning_line in rule_health.get("warnings", []):
            print("  Rule health: " + warning_line)
        print(
            "  Graph: "
            f"configured={graph.get('configured') or 'default'} "
            f"selected={graph['selected']} available={graph['available']} fresh={graph['fresh']}"
        )
        for warning in graph.get("warnings", []):
            print(f"  Graph warning: {warning}")
        if graph.get("configured") == "codegraph" and not graph.get("available"):
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
            # Deployment manifests are environment diagnostics, not project
            # correctness gates.  A stale optional host must not make a
            # read-only doctor invocation (or normal PDCA work) unusable.
            print(f"  ⚠️  {detail}")
        for warning in parity["warnings"]:
            print(f"  ⚠️  {warning}")

        ownership = check_rule_ownership(root)
        print(
            "  Rule ownership: "
            f"pactkit={len(ownership['pactkit_owned'])} "
            f"project={len(ownership['project_owned'])} "
            f"user={len(ownership['user_owned'])} "
            f"conflicts={len(ownership['conflicts'])}"
        )
        for item in ownership["conflicts"]:
            print(
                f"  ⚠️  Rule conflict: {item['path']} preserved; "
                f"review candidate {item['candidate']}"
            )
        for item in ownership["potential_conflicts"]:
            print(
                f"  ⚠️  Personal rule advisory: {item['path']}:{item['line']} "
                f"contains {item['signal']}"
            )
        for warning in ownership["warnings"]:
            print(f"  ⚠️  {warning}")

        from pactkit.doctor import resolve_rule_context

        resolution = resolve_rule_context("project-sprint")
        loaded_rule_ids = ", ".join(item["id"] for item in resolution["loaded"])
        print(
            "  Rule resolution: "
            f"command={resolution['command']} "
            f"phase={resolution['active_phase'] or 'dynamic'} "
            f"loaded={loaded_rule_ids or 'none'}"
        )
        print(f"  Rule precedence: {resolution['precedence']}")
        for warning in resolution["warnings"]:
            print(f"  ⚠️  Rule resolution: {warning}")

        from pactkit.doctor import check_codex_execution_capability, check_codex_hook_capability

        codex_execution = check_codex_execution_capability()
        print(
            "  Codex execution capability: "
            f"mode={codex_execution['execution_mode']} "
            f"session={codex_execution['session_execution']} "
            f"background={str(codex_execution['background_execution']).lower()} "
            f"thread_resume={str(codex_execution['thread_resume']).lower()} "
            f"finish_guard={str(codex_execution['finish_guard_supported']).lower()} "
            f"guarantee={codex_execution['guarantee_level']}"
        )
        for warning in codex_execution["warnings"]:
            print(f"  ⚠️  {warning}")

        # STORY-slim-20260827024e71df170f R4: native-hooks thin registration
        codex_hooks = check_codex_hook_capability(root)
        print(
            "  Codex hooks capability: "
            f"engine={codex_hooks['engine']} "
            f"version={codex_hooks['codex_version'] or 'n/a'} "
            f"hooks_json={codex_hooks['hooks_json']} "
            f"entry={str(codex_hooks['entry_present']).lower()} "
            f"trust={codex_hooks['trust']}"
        )
        for warning in codex_hooks["warnings"]:
            print(f"  ⚠️  {warning}")

        # STORY-slim-142 R3: adapter package version skew (report-only)
        from pactkit.doctor import check_adapter_skew

        for warning in check_adapter_skew():
            print(f"  ⚠️  {warning}")

        # Core source vs distribution metadata divergence is an installation
        # diagnostic.  It must not make a project doctor invocation fail: an
        # editable checkout or an older host install cannot block normal work.
        from pactkit.doctor import check_core_metadata_divergence

        for warning in check_core_metadata_divergence():
            print(f"  ⚠️  {warning}")

        from pactkit.continuation import ContinuationStore

        for warning in ContinuationStore(root).diagnostics():
            print(f"  ⚠️  {warning}")

        workflow_health = check_workflow_continuation(root)
        print(
            "  Workflow continuation: "
            f"guarantee={workflow_health['guarantee_level']} "
            f"finish_guard={str(workflow_health['finish_guard_supported']).lower()} "
            f"auto_resume_available={str(workflow_health['auto_resume_available']).lower()}"
        )
        for warning in workflow_health["warnings"]:
            print(f"  ⚠️  {warning}")

        # STORY-slim-20260827024e71df170f R3: gate enforcement completeness
        # is reported, never silently degraded.
        from pactkit.enforcement import render_summary

        print(render_summary(assess_enforcement(root)))

        if not has_issues:
            print("Health: OK")
        else:
            print("Health: NEEDS ATTENTION")
            raise SystemExit(1)

    elif args.command == "backfill-release":
        from pathlib import Path

        from pactkit.backfill import scan_and_replace_tbd

        result = scan_and_replace_tbd(project_root, args.version)
        for item in result["backfilled"]:
            print(f"  Backfilled: {item['id']} → {args.version}")
        for item in result["skipped"]:
            print(f"  Skipped: {item['id']} ({item['reason']})")
        if not result["backfilled"] and not result["skipped"]:
            print("No specs with Release: TBD found")

    elif args.command == "issue-sync":
        from pathlib import Path

        from pactkit.issue_sync import issue_sync

        result = issue_sync(args.item_id, project_root)
        print(result["message"])
        if result["action"] == "error":
            raise SystemExit(1)

    elif args.command == "test-map":
        from pathlib import Path

        from pactkit.test_mapper import map_to_tests

        if not args.files:
            print("Usage: pactkit test-map <file1> [file2 ...]")
            raise SystemExit(1)
        result = map_to_tests(args.files, project_root)
        for test_path in result["mapped"]:
            print(test_path)

    elif args.command == "lint":
        from pathlib import Path

        from pactkit.lint_runner import run_lint

        result = run_lint(project_root, fix=args.fix)
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

        from pactkit.governance import LessonRepository
        from pactkit.lessons import _is_duplicate, _is_specific

        repository = LessonRepository(project_root)
        if not _is_specific(args.text):
            result = {"action": "skipped", "reason": "not specific enough — no file/function reference"}
        elif _is_duplicate(args.text, [record["text"] for record in repository.recent(20)]):
            result = {"action": "skipped", "reason": "duplicate of recent entry"}
        else:
            lesson = repository.add(args.story, args.text, args.context)
            result = {"action": "appended", "reason": f"lesson added for {args.story}", **lesson}
        import json
        print(json.dumps(result))

    elif args.command == "invariants-refresh":
        from pathlib import Path

        from pactkit.invariants import refresh_test_count

        result = refresh_test_count(project_root, args.test_count)
        import json
        print(json.dumps(result))

    elif args.command == "coverage-gate":
        from pathlib import Path

        from pactkit.coverage_gate import check_coverage

        result = check_coverage(args.files, project_root)
        import json
        print(json.dumps(result, indent=2))
        # A "block" verdict must block — exit 0 made the gate prompt-only
        # (STORY-slim-20260826ce35b77ce005 R4, Code Enforces).
        if result.get("overall") == "block":
            raise SystemExit(1)

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

        results, exit_code = verify_story(args.story_id, project_root)
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
            lines, exit_code = install_deps(project_root, assume_yes=args.yes)
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

    elif args.command == "gate":
        import sys

        if args.hook:
            from pactkit.session_gate import pre_compact_entry, session_start_entry

            if args.hook == "session-start":
                text, code = session_start_entry(project_root)
            else:
                text, code = pre_compact_entry(project_root)
            if text:
                print(text, end="")  # stdout is injected as context by the host
            raise SystemExit(code)

        if args.scope:
            from pactkit.auth_gate import authorize

            # HOTFIX-slim-20260830bbb5bc219d35: the gate messages and the
            # L1 Override Protocol document `pactkit gate authorize <scope>`;
            # accept the keyword form alongside the bare positional form.
            tokens = list(args.scope)
            if tokens and tokens[0] == "authorize":
                tokens = tokens[1:]
            if len(tokens) != 1:
                parser.error("gate: authorize takes exactly one scope "
                             "(pr|release|repo|publish|spec_edit)")
            print(authorize(project_root, tokens[0], args.ttl_minutes))
            raise SystemExit(0)

        parser.error("gate: --hook or a scope (authorize) is required")

    elif args.command == "commit-gate":
        import sys
        from pathlib import Path

        from pactkit.commit_gate import hook_entry, install_git_hook, run_gate

        if args.install_git_hook:
            print(install_git_hook(project_root))
            raise SystemExit(0)
        if args.push_gate:
            from pactkit.commit_gate import check_push

            message, exit_code = check_push(project_root, "git push")
            if message:
                print(message, file=sys.stderr)
            raise SystemExit(1 if exit_code else 0)
        if args.hook:
            message, exit_code = hook_entry(sys.stdin.read(), project_root)
            if message:
                print(message, file=sys.stderr)
            raise SystemExit(exit_code)
        result = run_gate(project_root)
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

        cwd = project_root
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
        import json
        import sys
        from pathlib import Path

        from pactkit.config import load_config
        from pactkit.graph_query import GraphProviderError, GraphQueryRequest, project_router

        config = load_config()
        graph_provider = config.get("visualize", {}).get("graph_provider")
        from pactkit.graph_query import resolve_graph_provider

        graph_provider = resolve_graph_provider(graph_provider, project_root)
        try:
            selected = next(
                (
                    (kind, value)
                    for kind, value in (
                        ("callers", args.callers), ("callees", args.callees),
                        ("chain", args.chain), ("explore", args.explore), ("impact", args.impact),
                    )
                    if value is not None
                )
            )
            request = GraphQueryRequest(
                selected[0], selected[1], direction="down" if args.down else "up"
            )
            db_path = Path(args.db) if args.db else None
            result = project_router(project_root, db_path=db_path).query(
                request, configured_provider=graph_provider, allow_fallback=args.allow_fallback,
            )
        except (GraphProviderError, ValueError) as exc:
            reason = getattr(exc, "reason_code", "invalid_query")
            print(f"Graph query error [{reason}]: {exc}", file=sys.stderr)
            raise SystemExit(1)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if args.explain:
                decision = result.decision
                print(
                    f"provider={decision.selected_provider} freshness={decision.freshness} "
                    f"reason={decision.reason_code} fallback={decision.fallback}"
                )
                for warning in decision.warnings:
                    print(f"warning={warning}")
            for item in result.results:
                if {"name", "file_path", "start_line"} <= set(item):
                    print(f"{item['name']} ({item['file_path']}:{item['start_line']})")
                elif "text" in item:
                    print(item["text"])
                else:
                    print(json.dumps(item, ensure_ascii=False))

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


def _run_guide_show(name: str, *, deploy_roots, project_root) -> int:
    """STORY-slim-20260903a4ef6915ed62: guide choke point — print + record.

    Resolves the guide across deploy roots (classic/opencode layouts, codex
    embedded references), prints it, and records a guide_loaded telemetry
    event. Name is whitelisted to registered guides — no path resolution.
    """
    import re as _re
    import sys as _sys

    from pactkit.prompts.guides import GUIDE_DEFINITIONS
    from pactkit.rule_events import append_rule_event

    registered = {n.removesuffix(".md"): n for n in GUIDE_DEFINITIONS}
    if name not in registered or _re.search(r"[/\\]", name):
        names = ", ".join(sorted(registered))
        print(f"Unknown guide: {name!r}\nAvailable: {names}", file=_sys.stderr)
        return 1
    filename = registered[name]
    for base in deploy_roots:
        for candidate in (
            base / "skills" / "_rules" / "guides" / filename,
            base / "skills" / "project-act" / "references" / "guides" / filename,
        ):
            if candidate.is_file():
                print(candidate.read_text(encoding="utf-8"), end="")
                append_rule_event(project_root, "guide_loaded", {"guide": name})
                return 0
    names = ", ".join(sorted(registered))
    print(f"Guide '{name}' is registered but not deployed — run `pactkit update`.\n"
          f"Registered: {names}", file=_sys.stderr)
    return 1
