# STORY-042: Spec Linter — Non-AI Structural Validation Gate

| Field     | Value |
|-----------|-------|
| ID        | STORY-042 |
| Status    | Draft |
| Priority  | High |
| Release   | 1.3.1 |
| Author    | System Architect |
| Source    | Gap Analysis: OpenSpec `validate --strict` |

## Background

PactKit 的 "Spec is Law" 治理体系依赖 Agent 自觉遵守 Spec 格式约定。但 LLM 存在"偷懒"行为——偶尔生成的 Spec 缺少验收标准、遗漏依赖关系、或留空回滚策略。当前没有任何机制在 `/project-act` 之前拦截不合格的 Spec。

OpenSpec 通过 `openspec validate --strict` + schema 系统提供了 opt-in 的结构校验。PactKit 需要一个更强的版本：**默认开启、不可绕过的 Spec 结构校验**，作为 Act 入口的硬性门禁。

关键原则：校验逻辑必须是**非 AI 的**（正则/AST），不依赖 LLM 判断，确保结果确定性和可重复性。

## Target Call Chain

```
/project-act (commands.py)
  → Phase 0: The Thinking Process
    → Phase 0.5 (NEW): Spec Lint Gate
      → spec_linter.validate_spec(spec_path)
        → _check_metadata()        # 元数据表完整性
        → _check_required_sections()  # 必须 section 存在性
        → _check_section_content()    # section 非空检查
        → _check_acceptance_criteria()  # AC 格式校验
      → IF errors: STOP, report, do NOT proceed
      → IF warnings only: report, continue
  → Phase 1: Precision Targeting (existing)
```

## Requirements

### R1: Spec Linter Script (MUST)

Create `src/pactkit/skills/spec_linter.py` 提供 `validate_spec(spec_path: str) -> LintResult` 函数。

**校验规则（ERROR 级 — 阻断）：**

| Rule ID | Check | Description |
|---------|-------|-------------|
| E001 | Metadata table exists | Spec 必须以 `\| Field \| Value \|` 格式的元数据表开头 |
| E002 | Required metadata fields | `ID`, `Status`, `Priority`, `Release` 字段必须存在且非空 |
| E003 | `## Requirements` section exists | 必须包含 Requirements section |
| E004 | At least one requirement | Requirements section 必须包含至少一个 `### R{N}:` 子标题 |
| E005 | `## Acceptance Criteria` section exists | 必须包含 Acceptance Criteria section |
| E006 | At least one AC | AC section 必须包含至少一个 `### AC{N}:` 或 `### Scenario {N}:` 子标题 |
| E007 | AC contains Given/When/Then | 每个 AC 必须包含 `Given`、`When`、`Then` 关键词（不区分大小写） |
| E008 | Release is not `TBD` | Release 字段不能是 TBD（在 Act 入口时必须已确定） |

**校验规则（WARN 级 — 报告但不阻断）：**

| Rule ID | Check | Description |
|---------|-------|-------------|
| W001 | `## Background` section exists | 推荐包含背景说明 |
| W002 | `## Target Call Chain` exists | 推荐包含调用链 |
| W003 | Requirements use RFC 2119 keywords | `### R{N}` 内容应包含 MUST/SHOULD/MAY |
| W004 | `## Out of Scope` or `## Non-Goals` exists | 推荐明确边界 |

**返回值：**
```python
@dataclass
class LintResult:
    errors: list[LintIssue]    # ERROR 级问题
    warnings: list[LintIssue]  # WARN 级问题
    passed: bool               # len(errors) == 0

@dataclass
class LintIssue:
    rule_id: str      # E001, W001, etc.
    message: str      # 人类可读描述
    line: int | None  # 问题所在行号（可选）
```

### R2: Act Phase 集成 (MUST)

在 `project-act.md` playbook 的 Phase 0 和 Phase 1 之间插入 **Phase 0.5: Spec Lint Gate**：

1. 读取当前 Story 对应的 Spec 文件路径
2. 调用 `validate_spec(spec_path)`
3. **如果有 ERROR**：STOP，输出所有 ERROR 和 WARN，指示用户修正 Spec 后重新运行 `/project-act`
4. **如果只有 WARN**：输出 WARN 列表，继续执行 Phase 1
5. **如果全部通过**：静默跳过，继续执行 Phase 1

### R3: Plan Phase 集成 (SHOULD)

在 `/project-plan` Phase 3（Deliverables）Spec 生成后，自动运行 Linter 进行自检：
- 如果 Linter 报 ERROR，Plan 阶段自行修复（因为 Spec 是 Plan 刚生成的，Plan 有权修改）
- 这形成一个 **write → validate → fix** 的闭环，减少 Spec 流转到 Act 时被拦截的概率

### R4: CLI 独立调用 (SHOULD)

支持从命令行独立运行：
```bash
python3 src/pactkit/skills/spec_linter.py docs/specs/STORY-042.md
python3 src/pactkit/skills/spec_linter.py --all  # 校验所有 specs
```

输出格式：
```
docs/specs/STORY-042.md
  [ERROR] E005: Missing ## Acceptance Criteria section
  [WARN]  W002: Missing ## Target Call Chain section

Result: FAIL (1 error, 1 warning)
```

### R5: Hotfix 豁免 (MUST)

`/project-hotfix` 路径 MUST 跳过 Spec Lint Gate。Hotfix 的设计目标是轻量快速，不适用完整的 Spec 结构要求。

## Acceptance Criteria

### AC1: ERROR 阻断 Act
**Given** 一个缺少 `## Acceptance Criteria` section 的 Spec
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.5 输出 `[ERROR] E005: Missing ## Acceptance Criteria section`
**And** Act 流程 STOP，不进入 Phase 1

### AC2: WARN 不阻断
**Given** 一个包含所有必填 section 但缺少 `## Out of Scope` 的 Spec
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.5 输出 `[WARN] W004: Missing ## Out of Scope or ## Non-Goals section`
**And** Act 流程继续进入 Phase 1

### AC3: 全通过静默
**Given** 一个符合所有 ERROR 和 WARN 规则的 Spec
**When** 执行 `/project-act STORY-XXX`
**Then** Phase 0.5 不输出任何内容
**And** Act 流程直接进入 Phase 1

### AC4: Plan 自检闭环
**Given** `/project-plan` 生成了一个 Spec
**When** Plan Phase 3 完成后运行 Linter
**Then** 如果有 ERROR，Plan 自动修复并重新校验
**And** 最终输出的 Spec 通过 Linter

### AC5: 独立 CLI 调用
**Given** 存在多个 Spec 文件
**When** 运行 `python3 src/pactkit/skills/spec_linter.py --all`
**Then** 输出每个文件的校验结果和总计

### AC6: Hotfix 豁免
**Given** 通过 `/project-hotfix` 执行修复
**When** Hotfix 流程运行
**Then** 不触发 Spec Lint Gate

## Out of Scope

- 校验 Spec 的语义正确性（这需要 AI 判断，不在本 Story 范围内）
- 修改现有 Spec 文件使其通过 Linter（这是后续迁移工作）
- 自定义校验规则配置（未来可通过 `pactkit.yaml` 扩展）
