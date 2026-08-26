# Test Case: STORY-slim-20260826ac1f0bfe4148

Prompt-to-CLI contract consistency.

## TC-01: fabricated subcommand fails the contract test (R1, AC1)

- **Given** a prompts module referencing `pactkit nonexistent-cmd`
- **When** the contract test runs
- **Then** it fails naming the fabricated subcommand

## TC-02: current tree passes (R1, AC2)

- **Given** the current prompts source
- **When** the contract test runs
- **Then** all referenced subcommands are registered (extraction tolerates multiline add_parser)

## TC-03: add_task round-trips (R2, AC3)

- **Given** an existing story
- **When** StoryRepository.add_task appends a task
- **Then** the record contains it with completed false; a done story reopens

## TC-04: duplicate task rejected (R2, AC3)

- **Given** an existing task title
- **When** add_task is called with the same title
- **Then** GovernanceError is raised

## TC-05: prose basename does not double-add (R3, AC4)

- **Given** a spec whose table declares a path and whose prose backtick-mentions the bare basename
- **When** spec-preflight runs
- **Then** the file is inlined exactly once

## TC-06: oversized prose reference warns (R3, AC5)

- **Given** a spec whose prose backtick-mentions a 40KB undeclared file
- **When** spec-preflight runs
- **Then** a WARN with declaration hint is emitted and preflight completes

## TC-07: playbook interface inventory (R4)

- **Given** the Done playbook
- **When** rendered
- **Then** board.py subcommands and spec-status accepted values are enumerated
