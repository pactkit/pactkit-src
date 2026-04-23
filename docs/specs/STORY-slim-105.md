# STORY-slim-105: SHOULD 覆盖追踪与改动类型声明

| Field | Value |
|-------|-------|
| ID | STORY-slim-105 |
| Status | Done |
| Priority | P1 |
| Release | 2.11.0 |

## Background

AI 在实现 Spec 时存在三个系统性偷懒问题：

1. **SHOULD 被静默跳过**：Spec 中的 SHOULD 条目被当作"可选"处理，没有任何留痕机制，用户事后才发现功能不完整
2. **Hardcode 是默认路径**：实现时倾向于最快路径（字面量、魔法数字），导致后期维护成本指数增长
3. **Workaround 无痕绕过**：遇到问题时倾向于绕过而非修复根因，问题会复发，技术债累积

现有规则（Memory 中的 feedback、01-core-protocol 中的 Signal Strength Convention）是 Prompt 层面的提醒，不是 Code 层面的约束。提醒可以被忽略，约束不能。

本 Story 的目标是把"隐性跳过"变成"显性留痕"，用 Code 约束替代 Prompt 提醒。

## Requirements

### R1: DEFERRED 注释机制 (MUST)

任何 Spec 中标记为 SHOULD 的需求如果不实现，**MUST** 在代码中留下 DEFERRED 注释：

```python
# DEFERRED(SHOULD): R2 支持批量操作 — 当前版本仅支持单条，批量待 v2.12
```

格式规范：
- `# DEFERRED(SHOULD):` 前缀（固定）
- `R{N}` 引用对应的 Spec 需求编号
- `—` 后跟跳过理由

### R2: 实现覆盖表输出 (MUST)

Act 阶段 Phase 4 完成后，**MUST** 输出一个覆盖表，列出 Spec 中每个 R{N} 条目的实现状态：

| Spec 条目 | 类型 | 状态 | 位置 |
|-----------|------|------|------|
| R1 支持单条 | MUST | ✓ | parser.py:45 |
| R2 支持批量 | SHOULD | DEFERRED | — 理由:当前版本不需要 |

用户可一眼验收，不依赖 AI 的"已完成"声明。

### R3: 改动类型声明 (MUST)

每次修改代码前，**MUST** 声明改动类型：

| 类型 | 含义 | 附带要求 |
|------|------|----------|
| `ROOT_CAUSE` | 修复根因 | 无 |
| `WORKAROUND` | 临时绕过 | **MUST** 同时创建 tech-debt Story |

选 WORKAROUND 可以，但必须付出代价（创建 Story），不能无痕绕过。

### R4: Hardcode 检测 (SHOULD)

在 spec_linter 中新增一个检测 pass，识别常见 hardcode 模式：
- URL 字符串字面量（http://、https://）
- 魔法数字（非 0、1、2 的整数字面量在业务逻辑中）
- 配置字面量（端口号、超时值、阈值）

检测结果作为 WARNING（W010），不阻塞 Act。

### R5: 规则文件更新 (MUST)

更新 `~/.claude/rules/01-core-protocol.md`，将 SHOULD 的语义从"non-blocking warning"升级为"MUST leave trace if skipped"。

更新 `~/.claude/rules/05-workflow-conventions.md`，新增 DEFERRED 注释规范和改动类型声明规范。

## Acceptance Criteria

### AC1: DEFERRED 注释被 grep 发现 (R1)

- **Given** 一个实现文件中包含 `# DEFERRED(SHOULD): R2 xxx — reason`
- **When** 运行 `grep -r "DEFERRED(SHOULD)" src/`
- **Then** 返回该文件和行号，用户可直接定位未实现的 SHOULD

### AC2: 覆盖表输出格式正确 (R2)

- **Given** Spec 中有 R1 (MUST) 和 R2 (SHOULD) 两个需求
- **When** Act Phase 4 完成
- **Then** 输出的覆盖表包含两行，R1 状态为 ✓ 带文件位置，R2 状态为 DEFERRED 带理由

### AC3: Workaround 必须建 Story (R3)

- **Given** AI 声明改动类型为 WORKAROUND
- **When** 未创建对应的 tech-debt Story
- **Then** Phase 4 无法通过（AI 自检 + 规则约束）

### AC4: Hardcode 检测触发 W010 (R4)

- **Given** 代码中有 `url = "https://api.example.com/v1"`
- **When** 运行 spec_linter 的 hardcode 检测
- **Then** 输出 `[WARN] W010: Potential hardcoded value at line X`

### AC5: 规则文件语义一致 (R5)

- **Given** 更新后的 01-core-protocol.md
- **When** 读取 Signal Strength Convention 表格
- **Then** L3 SHOULD 的 Semantics 列包含 "MUST leave DEFERRED comment if skipped"

## Target Call Chain

```
/project-act
  └── Phase 0.5: pactkit spec-lint (spec_linter.py:validate_spec)
  └── Phase 3: 实现代码
  └── Phase 4: 输出覆盖表 (新增)

spec_linter.py:validate_spec()
  └── _check_metadata()
  └── _check_requirements_section()
  └── _check_hardcode() (新增 R4)
  └── ...
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/rules/01-core-protocol.md` | 更新 SHOULD 语义定义 | None | Low |
| 2 | `~/.claude/rules/05-workflow-conventions.md` | 新增 DEFERRED 注释规范 + 改动类型声明 | Step 1 | Low |
| 3 | `src/pactkit/schemas.py` | 新增 DEFERRED_COMMENT_PATTERN 常量 | None | Low |
| 4 | `src/pactkit/skills/spec_linter.py` | 新增 W010 hardcode 检测 | Step 3 | Medium |
| 5 | `pactkit-plugin/commands/project-act.md` | Phase 4 新增覆盖表输出要求 | Step 1,2 | Low |
| 6 | `tests/unit/test_spec_linter.py` | 新增 W010 测试用例 | Step 4 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | 无用户输入，仅静态分析 |
| SEC-2 Auth/AuthZ | N/A | 无认证相关改动 |
| SEC-3 Data Exposure | N/A | 无敏感数据处理 |
| SEC-4 SQL/NoSQL Injection | N/A | 无数据库操作 |
| SEC-5 XSS/CSRF | N/A | 无 Web 界面 |
| SEC-6 Path Traversal | N/A | 无文件路径操作 |
| SEC-7 Dependency | N/A | 无新依赖 |
| SEC-8 Secrets | N/A | 无 secrets 处理 |

## Out of Scope

- Hardcode 检测的自动修复（只检测，不自动提取常量）
- 覆盖表的持久化存储（输出到终端即可，不需要写文件）
- 与 CI/CD 的集成（本 Story 仅在 AI 工作流内生效）
