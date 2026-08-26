# Test Cases: STORY-slim-20260825b1c83a046b4b — 场景化规则与非阻塞执行

| Field | Value |
|---|---|
| Spec | STORY-slim-20260825b1c83a046b4b |

## TC-01: 普通任务只加载 Runtime（AC1）

- **Given** PactKit 已部署但用户未调用 `project-*` skill
- **When** 宿主加载全局规则
- **Then** 只加载 `pactkit-runtime`；不包含 TDD、Visual First、Board、WorkUnit 或阶段门禁

## TC-02: Act 加载精确的阶段与共享规则（AC2）

- **Given** 用户调用 `project-act`
- **When** 渲染 Classic import、OpenCode inline 或 Codex/Copilot command 内容
- **Then** 包含 Runtime、Act contract、shared execution、preflight 和声明的能力模块；不包含 Plan/Release contract 或未选 guide

## TC-03: Required 失败不锁住当前工作（AC3）

- **Given** preflight receipt 缺失或旧 workflow 状态为 blocked
- **When** 用户继续阅读、调查、修复或运行测试
- **Then** 规则将完成状态标为 incomplete，并给出下一步；不要求新 session 或阻止安全操作

## TC-04: Hard 规则仅阻止具体风险动作（AC4）

- **Given** 未授权 push/release、凭据暴露或不可逆写入风险
- **When** 尝试对应动作
- **Then** 仅该动作被阻止，读取、诊断与本地安全修复仍可继续

## TC-05: Claude Code 文本不含 Codex 编排术语（AC5）

- **Given** 规则和 command 部署到隔离 Classic target
- **When** 扫描全部部署文本
- **Then** 不出现 `codex runner`、`--owner codex`、`Codex thread` 或强制新 session 的指令

## TC-06: 用户规则与已修改 managed rule 无损（AC6、AC9）

- **Given** target 含用户规则及 hash 与 manifest 不一致的 PactKit managed rule
- **When** 执行升级部署
- **Then** 用户文件和修改后的 managed 文件保持不变，生成 `.pactkit-new` 候选并报告冲突

## TC-07: Guides 是风险驱动建议（AC7）

- **Given** 十九个 engineering guides
- **When** 执行 registry/content 测试
- **Then** 每个 guide 有 Trigger、Defaults、Hard Safety、Evidence，且没有无条件 TTL、幂等键、health endpoint、固定事务/timeout 阈值

## TC-08: 四 adapter 的注册表语义一致（AC8）

- **Given** 同一 Rule Registry
- **When** 分别隔离部署 Classic、Codex、OpenCode、Copilot
- **Then** Runtime 与 phase/shared 模块逻辑身份一致，且每个宿主只使用其原生路径和引用语法

## TC-09: Runtime 预算与 maintainer 隔离（AC10、AC12）

- **Given** Runtime Kernel、业务仓库和 PactKit 仓库
- **When** 执行预算与命令加载检查
- **Then** Runtime 不超过 70 行，且 `pactkit-maintainer` 不进入业务项目的 command 上下文

## TC-10: 旧规则迁移幂等且失败不破坏现有部署（AC9）

- **Given** 隔离 target 含旧 manifest、已知 legacy rules、自定义配置和用户修改过的 managed 文件
- **When** 连续部署两次，并模拟候选写入或 manifest 更新失败
- **Then** 成功部署保持幂等；失败不覆盖用户版本，最后一个完整 manifest 仍可用于归属判断和恢复

## TC-11: 冲突规则按明确优先级解析（AC11）

- **Given** 用户当前明确指令、项目本地约束、旧 Spec 与 advisory guide 相互冲突
- **When** Runtime 与当前 phase contract 解析可执行行为
- **Then** 平台安全仍为最高边界；其余采用用户当前决定和项目约束，旧 Spec 被标注待同步，advisory 不得锁住 workflow

## TC-12: Personal Rules 只读诊断且不误报友好说明（R13）

- **Given** PactKit-owned、project-owned、user-owned rules 以及 `.pactkit-new` 候选并存
- **When** 执行 doctor ownership audit
- **Then** 按 manifest 证据区分三类 owner，报告高置信冲突和 side-by-side 候选，不修改任何规则，也不把“new session is optional”误报为强制拆分 session
