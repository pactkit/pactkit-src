# Test Cases: STORY-slim-144 — Sprint Wave Mode: conflict-aware parallel orchestration

## TC-1: JSON output shape (AC1)

- **Given** 两个 wave + 一个同 wave 冲突的 Spec 集合
- **When** 运行 `pactkit spec-graph --json`
- **Then** 输出合法 JSON 含 `waves`（排序的 ID 列表的列表）与 `conflicts`（含 story_a/story_b/shared/same_wave），两次运行字节一致

## TC-2: Cycle under --json (AC2)

- **Given** 两个互相依赖的 Spec
- **When** 运行 `pactkit spec-graph --json`
- **Then** 以非零码退出且 stderr 含 cycle 路径

## TC-3: Mode detection (AC3)

- **Given** 更新后的 SPRINT_PROMPT / project-sprint.md
- **When** 阅读入口 Phase
- **Then** 非空 `$ARGUMENTS` → 单 story 模式（行为不变）；空 → wave 模式（board 扫描 + `spec-graph --json` + 无可并行 story 时回退建议）

## TC-4: Scheduling policy (AC4)

- **Given** 更新后的 playbook
- **When** 阅读 Wave Mode section
- **Then** 编码全部策略：声明 Touches 且两两无冲突才并行 / `sprint.max_parallel` 默认 3 / 冲突或未声明者串行 / 按引用复用 Stage A-C（不复制定义）

## TC-5: Wave gate & failure policy (AC5)

- **Given** 更新后的 playbook
- **When** 阅读 Wave Mode section
- **Then** 编码：wave N+1 阻塞至 N 全部 merge 绿 / fail-fast 且 NEVER auto-retry / merge 冲突提示 `git merge --abort` / dispatch 前打印 wave plan 并等用户确认

## TC-6: Prompt hygiene (AC6)

- **Given** 实现完成
- **When** 运行全量测试
- **Then** 全部通过（prompt 基线 bump 均带 justification 注释）
