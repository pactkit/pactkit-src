# Governance Rules

## Architecture Decisions

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| ADR-001 | Python 3.10+ with hatchling build | Broad compatibility, modern packaging | 2025-01 |
| ADR-002 | Prompt templates as Python string constants | Zero external deps for core, easy to test | 2025-01 |
| ADR-003 | pactkit.yaml for selective deployment config | User controls which agents/commands/rules deploy | 2025-02 |

## Invariants

1. All 1248+ tests must pass before any commit to `main`.
2. Specs (`docs/specs/`) are the source of truth — code conforms to specs, not the reverse.
3. CLI entry point is `pactkit` via `src/pactkit/cli.py:main`.
4. No runtime dependencies beyond `pyyaml`.
