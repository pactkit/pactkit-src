# Sprint Board

## 📋 Backlog

### STORY-025: Conditional CI/CD Pipeline Generation
- [ ] Add `ci` configuration section to pactkit.yaml with provider field (default: none)
- [ ] Implement GitHub Actions workflow generation when provider is github
- [ ] Implement GitLab CI configuration generation when provider is gitlab
- [ ] Add CI workflow templates with pytest and linting commands
- [ ] Ensure backward compatibility for projects without ci section
- [ ] Add config validation for invalid CI providers

### STORY-026: Conditional Issue Tracker Integration
- [ ] Add `issue_tracker` configuration section to pactkit.yaml (default: none)
- [ ] Integrate GitHub Issue creation in /project-plan command
- [ ] Integrate GitHub Issue closure in /project-done command
- [ ] Add Sprint Board linking to external issue URLs
- [ ] Implement graceful fallback when GitHub CLI unavailable
- [ ] Ensure standalone Sprint Board operation preservation

### STORY-027: Safe Opt-in Hook Templates
- [ ] Add `hooks` configuration section with boolean template flags
- [ ] Create safe pre-commit lint hook template (command-type, exit 0)
- [ ] Create post-test coverage hook template (report-only)
- [ ] Create pre-push check hook template (warning-only)
- [ ] Deploy enabled hook scripts to .claude/hooks/ directory
- [ ] Integrate with git hooks while preserving existing hooks

### STORY-028: Context-Aware Rule Scoping
- [ ] Add optional `scope` field to rule configuration with glob patterns
- [ ] Generate Claude Code includeFiles frontmatter for scoped rules
- [ ] Implement glob pattern validation with warning for invalid patterns
- [ ] Support multiple scope patterns per rule as YAML list
- [ ] Maintain backward compatibility for rules without scope
- [ ] Test rule scoping with common patterns (auth, api, frontend modules)

### STORY-029: Enhanced Doctor Diagnostics
- [ ] Implement stale architecture graph detection (7+ days old)
- [ ] Add orphaned spec detection (specs without Sprint Board entries)
- [ ] Add missing spec detection (Sprint Board stories without specs)
- [ ] Implement configuration drift detection (pactkit.yaml vs deployed files)
- [ ] Generate structured health report with severity levels (INFO/WARN/ERROR)
- [ ] Group findings by category with actionable remediation suggestions

### STORY-030: Smart Lint Integration in Done Command
- [ ] Read lint_command from LANG_PROFILES for detected stack
- [ ] Add `lint_blocking` configuration option (default: false)
- [ ] Add `auto_fix` configuration option (default: false)
- [ ] Implement non-blocking lint warnings as default behavior
- [ ] Support blocking lint mode when configured
- [ ] Implement auto-fix with verification re-run capability

## 🔄 In Progress

## ✅ Done

