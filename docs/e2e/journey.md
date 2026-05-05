# User Journey Format Specification

> This document defines the canonical format for `docs/e2e/journey.md` in PactKit-managed projects.
> It is a **format specification template** -- projects copy and fill this structure with their own journeys.

## Purpose

A user journey describes an end-to-end flow that spans multiple stories. While individual stories
have their own acceptance criteria (in `docs/test_cases/`), journeys capture the cross-story
integration path that a real user follows.

**Relationship to other artifacts:**
- `docs/test_cases/{ID}_case.md` -- single-story acceptance (Gherkin scenarios)
- `docs/e2e/journey.md` -- cross-story user flows (this document)
- `tests/e2e/` -- executable E2E test code implementing journey segments

---

## Journey Structure

Each journey follows this format:

```markdown
## Journey: {Journey Name}

> {One-line description of the user goal}

### Pre-conditions (Fixtures)

| Fixture | Description | Setup Method |
|---------|-------------|--------------|
| {name} | {what it provides} | {seed script / API call / fixture function} |

### Steps

#### Step 1: {Step Title} [client]

**Action**: {What the user does}

**Assertions**:
- STRUCTURE: {element/component} exists on page
- STRUCTURE: {data container} is non-empty
- BEHAVIOR: {interaction} triggers {expected response}

#### Step 2: {Step Title} [server]

**Action**: {What the system processes}

**Assertions**:
- STRUCTURE: {database record / API response} contains expected fields
- STRUCTURE: {response payload} is non-empty
- BEHAVIOR: {side effect} is observable (log entry, event emitted, etc.)

#### Step 3: {Step Title} [server+client]

**Action**: {Full-stack interaction}

**Assertions**:
- STRUCTURE: {UI element} renders with data from server
- STRUCTURE: {response} matches expected schema shape
- BEHAVIOR: {round-trip} completes within timeout
```

---

## Execution Layer Annotations

Each step MUST be annotated with its execution layer:

| Annotation | Meaning | Test Tooling |
|------------|---------|--------------|
| `[client]` | Browser/UI interaction only | Playwright, Cypress |
| `[server]` | Backend/API processing only | pytest + httpx, curl |
| `[server+client]` | Full-stack round-trip | Playwright + API assertions |

---

## Assertion Types

Assertions are classified into two categories with different enforcement rules:

### Structure Assertions (MUST)

Structure assertions verify that the expected elements, fields, or components **exist** and are
**non-empty**. These are deterministic and safe to assert in any context.

Examples:
- "SQL code block element exists on page"
- "Chart component is rendered"
- "API response contains `data` field"
- "Answer container has text content (length > 0)"

### Content Assertions (MUST NOT for AI-generated content)

Content assertions verify specific text values, numbers, or exact strings. These are appropriate
for deterministic outputs but MUST NOT be used for AI-generated content.

**When content is deterministic** (e.g., user profile display, static labels):
- Exact text matching is acceptable
- Numeric value assertions are acceptable

**When content is AI-generated** (e.g., chatbot responses, generated analysis):
- MUST NOT assert specific text content
- MUST NOT assert exact numeric values in generated output
- MUST NOT assert specific word choices or phrasing

---

## AI Content Assertion Strategy

> This section provides guidance for projects that include AI-generated content in their user journeys
> (e.g., chatbots, AI assistants, generated reports, analysis tools).

### What to Assert (MUST)

| Category | Example Assertion |
|----------|------------------|
| Structure exists | "SQL code block element is present in the response area" |
| Non-empty | "Response container has text content with length > 0" |
| Component renders | "Chart component is mounted and visible" |
| Schema shape | "API response has `answer` field of type string" |
| Timing | "Response arrives within N seconds" |
| State transition | "Loading spinner disappears after response" |

### What NOT to Assert (MUST NOT)

| Anti-Pattern | Why It Fails |
|--------------|--------------|
| `assert response.text == "The answer is 42"` | AI output is non-deterministic |
| `assert chart.data_points == [1.5, 2.3, 4.1]` | Generated values vary per run |
| `assert sql_block.contains("SELECT * FROM users")` | AI may generate equivalent but different SQL |
| `assert summary.word_count == 150` | Length varies with model/prompt |

### Correct Pattern

```python
# STRUCTURE: verify element exists
assert page.locator(".sql-code-block").is_visible()

# NON-EMPTY: verify content was generated
sql_content = page.locator(".sql-code-block").text_content()
assert len(sql_content.strip()) > 0

# SCHEMA: verify response shape, not content
response = api_client.get("/chat/answer")
assert "answer" in response.json()
assert isinstance(response.json()["answer"], str)
assert len(response.json()["answer"]) > 0

# BEHAVIOR: verify state transition occurred
assert page.locator(".loading-spinner").is_hidden()
assert page.locator(".answer-area").is_visible()
```

---

## Pre-condition Fixtures

Each journey MUST declare its pre-conditions as named fixtures:

```markdown
### Pre-conditions (Fixtures)

| Fixture | Description | Setup Method |
|---------|-------------|--------------|
| authenticated_user | Logged-in user session | `conftest.py::auth_fixture` |
| sample_dataset | Pre-loaded test data | `scripts/seed_test_data.py` |
| clean_state | Empty database with schema | `pytest fixture: db_reset` |
```

Fixtures are referenced by name in step pre-conditions, enabling:
- Test isolation (each journey starts from a known state)
- Parallelization (independent journeys can run concurrently)
- Debugging (reproduce failures by loading specific fixtures)

---

## Example: Complete Journey

```markdown
## Journey: First Question to Answer

> New user asks their first question and receives an AI-generated answer.

### Pre-conditions (Fixtures)

| Fixture | Description | Setup Method |
|---------|-------------|--------------|
| authenticated_user | Logged-in user with valid session | `conftest.py::auth_user` |
| connected_datasource | At least one data source configured | `seed/datasource.sql` |

### Steps

#### Step 1: Navigate to Chat [client]

**Action**: User opens the chat interface from dashboard.

**Assertions**:
- STRUCTURE: Chat input field is visible
- STRUCTURE: Message history area exists (may be empty)
- BEHAVIOR: Input field accepts text input

#### Step 2: Submit Question [server+client]

**Action**: User types a question and presses Enter.

**Assertions**:
- STRUCTURE: Loading indicator appears
- STRUCTURE: User message appears in history
- BEHAVIOR: API call to `/api/chat` is triggered

#### Step 3: Receive Answer [server+client]

**Action**: Server processes the question and streams response.

**Assertions**:
- STRUCTURE: Answer area becomes visible
- STRUCTURE: Answer text content is non-empty
- STRUCTURE: SQL code block is present (if query was data-related)
- BEHAVIOR: Loading indicator disappears
- MUST NOT: Assert specific answer text content (AI-generated)
- MUST NOT: Assert exact SQL query string (AI-generated)

#### Step 4: View Generated Visualization [client]

**Action**: User clicks on the chart tab to see generated visualization.

**Assertions**:
- STRUCTURE: Chart component is rendered
- STRUCTURE: Chart has at least one data series
- BEHAVIOR: Chart responds to hover interaction
- MUST NOT: Assert specific chart data values (AI-generated)
```

---

## Usage in Check Phase 4

When `/project-check` Phase 4 (E2E Execution) runs:

1. If `docs/e2e/journey.md` exists, read it to identify journey segments affected by the current story
2. E2E tests SHOULD cover the affected segments (not the full journey)
3. Journey definitions inform test scope; `docs/test_cases/` informs acceptance criteria
