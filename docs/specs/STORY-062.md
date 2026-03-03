# STORY-062: Print MCP Recommendations After Init/Update

| Field       | Value                                |
|-------------|--------------------------------------|
| ID          | STORY-062                            |
| Type        | Feature                              |
| Priority    | Medium                               |
| Estimate    | S (small)                            |
| Status      | Planned                              |
| Release     | 1.6.1                                |
| Spec Author | System Architect                     |

## Summary

After `pactkit init` or `pactkit update` completes successfully, print a static list of recommended MCP servers that enhance PactKit's PDCA workflow. This helps users discover and configure optional but valuable integrations.

## Background

PactKit's `06-mcp-integration.md` rule defines 6 MCP servers that the PDCA workflow can leverage:
- **Context7** — library documentation lookup during Act
- **Memory** — cross-session context persistence
- **Playwright** — browser automation for Check phase
- **Chrome DevTools** — performance tracing and diagnostics
- **Draw.io** — interactive diagram editing
- **shadcn** — UI component search (for frontend projects)

Currently, users must read the rules file to discover these integrations. A post-init prompt surfaces this information at the right moment.

## Requirements

### R1: MCP Recommendations Constant
The deployer module MUST define a constant `MCP_RECOMMENDATIONS` containing the list of recommended MCP servers with their names, purposes, and configuration hints.

### R2: Print After Classic Deploy
After `deploy()` prints the success message (`✅ Deployed: ...`), it MUST call a helper function to print the MCP recommendations.

### R3: Print After Plugin Deploy
After `_deploy_plugin()` prints the success message (`✅ Plugin: ...`), it MUST call the same helper function to print the MCP recommendations.

### R4: Output Format
The recommendations output SHOULD:
- Use a clear header (e.g., `📦 Recommended MCP Servers`)
- List each MCP with its name and one-line purpose
- Include a note about where to configure (Claude Code settings.json)
- Be visually distinct but not overwhelming (compact table or list)

### R5: Suppressible Output (OPTIONAL)
The output MAY be suppressed via a `--quiet` flag or `enterprise.non_interactive` config, but this is NOT required for v1.

## Acceptance Criteria

### AC1: Recommendations printed after classic init
**Given** a user runs `pactkit init`
**When** the deployment completes successfully
**Then** a list of 6 recommended MCP servers is printed after the success message

### AC2: Recommendations printed after plugin deploy
**Given** a user runs `pactkit init --format plugin`
**When** the plugin deployment completes successfully
**Then** the same MCP recommendations list is printed

### AC3: Each MCP has name and purpose
**Given** the MCP recommendations output
**When** the user reads it
**Then** each MCP entry includes: server name, one-line purpose description

### AC4: Configuration hint included
**Given** the MCP recommendations output
**When** the user reads it
**Then** there is a note indicating how to configure (e.g., "Configure in Claude Code settings.json → mcpServers")

## Target Call Chain

```
cli.py:main()
  └── deployer.py:deploy()
        └── print("✅ Deployed...")     # line 149
        └── _print_mcp_recommendations()  # NEW
  └── deployer.py:_deploy_plugin()
        └── print("✅ Plugin...")        # line 183
        └── _print_mcp_recommendations()  # NEW
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `src/pactkit/generators/deployer.py` | Add `MCP_RECOMMENDATIONS` constant (list of dicts) | None | Low |
| 2 | `src/pactkit/generators/deployer.py` | Add `_print_mcp_recommendations()` helper function | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | Call helper after `deploy()` success print | Step 2 | Low |
| 4 | `src/pactkit/generators/deployer.py` | Call helper after `_deploy_plugin()` success print | Step 2 | Low |
| 5 | `tests/unit/test_story062_mcp_recommendations.py` | Create tests for AC1-AC4 | Step 3, 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source code modified (deployer.py) |
| SEC-2 | No | No user input handling |
| SEC-3 | No | No database operations |
| SEC-4 | No | No frontend code |
| SEC-5 | No | No auth/session code |
| SEC-6 | No | No API endpoints |
| SEC-7 | No | No exception handling changes |
| SEC-8 | No | No dependency changes |
