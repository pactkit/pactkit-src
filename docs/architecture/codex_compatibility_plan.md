# PactKit 面向 Codex 的能力迁移方案（分析版）

## 1. 背景与目标

当前 PactKit 的核心体验深度绑定 Claude Code（目录约定、命令入口、提示词语法、工具名、MCP 引导文案）。
但仓库已经具备“多 Agent 兼容”的基础雏形（如 adapter、`--agent` 参数、multi-agent 测试）。

本方案目标是：

1. **保留 Claude 现有体验不退化**（零破坏）。
2. **让 Codex 用户可用同一套 PDCA 能力**（命令、agent、skills、治理规则）。
3. **建立可持续的多平台适配层**（后续新增平台低成本）。

---

## 2. 现状分析（关键差距）

### 2.1 CLI 参数与部署链路未打通

- CLI 暴露了 `--agent`（claude/cursor/copilot/generic/all），但 `deploy()` 调用未传递 agent 参数。
- `deploy()` 也没有接收并分流 agent 类型；`classic` 逻辑仍固定写入 `.claude` 生态。

**结论**：当前“多 agent”更多是接口层承诺，尚未形成端到端行为。

### 2.2 adapter 能力存在，但仅覆盖“文档前置头剥离”

- `src/pactkit/generators/adapter.py` 仅实现：frontmatter strip、目标目录、扩展名。
- 未覆盖：工具名映射、命令调用语法映射、平台特定安全/权限提示、MCP 文案映射。

**结论**：适配层粒度过粗，无法支撑 Codex 可执行工作流。

### 2.3 Prompt 资产平台耦合较重

- 大量 prompt 文案硬编码 `~/.claude/...`、Claude 命令语义、Claude MCP 指引。
- `README` 与配置说明主要围绕 Claude 路径与运行方式。

**结论**：需要把“平台无关治理语义”与“平台实现细节”解耦。

### 2.4 配置模型缺少“平台能力矩阵”

- 当前配置强调启用哪些 agents/commands/skills/rules。
- 缺少“平台能力开关”（例如：是否支持 slash 命令、是否支持 tool 白名单、是否支持 MCP、PR 自动化方式）。

**结论**：若直接复制 Claude 提示词到 Codex，会出现大量不可执行指令。

---


## 2.5 你提到的关键对象是否覆盖（补充结论）

是的，迁移必须把下面 6 类对象作为**一个系统**处理，而不是只改 adapter：

1. `CLAUDE.md`（全局宪法入口）
2. `rules/*.md`（模块化规则）
3. `pactkit.yaml`（组件开关 + 行为策略）
4. `commands/*.md`（PDCA 命令编排）
5. `skills/*`（脚本技能 + prompt 技能）
6. `agents/*.md`（角色定义与工具边界）

如果只做“命令文档转换”，不处理上面依赖关系，Codex 下会出现：
- 规则失联（CLAUDE.md 引用路径不成立）
- 命令存在但 agent 角色不可执行
- skill 名字存在但脚本路径/调用方式失效
- 配置项开启了功能但运行时能力不支持

---

## 2.6 当前仓库里的真实依赖拓扑（落地视角）

建议把 PactKit 运行抽象为如下链路：

`pactkit.yaml`（启用清单 + 策略）
→ deployer 生成 `CLAUDE.md / rules / commands / agents / skills`
→ `CLAUDE.md` 再通过 `@` 引用 rules
→ rules 的 routing/shared/mcp 约束命令和 agent 行为
→ commands 在执行中调用 skills / agents / workflows

这意味着 Codex 迁移不能只做“文件格式转换”，而是要做“**引用系统 + 能力系统 + 目录系统**”整体迁移。

---

## 3. 目标架构（推荐）

采用“三层架构”：

1. **Core Spec Layer（平台无关）**
   - PDCA 状态机
   - 角色职责
   - 治理规则（Spec > Tests > Code）
   - 安全/质量门禁定义

2. **Runtime Contract Layer（能力契约）**
   - 抽象能力：`read_file`, `write_file`, `run_test`, `open_pr`, `take_screenshot`, `use_mcp`
   - 每个平台提供 capability manifest（claude/codex/cursor...）

3. **Adapter Render Layer（平台落地）**
   - 模板渲染：命令入口、目录结构、前置说明、工具调用示例
   - 语法转换：frontmatter、命令风格、工具名

这样 Codex 仅需新增一份 manifest + 若干模板，而不是 fork 整套 prompts。

---

## 4. Codex 迁移实施路线图

## Phase 0：基线与验收定义（1 周）

- 建立 `codex` 目标定义：
  - 目录规范（例如 `.codex/`）
  - 命令触发约定
  - 可用工具/限制模型
- 定义 DoD：
  - `pactkit init --agent codex` 可部署
  - 至少跑通 Clarify/Plan/Act/Check/Done 一条完整链路
  - 关键回归测试通过

## Phase 1：最小可用适配（MVP，1~2 周）

1. 在 adapter/cli/deployer 中增加 `codex` 一等支持。
2. 打通 `--agent` 参数传递和部署分流。
3. 先支持“文档+规则+命令模板”的 Codex 版本（不追求全自动工具调用）。
4. 以 `generic` 为基础，新增 Codex 专属覆盖模板。

**交付标准**：Codex 用户可执行文本工作流，不因 Claude 专属指令卡死。

## Phase 2：工具与工作流深度对齐（2~3 周）

1. 建立 Tool Mapping：
   - Claude 工具名 → Codex 可用工具名/调用方式。
2. MCP 指令模块化：
   - “若可用则调用，否则降级”改为平台能力驱动。
3. PR/发布链路适配：
   - 将 gh CLI 强绑定改为 provider 抽象。

**交付标准**：Codex 下可稳定执行 Act/Check/Done（含测试、检查、PR）。

## Phase 3：统一多平台模板系统（2 周）

1. 提取平台无关 prompt 片段（角色意图、流程步骤、门禁规则）。
2. 平台差异通过模板变量注入，不再在主文案里硬编码 `.claude`。
3. 输出平台能力报告（用户可见）。

**交付标准**：新增平台时，不再复制 11 命令 x 9 agents 全量文本。

---

## 5. 代码改造清单（建议）

1. **CLI / Deployer**
   - `cli.py`：`--agent` 参数传入 deploy。
   - `deployer.py`：新增 `agent` 参数与 dispatch（claude/codex/...）。

2. **Adapter**
   - `SUPPORTED_AGENTS` 增加 `codex`。
   - 新增 `transform_for_codex()`：
     - frontmatter 处理
     - 工具名与命令格式转换
     - 平台前置说明注入

3. **Prompts 资产拆分**
   - 基础模板：`prompts/base/*`
   - 平台覆盖：`prompts/platforms/{claude,codex}/*`

4. **配置模型**
   - `pactkit.yaml` 增加：
     - `runtime.platform: claude|codex|...`
     - `runtime.capabilities`（可自动探测 + 手动覆盖）

5. **测试体系**
   - 单测：adapter/路径/扩展名/模板渲染
   - 集成：`init --agent codex` 产物快照
   - e2e：至少一条 PDCA happy-path

---

## 6. 风险与缓解

1. **风险：Claude 文案直接迁移导致 Codex 执行偏差**
   - 缓解：建立 capability matrix，所有工具调用都走抽象动作。

2. **风险：多平台后测试成本飙升**
   - 缓解：基于共享基线测试 + 平台差异测试分层。

3. **风险：历史用户配置兼容**
   - 缓解：配置自动迁移（默认 claude），并输出一次性升级提示。

---

## 7. 里程碑建议（可直接立项）

- **M1（第 1 周）**：设计评审通过（架构+能力矩阵+DoD）。
- **M2（第 3 周）**：Codex MVP（可部署、可跑主流程）。
- **M3（第 6 周）**：Codex 深度可用（工具/PR/检查链路稳定）。
- **M4（第 8 周）**：多平台模板统一，进入常态维护。

---

## 8. 建议的下一步执行

1. 先补一个 `STORY-CODEX-001` 规格文档，冻结验收标准。
2. 开一个最小 PR：仅打通 CLI→deploy→adapter 的 `codex` 参数通路。
3. 第二个 PR 再做 prompt 模板拆分，避免一次性大改风险。




## 9. 面向你关注点的专项迁移清单（CLAUDE.md / rules / pactkit.yaml / commands / skills / agents）

### 9.1 CLAUDE.md 与 Rules（宪法层）

**现状问题**
- `CLAUDE.md` 使用固定 `@~/.claude/rules/...` 引用。
- Rules 文案里混有 Claude 特定工具名、命令调用范式和 MCP 触发描述。

**Codex 方案**
1. 引入“Constitution Entry Template”按平台渲染：`CLAUDE.md`（claude）/`CODEX.md`（codex，名称可配置）。
2. 引用路径改为变量：`{{runtime.rules_root}}/01-core-protocol.md`。
3. Rules 内容分层：
   - policy 层（平台无关）
   - runtime hint 层（平台特定，如 tool 名称、MCP 调用形式）

**验收**
- 宪法入口文件可在 Codex 环境完整解析 rules，且不含失效路径。

### 9.2 pactkit.yaml（配置与能力协商层）

**现状问题**
- 现有配置主要管理“启用哪些组件”，缺少“运行时平台能力协商”。

**Codex 方案**
新增：
```yaml
runtime:
  platform: codex
  commands_mode: prompt   # slash | prompt | hybrid
  mcp: auto               # auto | on | off
  pr_provider: gh          # gh | api | none
  capabilities:
    tool_calling: true
    screenshot: true
    mcp: true
    subagent: false
```
并规定：commands/agents/skills 渲染时必须读取 `runtime.capabilities` 做条件降级。

**验收**
- 同一份组件清单在 Claude/Codex 两端都可部署；差异由 runtime 段控制。

### 9.3 PDCA Commands（工作流编排层）

**现状问题**
- command playbook 里可能存在 Claude 风格命令触发语法与工具调用假设。

**Codex 方案**
1. 建立 command IR（中间表示）：Phase、Gate、Action、Fallback。
2. 再渲染到平台模板：
   - Claude: slash-first
   - Codex: prompt/tool-first
3. 对每个 command 增加 capability fallback 块（例如 MCP 不可用时的替代流程）。

**验收**
- 11 个命令至少有 Codex 版渲染产物；`project-sprint` 能编排串联主链路。

### 9.4 Skills（pactkit-* 能力层）

**现状问题**
- 部分 skill 是脚本型（visualize/board/scaffold），部分是 prompt 型；当前路径与调用文案更偏 Claude 生态。

**Codex 方案**
1. Skill Manifest 化：
   - `type: scripted | prompt`
   - `entry`: 脚本入口
   - `requires`: 运行能力（python/bash/mcp/...）
2. 部署时按能力过滤：Codex 不支持的能力自动禁用或降级。
3. 脚本 skill 保持不变（尽量复用 Python 实现），只替换调用说明模板。

**验收**
- `pactkit-visualize / board / scaffold` 在 Codex 路径下可被调用并产生产物。

### 9.5 Agents（角色与权限边界层）

**现状问题**
- agent 定义通常绑定 Claude 风格 frontmatter 与工具白名单语义。

**Codex 方案**
1. 把 agent 定义拆成：
   - role policy（职责、输入输出、停止条件）
   - runtime binding（工具声明、模型声明、温度/成本策略）
2. `agent_models` 继续保留，但增加平台映射（例如 sonnet/opus 与 Codex 模型层级映射表）。
3. 对不支持 subagent 的平台，启用“单代理模拟多角色”策略（按 phase 切换 role prompt）。

**验收**
- 9 个角色都可在 Codex 下被“真实多代理”或“单代理角色切换”执行。

### 9.6 一次性全局检查项（避免遗漏）

迁移前必须做一次仓库级扫描（建议做成 CI 规则）：

1. 所有 `~/.claude` 硬编码路径。
2. 所有 `mcp__*` 工具名与平台能力不一致处。
3. 所有 `project-*` 命令触发说明与目标平台语法差异处。
4. 所有技能脚本调用路径是否可被平台正确解析。
5. `README` 与用户文档是否仍宣称“仅 Claude”。

---

## 10. 建议拆分为 3 个实现 PR（比大 PR 更稳）

1. **PR-A（基础通路）**
   - 打通 `--agent codex` 参数：CLI → deployer → adapter
   - 增加 codex 目标目录/扩展名/基础 transform

2. **PR-B（配置与模板）**
   - 引入 `runtime` 配置段
   - commands/agents/skills 增加 capability 条件渲染

3. **PR-C（宪法与规则解耦）**
   - CLAUDE.md/CODEX.md 入口模板化
   - rules 中平台相关段落模块化
   - 增加跨平台回归测试矩阵

这样每个 PR 都可回归验证，不会在一个改动里同时重构所有 prompt 资产。
