# STORY-008: Constitution Sharpening — 删除伪优势，强化治理规则

- **Priority**: 3 (Impact 4 / Effort 2)
- **Agent**: System Architect
- **Release**: 1.1.0
- **Depends on**: STORY-006

## Background

PactKit 的 6 个 constitution 模块（01-06）中，部分规则与 Opus 4.6 原生行为高度重叠，属于「伪优势」。这些规则不仅不增加价值，还增加了 prompt token 消耗（每个 session 都要读），降低了真正有价值的规则的信噪比。

### 伪优势清单（Opus 4.6 已原生支持）

| 规则 | 所在模块 | 为什么是伪优势 |
|------|---------|---------------|
| `<thinking>` block | 01-core-protocol | Opus 内置 extended thinking |
| Enterprise Expert mode | 01-core-protocol | 描述模糊，Opus 默认就是 expert 级别 |
| Atomic Tools 偏好 | 01-core-protocol | Opus system prompt 已内置完全相同的规则 |
| Language Mirror | 01-core-protocol | Opus 原生支持语言镜像 |
| Output Conventions (lead with conclusions, tables, bullets) | 01-core-protocol | Opus 默认输出风格已经很好 |

### 真正的差异化规则（Opus 原生做不到的）

| 规则 | 所在模块 | 为什么有价值 |
|------|---------|-------------|
| Hierarchy of Truth (Spec > Tests > Code) | 02-hierarchy | **核心差异** — Opus 默认是 "make code work"，不是 "make code match spec" |
| Strict TDD (RED → GREEN) | 01-core-protocol | Opus 知道 TDD 但不会主动强制执行 |
| Visual First (visualize before modify) | 01-core-protocol | 需要 PactKit skill 支持，Opus 没有 |
| Conflict Resolution Rules | 02-hierarchy | Spec 优先级体系是独特的 |
| File Atlas | 03-file-atlas | 项目结构约定是 PactKit 特有的 |
| Regression Gate (no blind fix) | Commands | 过程纪律约束 |

## Requirements

### R1: Remove Pseudo-advantages from 01-core-protocol (MUST)
从 `RULES_MODULES['core']` 中删除以下内容：
- `<thinking>` block 指令
- "Enterprise Expert" mode 声明
- "Language: Mirror the user's input language" 指令
- "Atomic Tools" 完整章节
- "Output Conventions" 完整章节

### R2: Strengthen Process Governance Rules (MUST)
在 01-core-protocol 中，将释放出的空间用于强化真正的治理规则：
- **Strict TDD**: 保留并强化（加入 "agent MUST NOT skip TDD except /project-hotfix"）
- **Visual First**: 保留并强化
- 新增 **Session Context**: "On cold start, read `docs/product/context.md` to understand project state before taking action"

### R3: Sharpen 02-hierarchy (SHOULD)
强化 Hierarchy of Truth 的措辞，增加具体示例：
- 添加 "Pre-existing test failure protocol" 摘要（引用 Done/Act 的 Gate 规则）
- 这是 PactKit 最核心的差异化规则，措辞应该更加明确

### R4: Reduce Token Footprint (SHOULD)
清理后的 01-core-protocol SHOULD 减少至少 30% 的 token 数量。更少的规则 = 更高的信噪比 = agent 更容易遵守。

### R5: Backward Compatibility (MUST)
- 所有现有测试 MUST 通过
- 删除伪优势不改变任何命令行为（命令 playbook 不引用这些规则）
- Plugin 模式 inline CLAUDE.md 同步更新

## Acceptance Criteria

### Scenario 1: Core protocol trimmed
**Given** the updated `RULES_MODULES['core']`
**When** compared to the old version
**Then** "thinking block", "Enterprise Expert", "Atomic Tools" section, "Output Conventions" section, and "Language Mirror" are all absent

### Scenario 2: TDD and Visual First preserved
**Given** the updated `RULES_MODULES['core']`
**When** inspected
**Then** "Strict TDD" and "Visual First" sections are present and their content is preserved or strengthened

### Scenario 3: Session Context rule added
**Given** the updated `RULES_MODULES['core']`
**When** inspected
**Then** a new "Session Context" section exists with instructions to read `context.md` on cold start

### Scenario 4: Token reduction
**Given** the old and new `RULES_MODULES['core']`
**When** token counts are compared
**Then** the new version has at least 30% fewer tokens

### Scenario 5: All tests pass
**Given** the updated rules modules
**When** `pytest tests/` is run
**Then** all tests pass (some tests checking exact rule content may need updating)

## Implementation Notes

1. 主要改动在 `src/pactkit/prompts/rules.py` — 编辑 `RULES_MODULES['core']` 和 `RULES_MODULES['hierarchy']` 的文本内容
2. 部分测试（如 `test_rules_content.py`）可能检查精确文本，需要同步更新
3. Plugin inline CLAUDE.md 自动跟随（因为它读 `RULES_MODULES`）
4. 这是一个 **prompt engineering** 任务，不是代码逻辑变更
