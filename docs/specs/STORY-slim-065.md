# STORY-slim-065: Move _PACKAGING_MODES to FormatProfile (SSoT)

- **Status**: Done
- **Priority**: P3
- **Release**: TBD
- **Created**: 2026-03-30

## Problem

In `deployer.py`, `_PACKAGING_MODES = {"plugin", "marketplace"}` is a bare local set inside `deploy()`. This violates Architecture Principle #1 (Single Source of Truth). The set defines which formats are excluded from `format=all` deployment, but this knowledge is not on `FormatProfile` or in any canonical location.

## Root Cause

When `format=all` was implemented, the exclusion set was hardcoded locally for speed. It should be derived from `FormatProfile` metadata (e.g., a `packaging_only: bool` field).

## Requirements

### R1: Move to FormatProfile
Add a `packaging_only` (or similar) field to `FormatProfile` in `profiles.py`. Formats like `plugin` and `marketplace` should be marked `packaging_only=True`.

### R2: Deploy uses profile metadata
`deploy()` should filter formats using `profile.packaging_only` instead of a hardcoded set. Remove `_PACKAGING_MODES`.

### R3: No behavior change
The set of formats included in `format=all` must remain the same before and after.

## Acceptance Criteria
- [ ] R1: `FormatProfile` has a field distinguishing packaging-only formats
- [ ] R2: `_PACKAGING_MODES` local set removed from `deployer.py`
- [ ] R3: `pactkit init` (format=all) still deploys exactly classic + opencode + codex
