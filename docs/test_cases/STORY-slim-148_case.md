# Test Cases: STORY-slim-148 — 分片治理事实与低冲突协作

| Field | Value |
|---|---|
| Spec | STORY-slim-148 |

## TC-1: 治理事实具有唯一写入位置（AC1）

- **Given** Story、Lesson、Context 与 Board 四类治理信息
- **When** repository 执行写入
- **Then** Story 写入独立 YAML、Lesson 写入独立 Markdown、Context 为本地缓存、Board 仅为投影，不发生双写

## TC-2: 并行 Story 不共享 Board 写入（AC2）

- **Given** 两个从同一基线创建的工作树
- **When** 分别新增和推进不同 Story
- **Then** 只修改各自 Story record，合并不因 sprint_board.md 产生冲突

## TC-3: Board projection 不参与状态决策（AC3）

- **Given** Story facts 与过期或缺失的 Board projection
- **When** continuation、doctor、done gate 或 board 命令读取状态
- **Then** 决策来自 StoryRepository；projection drift 被报告但不被当作事实源

## TC-4: 并行 Lesson 无共享追加冲突（AC4）

- **Given** 两个并行工作树记录不同 Lesson
- **When** 分别提交并合并
- **Then** 生成不同的不可变 Lesson 文件且不会修改共享 lessons.md

## TC-5: Context 不进入功能 PR（AC5）

- **Given** 项目生成会话 Context
- **When** 执行 pactkit context 并检查 Git 状态
- **Then** 内容写入被忽略的 .pactkit/context.md，不修改受跟踪的 docs/product/context.md

## TC-6: 并行 ITEM ID 不碰撞且兼容旧 ID（AC6）

- **Given** 同一开发者和相同基线上的并行分配
- **When** 多次生成 ITEM ID
- **Then** 新 ID 含抗碰撞熵且唯一，旧格式 ID 仍可解析和读取

## TC-7: 旧聚合数据无损迁移且可回滚（AC7）

- **Given** legacy Board、Lesson 与 archive 数据
- **When** 先 dry-run 再 apply migration
- **Then** 所有记录完成 reconciliation，legacy 文件保留；任一安装阶段失败时新目录全部回滚

## TC-8: 新格式禁止双写（AC8）

- **Given** 分片治理已启用
- **When** 新增 Story、完成 Task、追加 Lesson 或生成 Context
- **Then** 只更新相应权威 record，本地 projection 仅通过显式 render 更新

## TC-9: 同一 Story 的并发修改保留真实冲突（AC9）

- **Given** 两个工作树同时修改同一个 Story fact
- **When** Git 合并两个分支
- **Then** 同一 YAML 文件产生可见冲突，不静默覆盖任一修改

## TC-10: 新旧项目与四种 Adapter 可升级（AC10）

- **Given** legacy 和新治理项目以及四种目标平台
- **When** 安装或更新 PactKit 并执行隔离部署
- **Then** 历史 ID 和数据保持可读，四个平台部署内容及治理语义一致
