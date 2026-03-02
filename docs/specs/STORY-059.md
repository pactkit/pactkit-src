# Spec STORY-059: Add Prototype Generation Phase to project-design

## Metadata
| Field | Value |
|-------|-------|
| ID | STORY-059 |
| Title | Add Prototype Generation Phase to project-design |
| Status | Draft |
| Priority | P2 |
| Author | System Architect |
| Created | 2026-03-02 |
| Release | 1.6.0 |

## Summary
Add a new Section 1.6 (Prototype Generation) to the `/project-design` command's `DESIGN_PROMPT`. After the Page/Screen Design phase (Section 1.5), the Product Designer agent generates single-file HTML + Tailwind CDN prototypes for each key page, writes them to `docs/prototypes/`, and optionally opens them in the browser via Playwright MCP for live preview.

## Background
The current `/project-design` command outputs only text-based artifacts: PRD (markdown), Specs (markdown), Architecture (mermaid). The Page/Screen Design section (1.5) describes UI component hierarchy in plain text, but produces nothing visually interactive. Users cannot see what the product looks like until the Act phase generates real code.

Gemini Canvas demonstrates that generating runnable HTML prototypes during the design phase dramatically accelerates product iteration. A single-file HTML + Tailwind CDN approach requires zero project dependencies and can be opened directly in any browser.

## Requirements

### R1: Insert Prototype Generation Section
The system MUST add a new Section 1.6 (Prototype Generation) to `DESIGN_PROMPT` in `workflows.py`, inserted after the existing Section 1.5 (Page/Screen Design).

### R2: Renumber Existing Sections
The existing Sections 1.6 through 1.9 MUST be renumbered to 1.7 through 2.0 to accommodate the insertion.

### R3: One Prototype Per Key Page
Section 1.6 MUST instruct the Product Designer to generate one `.html` file per key page defined in Section 1.5.

### R4: Self-contained HTML with CDN Only
Each generated HTML file MUST be a self-contained single file using only:
- Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`)
- Lucide Icons via CDN (`<script src="https://unpkg.com/lucide@latest"></script>`)
- Vanilla JavaScript for interactions (no React, no build step)

### R5: Output Path
Prototype files MUST be written to `docs/prototypes/{page-name}.html`.

### R6: Playwright MCP Preview (Conditional)
The system SHOULD use Playwright MCP (`mcp__playwright__browser_navigate`) to open the prototype in a browser for live preview, conditional on MCP availability. If Playwright MCP is not available, the file path is printed as the sole output.

### R7: Update "Does NOT" Section
The "What This Command Does NOT Do" section MUST be updated to remove the "Does NOT generate UI wireframe images" line and replace it with a note that prototypes are HTML-only (no production React/Vue code).

### R8: No README Change
The `README.md` MUST NOT be updated in this story — README updates are deferred to the release cycle.

## Acceptance Criteria

### Scenario 1: DESIGN_PROMPT contains new Section 1.6
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** the prompt is read
- **Then** it contains "### 1.6 Prototype Generation" between Section 1.5 and Section 1.7

### Scenario 2: Section renumbering is correct
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** the prompt is read
- **Then** Sections 1.1 through 2.0 exist in sequential order with no gaps or duplicates

### Scenario 3: Prototype section references Tailwind CDN
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** Section 1.6 content is examined
- **Then** it contains `cdn.tailwindcss.com` and `lucide`

### Scenario 4: Prototype output path specified
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** Section 1.6 content is examined
- **Then** it contains `docs/prototypes/`

### Scenario 5: Playwright MCP is conditional
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** Section 1.6 content is examined
- **Then** it contains both `mcp__playwright__` (the tool name) and a conditional check ("IF ... available")

### Scenario 6: "Does NOT" section updated
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** the "What This Command Does NOT Do" section is examined
- **Then** it does NOT contain "Does NOT generate UI wireframe images"
- **And** it contains a note about prototypes being HTML-only, not production code

### Scenario 7: Backward compatibility — existing phases intact
- **Given** the `DESIGN_PROMPT` string in `workflows.py`
- **When** the prompt is read
- **Then** it still contains Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5
- **And** Phase 0 still references "thinking"
- **And** Phase 1 still references "PRD Generation"

### Scenario 8: Existing test_design_command tests still pass
- **Given** the existing test suite `tests/unit/test_design_command.py`
- **When** `pytest tests/unit/test_design_command.py` is run
- **Then** all tests pass without modification

## Design

### Insertion Point
```python
# workflows.py DESIGN_PROMPT structure (current → proposed)
#
# Section 1.5 Page/Screen Design  (unchanged)
# Section 1.6 Prototype Generation (NEW)  ← INSERT HERE
# Section 1.7 API Design           (was 1.6)
# Section 1.8 Non-Functional Req   (was 1.7)
# Section 1.9 Success Metrics      (was 1.8)
# Section 2.0 MVP Roadmap          (was 1.9)
```

### HTML Template (embedded in prompt)
The Section 1.6 prompt will include a few-shot HTML template demonstrating the expected output format: Tailwind CDN, Lucide Icons, responsive layout, vanilla JS interactivity.

### Playwright MCP Conditional Pattern
Follow the same pattern already used in `DRAW_PROMPT_TEMPLATE` (line 218):
```
IF `browser_navigate` tool is available (Playwright MCP), navigate to the file.
IF Playwright MCP is not available, skip — the file on disk is the sole output.
```

## Target Call Chain
```
/project-design (commands.py)
  → DESIGN_PROMPT (workflows.py:681)
    → Phase 1, Section 1.5: Page/Screen Design (text)
    → Phase 1, Section 1.6: Prototype Generation (NEW)
        → Write tool: docs/prototypes/{page}.html
        → Playwright MCP: browser_navigate (conditional)
    → Phase 1, Section 1.7+: API Design, NFR, Metrics, Roadmap
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/prompts/workflows.py` | Insert Section 1.6 into DESIGN_PROMPT, renumber 1.6-1.9 → 1.7-2.0, update "Does NOT" section | None | Low |
| 2 | `tests/unit/test_design_command.py` | Add tests for Scenario 1-7 (new Section 1.6 assertions) | Step 1 | Low |
