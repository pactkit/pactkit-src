# BUG-slim-007: W007 substring matching causes false negatives and inconsistency

| Field | Value |
|-------|-------|
| ID | BUG-slim-007 |
| Status | Draft |
| Priority | P1 |
| Release | 2.3.6 |
| Origin | Cross-model code review (2026-03-24) |

## Background

W007 (Req-AC coverage check) was introduced in STORY-slim-024 (v2.3.4) and patched in v2.3.5 to use `SPEC_RFC_KEYWORDS` instead of hardcoded `SHOULD`. Code review found that the implementation uses Python `in` (substring) matching in two places where word-boundary regex is required, plus a pattern divergence from the canonical source.

### Bug 1: R{N} coverage check — substring false negative

`spec_linter.py:241`:
```python
if req_id.lower() not in ac_lower:
```

When AC section mentions `R10`, the string `"r1"` is a substring of `"r10"` — so `R1` is falsely reported as covered. Similarly `"r1" in "r12"`, `"r2" in "r20"`, etc. Also non-R prefixed text like `"CR1"`, `"ERROR1"`, `"PR1"` would suppress W007 for `R1`.

**Impact**: Any spec with 10+ requirements silently passes W007 for R1-R9 when R10+ exists in AC. This directly undermines W007's purpose.

### Bug 2: RFC keyword detection — substring inconsistency with W003

`spec_linter.py:244`:
```python
found_keyword = next((kw for kw in SPEC_RFC_KEYWORDS if kw in req_upper), None)
```

W003 at line 172 uses `_RFC2119.search(body)` which is `SPEC_RFC_PATTERN` — a compiled regex with `\b` word boundaries. W007 uses plain `kw in req_upper` (substring). This means `"MAYONNAISE"` matches `MAY`, `"SHALLOW"` matches `SHALL`, etc.

Two rules in the same file detecting RFC 2119 keywords with different strategies is a consistency violation.

### Bug 3: _REQ_ID_PATTERN diverges from SPEC_REQUIREMENT_PATTERN

`spec_linter.py:203`:
```python
_REQ_ID_PATTERN = re.compile(r"###\s+(R\d+)[:\s]", re.MULTILINE)
```

`schemas.py:32`:
```python
SPEC_REQUIREMENT_PATTERN = r"### R\d+[:\s]"
```

E004 uses `SPEC_REQUIREMENT_PATTERN` (literal single space after `###`), while W007 uses `_REQ_ID_PATTERN` (`\s+` — allows tab, multiple spaces). A heading `###  R1:` (double space) would be found by W007 but missed by E004. Both patterns should derive from the same canonical source.

## Requirements

### R1: Word-boundary matching for R{N} coverage (MUST)

W007 MUST use word-boundary regex to check whether an R{N} ID appears in the AC section. `R1` MUST NOT match `R10`, `R12`, `CR1`, `ERROR1`, or any other superstring.

Pattern: `re.search(rf"\b{req_id}\b", ac_section, re.IGNORECASE)`

### R2: Word-boundary matching for RFC 2119 keywords (MUST)

W007's RFC 2119 keyword detection MUST use `SPEC_RFC_PATTERN` (from `schemas.py`) — the same compiled regex with `\b` word boundaries that W003 already uses. `MAY` MUST NOT match `MAYONNAISE`.

### R3: _REQ_ID_PATTERN MUST derive from SPEC_REQUIREMENT_PATTERN (SHOULD)

`_REQ_ID_PATTERN` SHOULD be constructed from `SPEC_REQUIREMENT_PATTERN` or share the same whitespace semantics, so that E004 and W007 agree on what constitutes a valid `### R{N}` heading.

If intentional divergence is needed (e.g., W007 is more tolerant), document the reason inline.

### R4: Test coverage for multi-digit R{N} (MUST)

Tests MUST include a spec with R1 through R10+ where only R10 is referenced in AC, to verify R1 is correctly flagged as uncovered.

### R5: Test coverage for all 7 RFC 2119 keywords (SHOULD)

Tests SHOULD cover all 7 keywords from `SPEC_RFC_KEYWORDS`, not just MUST/SHOULD/MAY. Tests SHOULD also cover the no-keyword case (empty emphasis).

## Acceptance Criteria

### AC1: R1 not falsely covered by R10 (R1, R4)

- **Given** a spec with `### R1: First` and `### R10: Tenth` in Requirements
- **When** AC section mentions only `R10` (not `R1`)
- **Then** W007 fires for R1 with message "Requirement R1 has no corresponding AC reference"
- **And** W007 does NOT fire for R10

### AC2: Non-R prefix text does not suppress W007 (R1)

- **Given** a spec with `### R1: Something` in Requirements
- **When** AC section contains `ERROR1` or `CR1` but not standalone `R1`
- **Then** W007 fires for R1

### AC3: RFC keyword word-boundary (R2)

- **Given** a spec with unreferenced `### R1: The system MAYONNAISE handler`
- **When** spec linter runs
- **Then** W007 message does NOT contain `(MAY)` — substring `MAY` inside `MAYONNAISE` is not a match
- **And** emphasis is empty (no RFC keyword found)

### AC4: All 7 RFC keywords detected (R2, R5)

- **Given** specs with unreferenced requirements containing each of: MUST, SHOULD, MAY, SHALL, REQUIRED, RECOMMENDED, OPTIONAL
- **When** spec linter runs
- **Then** each W007 message contains the correct keyword in parentheses: `(MUST)`, `(SHOULD)`, etc.

### AC5: W003 and W007 use same detection mechanism (R2)

- **Given** the spec_linter.py source code
- **When** inspecting both W003 and W007 RFC 2119 detection
- **Then** both use `SPEC_RFC_PATTERN` (or `_RFC2119` alias) for matching — no plain `kw in string`

### AC6: Existing tests still pass (regression)

- **Given** all pre-existing tests in test_story_slim024.py and test_story042_spec_linter.py
- **When** running the full test suite
- **Then** all tests pass — no regressions from word-boundary change

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/skills/spec_linter.py:241` | Replace `req_id.lower() not in ac_lower` with `re.search(rf"\b{re.escape(req_id)}\b", ac_section, re.IGNORECASE)` | None | Low |
| 2 | `src/pactkit/skills/spec_linter.py:244` | Replace `next((kw for kw in SPEC_RFC_KEYWORDS if kw in req_upper), None)` with `SPEC_RFC_PATTERN.search(req_body)` using match group | Step 1 | Low |
| 3 | `src/pactkit/skills/spec_linter.py:203` | Add inline comment documenting why `_REQ_ID_PATTERN` uses `\s+` vs `SPEC_REQUIREMENT_PATTERN`'s literal space, or unify | None | Low |
| 4 | `tests/unit/test_story_slim024.py` | Add R10 multi-digit test (AC1), non-R-prefix test (AC2), MAYONNAISE test (AC3), all-7-keywords test (AC4), no-keyword test (AC5 empty emphasis) | Steps 1-2 | Low |
| 5 | `tests/unit/test_story_slim024.py` | Migrate from `tempfile.NamedTemporaryFile(delete=False)` to pytest `tmp_path` fixture (consistency with test_story042) | None | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1~8 | No | Lint rule logic change, no I/O or auth |

## Out of Scope

- `_section_text()` returning heading line (fragile but extremely unlikely to cause false suppression)
- Sectional write rule 150 vs 300 inconsistency in `rules.py:359` (trivial fix, separate commit)
- `config.py:961` api_spec empty string default (docs already fixed, code default is cosmetic)
- Board archive section ordering (functional, not a bug)
