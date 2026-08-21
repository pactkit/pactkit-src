# STORY-slim-145: Codex 部署命令语义完整性与 Adapter 兼容门禁

| Field | Value |
|-------|-------|
| ID | STORY-slim-145 |
| Status | Draft |
| Priority | P0 |
| Release | 2.20.0 |

## Background

PactKit Core 2.19.0 与已安装的 `pactkit-codex` 2.17.0 组合部署后，Codex 的 `project-act/SKILL.md` 出现了确定性的语义损坏。Core 将 Codex profile 固定标记为 `has_pactkit_cli=False`，adapter 随后通过 `_replace_cli_with_scripts()` 对 Markdown 正文执行前缀级 `str.replace()`。该转换没有消费完整代码 span 和参数，导致下列有效命令被改写成无效或歧义文本：

```text
Run `pactkit regression` ...
  → Run run the full test suite directly (...)` ...

Run `pactkit context --continuation ...`
  → Run update `docs/product/context.md` manually --continuation ...
```

相同转换同时作用于 rules、command skills 与 embedded skills，因此问题不局限于 `$project-act`。本机 Codex 实际具备 shell 且 `pactkit` 在 PATH 中，说明“Codex 格式”并不等价于“运行时没有 PactKit CLI”。当前 adapter 的依赖也声明 `pactkit>=2.17.0`，与无条件移除 PactKit CLI 指令的行为矛盾。

现有 deploy-output guard 只检查外部路径和 CLI 字符串是否残留，不检查转换后的 Markdown 是否语法完整、关键工作流步骤是否保留，也不阻止旧 adapter 配新 Core 继续部署。这使损坏内容可以通过测试并进入 `~/.codex/skills/`。

本 Story 修复部署语义与版本兼容边界，不实现 Act 的跨 turn 持久化状态机。后者需要独立 Story。

## Target Call Chain

```text
pactkit init/update --format codex
  -> cli.py
  -> generators/deployer.py: deploy()
  -> entry point pactkit.deployers[codex]
  -> pactkit_codex.deployer: CodexDeployer.deploy()
     -> deploy_codex_rules()
     -> deploy_codex_command_skills()
     -> deploy_codex_skills()
     -> _render_prompt()
     -> _replace_cli_with_scripts()       # 当前有损转换点
     -> DeployerBase.validate_deployed_content()
     -> atomic_write(SKILL.md/rules)

Codex runtime
  -> user invokes $project-act STORY-XXX
  -> loads ~/.codex/skills/project-act/SKILL.md
  -> model executes deployed Phase 0..4 instructions
```

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-084, STORY-slim-139, STORY-slim-142 |
| Provides | Structured operation rendering, prompt-integrity validation, and adapter compatibility gate |
| Touches | Core deployment/profile/version dispatch plus external `../pactkit-codex` and `../pactkit-copilot` rendering and tests |
| Conflict risk | High — both repositories share `FormatProfile`, `_render_prompt()`, `DeployerBase`, and adapter entry-point contracts |

## Requirements

### R1: 将 CLI 可用性建模为部署策略而非固定格式事实 (MUST)

Core MUST replace or extend the boolean `FormatProfile.has_pactkit_cli` with a policy that can distinguish at least:

- `required`: generated workflow relies on PactKit CLI;
- `preferred`: preserve PactKit CLI commands, with an explicit whole-operation fallback when unavailable;
- `unavailable`: generated workflow must not require PactKit CLI.

Codex MUST use `preferred`; Classic MUST use `required` or an equivalent CLI-preserving policy; Copilot MAY remain `unavailable`. Existing third-party profiles that omit the new field MUST retain a documented backward-compatible default.

The policy MUST describe deploy-output behavior only. It MUST NOT claim that a product format is permanently sandboxed or infer the current process PATH during module import.

### R2: 为 PactKit 操作提供结构化渲染契约 (MUST)

Core MUST expose named prompt variables or an equivalent structured operation map for operations currently rewritten from free text, including at least:

- regression classification;
- lint;
- context continuation update;
- cleanup;
- lazy visualization;
- installation/update guidance;
- guard;
- doctor.

Source command templates MUST reference those structured operations. Adapter code MUST NOT discover these operations by matching arbitrary natural-language prefixes such as `` `pactkit regression``.

For CLI-preserving profiles, rendered commands MUST retain the exact supported PactKit CLI invocation. For CLI-unavailable profiles, a fallback MUST replace the complete operation token or complete code span, including arguments and closing delimiter.

### R3: Codex 与 Copilot adapter 停止有损/本地 CLI 前缀替换 (MUST)

> Scope 扩大至 Copilot:Act Phase 0 用户授权(OpenCode 因 `has_pactkit_cli=True` 无 CLI fallback,不适用,排除在外)。

`pactkit-codex` MUST remove the current prefix-based `_CLI_TO_SCRIPT` replacements for `pactkit regression`, `lint`, `context`, `clean`, `visualize`, `guard`, `doctor`, and `update`, or replace them with the structured contract from R2. `pactkit-copilot` MUST likewise remove its local `content.replace()` CLI fallback table (copilot deployer.py:640-) and consume the R2 structured contract. Codex 产生过实证损坏(`Run run`、参数游离);Copilot 虽未产生双 Run,但其 `--continuation` 等参数仍可游离,且 local fallback table 违反 R2 的"adapter MUST NOT match natural-language prefixes"。

Codex deployment MUST continue to perform genuine format conversions:

- Claude/OpenCode paths to Codex paths;
- `/project-*` references to `$project-*`;
- unsupported frontmatter removal;
- Claude/Anthropic model-brand cleanup.

These transformations MUST preserve all command arguments and surrounding Markdown. A fallback MUST be operation-equivalent; for example, `pactkit regression` MUST NOT silently become an unconditional full-suite command because that loses SKIP/IMPACT/FULL classification.

### R4: 增加部署内容语法与工作流语义门禁 (MUST)

Core MUST extend deploy-output validation, or add a dedicated prompt-integrity validator, to detect at least:

- duplicated imperative fragments such as `Run run`;
- unbalanced Markdown backticks introduced by deployment;
- CLI options appended to prose fallback, such as `manually --continuation`;
- unresolved known template variables;
- missing required Act workflow capabilities.

For `project-act`, the validator MUST verify the presence of semantic steps for Spec lint, TDD RED/GREEN, regression classification, lint, continuation update, and Requirement coverage output. Validation MUST compare normalized operations rather than require identical Claude and Codex prose.

Release/deployment tests MUST treat syntax corruption or a missing MUST workflow capability as failure, not warning. Foreign-path diagnostics MAY remain warnings where existing compatibility requires it.

### R5: 建立 Claude 与 Codex 的规范化行为等价测试 (MUST)

Tests MUST render the canonical `project-act` workflow for Classic and Codex, normalize environment-specific paths, invocation prefixes, and frontmatter, then assert that their required operation sets are equivalent.

The test MUST fail if Codex loses any required phase or operation even when all forbidden raw strings have disappeared. It MUST include regression cases for the exact previously observed corruptions.

### R6: Adapter/Core 版本兼容成为部署前门禁 (MUST)

Core MUST extend the existing `doctor.check_adapter_skew()` (delivered by STORY-slim-142, currently report-only) with a deploy-time gate, not replace it. Before `pactkit init/update` invokes an external adapter, Core MUST compare the runtime Core version with the adapter distribution version. Major/minor mismatch MUST block that adapter deployment with an actionable error unless an explicit escape hatch such as `--allow-adapter-skew` is supplied. Patch-only mismatch MAY warn.

The check MUST also detect divergence between `pactkit.__version__` and `importlib.metadata.version("pactkit")`, because editable installs can otherwise report one source version and another distribution version. Metadata lookup failures MUST degrade to an actionable diagnostic without crashing unrelated Classic deployment.

Adapter package dependencies SHOULD constrain compatible Core versions, for example `pactkit>=2.20,<2.21`, instead of accepting all future Core versions.

### R7: 安全迁移并验证现有 Codex 部署 (MUST)

After Core and `pactkit-codex` are released at the same compatible version, the migration procedure MUST:

1. install the aligned adapter without overwriting user-owned `~/.codex/config.toml`;
2. regenerate managed Codex skills and rules;
3. run `pactkit doctor`;
4. scan deployed content for known corruption signatures;
5. verify a disposable `$project-act` fixture reaches its final coverage output or an explicit legitimate blocker.

No test or migration command may write to a real user home when a temporary target is supplied.

### R8: Preserve existing interfaces and user-owned configuration (MUST)

- Existing `$project-*` invocation names MUST remain unchanged.
- Existing `pactkit init/update` CLI signatures MUST remain compatible except for the optional skew override.
- Existing `config.toml` MUST remain byte-identical during adapter deployment.
- Classic and OpenCode output MUST not regress.
- The Core repository MUST NOT vendor the `pactkit-codex` implementation; the adapter remains an external package using the shared contract.

## Acceptance Criteria

### AC1: Codex Act 不再生成损坏文本 (R2, R3, R4)

- **Given** canonical `project-act` template and the Codex profile
- **When** `CodexDeployer.deploy_codex_command_skills()` renders it into a temporary directory
- **Then** output contains none of `Run run`, `Run update`, `manually --continuation`, or unbalanced backticks, and all command arguments remain attached to an executable operation

### AC2: Codex 保留 PactKit CLI 的确定性语义 (R1, R2, R3)

- **Given** Codex uses the `preferred` CLI policy
- **When** command and rule content are rendered
- **Then** `pactkit regression`, `pactkit lint`, `pactkit context --continuation`, `pactkit clean`, and lazy visualization retain their canonical semantics, with any fallback expressed as a complete conditional operation rather than partial prose substitution

### AC3: Classic/Codex Act 行为等价 (R4, R5)

- **Given** Classic and Codex deployments from the same Core templates
- **When** a test extracts and normalizes their required Act operations
- **Then** both contain Spec lint, TDD RED/GREEN, regression classification, lint, continuation update, graph synchronization, Board update, and Requirement coverage output

### AC4: 语义损坏阻止部署测试通过 (R4)

- **Given** fixtures containing each historical corruption signature or with one required Act operation removed
- **When** prompt-integrity validation runs
- **Then** each fixture returns a deterministic failure identifying the file and violated invariant

### AC5: Adapter 版本错配不再静默部署 (R6)

- **Given** Core 2.20.x and `pactkit-codex` 2.19.x are installed
- **When** `pactkit update --format codex` runs
- **Then** Codex deployment is blocked before managed files are written, the error names both versions and the upgrade command, while Classic deployment remains available

### AC6: Editable install 元数据分裂可见 (R6)

- **Given** imported `pactkit.__version__` differs from distribution metadata
- **When** compatibility validation or `pactkit doctor` runs
- **Then** output explicitly reports source/distribution divergence and does not claim the installation is aligned

### AC7: 对齐版本后的迁移安全 (R7, R8)

- **Given** a temporary Codex home with an existing `config.toml` sentinel
- **When** aligned Core/adapter deployment and migration verification run
- **Then** `config.toml` is byte-identical, managed files are regenerated, doctor reports no adapter skew/content corruption, and no writes occur outside the temporary target

### AC8: 回归兼容 (R8)

- **Given** the completed implementation across core, codex, and copilot repositories
- **When** Core and adapter targeted/full test suites and linters run
- **Then** all pre-existing tests pass without weakening existing assertions, and Classic/OpenCode deployment snapshots remain semantically unchanged

### AC9: Copilot 消费共享 operation 契约 (R2, R3)

- **Given** canonical `project-act` template and the Copilot profile (CLI-unavailable, `has_pactkit_cli=False`)
- **When** `CopilotDeployer` renders it into a temporary directory
- **Then** Copilot no longer maintains a local CLI fallback `content.replace()` table, rendered commands resolve via the Core R2 operation tokens, command arguments remain attached to an executable operation, and no `--continuation`-style option is left stranded in prose

## Technical Design

### Lateral Scan Results

- Operation: environment-specific prompt rendering and CLI fallback conversion
- Existing implementations: at least three independent paths — Core `_render_prompt()`, Codex `_replace_cli_with_scripts()`, and Copilot/OpenCode adapter-specific replacements
- Assessment: extract a shared structured operation contract in Core. Adding another adapter-local replacement table would deepen an already demonstrated drift pattern and violate the project's shared-abstraction threshold.

### Capability model

Prefer a small enum-like policy over additional format-name branches. `_render_prompt()` remains the single environment rendering boundary. It exposes structured operation variables (`{PACTKIT_OP_*}` in its existing `var_map`, deployer.py:71) as the canonical contract, AND — as the equivalent structured operation map permitted by R2 ("or equivalent") — performs safe complete code-span replacement of canonical `pactkit` CLI commands with fallback operations for CLI-unavailable profiles (`has_pactkit_cli=False`). Source templates may use either `{PACTKIT_OP_*}` tokens or hardcoded CLI code spans; both resolve correctly (token path via var_map, hardcoded path via Core replace). Adapter packages MUST NOT maintain local prefix-replacement tables (R3) — fallback rendering is Core-owned, never adapter-local.

Runtime PATH probing SHOULD occur only as an explicit preflight instruction or CLI command, not while importing profiles. Normal Codex installation includes PactKit as an adapter dependency, so the generated default SHOULD preserve the canonical CLI path.

### Prompt integrity

Validation should have two layers:

1. lexical integrity: malformed Markdown and known corruption signatures;
2. semantic integrity: required operation IDs extracted from canonical markers or structured tokens.

Operation IDs are preferable to English sentence matching. Example conceptual marker: `PACTKIT_OP:context_continuation`; deployment may render different user-facing text while tests compare the same operation identity.

### Version compatibility

Compatibility checking belongs in Core immediately before adapter invocation because Core owns entry-point dispatch. It MUST reuse `doctor.check_adapter_skew()` (STORY-slim-142) as the metadata-reading layer and add two new layers on top: (1) a deploy-time block with `--allow-adapter-skew` override, and (2) editable-install divergence detection comparing `pactkit.__version__` against `importlib.metadata.version("pactkit")` (AC6). Adapter dependency bounds provide a second layer but cannot replace runtime validation in editable or partially upgraded installations.

### Failure behavior

- Corrupt generated content: fail before atomic write of that artifact set.
- Incompatible adapter: skip/block only that adapter with remediation; do not destroy existing deployment.
- Missing metadata: report diagnostically and preserve unrelated formats.
- Explicit skew override: print a prominent warning and record the override in command output; never imply compatibility was verified.

## Implementation Steps

| Step | Repository / File | Action | Dependencies | Risk |
|------|-------------------|--------|--------------|------|
| 1 | `pactkit/tests/` | Add RED tests for CLI policy, operation rendering, prompt integrity, parity, and version gates | None | Low |
| 2 | `pactkit/src/pactkit/profiles.py` | Replace/extend boolean CLI capability with policy | Step 1 | Medium |
| 3 | `pactkit/src/pactkit/generators/deployer.py` + prompt templates | Add structured operation variables/tokens and canonical render path | Steps 1-2 | High |
| 4 | `pactkit/src/pactkit/generators/deploy_base.py` | Add lexical and semantic prompt-integrity validation | Step 3 | Medium |
| 5 | `pactkit/src/pactkit/generators/deployer.py`, `doctor.py`, `cli.py` | Enforce adapter compatibility before dispatch and report metadata divergence | Step 1 | Medium |
| 6 | `../pactkit-codex/src/pactkit_codex/deployer.py` | Consume shared operation contract; remove prefix CLI rewriting | Steps 2-4 | High |
| 7 | `../pactkit-codex/tests/` | Add exact corruption regressions, normalized parity, and isolated deployment tests | Step 6 | Medium |
| 7b | `../pactkit-copilot/src/pactkit_copilot/deployer.py` | Consume shared operation contract; remove local CLI fallback `content.replace()` table (deployer.py:640-) | Steps 2-4 | Medium |
| 7c | `../pactkit-copilot/tests/` | Add token-consumption and no-stranded-argument regression tests | Step 7b | Medium |
| 8 | All three repositories (core, codex, copilot) | Run targeted tests, full suites, lint, package-build checks, and temporary-home migration verification | Steps 1-7c | Medium |
| 9 | Release operations | Release matching Core/adapter versions, reinstall, redeploy, and run doctor/scan smoke test | Step 8 | Medium |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Source, generated instructions, and package compatibility logic change; no credentials may be printed or overwritten |
| SEC-2 | Yes | Adapter names, versions, paths, and generated prompt content cross validation boundaries and require bounded parsing |
| SEC-3 | No | No database access |
| SEC-4 | No | No browser or frontend rendering |
| SEC-5 | No | No authentication/session behavior |
| SEC-6 | No | No network API or rate limiting |
| SEC-7 | Yes | Missing/corrupt package metadata and partial adapter failure must degrade safely without overwriting good deployments |
| SEC-8 | Yes | Package dependency bounds and cross-package version compatibility are central to this Story |

## Out of Scope

- Terra/GPT model prompt tuning or provider routing changes.
- Codex Runtime `unsupported custom tool call` defects.
- A durable Act state machine, per-phase state file, or automatic cross-turn resume; create a follow-up Story after deployment parity is restored.
- Changing the `$project-act` user-facing invocation syntax.
- Folding external adapter repositories into PactKit Core.
- Running migration against the real user home during automated tests.

## Rollback

If the aligned release causes deployment regressions:

1. stop before overwriting existing managed artifacts when integrity validation fails;
2. reinstall the previous matching Core/adapter pair, never a mixed pair;
3. redeploy managed files while preserving `config.toml`;
4. verify the previous `.pactkit-deployed.json` hashes and `pactkit doctor` output;
5. retain the new corruption fixtures so the faulty transformation cannot be reintroduced silently.
