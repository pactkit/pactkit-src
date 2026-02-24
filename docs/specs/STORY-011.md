# STORY-011: PDCA Slim — 辅助命令降级为 Skill，精简用户界面

- **Status**: Backlog
- **Priority**: 5.0 (Impact 5 / Effort 1)
- **Release**: 1.1.2
- **Author**: System Architect
- **Created**: 2026-02-13

## Background

PactKit currently exposes 14 top-level `/project-*` commands. As the command surface grows, users face cognitive overload — most sessions only use 4-6 commands. Six of the 14 commands are **supporting utilities** (trace, draw, status, doctor, review, release) that are better served as skills embedded into the PDCA core commands, where they are auto-invoked at the right moment.

This refactoring reduces the user-facing command count from 14 → 8 while preserving all functionality. Skills become the "invisible infrastructure" that powers the PDCA workflow.

## Current Architecture

```
14 Commands (all top-level, user must choose)
├── PDCA Core: plan, act, check, done
├── Lifecycle: init, design, release
├── Orchestration: sprint, hotfix
└── Utilities: trace, draw, status, doctor, review
```

## Target Architecture

```
8 Commands (PDCA-centric, user focuses on workflow)
├── PDCA Core: plan, act, check, done
├── Lifecycle: init, design
├── Orchestration: sprint, hotfix
│
6 Skills (embedded, auto-invoked by commands)
├── pactkit-trace     → Plan Phase 1, Act Phase 1
├── pactkit-draw      → Plan Phase 2 (on-demand), Design Phase 2
├── pactkit-status    → Init Phase 6, cold-start detection
├── pactkit-doctor    → Init (auto-check)
├── pactkit-review    → Check Phase 4 (PR variant)
└── pactkit-release   → Done Phase 4 (release variant, when version arg given)
```

## Target Call Chain

```
deployer.py::_deploy_skills()  →  writes 9 skill dirs (3 existing + 6 new)
deployer.py::_deploy_commands() → writes 8 command files (down from 14)
config.py::VALID_COMMANDS       → 8 entries (down from 14)
config.py::VALID_SKILLS         → 9 entries (up from 3)
prompts/commands.py::COMMANDS_CONTENT → 8 entries (move 6 to skills.py)
prompts/skills.py               → 9 SKILL_*_MD templates (up from 3)
prompts/agents.py               → update agent skills references
prompts/rules.py::RULES_MODULES['routing'] → 8 entries in routing table
```

## Requirements

### R1: Command Reduction (MUST)
The following commands MUST be removed from `VALID_COMMANDS` and `COMMANDS_CONTENT`:
- `project-trace` → becomes `pactkit-trace` skill
- `project-draw` → becomes `pactkit-draw` skill
- `project-status` → becomes `pactkit-status` skill
- `project-doctor` → becomes `pactkit-doctor` skill
- `project-review` → becomes `pactkit-review` skill
- `project-release` → becomes `pactkit-release` skill

### R2: Skill Promotion (MUST)
Each removed command MUST be converted to a skill with:
- A `SKILL_*_MD` template in `prompts/skills.py` containing the original prompt content
- A Python script in `src/pactkit/skills/` (if the skill needs executable logic)
- Registration in `VALID_SKILLS` in `config.py`

### R3: PDCA Command Integration (MUST)
The core PDCA commands MUST reference the new skills where previously they referenced sibling commands:
- `project-plan.md`: Phase 1 MUST invoke `pactkit-trace` skill instructions (instead of "run `/project-trace`")
- `project-act.md`: Phase 1 MUST invoke `pactkit-trace` skill instructions
- `project-check.md`: MUST include `pactkit-review` capability for PR review scenarios
- `project-done.md`: MUST reference `pactkit-release` for version release scenarios

### R4: Routing Table Update (MUST)
`RULES_MODULES['routing']` MUST be updated to list only the 8 remaining commands and reference the 6 new skills with their embedding locations.

### R5: Agent Skill References (MUST)
`AGENTS_EXPERT` skill lists MUST be updated to include the new skills where relevant:
- `system-architect`: add `pactkit-trace`, `pactkit-draw`
- `senior-developer`: add `pactkit-trace`
- `qa-engineer`: add `pactkit-review`
- `repo-maintainer`: add `pactkit-release`
- `system-medic`: add `pactkit-status`, `pactkit-doctor`

### R6: Config Auto-Merge Compatibility (MUST)
The `auto_merge_config_file()` function MUST handle the transition:
- New skills added to `VALID_SKILLS` will auto-merge into existing `pactkit.yaml` files
- Removed commands will NOT be auto-removed (user's yaml is authoritative)

### R7: Deployer Adaptation (MUST)
`deployer.py` MUST deploy the 6 new skills (each as a directory with `SKILL.md`). Skills that have no executable script only need `SKILL.md` (prompt-only skills).

### R8: Backward Compatibility (SHOULD)
Existing `pactkit.yaml` files that list removed commands SHOULD be handled gracefully:
- `load_config()` SHOULD emit a deprecation warning for commands that have been converted to skills
- The warning SHOULD suggest the user update their config

### R9: Test Updates (MUST)
- All count-based tests MUST be updated (VALID_COMMANDS: 14→8, VALID_SKILLS: 3→9)
- Command deployment tests MUST be updated
- New skill deployment tests MUST be created

## Acceptance Criteria

### Scenario 1: Fresh Install
Given a new user runs `pactkit init`
When the deployment completes
Then 8 command files exist in `~/.claude/commands/`
And 9 skill directories exist in `~/.claude/skills/`
And `pactkit.yaml` lists 8 commands and 9 skills

### Scenario 2: Upgrade from v1.1.0
Given a user with v1.1.0 `pactkit.yaml` listing 14 commands and 3 skills
When they run `pactkit init` (triggering auto-merge)
Then 6 new skills are auto-added to their yaml
And a deprecation warning is emitted for the 6 removed commands
And the deployer deploys only the 8 valid commands (ignoring removed ones)

### Scenario 3: Plan invokes Trace skill
Given a user runs `/project-plan "modify feature X"`
When the agent reaches Phase 1 (Archaeology)
Then the agent uses the pactkit-trace skill instructions directly
And does NOT reference `/project-trace` as a separate command

### Scenario 4: Done invokes Release skill
Given a user runs `/project-done` after completing a version bump story
When the agent reaches Phase 4
Then the agent can invoke pactkit-release skill for tagging and snapshot
And does NOT require a separate `/project-release` command

### Scenario 5: Check includes Review capability
Given a user runs `/project-check PR-123`
When the argument matches a PR pattern
Then the agent uses pactkit-review skill to perform PR code review
And does NOT require a separate `/project-review` command

### Scenario 6: Doctor embeds Status
Given a user runs `/project-doctor` (which remains as a check capability, embedded into init/check)
When the health check runs
Then it includes the status report (from pactkit-status skill)
And provides the same information as the former `/project-status` command
