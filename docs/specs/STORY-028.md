# STORY-028: Context-Aware Rule Scoping

| Field     | Value |
|-----------|-------|
| Status    | Open |
| Author    | System Architect |
| Release   | TBD |

## Context

PactKit's current rule system applies all enabled rules project-wide, which can be inefficient and irrelevant. Security rules may only apply to authentication modules, performance rules to API endpoints, and style rules to frontend components. Context-aware scoping allows rules to target specific file patterns, improving relevance and reducing noise.

This addresses a common complaint about linting and analysis tools: too many irrelevant warnings in unrelated files. Scoped rules provide better signal-to-noise ratio and allow for specialized governance per module.

### Competitive Gap

- **SonarQube**: File pattern exclusions and module-specific rules
- **ESLint**: Directory-specific configuration overrides
- **Pylint**: Per-directory pylintrc files
- **PactKit**: Global rules only, no scoping mechanism

## Target Call Chain

```
pactkit init / pactkit update
  → deployer.deploy()
    → _deploy_rules(rules_dir, enabled_rules)
      → for each rule:
          → read rule template from RULES_*
          → check for scope glob pattern in pactkit.yaml
          → if scope exists:
              → validate glob pattern
              → add includeFiles to rule frontmatter
          → atomic_write(rule_path, content)
```

## Requirements

### R1: Optional Scope Configuration
- `pactkit.yaml` rule entries MUST support an optional `scope` field with glob pattern values.
- The `scope` field MUST use standard glob patterns (e.g., `src/auth/**`, `*.py`, `**/api/*.js`).
- Rules without a `scope` field MUST continue to apply project-wide (backward compatibility).
- The `validate_config()` function MUST warn on invalid glob patterns.

### R2: Claude Code includeFiles Integration
- When a rule has a `scope` field, the deployer MUST add `includeFiles` to the rule's frontmatter.
- The `includeFiles` value MUST be the glob pattern from the `scope` field.
- The frontmatter MUST be valid YAML that Claude Code can parse.
- Multiple glob patterns MUST be supported as a YAML list.

### R3: Glob Pattern Validation
- The deployer MUST validate glob patterns for basic syntax correctness.
- Invalid patterns (e.g., unclosed brackets, invalid escapes) MUST emit warnings.
- Invalid patterns MUST NOT prevent deployment but SHOULD be ignored.
- Common patterns MUST be supported: `**` (recursive), `*` (wildcard), `{}` (alternatives).

### R4: Backward Compatibility
- Existing `pactkit.yaml` files without `scope` fields MUST work unchanged.
- Rules without scope MUST apply project-wide as before.
- The rule deployment process MUST NOT break for configurations missing scope fields.
- Legacy rule behavior MUST remain identical when no scope is specified.

### R5: Multiple Scope Patterns
- A single rule MAY have multiple scope patterns as a YAML list.
- Example: `scope: ["src/auth/**", "src/security/**"]`
- Multiple patterns MUST be combined with OR logic (rule applies if any pattern matches).
- The deployer MUST serialize multiple patterns correctly in Claude Code frontmatter.

## Acceptance Criteria

### AC1: Unscoped Rule Behavior (Backward Compatibility)
- **Given** a rule in `pactkit.yaml` without a `scope` field
- **When** rules are deployed
- **Then** the rule file contains no `includeFiles` in frontmatter
- **And** the rule applies project-wide as before

### AC2: Single Scope Pattern
- **Given** a rule with `scope: "src/auth/**"`
- **When** rules are deployed
- **Then** the rule frontmatter contains `includeFiles: src/auth/**`
- **And** the rule only applies to files matching the pattern

### AC3: Multiple Scope Patterns
- **Given** a rule with `scope: ["src/auth/**", "src/security/**"]`
- **When** rules are deployed
- **Then** the rule frontmatter contains:
```yaml
includeFiles:
  - src/auth/**
  - src/security/**
```
- **And** the rule applies to files matching either pattern

### AC4: Invalid Glob Pattern Warning
- **Given** a rule with `scope: "src/auth/[unclosed"`
- **When** config validation is run
- **Then** a warning is emitted about invalid glob pattern
- **And** the rule is deployed without the scope (project-wide)

### AC5: Security Rule Example
- **Given** security rule with `scope: "src/auth/**"`
- **When** the deployed rule is inspected
- **Then** it contains valid Claude Code frontmatter
- **And** the `includeFiles` field limits rule application
- **And** the rule content remains unchanged

### AC6: Frontend Style Rule Example
- **Given** style rule with `scope: "frontend/**/*.{js,tsx}"`
- **When** the rule is deployed
- **Then** the glob pattern is preserved in frontmatter
- **And** the pattern targets JavaScript and TypeScript React files
- **And** other file types are excluded from the rule

### AC7: Performance Rule Example
- **Given** performance rule with `scope: "**/api/**/*.py"`
- **When** the rule is deployed
- **Then** the rule only applies to Python files in api directories
- **And** the recursive `**` pattern is correctly serialized

### AC8: Config Without Scope Fields
- **Given** an existing `pactkit.yaml` with no `scope` fields on any rules
- **When** `pactkit update` is run
- **Then** all rules deploy successfully
- **And** no `includeFiles` appears in any rule frontmatter
- **And** all rules continue to work project-wide

### AC9: Mixed Scoped and Unscoped Rules
- **Given** some rules have `scope` fields and others don't
- **When** rules are deployed
- **Then** scoped rules have `includeFiles` in frontmatter
- **And** unscoped rules have no `includeFiles` in frontmatter
- **And** both types of rules function correctly