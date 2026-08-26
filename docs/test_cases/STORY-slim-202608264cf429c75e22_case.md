# Test Case: STORY-slim-202608264cf429c75e22

Unify deployment ownership safety across skills, agents, CLAUDE.md and rollback.

## TC-01: User-modified skill preserved with candidate (AC1)

- **Given** a deployed skill `skills/pactkit-visualize/SKILL.md` whose bytes drift from both the newly rendered content and the manifest-recorded hash
- **When** `pactkit update` runs
- **Then** the drifted SKILL.md is byte-identical to before
- **And** a `SKILL.md.pactkit-new` candidate exists next to it
- **And** a preservation warning is printed

## TC-02: User-modified skill script preserved with candidate (AC1)

- **Given** a deployed skill script `scripts/visualize.py` whose bytes drift from both the new content and the manifest-recorded hash
- **When** `pactkit update` runs
- **Then** the drifted script is byte-identical to before and a `visualize.py.pactkit-new` candidate exists

## TC-03: Manifest-proven skill updates in place (AC2)

- **Given** a deployed SKILL.md whose bytes equal the manifest-recorded hash but differ from newly rendered content
- **When** `pactkit update` runs
- **Then** SKILL.md is overwritten in place and no `.pactkit-new` file is created

## TC-04: Agent retirement without proof preserves user file (AC3)

- **Given** `agents/system-architect.md` exists with user content and no manifest record proves ownership
- **When** `pactkit update` runs with that agent disabled in config
- **Then** the file is preserved with a warning

## TC-05: Agent retirement with proof deletes (AC3)

- **Given** `agents/system-architect.md` exists, the previous manifest records its hash, and the bytes match
- **When** `pactkit update` runs with that agent disabled in config
- **Then** the file is deleted

## TC-06: User-modified enabled agent preserved (AC3)

- **Given** an enabled agent's deployed file has drifted and has no manifest proof
- **When** `pactkit update` runs
- **Then** the drifted file is preserved and a `.md.pactkit-new` candidate is written

## TC-07: Manifest-proven enabled agent updates in place (AC3)

- **Given** an enabled agent's deployed file has drifted but matches the manifest-recorded hash
- **When** `pactkit update` runs
- **Then** the file is overwritten in place with no candidate

## TC-08: User file in skill dir not claimed by manifest (AC4)

- **Given** `skills/pactkit-visualize/references/my-notes.md` exists (user-created, not in the skill manifest)
- **When** `write_deploy_manifest` runs
- **Then** `my-notes.md` does not appear in the manifest `files` map
- **And** `SKILL.md` and the registered script do appear

## TC-09: Unreadable CLAUDE.md preserved (AC5)

- **Given** a global CLAUDE.md that raises OSError or UnicodeDecodeError on read
- **When** deployment runs
- **Then** the original file is untouched and a `CLAUDE.md.pactkit-new` candidate is written

## TC-10: Appended CLAUDE.md content survives managed update (AC6)

- **Given** a global CLAUDE.md with the PactKit managed header and import line, followed by user content
- **When** `pactkit update` runs
- **Then** the managed block is refreshed and every non-managed line is preserved verbatim

## TC-11: Non-managed CLAUDE.md untouched (AC5)

- **Given** a global CLAUDE.md whose first line is not a PactKit managed header
- **When** deployment runs
- **Then** the file is not modified and no candidate is written

## TC-12: Ctrl-C mid-deployment rolls back (AC7)

- **Given** an adapter deployment wrapped in `rollback_paths` with existing files snapshotted
- **When** the deployment body raises KeyboardInterrupt
- **Then** all snapshotted paths are restored to pre-deployment bytes and the KeyboardInterrupt propagates

## TC-13: Rollback restore failure does not abort remaining restores (AC10)

- **Given** two snapshotted paths where restoring the first raises OSError
- **When** the deployment body raises
- **Then** the second path is still restored and the original exception propagates

## TC-14: Disabled skill retired with proof (AC8)

- **Given** a skill disabled in config whose deployed directory contains exactly the registered artifacts, each matching the previous manifest hash
- **When** `pactkit update` runs
- **Then** the skill directory is removed

## TC-15: Drifted disabled skill preserved (AC8)

- **Given** a skill disabled in config whose SKILL.md has drifted from the manifest-recorded hash
- **When** `pactkit update` runs
- **Then** the drifted directory is preserved with a warning

## TC-16: Rules and guides preservation semantics unchanged (AC9)

- **Given** a deployed rule file and a deployed guide file, each drifted from rendered content without manifest proof
- **When** `pactkit update` runs
- **Then** both are preserved with `.pactkit-new` candidates, identical to skill and agent preservation behavior

## TC-17: Plugin regeneration keeps overwriting (regression guard)

- **Given** a plugin-format build directory containing a stale generated SKILL.md
- **When** plugin deployment regenerates
- **Then** the stale file is overwritten and no `.pactkit-new` files are created

## TC-18: User-modified command skill preserved (AC1, QA clarification)

- **Given** a deployed command skill `skills/project-act/SKILL.md` whose bytes drift from rendered content and manifest hash
- **When** `pactkit update` runs
- **Then** the drifted file is preserved and a `SKILL.md.pactkit-new` candidate is written

## TC-19: CLAUDE.md content between header and import preserved (R5 clarification)

- **Given** a managed CLAUDE.md with non-blank user content between the managed header and the runtime import line
- **When** deployment runs
- **Then** the file is preserved untouched and a candidate is written

## TC-20: CLAUDE.md quoted import line preserved (R5 clarification)

- **Given** a managed CLAUDE.md without a managed import line whose user content contains a standalone line equal to the import line
- **When** deployment runs
- **Then** the file is preserved untouched and a candidate is written

## TC-21: Bare deploy_skills call fails safe (gate unification)

- **Given** a drifted deployed skill and a `_deploy_skills` call with neither profile nor legacy prefix
- **When** the call runs
- **Then** the drifted file is preserved with a candidate (ownership enforced, not silently degraded)

## TC-22: Empty user subdirectory blocks skill retirement

- **Given** a proven-unchanged skill directory containing a user-created empty subdirectory
- **When** the skill is disabled and `pactkit update` runs
- **Then** the directory is preserved with a warning

## TC-23: Preserved skill not counted as deployed

- **Given** a drifted deployed skill
- **When** `_deploy_skills` runs
- **Then** the returned deployed count excludes the preserved skill
