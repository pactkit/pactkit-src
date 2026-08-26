# Test Case: STORY-slim-20260826f9492ab32c3d

pactkit.yaml read/sync precedence unified into one canonical order.

## TC-01: effective copy propagates, not .claude (R1, AC1)

- **Given** .opencode/pactkit.yaml and .claude/pactkit.yaml with different content
- **When** sync_config_copies runs
- **Then** .claude receives .opencode's content and .opencode is unchanged

## TC-02: user edits to the effective copy survive (R1, AC1)

- **Given** a user-edited effective copy
- **When** sync runs
- **Then** the edits are preserved and propagated

## TC-03: readers and sync agree (R1, AC2)

- **Given** multiple copies
- **When** find_pactkit_yaml and sync_config_copies both run
- **Then** the effective copy is never the one overwritten and synced copies match its content

## TC-04: crash-safe sync (R2, AC3)

- **Given** os.replace raising mid-sync
- **When** sync runs
- **Then** the pre-existing copy content is intact

## TC-05: divergence is reported (R3, AC4)

- **Given** differing copies
- **When** sync runs
- **Then** stdout names the overwritten copy
