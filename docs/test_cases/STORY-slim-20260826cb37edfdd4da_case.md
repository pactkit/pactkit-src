# Test Case: STORY-slim-20260826cb37edfdd4da

Freeze and isolate the legacy workflow engine.

## TC-01: import paths survive the move (R1, AC1)

- **Given** the legacy package in place
- **When** pactkit.workflow_engine and pactkit.host_continuation are imported
- **Then** they resolve to the same module objects as pactkit.legacy.*

## TC-02: mock.patch targets keep working (R1)

- **Given** a patch on pactkit.workflow_engine._fingerprint
- **When** legacy internals read it
- **Then** the patch is visible (sys.modules alias, not re-export)

## TC-03: FROZEN markers (R1, AC6)

- **Given** the legacy modules
- **When** their docstrings are read
- **Then** each declares the frozen policy and deletion criterion

## TC-04: constant single source (R2)

- **Given** pactkit.protocols.CORE_PROTOCOL_VERSION
- **When** deploy_manifest reads it
- **Then** both are the same object

## TC-05: counter increments (R3, AC3)

- **Given** HOME redirected and the kill-switch unset
- **When** record_legacy_usage runs
- **Then** ~/.pactkit/legacy-engine-usage.json records count 1 with dates

## TC-06: active gates not counted (R3, AC4)

- **Given** ContinuationEngine.validate_managed_operation invoked
- **When** it runs
- **Then** the counter file is not created

## TC-07: doctor surfaces usage (R3, AC5)

- **Given** recorded invocations
- **When** check_legacy_engine_usage runs
- **Then** totals, per-command counts, and last-seen are reported

## TC-08: test invocations never count (R3)

- **Given** the root conftest autouse kill-switch
- **When** the full suite runs
- **Then** the machine counter stays empty

## TC-09: explicit CLI still works (R2, AC2)

- **Given** a temp initialized project
- **When** pactkit workflow registry runs
- **Then** exit code 0

## TC-10: deprecation notice (R4, AC7)

- **Given** CHANGELOG.md
- **When** read
- **Then** the legacy engine is declared a deletion candidate with the criterion

## TC-11: engine tests survive the move (R5, AC8)

- **Given** the ten engine-related test files after import-path updates
- **When** the full suite runs
- **Then** all previously passing engine tests pass and no test file was deleted
