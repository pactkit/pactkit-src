# STORY-slim-20260826ac1f0bfe4148: Prompt-to-CLI contract consistency: machine-checked and gap-closed

| Field | Value |
|-------|-------|
| ID | STORY-slim-20260826ac1f0bfe4148 |
| Status | Done |
| Priority | P1 |
| Release | 2.23.0 |

## Background

The architecture principle "Code Enforces, Prompt Instructs" has an
unguarded seam: nothing checks that the instructions (prompts, skills,
playbooks embedded in src/pactkit/prompts/ and the PactKit skill
markdown) reference CLI subcommands and script interfaces that actually
exist. During the 2026-08-26 session, three live failures of this class
occurred:

1. `board.py add_task` invoked per a plausible-but-wrong assumption —
   the script only ships add_story, update_task, snapshot, move_story,
   archive, list_stories, fix_board, render. The agent had no way to
   know without reading the script, and the playbook only documents
   update_task.
2. `pactkit spec-status {ID} implemented` — argparse rejects it; only
   Draft/In Progress/Done are valid. Prompts never enumerate valid
   values.
3. `spec-preflight` auto-discovers backtick-quoted file references in
   Spec prose (spec_preflight.py:86-130): a bare basename mentioned in
   prose is rglob-resolved and force-inlined; a >32KB file (the
   deployed manifest, at 37KB in this repo) aborts preflight with a hard
   error,
   and a file already declared in the Implementation Inputs table under
   its full path can still be re-added via a prose basename
   (spec_preflight.py:97 checks `value in known` BEFORE rglob
   resolution, so a resolved duplicate is appended with mode=auto).

The same drift class explains recurring "AI does something dumb"
friction: any assistant (Claude Code, codex, future models) following
the written playbook hits an interface that no longer matches, then
hand-recovers — visible to the user as flaky, unreliable tooling.

Lateral scan: no existing mechanism checks prompt↔CLI consistency
(grepped prompts/, tests/, CI config). New test is justified — it is
the missing enforcement layer for an existing principle, not a new
pattern copy.

## Requirements

### R1: Prompt-referenced CLI subcommands exist (MUST)

A unit test MUST extract every `pactkit <subcommand>` reference from
src/pactkit/prompts/*.py rendered content and assert each subcommand is
registered in the CLI parser. The same test MUST extract
`board.py <subcommand>` and `scaffold.py <subcommand>` references and
assert they exist in the respective script's argparse choices. This is
the machine-enforced half of "Code Enforces, Prompt Instructs".

### R2: board.py gains add_task (MUST)

board.py MUST provide `add_story`-symmetric `add_task {STORY_ID}
"{title}"` so mid-story task additions (QA fix iterations) have a
governed path instead of hand-edited YAML. Appended tasks MUST follow
the existing task schema and the update MUST be logged.

### R3: spec-preflight prose-reference hardening (MUST)

Backtick references discovered in prose MUST NOT be force-inlined when
(a) the resolved file already appears in the Implementation Inputs
table under any path spelling, or (b) the file exceeds the inline budget
— case (b) MUST downgrade to a WARN with a hint to declare the input
with an extraction mode, not abort the preflight.

### R4: playbook interface inventory (SHOULD)

The board/spec-status command playbooks (prompts and PactKit skill
markdown) SHOULD enumerate accepted values and available subcommands
for the interfaces they instruct on, so the LLM contract is explicit
rather than discovered by trial-and-error.

## Acceptance Criteria

### AC1: contract test catches a fabricated subcommand (R1)

- **Given** a temporarily injected reference to `pactkit nonexistent-cmd` in a prompts module (test fixture)
- **When** the contract test runs
- **Then** it fails, naming the fabricated subcommand

### AC2: all current references pass (R1)

- **Given** the current prompts source tree
- **When** the contract test runs
- **Then** it passes with zero unregistered references

### AC3: add_task round-trips (R2)

- **Given** an existing story with completed tasks
- **When** `board.py add_story`-style `add_task {ID} "title"` runs
- **Then** the story yaml contains the new task (completed: false) and pactkit board list accepts the file without governance error

### AC4: prose basename does not double-add (R3)

- **Given** a Spec whose Implementation Inputs table declares the .github deployed manifest by full path and whose prose mentions its bare basename
- **When** spec-preflight runs
- **Then** the file is inlined exactly once (from the table's mode), not re-added with mode=auto

### AC5: oversized prose reference warns instead of aborting (R3)

- **Given** a Spec whose prose backtick-mentions a 37KB file not declared in the table
- **When** spec-preflight runs
- **Then** the result contains a WARN advising declaration with an extraction mode, and preflight completes (exit 0)

## Target Call Chain

```
CI / unit tests
  → new test_prompt_cli_contract.py        [R1 — extracts refs, asserts parser registration]
  → src/pactkit/cli.py (parser introspection via pactkit.__main__ / argparse)
  → ~/.claude/skills/pactkit-board/scripts/board.py  [R2 — add_task]
  → src/pactkit/spec_preflight.py: _discover_references  [R3 — dedup + budget downgrade]
```

## Implementation Inputs

| Path | Mode | Range | Required |
|------|------|-------|----------|
| src/pactkit/spec_preflight.py | all | all | MUST |
| src/pactkit/cli.py | interface | all | MUST |
| src/pactkit/prompts/commands.py | interface | all | MUST |

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | tests/unit/test_prompt_cli_contract.py | RED: AC1/AC2 contract test (fixture injection + current tree) | None | Low |
| 2 | board.py (skill scripts) | add_task subcommand (R2) | None | Low |
| 3 | tests/unit/ | RED: AC3 add_task round-trip | Step 2 | Low |
| 4 | src/pactkit/spec_preflight.py | dedup after resolution + budget downgrade to WARN (R3) | None | Medium |
| 5 | tests/unit/ | RED: AC4/AC5 preflight behavior | Step 4 | Low |
| 6 | prompts + skill markdown | Enumerate accepted values for board/spec-status usage (R4) | Steps 2-4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-2 | Yes | spec_preflight input handling changes — downgraded oversized inputs MUST still respect project-root containment and no-symlink-escape rules |
| Others | N/A | test/tooling surface, no runtime auth/network/DB change |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | None |
| Provides | prompt→CLI contract test (reusable guard for all future prompt edits) |
| Touches | src/pactkit/spec_preflight.py, tests/unit/, board.py skill script, prompts + skill markdown |
| Conflict risk | LOW |

## Out of Scope

- preflight_guard write-scope enforcement (hook contract design, separate story)
- Full playbook rewrite (only interface-inventory touch points for R4)
- workflow engine robustness (STORY-slim-202608267c3989223b4d)
