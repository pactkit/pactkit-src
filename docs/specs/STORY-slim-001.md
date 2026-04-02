# STORY-slim-001: Tool Integration Guide — Checklist for Adapting PactKit to New AI Coding Tools

| Field | Value |
|-------|-------|
| ID | STORY-slim-001 |
| Status | Draft |
| Priority | P2 |
| Release | 2.0.2 |

## Background

PactKit 从 Claude Code 专属工具扩展为双平台支持（Claude Code + OpenCode），经历了 6 个 Story（STORY-069/070/071/072/073 + BUG-035），改动覆盖 29 个文件、3939 行新增。过程中多次因遗漏适配点导致返工。

为了未来适配新工具（如 Codex、Cursor、Windsurf 等）时不再踩坑，需要提炼一份**集成检查清单（Integration Checklist）**，将 OpenCode 适配过程中的所有改动点系统化。

### 问题回溯

以下是 OpenCode 适配过程中**实际踩过的坑**（按发现顺序）：

| 轮次 | 问题 | 根因 | 发现方式 |
|------|------|------|----------|
| STORY-069 | 基础框架搭建 | 全新功能 | 主动设计 |
| BUG-035 | opencode.json 放在了全局目录 | 未理解双层架构 | 用户反馈 |
| STORY-070 | Agent 缺 mode:subagent、name 多余、command 仍用 allowed-tools | 未对照官方文档 | 深度审计 |
| STORY-071 | AGENTS.md 12KB 太大、缺 permission/MCP 配置 | 未考虑 @import 不支持 | 用户提问 |
| STORY-072 | pactkit.yaml 硬编码在 .claude/，OpenCode 用户没有 | 未考虑工具无关性 | 用户质疑 |
| STORY-073 | Command 缺 model: 字段、project-init 无条件创建 CLAUDE.md | 全量审计遗漏 | 用户发现模型路由不生效 |
| Hotfix | model: 写了 provider-specific ID 到共享文件 | 未区分本地配置 vs 共享文件 | 用户发现内部名称泄露 |

## Requirements

### R1: 创建 `docs/guides/tool-integration-checklist.md` (MUST)

MUST 创建集成检查清单文档，包含以下 **11 个维度**（维度 0 为前置评估，维度 1-10 为实施检查），每个维度有具体的检查项和验证方法：

---

#### 维度 0: 工具能力矩阵（前置评估，MUST 最先完成）

不同 AI 编码工具的架构差异巨大。在开始任何实现之前，MUST 填写目标工具的能力矩阵：

| 能力维度 | Claude Code | OpenCode | Codex | 目标工具 |
|----------|-------------|----------|-------|----------|
| **Agents（多角色）** | 有（.claude/agents/*.md） | 有（agents/*.md, mode: subagent） | 无（单 agent） | ？ |
| **Commands（自定义命令）** | 有（.claude/commands/*.md） | 有（commands/*.md, frontmatter） | 有（但格式不同） | ？ |
| **Skills（技能脚本）** | 有（.claude/skills/*/） | 有（skills/*/SKILL.md） | 有（.codex/skills/） | ？ |
| **Rules（规则模块）** | 有（rules/*.md, @import） | 有（rules/*.md, instructions） | 无（只有 AGENTS.md） | ？ |
| **全局配置文件** | ~/.claude/CLAUDE.md | ~/.config/opencode/opencode.json | ~/.codex/ | ？ |
| **项目配置目录** | .claude/ | .opencode/ | .codex/ | ？ |
| **项目指令文件** | .claude/CLAUDE.md | ./AGENTS.md | ./AGENTS.md | ？ |
| **@import 规则引用** | 支持 | 不支持（用 instructions） | 不支持 | ？ |
| **Model 路由** | 无原生支持（prompt 级） | agent/command 级 model 字段 | 无（单模型） | ？ |
| **Permission 配置** | settings.json | opencode.json permission | sandbox 模式 | ？ |
| **MCP 支持** | settings.json mcpServers | opencode.json mcp | 有限支持 | ？ |
| **多 Provider** | 仅 Anthropic | 75+ providers | 仅 OpenAI | ？ |
| **图片/Vision** | 原生支持 | 需 capabilities 声明 | 未知 | ？ |
| **npm 包系统** | 无 | provider npm 包 | 无 | ？ |

**关键决策点**：根据矩阵判断适配策略

| 目标工具能力 | PactKit 适配策略 |
|-------------|-----------------|
| **有 agents** | 全量部署 9 个 agent，做格式转换 |
| **无 agents** | 将所有 agent 角色编码到 rules/AGENTS.md 中，通过 prompt 指令路由 |
| **有 commands** | 部署 11 个 command，做 frontmatter 转换 |
| **无 commands** | 将 command playbook 嵌入 AGENTS.md 或 rules 中，通过 `/` 前缀触发 |
| **有 skills** | 部署 10 个 skill，适配发现机制 |
| **无 skills** | 脚本直接放入全局目录，playbook 中用绝对路径调用 |
| **有 rules** | 模块化部署，适配加载机制 |
| **无 rules** | 全部内联到一个主文件（如 AGENTS.md） |
| **有 model routing** | 配置级路由（agent/command model 字段） |
| **无 model routing** | prompt 级路由（Model Guard Protocol） |
| **单 provider** | 无需 provider 解析，直接写 model ID |
| **多 provider** | 需要 model shortname → provider/model-id 映射 |

---

#### 维度 1: 目标工具研究

在写任何代码之前，MUST 完成以下研究：

| 检查项 | 说明 | 验证方法 |
|--------|------|----------|
| 1.1 官方文档阅读 | 阅读目标工具的 agents、commands、skills、rules、config、permissions、MCP 文档 | 列出每个概念的文档 URL |
| 1.2 配置格式差异 | 对比目标工具与 Claude Code 的配置格式（frontmatter 字段、YAML vs JSON） | 制作差异对比表 |
| 1.3 文件系统约定 | 目标工具的全局目录（如 `~/.config/opencode/`）和项目目录（如 `.opencode/`） | 确认路径 |
| 1.4 规则加载机制 | 目标工具如何加载 rules（@import？instructions？直接读取？） | 测试验证 |
| 1.5 模型路由机制 | 目标工具的 agent/command model 配置方式 | 对比 Claude Code |
| 1.6 权限模型 | 目标工具的 permission/safety 配置 | 确认字段名和格式 |
| 1.7 MCP 支持 | 目标工具的 MCP server 配置格式（remote/local/stdio） | 配置示例 |
| 1.8 图片/多模态支持 | 目标工具如何声明模型的 vision 能力（capabilities 配置？自动检测？） | 测试粘贴图片 |

---

#### 维度 2: 部署架构（deployer.py）

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 2.1 新增 `_deploy_{tool}()` 函数 | 主入口函数，编排所有子部署 | STORY-069 |
| 2.2 `deploy()` 入口添加 format 分支 | `if format == "{tool}": _deploy_{tool}(target)` | STORY-069 |
| 2.3 全局 vs 项目级分离 | 全局部署（CLI `pactkit init`）只写共享资源，项目级由 `/project-init` 处理 | BUG-035 |
| 2.4 双层目录结构 | 全局: `~/.<config>/{tool}/`，项目: `.{tool}/` | BUG-035 |

---

#### 维度 3: Agent 格式转换

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 3.1 identification 方式 | 文件名 vs frontmatter `name:` 字段 | STORY-070 |
| 3.2 mode 字段 | 是否需要 `mode: subagent` 或类似声明 | STORY-070 |
| 3.3 tools 格式 | string (`"Read, Write"`) vs record (`{ read: true }`) vs array | STORY-069 R7 |
| 3.4 model 字段 | `inherit` 是否需要省略，model 格式是 shortname 还是 provider/id | STORY-070 |
| 3.5 工具专有字段清理 | 移除上一个工具的专有字段（如 `permissionMode`, `memory`, `skills`） | STORY-070 |
| 3.6 routing reference | Agent 底部的 routing 引用路径是否指向正确的全局规则文件 | STORY-070 |

---

#### 维度 4: Command 格式转换

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 4.1 权限声明 | `allowed-tools: [...]` vs `agent: build` vs 其他方式 | STORY-070 |
| 4.2 model 路由 | frontmatter `model:` vs 外部配置文件 vs 无此概念 | STORY-073 + Hotfix |
| 4.3 model ID 格式 | provider-specific ID 不能写入共享文件，必须在本地配置中 | Hotfix |
| 4.4 参数传递 | `$ARGUMENTS` / `$1` / `$2` 等占位符语法是否兼容 | — |
| 4.5 description 字段 | 是否保持不变或需要格式调整 | STORY-070 |

---

#### 维度 5: Rules 加载

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 5.1 @import 支持 | 目标工具是否支持 `@` 引用？如不支持需要替代方案 | STORY-071 |
| 5.2 替代加载机制 | `instructions` 字段 / glob 模式 / 目录自动扫描 | STORY-071 |
| 5.3 全局规则文件 | CLAUDE.md → AGENTS.md → ？ 名字和加载优先级 | STORY-071 |
| 5.4 规则文件大小 | 内联 vs 模块化拆分，目标工具的上下文窗口限制 | STORY-071 |

---

#### 维度 6: Skills 格式

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 6.1 发现机制 | 文件名扫描 / frontmatter / 注册表 | STORY-069 |
| 6.2 frontmatter 格式 | `name` + `description` 或其他字段 | STORY-069 |
| 6.3 脚本路径前缀 | `_rewrite_skills_prefix()` 需要新的目标路径 | STORY-069 |

---

#### 维度 7: 配置文件（pactkit.yaml）

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 7.1 配置文件位置 | `.claude/pactkit.yaml` → `.{tool}/pactkit.yaml` | STORY-072 |
| 7.2 `load_config()` 多路径 | `PACTKIT_YAML_CANDIDATES` 列表添加新路径 | STORY-072 |
| 7.3 `resolve_pactkit_yaml_dir()` | 环境检测写入正确目录 | STORY-072 |
| 7.4 `_generate_config_if_missing()` | 环境感知生成 | STORY-072 |

---

#### 维度 8: Playbook 和 Prompt 文本

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 8.1 Init Guard marker | 检查配置存在性的路径列表 | STORY-072 |
| 8.2 `/project-init` 条件分支 | CLAUDE.md vs AGENTS.md vs 目标工具的项目指令文件 | STORY-073 |
| 8.3 `/project-plan` 配置读取 | Release 字段、developer 前缀等读取路径 | STORY-072 |
| 8.4 Skill/workflow 路径引用 | doctor、sprint 等 prompt 中的硬编码路径 | STORY-072 |
| 8.5 反向指令检查 | 确保没有"不要在 .{tool}/ 创建"这种过时指令 | STORY-072 |

---

#### 维度 9: CLI 和外部配置

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 9.1 CLI `--format` 选项 | `init`, `update`, `upgrade` 的 choices 列表 | STORY-069, STORY-070 |
| 9.2 全局配置文件合并 | 目标工具的全局 config（如 opencode.json）的 merge 策略 | STORY-071 |
| 9.3 权限配置生成 | permission + deny rules 的格式和内容 | STORY-071 |
| 9.4 MCP 配置生成 | remote vs local，哪些公共 MCP 可以预配置 | STORY-071 |
| 9.5 YAML 注释更新 | 生成的 pactkit.yaml 注释不能引用特定工具路径 | STORY-073 |
| 9.6 源码文档字符串 | skills.py 等的 docstring 需要包含所有工具路径 | STORY-073 |

---

#### 维度 10: 验证和发布

| 检查项 | 说明 | 对应 Story |
|--------|------|-----------|
| 10.1 容器化验证 | Docker 容器安装 + 部署产物检查 | 发布阶段 |
| 10.2 文件结构验证 | 所有目录和文件是否正确生成 | 容器测试 |
| 10.3 格式验证 | frontmatter 字段、model 格式、tools 格式 | 容器测试 |
| 10.4 CI 兼容性 | 测试在无目标工具的环境下（CI runner）能否通过 | CI 修复 |
| 10.5 文档更新 | README、pactkit.dev 全站（8 个页面）、landing page | 发布阶段 |
| 10.6 PyPI 发布 | 版本号、build、upload、GitHub Release | 发布阶段 |
| 10.7 共享文件 vs 本地配置 | 确保共享文件中不含 provider-specific 信息 | Hotfix |

---

### R2: 在 `docs/guides/` 下创建 Codex 适配预研模板 (SHOULD)

基于 checklist，SHOULD 创建一份 `codex-integration-preresearch.md`，列出需要回答的问题清单，作为未来适配 Codex 时的起点。

### R3: 将 checklist 引用加入 `/project-plan` playbook (SHOULD)

`/project-plan` playbook 在检测到新 format 适配需求时，SHOULD 提示开发者参考集成检查清单：

```
If the requirement involves adapting PactKit to a new AI coding tool,
refer to `docs/guides/tool-integration-checklist.md` for the complete integration checklist.
```

## Acceptance Criteria

### AC1: Checklist 文档完整

- **Given** `docs/guides/tool-integration-checklist.md` 已创建
- **When** 按 11 个维度逐项检查（维度 0 能力矩阵 + 维度 1-10 实施检查）
- **Then** 维度 0 包含能力矩阵表和适配策略决策表
- **And** 维度 1-10 每个至少有 3 个检查项

### AC2: Checklist 覆盖所有已知坑

- **Given** OpenCode 适配的 6 个 Story + 1 个 Hotfix
- **When** 逐个核对每个 Story 的改动
- **Then** 每个改动点在 checklist 中都能找到对应检查项

### AC3: Codex 预研模板

- **Given** `docs/guides/codex-integration-preresearch.md` 已创建
- **When** 阅读文档
- **Then** 包含维度 1 的所有研究问题，并标注"待填写"

## Target Call Chain

```
# 新工具适配流程
开发者阅读 docs/guides/tool-integration-checklist.md
→ 维度 0: 填写能力矩阵，确定适配策略（全量 vs 降级）
→ 维度 1: 研究目标工具（填写 preresearch 模板）
→ 维度 2-6: 实现部署架构（deployer.py + format 转换，按能力矩阵决定哪些维度适用）
→ 维度 7-9: 适配配置和 playbook（config.py + commands.py）
→ 维度 10: 验证和发布（容器测试 + 文档 + PyPI）
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|--------------|------|
| 1 | `docs/guides/tool-integration-checklist.md` | 创建完整的 10 维度集成检查清单 | None | Low |
| 2 | `docs/guides/codex-integration-preresearch.md` | 创建 Codex 预研模板 | Step 1 | Low |
| 3 | `src/pactkit/prompts/commands.py` | `/project-plan` 添加集成检查清单提示 | Step 1 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | No | Docs-only change (guides + playbook text) |
| SEC-2 | No | N/A |
| SEC-3 | No | N/A |
| SEC-4 | No | N/A |
| SEC-5 | No | N/A |
| SEC-6 | No | N/A |
| SEC-7 | No | N/A |
| SEC-8 | No | N/A |

## Out of Scope

- 实际的 Codex 适配实现（本 Story 只产出 checklist 和预研模板）
- 自动化检查脚本（未来可将 checklist 转化为自动化测试）
- 现有 OpenCode 代码的重构（checklist 是面向未来的指南）
