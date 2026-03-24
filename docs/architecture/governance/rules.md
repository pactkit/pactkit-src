# Governance Rules

## Architecture Decisions

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| ADR-001 | Python 3.10+ with hatchling build | Broad compatibility, modern packaging | 2025-01 |
| ADR-002 | Prompt templates as Python string constants | Zero external deps for core, easy to test | 2025-01 |
| ADR-003 | pactkit.yaml for selective deployment config | User controls which agents/commands/rules deploy | 2025-02 |
| ADR-004 | FormatProfile dataclass registry (`profiles.py`) | OCP: new tool = one registry entry; eliminates if-else branching | 2026-03 |
| ADR-005 | schemas.py as document structure source of truth | DRY: one place for Spec/Board/Context/Lessons/TestCase rules | 2026-03 |
| ADR-006 | Sequential str.replace in `_render_prompt()` | Safe with user-facing complex keys; format_map fails on `{R1, R2}` | 2026-03 |
| ADR-007 | Deploy chain parity over premature abstraction | Add functions one-by-one rather than shared `_deploy_standard()` | 2026-03 |
| ADR-008 | Lazy rule loading: RULES_CORE_FILES + RULES_ONDEMAND_FILES + RULES_INSTRUCTIONS_CORE | OpenCode instructions glob loads all files every turn; split avoids -62% token overhead | 2026-03 |

## Invariants

1. All 2852+ tests must pass before any commit to `main`.
2. Specs (`docs/specs/`) are the source of truth — code conforms to specs, not the reverse.
3. CLI entry point is `pactkit` via `src/pactkit/cli.py:main`.
4. No runtime dependencies beyond `pyyaml`.
5. New tool format requires only a `FormatProfile` entry — no other file changes needed.
6. Document structure rules exist only in `schemas.py` — consumers inline with source-of-truth comment.
7. `RULES_FILES` contains only PactKit-managed files; user-managed files (09-*, 10-*) go in `RULES_INSTRUCTIONS_CORE` only.
