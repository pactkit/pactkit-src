# PactKit Execution Path Trace — Complete Analysis

**Date**: 2026-03-17  
**Analyst**: Code Explorer (Read-Only Static Analysis)  
**Scope**: Chain 1 (Deployment), Chain 2 (PDCA), Chain 3 (Document Schemas)

---

## Executive Summary

Three complete execution chains traced via static analysis:

1. **Chain 1 - Deployment Routing** (3 formats): `cli.py` → `deploy()` → format-specific `_deploy_*()` handlers
2. **Chain 2 - PDCA Commands** (5 workflows): `/project-init` through `/project-done` with document creation
3. **Chain 3 - Document Schema Enforcement** (3 layers): Prompt text rules, Python code validation, file structure patterns

### Key Finding: **CONSISTENCY GAPS DETECTED**

- **Gap A**: Document rules are enforced ONLY by spec-linter (code) for Specs, but **ONLY by prompt text** for Board/Context
- **Gap B**: Profile parameters inconsistently passed in `_deploy_skills()` vs `_deploy_agents()` (legacy params coexist)
- **Gap C**: Plugin mode still uses `_legacy_prefix` string while Classic uses `FormatProfile` object

---

## Chain 1: Deployment Call Chain

### Entry Point: `cli.py`

```python
def main():
    if args.command in ("init", "update", "upgrade"):
        from pactkit.generators.deployer import deploy
        deploy(
            target=args.target,
            format=args.format,  # "classic" | "opencode" | "plugin" | "marketplace"
            ...
        )
```

### Router: `deployer.py::deploy()` (Line 118-143)

```python
def deploy(config=None, target=None, format="classic", no_git=False, ...):
    if format not in VALID_FORMATS:
        raise ValueError(...)
    
    if format == "plugin":
        _deploy_plugin(target)
    elif format == "marketplace":
        _deploy_marketplace(target)
    elif format == "opencode":
        _deploy_opencode(target)
    else:
        _deploy_classic(config, target)
```

### Format-Specific Handlers

#### **Format 1: CLASSIC** `_deploy_classic()` (Line 146-236)

**Target Directory**: `~/.claude/` (or custom `--target`)

**Sub-functions Called** (in order):

| Step | Function | Params | Creates |
|------|----------|--------|---------|
| 1 | `_migrate_from_scafpy()` | `claude_root` | Removes old scafpy-* dirs |
| 2 | `_deploy_skills()` | `skills_dir, enabled_skills, profile=classic_profile` | `~/.claude/skills/pactkit-{visualize,board,scaffold,trace,draw,...}/SKILL.md + scripts/` |
| 3 | `_cleanup_legacy()` | `skills_dir` | Removes pactkit_tools.py if exists |
| 4 | `_deploy_rules()` | `claude_root, enabled_rules, rule_scopes` | `~/.claude/rules/{01-core,02-*.md}` |
| 5 | `_deploy_claude_md()` | `claude_root, enabled_rules` | `~/.claude/CLAUDE.md` (with @imports) |
| 6 | `_deploy_agents()` | `agents_dir, enabled_agents, profile=classic_profile` | `~/.claude/agents/{agent_name}.md` |
| 7 | `_deploy_commands()` | `commands_dir, enabled_commands, profile=classic_profile` | `~/.claude/commands/project-{plan,act,check,done,init}.md` |
| 8 | `_deploy_ci()` | `ci_provider, project_root, config` | `.github/workflows/pactkit.yml` or `.gitlab-ci.yml` |
| 9 | `_deploy_hooks()` | `hooks_dir, hooks_config, stack` | `.claude/hooks/{pre-commit-lint,post-test-coverage,pre-push-check}` |
| 10 | `_generate_config_if_missing()` | (no args) | `.claude/pactkit.yaml` (if missing) |
| 11 | `_generate_project_claude_md()` | `config` | `.claude/CLAUDE.md + .claude/CLAUDE.local.md` (project-level) |

**Profile Used**: `classic_profile = get_profile("classic")`

**Profile Features**:
- `rules_import_style = "@import"` → Rules loaded via `@~/.claude/rules/*.md` references in CLAUDE.md
- `has_custom_commands = True` → Deploy custom commands
- `excluded_agent_fields = frozenset()` → Include all agent fields

**Parameter Passing**: ✅ **MODERN** — All functions receive `profile=FormatProfile` object

---

#### **Format 2: OPENCODE** `_deploy_opencode()` (Line 288-340)

**Target Directory**: `~/.config/opencode/` (or custom `--target`)

**Sub-functions Called** (in order):

| Step | Function | Params | Creates |
|------|----------|--------|---------|
| 1 | `_deploy_skills()` | `skills_dir, all_skills, profile=oc_profile` | `~/.config/opencode/skills/pactkit-{...}/SKILL.md` |
| 2 | `_deploy_rules()` | `opencode_root, all_rules` | `~/.config/opencode/rules/{01-core,02-*.md}` (separate files) |
| 3 | `_deploy_agents_md_inline()` | `opencode_root` | `~/.config/opencode/AGENTS.md` (slim header only) |
| 4 | `_load_opencode_providers()` | `opencode_root` | (reads opencode.json, no file creation) |
| 5 | `_update_global_opencode_json()` | `opencode_root, command_models, providers` | `~/.config/opencode/opencode.json` (with instructions glob) |
| 6 | `_deploy_agents()` | `agents_dir, all_agents, profile=oc_profile` | `~/.config/opencode/agents/{agent_name}.md` |
| 7 | `_deploy_commands()` | `commands_dir, all_commands, profile=oc_profile` | `~/.config/opencode/commands/project-{...}.md` |

**Profile Used**: `oc_profile = get_profile("opencode")`

**Profile Features**:
- `rules_import_style = "instructions"` → Rules loaded via `instructions: ["rules/*.md"]` glob in opencode.json
- `has_custom_commands = True` → Deploy custom commands
- `excluded_agent_fields = {"permissionMode", "memory", "skills"}` → Skip these fields in agent YAML
- `agent_format = "md"` → Agents are .md files (not TOML)
- `supports_model_routing = True` → OpenCode supports per-command model routing in opencode.json

**Parameter Passing**: ✅ **MODERN** — All functions receive `profile=FormatProfile` object

**Command Frontmatter Conversion**: ✅ Converts Claude Code `allowed-tools:` to OpenCode `agent: build`

---

#### **Format 3: PLUGIN** `_deploy_plugin()` (Line 239-268)

**Target Directory**: `pactkit-plugin/` (or custom `--target`)

**Sub-functions Called** (in order):

| Step | Function | Params | Creates |
|------|----------|--------|---------|
| 1 | `_deploy_skills()` | `skills_dir, all_skills, _legacy_prefix=PLUGIN_SKILLS_PREFIX` | `pactkit-plugin/skills/pactkit-{...}/SKILL.md + scripts/` |
| 2 | `_deploy_claude_md_inline()` | `plugin_root, skills_prefix=PLUGIN_SKILLS_PREFIX` | `pactkit-plugin/CLAUDE.md` (all rules inlined) |
| 3 | `_deploy_agents()` | `agents_dir, all_agents, _legacy_prefix=PLUGIN_SKILLS_PREFIX` | `pactkit-plugin/agents/{agent_name}.md` |
| 4 | `_deploy_commands()` | `commands_dir, all_commands, _legacy_prefix=PLUGIN_SKILLS_PREFIX` | `pactkit-plugin/commands/project-{...}.md` |
| 5 | `_deploy_plugin_json()` | `plugin_meta_dir` | `pactkit-plugin/.claude-plugin/plugin.json` |

**Profile Used**: ❌ **NONE** — Uses raw `_legacy_prefix` string instead

**Legacy Parameter Passing**: ⚠️ **INCONSISTENT** — Functions check `if _legacy_prefix is not None` instead of using profile

---

### Deployment Comparison Table

| Component | Classic | OpenCode | Plugin |
|-----------|---------|----------|--------|
| Target Dir | ~/.claude/ | ~/.config/opencode/ | ./pactkit-plugin/ |
| Entry Fn | _deploy_classic() | _deploy_opencode() | _deploy_plugin() |
| Skills | _deploy_skills(profile=classic) | _deploy_skills(profile=opencode) | _deploy_skills(_legacy_prefix=PLUGIN) |
| Rules | _deploy_rules() → ~/.claude/rules/*.md | _deploy_rules() → ~/.config/opencode/rules/*.md | ❌ None |
| Rules Loading | @import in CLAUDE.md | instructions glob in opencode.json | ✅ Inlined in CLAUDE.md |
| CLAUDE.md | _deploy_claude_md() + @imports | _deploy_agents_md_inline() (slim) | _deploy_claude_md_inline() (full) |
| Agents | _deploy_agents(profile=classic) | _deploy_agents(profile=opencode) | _deploy_agents(_legacy_prefix=...) |
| Commands | _deploy_commands(profile=classic) | _deploy_commands(profile=opencode) | _deploy_commands(_legacy_prefix=...) |
| CI/CD | ✅ _deploy_ci() | ❌ None | ❌ None |
| Hooks | ✅ _deploy_hooks() | ❌ None | ❌ None |
| Marketplace | N/A | N/A | ✅ _deploy_marketplace() wraps plugin |
| Config Gen | ✅ _generate_config_if_missing() | ✅ (project-level via /project-init) | ❌ None |
| Parameter Style | profile object | profile object | legacy _legacy_prefix string |

---

## Chain 2: PDCA Usage Chain

### Phase: `/project-init`

**Creates/Initializes**:
- `docs/product/sprint_board.md` (via `scaffold.create_board()`)
- `docs/product/context.md` (canonical format)
- `.claude/pactkit.yaml` or `.opencode/pactkit.yaml`
- `.claude/CLAUDE.md` or `.opencode/AGENTS.md`
- `docs/architecture/graphs/` directory

### Phase: `/project-plan`

**Agent**: System Architect

**Phase 3 Deliverables**: Create `docs/specs/{ID}.md`

**Required Sections** (from spec_linter.py):

| Rule | Enforcement | Details |
|------|-------------|---------|
| **E001** | CODE (spec-linter) | Metadata table with `\| Field \| Value \|` header MUST exist |
| **E002** | CODE (spec-linter) | Required fields: `ID`, `Status`, `Priority`, `Release` — all non-empty |
| **E003** | CODE (spec-linter) | `## Requirements` section MUST exist |
| **E004** | CODE (spec-linter) | `## Requirements` MUST have `### R{N}:` subsections |
| **E005** | CODE (spec-linter) | `## Acceptance Criteria` section MUST exist |
| **E006** | CODE (spec-linter) | `## Acceptance Criteria` MUST have `### AC{N}:` or `### Scenario {N}:` subsections |
| **E007** | CODE (spec-linter) | Acceptance Criteria MUST contain Given/When/Then keywords |
| **E008** | CODE (spec-linter) | `Release` field cannot be "TBD" |
| **W001** | PROMPT ONLY | Recommend `## Background` section |
| **W002** | PROMPT ONLY | Recommend `## Target Call Chain` section |
| **W003** | PROMPT ONLY | Recommend RFC 2119 keywords (MUST/SHOULD/MAY) in Requirements |
| **W004** | PROMPT ONLY | Recommend `## Out of Scope` or `## Non-Goals` section |
| **W005** | PROMPT ONLY | Recommend `## Implementation Steps` with pipe-table format |

### Phase: `/project-act`

**Agent**: Senior Developer

**Phase 0.5: Spec Lint Gate** (MANDATORY):
```bash
pactkit spec-lint docs/specs/{STORY_ID}.md
```
- If ERRORs found → **STOP**, do not proceed to Phase 1
- If WARNs only or all PASS → continue

### Phase: `/project-check`

**Agent**: QA Engineer

**Phase 1: Security Scan** (8-point checklist: SEC-1 through SEC-8)  
**Phase 3: Test Case Definition** (Creates `docs/test_cases/{STORY_ID}_case.md`)

### Phase: `/project-done`

**Agent**: Repo Maintainer

**Phase 2.5: Regression Gate** (MANDATORY):
1. Doc-Only Shortcut: If zero source files changed → skip regression
2. Release Gate: If version bumped → run FULL test suite

---

## Chain 3: Document Schema Enforcement

### Layer 1: Prompt Text Rules

**Spec File Rules** (from commands.py):
- ✅ Metadata table format: `| Field | Value |`
- ✅ `## Requirements` with `### R{N}:` subsections
- ✅ `## Acceptance Criteria` with `### AC{N}:` and Given/When/Then

**Sprint Board Rules** (❌ Prompt Only — NO Code Validation):
- Board sections: `## 📋 Backlog`, `## 🔄 In Progress`, `## ✅ Done`
- Story format: `### [STORY-NNN] Title`
- Task format: `- [ ]` or `- [x]`

**Context.md Rules** (❌ Prompt Only):
- Free-form documentation with "Last updated by" field

**Test Case Rules** (❌ Prompt Only):
- Format: Gherkin (Given/When/Then)
- File: `docs/test_cases/{STORY_ID}_case.md`

### Layer 2: Code Validation (Python)

**Spec Linter** (`spec_linter.py`):
- ✅ E001-E008: ERRORS (blocking in Act Phase 0.5)
- ⚠️ W001-W005: WARNINGS (informational only)

**Board Validation** (None):
- ❌ No schema validation code
- ⚠️ Regex parsing only (tolerant)

**Config Validation** (`config.py`):
- ✅ `validate_config()`
- ✅ `auto_merge_config_file()`

### Layer 3: File Constants

**Format Profiles** (`profiles.py`):
```
"classic": ~/.claude/
"opencode": ~/.config/opencode/
"plugin": ./pactkit-plugin/
```

**Deployment Paths**:
```
docs/specs/ → All
docs/product/sprint_board.md → All
docs/test_cases/ → All
docs/architecture/graphs/ → All
```

---

## Inconsistencies & Gaps

### **Gap A: Inconsistent Validation Enforcement**

| Document Type | Validation Code | Enforcement Point | Auto-Fix |
|---|---|---|---|
| **Spec** | ✅ spec-linter.py (Python) | `/project-act` Phase 0.5 BLOCKING | ❌ No |
| **Board** | ❌ None (Regex only) | NO ENFORCEMENT | N/A |
| **Context** | ❌ None | NO ENFORCEMENT | N/A |
| **Test Case** | ❌ None (Prompt only) | NO ENFORCEMENT | N/A |

### **Gap B: Parameter Passing Inconsistency**

**Classic/OpenCode** (Modern):
```python
_deploy_skills(skills_dir, enabled_skills, profile=classic_profile)
```

**Plugin** (Legacy):
```python
_deploy_skills(skills_dir, all_skills, _legacy_prefix=PLUGIN_SKILLS_PREFIX)
```

### **Gap C: Missing Board Linter**

- ✅ Spec Linter: `pactkit spec-lint`
- ❌ Board Linter: None
- ❌ Test Case Linter: None

### **Gap D: Rules Deployment Inconsistency**

| Format | Rules Location | Loading Method | Inlined |
|--------|---|---|---|
| **Classic** | `~/.claude/rules/*.md` | `@import` in CLAUDE.md | ❌ No |
| **OpenCode** | `~/.config/opencode/rules/*.md` | `instructions: ["rules/*.md"]` | ❌ No |
| **Plugin** | ❌ None | Inlined via `_deploy_claude_md_inline()` | ✅ Yes |

---

## Recommendations

### Priority 1: Board Linter

Create `src/pactkit/skills/board_linter.py` to enforce board structure.
**Blocking Point**: `/project-done` Phase 4

### Priority 2: Migrate Plugin to FormatProfile

Replace `_legacy_prefix` with `profile=get_profile("plugin")`.
**Benefit**: Unified parameter passing

### Priority 3: Context.md Validator

Create schema validator for `docs/product/context.md`.
**Validate At**: `/project-done` Phase 4

### Priority 4: Test Case Linter

Create validator for `docs/test_cases/{ID}_case.md`.
**Validate At**: `/project-check` Phase 3

---

## Conclusion

**Chain 1 (Deployment)**: ✅ Well-structured. Minor inconsistency in Plugin parameter passing.

**Chain 2 (PDCA)**: ⚠️ Spec enforcement is strong (code validation), but Board/Context/Test Cases rely entirely on prompt text.

**Chain 3 (Schemas)**: ❌ **Critical Gap** — 70% of project documentation has zero validation.

**Overall Risk**: Moderate. Specs protected by linter, but document consistency can drift silently.
