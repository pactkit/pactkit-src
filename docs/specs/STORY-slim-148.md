# STORY-slim-148: Git 友好的分片治理事实源与无冲突投影视图

| Field | Value |
|-------|-------|
| ID | STORY-slim-148 |
| Status | Done |
| Priority | P0 |
| Release | 2.21.0 |

## Background

PactKit 当前将执行状态、经验记录和会话摘要分别集中写入 `docs/product/sprint_board.md`、`docs/architecture/governance/lessons.md` 与 `docs/product/context.md`。这些文件便于人类阅读，却同时被 Plan、Act、Done、Init、Doctor、Garden、Release 和多个 CLI 模块当作可写事实源。两个并行分支即使处理完全不同的 Story，也会修改相同文件、相邻行或文件尾部，导致 PR 高频冲突。

`docs/specs/{ID}.md` 已经按 Story 分片，但 `pactkit next-id` 只扫描当前分支并递增编号；同一开发者从相同基线创建多个分支时仍可能分配同一 ID，从而直接产生 Spec 路径冲突。仅将三个聚合文件加入 `.gitignore` 无法解决这些消费者、历史数据、完成门禁和 ID 碰撞问题。

本 Story 保留这些信息能力，但重新划分事实所有权：Spec 只描述需求；逐 Story 文件保存执行状态和任务；逐 Lesson 文件保存经验；Board 与 Context 成为确定性生成视图。迁移采用“旧格式只读、新格式单写、校验后解除聚合文件跟踪”，禁止长期双写。

## Requirements

### R1: 定义无重叠的治理事实所有权 (MUST)

Core MUST 将治理数据划分为以下唯一事实源，任何字段不得同时由两个受版本控制的文件权威维护：

| 信息 | 唯一事实源 | 生命周期 |
|------|------------|----------|
| 需求、AC、技术设计、Spec 状态 | `docs/specs/{ITEM_ID}.md` | 按 Story 提交 |
| Story 标题、工作流状态、任务及完成时间 | `docs/product/stories/{ITEM_ID}.yaml` | 按 Story 提交 |
| 单条经验及来源元数据 | `docs/architecture/governance/lessons/{LESSON_ID}.md` | append-only 分片提交 |
| 跨会话执行进度 | `.pactkit/continuations/` | 本地，不提交 |
| Sprint Board | 从 Story records 生成 | 只读 projection |
| Session Context | 从 Story、Lesson、Git 与 continuation 生成 | 本地 cache/projection |

Story record MUST NOT 复制 Spec 的 Requirements、AC 或技术设计；Spec MUST NOT 复制任务完成状态。若 Spec `Status` 与 Story workflow status 都必须保留，前者表示需求文档生命周期，后者表示执行队列状态，并由明确状态映射校验，不得被视为同一字段的双写。

### R2: 以逐 Story 文件替代共享可写 Sprint Board (MUST)

`pactkit-board` 的 `add_story`、`update_task`、`move_story`、`archive`、`fix_board` 和 `list_stories` MUST 读取或原子修改单个 `docs/product/stories/{ITEM_ID}.yaml`，不得编辑共享 Markdown Board。Story schema MUST 至少包含 schema version、ID、title、spec path、workflow status、稳定 task ID、task title、completion state、created/updated timestamps 和可选 completion/archive metadata。

`sprint_board.md` MUST 由全部 Story records 确定性排序并生成；相同输入在不同机器和时间运行必须产生相同字节。生成内容 MUST 保持现有 Backlog、In Progress、Done 阅读结构和 Spec 链接，但不得成为状态验证或后续更新的输入。CLI MUST 提供 `pactkit board render` 与 `pactkit board render --check`；`--check` 只比较、不写入。

默认协作模式下 `sprint_board.md` MUST 退出功能分支的手工写入路径。仓库可选择不跟踪该文件，或仅由主分支 CI/bot 更新；两种策略必须通过配置明确，且功能 PR 的标准工作流不得要求提交该 projection。

### R3: 以不可变 Lesson 分片替代共享追加文件 (MUST)

`pactkit lesson add` MUST 将每条经验写入独立文件 `docs/architecture/governance/lessons/{LESSON_ID}.md`，文件名使用无中心唯一 ID，不依赖当前目录中的顺序计数。每条记录 MUST 包含 schema version、lesson ID、日期、关联 Story/上下文、具体经验文本和可选标签。写入必须 create-only；目标已存在时不得覆盖。

现有 specificity 与 duplicate 检查 MUST 保留，但去重范围改为扫描结构化 Lesson records。原 `lessons.md` 的表格汇总可由 `pactkit lessons render` 确定性生成，也可停止生成；无论选择哪种形式，任何业务命令都不得继续向共享汇总文件追加。Context 的近期决策必须直接读取 Lesson records，而非依赖汇总视图。

### R4: 将 Context 降级为未跟踪的本地生成视图 (MUST)

`pactkit context` MUST 从 Story records、Lesson records、Git 状态和 continuation checkpoints 生成会话摘要，并默认写入 `.pactkit/context.md` 或输出到 stdout。该产物 MUST 被 Git 忽略，Plan、Act、Done 和 Init 不得再 `git add`、提交或 amend 它。

Skill 冷启动 MUST 在本地 Context 缺失或 stale 时自动运行等价的只读生成逻辑，不得因 `docs/product/context.md` 缺失而停止。项目级 agent 指令不得强制 `@import` 一个未生成文件；应引用稳定的 context bootstrap 指令或由部署器维护的本地入口。Context 只是加速缓存，任何门禁都 MUST 从真实 Story、Spec、Lesson、Git 或 continuation 状态重新验证。

### R5: Story ID 必须支持同一开发者的并行分支无中心分配 (MUST)

`pactkit next-id` MUST 生成无需中央锁且在同一基线的并行分支间具有可验证低碰撞性的 ITEM ID。新格式 MUST 保留人类可识别的类型和 developer 前缀，并包含 ULID、UUID、随机或等价熵后缀；不得只依赖“当前最大数字 + 1”。

所有 ITEM ID regex、Spec/Case 文件解析、Board、Doctor、Garden、Backfill、Done Verify、Continuation 和 Spec Graph MUST 接受新旧两种 ID。旧 ID 永久可读，不要求批量重命名。测试必须从同一空快照并行生成至少 1000 个 ID 并证明无重复，同时验证路径字符 allowlist。

### R6: 提供无损、可回滚且禁止双写的迁移 (MUST)

Core MUST 提供显式迁移命令，将现有 Board block 转换为逐 Story records，将 `lessons.md` 及历史 archive 转换为逐 Lesson records，并生成本地 Context。迁移 MUST 先解析和验证全部输入，再在临时目录生成全部输出，完成数量、ID、标题、任务、状态和 Lesson 内容对账后才原子切换。任何解析歧义、重复 ID、未知状态或写入失败 MUST 保留旧文件并停止。

迁移期采用单向兼容：运行时优先读取新 records；新 records 不存在时允许读取旧聚合文件并提示迁移；一旦新 records 存在，所有写操作只写新格式。Core MUST NOT 同时写 Story record 与 `sprint_board.md`，也不得同时写 Lesson record 与 `lessons.md`，因为双写会制造新的漂移事实源。

迁移成功后，工具 MUST 给出可审计的 Git 操作清单，由用户确认后解除旧 `context.md`、`sprint_board.md`、`lessons.md` 的跟踪或将其转为主分支生成物。迁移命令不得自行删除已跟踪历史文件或执行 Git commit。

### R7: 所有消费者和完成门禁必须切换到事实源 API (MUST)

Context、Doctor、Garden、Audit、Backfill、Done Verify、Continuation、Plan/Act/Done/Init/Release prompts 和 deployer MUST 通过共享 repository/service API 读取 Story 与 Lesson facts，不得各自解析 projection Markdown。Guard MUST 检查新事实源目录与 schema，在兼容期才接受旧 Board。

完成和归档语义 MUST 从单个 Story record 与 Spec/Test evidence 验证。Archive 应更新 Story record 的终态和时间，而不是从 Board 剪切文本；历史展示可由状态过滤或单独 projection 生成。删除或修改 projection 不得改变任何 Story、Lesson 或完成判定。

### R8: 通过 PR 隔离和 projection 漂移门禁证明降冲突效果 (MUST)

测试 MUST 创建两个源于相同基线的模拟工作树，分别新增 Story、更新各自任务并新增 Lesson。两个分支的事实源变更路径 MUST 不重叠，顺序合并后不得产生文本冲突或丢失数据。若两个分支有意修改同一 Story record，Git 冲突仍应保留，不得使用 `merge=ours` 静默吞掉真实并发编辑。

CI MUST 运行 schema 校验、唯一 ID 检查、引用完整性检查和 projection `render --check`。对不提交 projection 的项目，CI 应在临时目录渲染并校验；对主分支维护 projection 的项目，只有专用 bot/合并后任务负责更新，功能 PR 不因时间戳、分支名或排序变化产生 diff。

### R9: 保持升级与多 Adapter 行为兼容 (SHOULD)

`pactkit update` SHOULD 为旧项目保留迁移提示而不隐式转换用户数据。Classic、OpenCode、Codex 和 Copilot 部署内容 SHOULD 共享相同的新路径、bootstrap 和禁止提交 projection 语义。README、初始化模板、schemas、rules 和相关 Skill 文档 SHOULD 同步更新，避免新项目继续生成旧共享可写结构。

## Acceptance Criteria

### AC1: 不同治理信息只有一个权威写入位置 (R1)

- **Given** 一个包含 Spec、Story tasks、Lesson、Context 和 continuation 的初始化项目
- **When** 检查 schema、写入 API 和生成链
- **Then** 每个字段只属于一个事实源，Board/Context/lesson 汇总均只读取事实且没有反向写入路径

### AC2: 两个并行 Story 不再修改同一个 Board 文件 (R2, R8)

- **Given** 从同一 Git commit 建立两个工作树
- **When** 两边分别 add Story、move Story 和 update 自己的 task
- **Then** 每边只修改自己的 `stories/{ITEM_ID}.yaml`，合并后两条 Story 都存在且 Board 可确定性重建

### AC3: Board projection 不参与状态决策 (R2, R7)

- **Given** Story records 已存在而 `sprint_board.md` 被删除、过期或人为修改
- **When** 运行 list、Doctor、Done Verify 和 Context
- **Then** 所有结果仍从 records 正确计算；`render --check` 单独报告 projection 漂移，不把错误视图当成事实

### AC4: 并行 Lesson 追加无共享文件冲突 (R3, R8)

- **Given** 两个分支从同一 lessons 基线开始
- **When** 各自添加一条不同 Lesson
- **Then** 生成两个不同 create-only 文件，合并无冲突，Context 和可选汇总同时包含两条经验

### AC5: Context 不再进入功能 PR (R4)

- **Given** Plan、Act 或 Done 在一个干净工作树运行 context refresh
- **When** 检查 `git status` 和 agent 冷启动行为
- **Then** 本地 Context 可被读取且不会出现在 tracked diff 中；删除它后可自动重建，门禁结果不受缓存影响

### AC6: 同基线并行分配不会碰撞 Story ID (R5)

- **Given** 相同 developer 和相同 specs 快照
- **When** 独立生成至少 1000 个新 ITEM ID
- **Then** ID 全部唯一、符合路径 allowlist，且所有 Core 解析器同时接受新 ID 和历史顺序 ID

### AC7: 旧聚合数据被完整迁移且失败可回滚 (R6)

- **Given** 包含 Backlog/In Progress/Done、归档 Story、重复 Lesson 和旧 Context 的 fixture
- **When** 执行 dry-run 和正式迁移
- **Then** dry-run 不写文件；正式迁移对账 Story/任务/Lesson 数量和内容后切换；注入任一失败时旧文件及已跟踪状态保持不变

### AC8: 新格式启用后不存在双写 (R6, R7)

- **Given** 项目已有 `stories/` 和 `lessons/` records
- **When** 执行 Plan、Act、Done、archive 和 lesson add
- **Then** 只有对应分片事实源变化，`sprint_board.md`、`lessons.md` 与 `docs/product/context.md` 不被业务命令修改

### AC9: 有意并发修改同一 Story 不被静默吞并 (R8)

- **Given** 两个分支修改同一 Story record 的同一 task 或状态
- **When** 合并分支
- **Then** Git 或语义合并门禁明确报告冲突，不使用 ours/theirs 策略自动丢弃任一修改

### AC10: 新旧项目和四种 Adapter 均可升级 (R9)

- **Given** 新初始化项目、仅含旧聚合文件的项目以及已迁移项目
- **When** 分别用 Classic、OpenCode、Codex、Copilot 部署并运行 guard/doctor
- **Then** 新项目只创建新事实源结构，旧项目获得可执行迁移提示，已迁移项目无 drift，adapter 生成物使用相同路径与语义

## Target Call Chain

    project-plan / project-act / project-done
      -> StoryRepository.load(ITEM_ID)
      -> atomic update of docs/product/stories/{ITEM_ID}.yaml
      -> optional BoardRenderer.render(records) [projection only]

    pactkit lesson add
      -> LessonRepository.validate_specificity_and_dedup()
      -> create-only lessons/{LESSON_ID}.md
      -> optional LessonsRenderer.render(records) [projection only]

    pactkit context / agent bootstrap
      -> StoryRepository.list() + LessonRepository.recent()
      -> Git state + ContinuationStore diagnostics
      -> .pactkit/context.md or stdout

    pactkit governance migrate
      -> LegacyBoardParser + LegacyLessonsParser
      -> validate and stage records in temporary directory
      -> reconcile counts/IDs/content
      -> atomic install records; preserve legacy inputs

    doctor / garden / audit / done-verify / backfill
      -> shared StoryRepository + LessonRepository
      -> deterministic diagnostics independent of projections

## Technical Design

### Lateral Scan Results

- Operation: 读取或修改 Sprint 状态。Existing implementations: `board.py`、`context_gen.py`、`doctor.py`、`done_verify.py`、`backfill.py`、`garden.py`、`audit.py` 及 prompts 中的直接 Markdown 路径。Assessment: 抽取 `StoryRepository` 和 `BoardRenderer`，禁止继续新增 Markdown parser。
- Operation: 读取或追加经验。Existing implementations: `lessons.py`、`context_gen.py`、`audit.py` 与 Done prompt。Assessment: 抽取 `LessonRepository` 和可选 renderer；保留 specificity/dedup 规则。
- Operation: 生成会话摘要。Existing implementation: `context_gen.generate_context()` 从 Board、Git、Lessons、Continuation 组合。Assessment: 保留生成器职责，替换输入 repository，并将输出移至未跟踪本地路径。

### Module and ownership design

新增治理 domain/repository 层，负责 typed record、schema validation、路径解析和原子单记录写入；renderer 只接收 record collection 并返回文本。CLI 负责显式持久化或 stdout，prompt 只调用 CLI。`doctor`、`done_verify` 等消费者必须依赖 repository 接口，不能依赖 renderer 或 Markdown projection，确保依赖方向为 facts → services → views。

Story record 使用 YAML 是为了保持人工可读且项目已依赖 PyYAML；字段顺序、task 排序和时间格式必须 canonical。Lesson record 使用带 YAML frontmatter 的 Markdown，以保留长文本可读性；Lesson ID 由标准库安全随机源或 ULID 等价实现生成，不新增运行时依赖。

### Projection policy

默认推荐不提交 `context.md`，并将其固定输出到已忽略的 `.pactkit/context.md`。Board/lesson 汇总是否提交由配置 `governance.projections` 决定，但默认也不由功能分支提交。所有 renderer 必须支持显式输出路径和 `--check`，且禁止把当前时间、当前分支等不稳定值写入受跟踪 projection。

### Migration and backwards compatibility

迁移器分为 parse、validate、stage、reconcile、install 五段。旧格式 parser 在兼容期仅用于 read fallback 与 migration，写路径只选择新格式。迁移报告列出每个生成文件和 legacy 文件的后续 Git 操作，但删除/`git rm` 必须由用户或 Done 阶段明确执行。所有历史 ITEM ID 保持原名；新 ID parser 使用共享 canonical pattern，消除当前多个模块各自维护 regex 的漂移。

### Capability Assessment

| Need | Source | Decision |
|------|--------|----------|
| YAML records | 已有 `pyyaml` 依赖 | 复用 `safe_load`/`safe_dump` 并增加 schema 校验 |
| 原子写入 | `utils.atomic_write()` | 复用 |
| Board 解析与任务操作 | `skills/board.py` | 拆分为 legacy parser、repository 与 renderer |
| Lesson specificity/dedup | `lessons.py` | 复用并改为扫描分片 records |
| Context 组合 | `context_gen.py` | 复用输出结构，替换数据源与默认路径 |
| 唯一 ID | Python 标准库安全随机能力 | 新增无中心 ID 生成，不引入第三方依赖 |

### Engineering concern decisions

- Module design：facts、repositories、renderers、migration 和 CLI 分层；低层 repository 不导入 prompts/deployer。
- Error recovery：单文件原子写入；迁移 staging + reconciliation；失败保留 legacy 输入；不使用静默 merge driver。
- Backwards compatibility：旧聚合格式只读兼容，新旧 ID 永久可读，升级不自动删除或提交用户文件。
- Data consistency：每字段唯一 owner；禁止双写；projection 只能单向生成；同 Story 并发修改必须显式冲突。
- Testing strategy：fixture 覆盖旧格式边界、property-style ID uniqueness、双工作树合并、renderer determinism、故障注入和四 adapter 部署。

## Implementation Steps

| Step | File / Repository | Action | Dependencies | Risk |
|------|-------------------|--------|--------------|------|
| 1 | 新治理 repository/renderer tests | RED：schema、单字段所有权、确定性 render、ID 唯一与路径安全 | None | High |
| 2 | `schemas.py`, new governance modules, `id_generator.py` | 定义 Story/Lesson records、共享 ID pattern 与无中心 ID | Step 1 | High |
| 3 | `skills/board.py`, `lessons.py`, CLI | 改为单记录原子写入并提供 render/check 命令 | Step 2 | High |
| 4 | `context_gen.py`, `.gitignore`, bootstrap/rules | 将 Context 改为本地 projection 并移除提交要求 | Steps 2-3 | High |
| 5 | migration module and fixtures | 实现 dry-run、staging、reconciliation、install 与 rollback | Steps 2-4 | High |
| 6 | doctor/garden/audit/backfill/done_verify/continuation | 全部消费者迁移到 repository API | Steps 2-5 | High |
| 7 | prompts, init templates, README, schemas | 更新 Plan/Act/Done/Init/Release 与新项目结构 | Steps 3-6 | Medium |
| 8 | Core + adapter integration tests | 双 worktree 冲突测试、全回归和四目标部署 parity | Steps 1-7 | High |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | Context 与 Lesson 可能包含命令摘要、路径和自由文本，写入前必须净化 secrets 与用户主目录 |
| SEC-2 | Yes | ITEM/LESSON ID、YAML、迁移输入和输出路径均不可信，必须 schema/allowlist 校验并阻止路径穿越与 YAML 非安全构造 |
| SEC-3 | No | 不使用数据库或 SQL |
| SEC-4 | No | Markdown/YAML 仅作为仓库文件和文本输出，不新增浏览器渲染入口 |
| SEC-5 | No | 不涉及认证、授权或会话身份 |
| SEC-6 | No | 不新增网络 API 或外部请求 |
| SEC-7 | Yes | 迁移、原子切换、并发写入、损坏 record 和 projection drift 必须 fail closed 且可恢复 |
| SEC-8 | Yes | 新旧项目、历史 ID、四 adapter、Core schema 版本和部署内容都需要兼容门禁 |

## Dependency Surface

| Field | Value |
|-------|-------|
| Depends on | STORY-slim-136, STORY-slim-139, STORY-slim-146, STORY-slim-147 |
| Provides | 分片 Story/Lesson 事实源、本地 Context、只读 Board projection、无冲突 ID 与无损迁移协议 |
| Touches | governance schemas/repositories, board/lesson/context/id CLI, guard/doctor/garden/audit/backfill/done verification, prompts/rules/templates, ignore policy, Core/adapter tests and system design |
| Conflict risk | HIGH |

## Out of Scope

- 用云数据库、GitHub Projects 或中央服务替代仓库内治理数据。
- 自动解决两个分支对同一 Story 或同一任务的真实语义冲突。
- 删除 Spec、Lesson、Board 或 Context 所提供的信息能力。
- 重写 STORY-slim-147 的 continuation workflow engine。
- 在迁移命令中自动执行 `git rm`、commit、push、rebase 或修改远端 PR。
