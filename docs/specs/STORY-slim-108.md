# STORY-slim-108: pactkit-trace --summary 模式：接口摘要输出

| Field | Value |
|-------|-------|
| ID | STORY-slim-108 |
| Status | Draft |
| Priority | P1 |
| Release | 2.12.0 |

## Background

pactkit-trace 当前输出完整源码（Phase 3 Deep Tracing），在大型工程中导致 LLM 上下文膨胀、注意力稀释。LLM 修改 A 模块时需要理解 B/C/D 的接口，但不需要读它们的实现。需要一种"接口摘要"输出模式，只提取公开签名+类型+docstring，信息密度约为完整源码的 1/10。

此增强不创建独立工具，而是扩展现有 pactkit-trace 的输出格式，保持工具链精简。

## Requirements

### R1: trace SKILL.md 增加 summary 输出模式 (MUST)

在 `pactkit-trace/SKILL.md` Phase 3 (Deep Tracing) 中增加"接口摘要"输出选项：
- 当相关模块（非目标修改模块）被 trace 到时，输出签名+类型+docstring 而非完整函数体
- 目标修改模块仍输出完整实现

### R2: Act Phase 1 playbook 引导优先加载摘要 (MUST)

修改 `project-act/SKILL.md` Phase 1 (Precision Targeting)，增加指导：
- 对于 trace 发现的相关（但不需修改）模块，读接口摘要而非完整源码
- 只在确认需要修改时才读完整实现

### R3: 多语言支持 (SHOULD)

接口摘要提取策略应覆盖 `LANG_PROFILES` 支持的主要语言：
- Python: class/function signature + type hints + docstring
- TypeScript/JavaScript: exported interface/type/function signature + JSDoc
- Go: exported function/struct signature + godoc comment

### R4: 不引入新的预生成产物 (MUST NOT)

接口摘要是 trace 阶段即时提取的输出格式调整，不生成独立文件。避免 stale 文件同步问题，符合 DRY 原则。

## Acceptance Criteria

### AC1: trace 输出包含接口摘要层 (R1)

- **Given** 一个 Python 项目有 module_a.py（目标）和 module_b.py（依赖）
- **When** trace 分析 module_a 的调用链时发现 module_b
- **Then** 对 module_b 输出接口摘要（签名+docstring），对 module_a 输出完整实现

### AC2: Act Phase 1 使用分层加载 (R2)

- **Given** 一个 Spec 要求修改 deployer.py
- **When** 执行 Act Phase 1 Precision Targeting
- **Then** 对 deployer.py 读完整源码，对其依赖（如 profiles.py, schemas.py）先读接口摘要

### AC3: 不产生新文件 (R4)

- **Given** 执行 trace 后
- **When** 检查项目目录
- **Then** 无新增的接口摘要文件（摘要仅作为 trace 输出的一部分呈现）

## Target Call Chain

```
pactkit-trace SKILL.md Phase 3
  → Deep Tracing (现有：读完整文件)
  → [新增] 接口摘要模式（对非目标模块，提取签名+docstring）
  
project-act SKILL.md Phase 1
  → Precision Targeting
  → [新增] "先摘要后实现"加载指导
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `~/.claude/skills/pactkit-trace/SKILL.md` | Phase 3 增加接口摘要输出规则 | None | Low |
| 2 | `~/.claude/skills/project-act/SKILL.md` | Phase 1 增加分层加载指导 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | Playbook 文本变更，无代码 |
| SEC-2 | No | 无用户输入 |
| SEC-3 | No | 无数据库 |
| SEC-4 | No | 无 UI |
| SEC-5 | No | 无认证 |
| SEC-6 | No | 无接口 |
| SEC-7 | No | 无错误输出 |
| SEC-8 | No | 无依赖变更 |

## Out of Scope

- 独立的 `pactkit-interface` 工具（本 story 通过扩展 trace 实现，不新增工具）
- 预生成接口摘要文件（违反 DRY）
- Plan Phase 的 trace 调整（Plan 使用 trace 方式不变）
