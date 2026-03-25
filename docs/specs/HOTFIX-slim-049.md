# HOTFIX-slim-049: Fix spec/PRD consistency issues

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-049 |
| Status | In Progress |
| Priority | P3 |

## Background

Cross-check of Sonnet-generated specs (039-048) against PRD revealed 4 consistency issues.

## Fixes

1. **STORY-slim-040 AC1**: Says "detect() and parse() are abstract" but R1 defines detect() as concrete default. Fix AC1 wording.
2. **STORY-slim-042 R1 markers**: Missing `kubernetes/, k8s/` entries that PRD includes. Add them.
3. **PRD §4.5 database/reads_db**: Not covered by any story. Remove from PRD to match actual scope.
4. **PRD §9 Roadmap**: Stories 039-048 still unchecked. Mark as done.
