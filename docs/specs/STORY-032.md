# Spec STORY-032: Greenfield redirect heuristic in /project-plan
- **Release**: 1.2.1

## Context
When a user sends a product ideation request to `/project-plan` (e.g., "I want to build a pet social app"), the Plan command treats it as an architectural expansion and attempts to create a single Spec. However, product ideation requests are better served by `/project-design`, which generates a full PRD, decomposes into multiple stories, and sets up the board.

The Plan command should detect "greenfield product ideation" intent and redirect to `/project-design`.

## Requirements
- The `/project-plan` command MUST detect greenfield product ideation signals in the user request during Phase 0 (Thinking).
- Detection heuristic signals SHOULD include:
  - Keywords: "from scratch", "new app", "startup", "MVP", "product idea", "创业", "从零开始"
  - Multi-story scope indicators: "multiple features", "full system", "complete app"
  - Empty sprint board (no existing stories)
  - Absence of existing source code files
- When greenfield intent is detected, the command MUST suggest: "This looks like a greenfield product design. Consider using `/project-design` instead."
- The command SHOULD NOT auto-redirect — it MUST ask the user to confirm the redirect.
- If the user chooses to stay in `/project-plan`, the command proceeds normally.

## Acceptance Criteria

### Scenario 1: Greenfield keywords trigger suggestion
- **Given** a user runs `/project-plan "I want to build a new social media app from scratch"`
- **When** Phase 0 analyzes the intent
- **Then** the command suggests `/project-design` as a better fit

### Scenario 2: User confirms redirect
- **Given** the greenfield suggestion is shown
- **When** the user confirms redirect
- **Then** the command hands off to `/project-design` with the original request

### Scenario 3: User stays in plan
- **Given** the greenfield suggestion is shown
- **When** the user declines redirect
- **Then** `/project-plan` proceeds normally with the original request

### Scenario 4: Non-greenfield request unaffected
- **Given** a user runs `/project-plan "Add 2FA to the login flow"`
- **When** Phase 0 analyzes the intent
- **Then** no redirect suggestion is shown, plan proceeds normally

### Scenario 5: Existing project with stories unaffected
- **Given** a project with existing stories on the sprint board
- **When** `/project-plan` is run with any request
- **Then** no greenfield redirect is triggered (existing project context overrides keyword detection)

## Design
Add a "Greenfield Detection" step to Phase 0 of `project-plan.md` in `commands.py`. After analyzing intent (New Feature vs Modification), check for greenfield signals. If detected, use `AskUserQuestion` to confirm redirect.

## Target Call Chain
`commands.py` → `COMMANDS_CONTENT["project-plan.md"]` → Phase 0 step 3 (new)
