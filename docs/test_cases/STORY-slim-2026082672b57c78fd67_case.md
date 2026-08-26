# Test Case: STORY-slim-2026082672b57c78fd67

Subtraction pass (delivered scope: R3 bounded, R4 partial, R5 project-level).

## TC-01: argparse surface byte-identical (R3, AC3)

- **Given** golden help snapshots captured after the sanctioned skew unification
- **When** the root and all 44 subcommand helps run after the refactor
- **Then** every output matches its golden snapshot byte-for-byte

## TC-02: shared builder catches drift (R3, AC3)

- **Given** a registration-order difference introduced during extraction
- **When** the golden test runs
- **Then** it fails naming the changed command (verified live during development: update's --if-needed order)

## TC-03: adapter.py gone, suite green (R4, AC4)

- **Given** the removal
- **When** the full suite runs
- **Then** zero failures and no module imports generators.adapter

## TC-04: scorecard single-sourced (R4)

- **Given** the json_only audit path
- **When** the scorecard is emitted
- **Then** it derives from the result dict and includes story_id

## TC-05: new format reaches doctor without edits (R5, AC5)

- **Given** FORMAT_PROFILES patched with a trae entry in a test fixture
- **When** _project_deploy_dirs runs
- **Then** the trae directory appears alongside the existing four

## TC-06: deploy params deferral documented (R4)

- **Given** deploy()'s parameter list
- **When** read
- **Then** a DEFERRED(SHOULD) comment explains why the four unused parameters stay
