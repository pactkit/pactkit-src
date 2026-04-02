---
mode: agent
description: "Standalone requirement clarification before planning"
---

# Command: Clarify (v1.1.0)
- **Usage**: `/project-clarify "$ARGUMENTS"`
- **Agent**: System Architect

> **PURPOSE**: Standalone requirement clarification. Run before `/project-plan` to surface ambiguities and assess risks upfront.

## Phase 1: Ambiguity Analysis
1.  Analyze `$ARGUMENTS` against the AMBIGUITY_SIGNALS checklist (same as Plan Phase 0.7).
2.  Generate 3–6 structured questions (Scope, Users, Constraints, Scale, Edge Cases, Non-Goals).
3.  Ask questions in the user's language.

## Phase 2: Pre-mortem Risk Probe
> **PURPOSE**: Reverse thinking — identify how the plan could fail before it starts.
1.  Based on `$ARGUMENTS` and Phase 1 findings, generate 1–2 pre-mortem questions (pick the most relevant):
    - "If this feature is deemed a failure 1 month after launch, what is the most likely reason?"
    - "What assumptions does this plan rely on? Which assumption is the most fragile?"
    - "What will the person maintaining this code in 6 months complain about the most?"
    - "What is the most likely integration point to break?"
2.  Ask in the user's language, together with Phase 1 questions.
3.  Total questions across Phase 1 + Phase 2 MUST NOT exceed 6. If Phase 1 already has 5–6, pick only 1 pre-mortem question. If Phase 1 has ≤ 4, pick up to 2.

## Phase 3: Clarified Brief Output
1.  After user responses, produce a **Clarified Brief**:
    ```markdown
    ## Clarified Brief: {feature name}
    - **Scope**: {confirmed operations}
    - **Users**: {confirmed target users / roles}
    - **Constraints**: {technical constraints}
    - **Scale**: {performance expectations}
    - **Edge Cases**: {failure scenarios and expected behavior}
    - **Non-Goals**: {explicitly excluded}
    - **Risks**: {top 1-2 identified risks from pre-mortem}
    ```
2.  Output: "Ready for Plan. Run: `/project-plan \"{clarified brief summary}\"`"


---

## Rules Reference

# Core Protocol

## Session Context
On new session, check `.github/pactkit.yaml` exists. If not, run `pactkit init --format copilot` from the terminal.
If `.github/pactkit.yaml` does not exist (check `.github/`), run `pactkit init --format copilot` from the terminal to create it before proceeding.
Then read `docs/product/context.md` to understand project state before taking action.
If the file is missing, suggest `/project-init` to bootstrap the project.
If "Last updated" date is before today, suggest running `$daily-retro`.

## Visual First
Before modifying code:
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py` to view file dependency graph
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode class` for class inheritance
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode call --entry <func>` to trace call chains
- Run `python3 .github/skills/pactkit-visualize/scripts/visualize.py --mode module` for module-level architectural overview
- **PDCA Exemption**: When a PDCA command is active, the command's own visualize phases take precedence — skip Visual First.

## Strict TDD
- Write tests first (RED), then write implementation (GREEN)
- The agent MUST NOT skip TDD except when running `/project-hotfix`
- All tests MUST pass before committing

## Language Matching
- Match the user's language (Chinese→Chinese, English→English).
- Technical terms (function names, file paths, git commands) stay in original form.

## Signal Strength Convention
All rules and playbooks MUST use signal keywords consistently per this 4-level hierarchy:

| Level | Keywords | Semantics | Use When |
|-------|----------|-----------|----------|
| **L1 Absolute** | `NEVER` / `MUST NOT` | Violation = bug, zero tolerance | Security red lines, data loss, Spec tampering |
| **L2 Strong** | `CRITICAL` / `MUST` / `ALWAYS` | Violation = must-fix issue | Phase gates, TDD enforcement, regression blocking |
| **L3 Recommended** | `IMPORTANT` / `SHOULD` | Violation = warning, non-blocking | Best practices, performance advice, style |
| **L4 Advisory** | `Prefer` / `Consider` / `If possible` | Suggestion, skip by judgment | Optimization hints, optional enhancements |

- `NEVER` and `MUST NOT` are reserved for L1 — do not use them for anything less than absolute prohibition.
- `DO NOT` is ambiguous — replace with `NEVER` (L1) or `MUST NOT` (L1) for prohibitions, or rephrase as `SHOULD NOT` (L3) for recommendations.
- When writing an L1 or L2 rule, append a consequence clause: `— {what goes wrong if violated}`.

### Credential Safety

NEVER print passwords, keys, or tokens to stdout.
NEVER commit secrets to version control.
