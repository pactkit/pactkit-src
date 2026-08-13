# STORY-slim-135: Schema-driven pactkit.yaml governance: minimal init, single renderer, drift detection

| Field | Value |
|-------|-------|
| ID | STORY-slim-135 |
| Status | Done |
| Priority | P1 |
| Release | 2.17.0 |

## Background

pactkit.yaml 治理存在三个实测病灶（2026-08-13 全部在本仓库实锤）：

1. **init 生成"默认值墙"**：`generate_default_yaml()` 给新项目倾泻 94 行配置，其中约 90 行是 `provider: none` / `enabled: false` / 默认阈值，用户真正要配的只有 `stack` + `developer` 两行。这与 STORY-slim-126 确立的方向（"缺失 key = 接受默认，保持 yaml 极简"，`auto_merge_config_file` 已停止回填）直接矛盾——合并侧说极简，脚手架侧说全量。更隐蔽的害处：init 把默认值显式固化进文件后，PactKit 日后调优默认值时存量项目永远拿着旧值（配置漂移温床）。

2. **渲染逻辑双写（DRY 违反）**：`generate_default_yaml()` 与 `_rewrite_yaml()` 各自手写逐段渲染（ci/check/pactguard/observe/e2e/visualize…），注释文案都不一致。新增一个配置键需改 5~6 处：`get_default_config` → `DEEP_MERGE_KEYS` → `KNOWN_KEYS` → `_rewrite_yaml` → `generate_default_yaml` → `validate_config`，违反 Open-Closed 与 No Magic Values。

3. **多副本漂移 + 静默优先级**：本项目同时存在 `.claude/`、`.codex/`、`.github/` 三份 pactkit.yaml，内容互不一致（`.codex` 副本 `developer: ""`，`.github` 副本残留 `version: 0.0.1`）。`find_pactkit_yaml()` 按 opencode > codex > copilot > classic 顺序取第一个命中，导致 `pactkit next-id` 静默读到 codex 副本、丢失 `slim` 前缀，输出 `STORY-074` 而非 `STORY-slim-135`——无任何告警。

## Requirements

### R1: CONFIG_SCHEMA 声明式注册表 (MUST)

在 `src/pactkit/config.py` 引入单一 `CONFIG_SCHEMA` registry：每个配置键一条声明式条目，包含 `default`、`deep_merge`（bool）、`comment`（yaml 段落注释文案）、`validator`（校验函数）。`get_default_config()`、`validate_config()`、yaml 渲染全部改为由 `CONFIG_SCHEMA` 驱动生成——新增配置键 MUST 只需新增一条 registry 条目，不得再触碰多个函数体。

### R2: init 只生成 stack + developer (MUST)

`generate_default_yaml()` 的输出 MUST 只包含：文件头注释（含"运行 `pactkit schema config` 查看全部可配项"的指引）、`stack`、`developer`。不得输出 ci / issue_tracker / lint / venv / release / regression / check / done / e2e / visualize / command_models 等默认值段。默认值解析继续由 `load_config()` 合并完成，行为不变。

### R3: 单一渲染器 (MUST)

`_rewrite_yaml()` 与 `generate_default_yaml()` 的手写逐段渲染 MUST 收敛为同一个 schema 驱动的渲染函数。`auto_merge_config_file()`、`update_yaml_stack()` 重写 yaml 时复用同一渲染器；用户已有的显式配置键和值 MUST 原样保留（含未知键的 Custom 段，即 BUG-023 行为）。

### R4: 多副本一致性治理 (MUST)

- `pactkit init` / `pactkit update` 写配置时，MUST 将同一 canonical 内容同步到所有已存在的副本路径（`.claude/`、`.codex/`、`.github/`、`.opencode/`），消除静默漂移。
- `pactkit doctor` MUST 新增副本漂移检测：多个副本的关键键（`stack`、`developer`）不一致时报告并给出修复建议。
- `find_pactkit_yaml()` 的命中优先级 MUST 在 `pactkit schema config` 输出中可见，消除"静默读到非预期副本"。

### R5: `pactkit schema config` 可发现性 (MUST)

`pactkit schema` 新增 `config` 类型：输出全部可配键、默认值、当前生效值（merge 后）、来源（default / 哪个副本文件）。这是 R2 极简化的配套——用户改配置前能查到全部选项。

### R6: 解析行为零回归 (MUST NOT)

`load_config()` 对所有现有配置键的合并结果 MUST NOT 改变。对以下 fixture 集合的 merge 结果 MUST 与重构前逐键一致：94 行老版全量 yaml、本项目当前三份副本、空文件、仅含 `stack` 的极简文件、含未知自定义键的文件。

## Acceptance Criteria

### AC1: 新 init yaml 极简 (R2)

- **Given** 在空目录执行 `pactkit init --format classic --non-interactive`
- **When** 读取生成的 `.claude/pactkit.yaml`
- **Then** 文件仅含头部注释 + `stack` + `developer`（≤ 12 行）；不存在 `check:`、`e2e:`、`visualize:`、`regression:` 等默认值段

### AC2: schema 单一事实源 (R1, R3)

- **Given** 重构完成后的 `src/pactkit/config.py`
- **When** 检查 `get_default_config()`、`validate_config()`、渲染函数的实现
- **Then** 三者均由 `CONFIG_SCHEMA` 驱动；代码中不再存在逐键手写的默认值字典、逐段手写的 yaml 渲染分支

### AC3: 解析等价性 golden 测试 (R6)

- **Given** fixture 集合：94 行老版 yaml、本项目三份当前副本、空文件、极简 yaml、含未知键 yaml
- **When** 用重构后的 `load_config()` 加载并合并
- **Then** 每个 fixture 的 merged dict 与重构前基准（重构时先固化快照）逐键一致

### AC4: 重写路径统一渲染 (R3)

- **Given** 一份显式自定义过的 pactkit.yaml（含自定义键 + 部分显式段）
- **When** 执行 `pactkit update`（触发 auto_merge）和 `pactkit redetect-stack`
- **Then** 重写后的文件保留全部用户显式键值；段落渲染与 init 输出同源（同一渲染函数）

### AC5: 副本漂移被检测并修复 (R4)

- **Given** 人为构造 `.claude/pactkit.yaml`（`developer: "slim"`）与 `.codex/pactkit.yaml`（`developer: ""`）不一致
- **When** 执行 `pactkit doctor`，再执行 `pactkit update`
- **Then** doctor 报告副本漂移及冲突键；update 后所有已存在副本内容一致，`pactkit next-id` 输出带 `slim` 前缀的 ID

### AC6: schema config 可查全部键 (R5)

- **Given** 本项目任意 pactkit.yaml
- **When** 执行 `pactkit schema config`
- **Then** 输出覆盖 `CONFIG_SCHEMA` 全部条目，每条含默认值、当前生效值、来源（default 或具体副本路径）

### AC7: 测试套件全通过 (R1-R6)

- **Given** 全部修改完成
- **When** 运行 `.venv/bin/pytest tests/ -v`
- **Then** 所有测试通过，无新失败

## Target Call Chain

```
pactkit init → deployer._generate_pactkit_yaml() → config.generate_default_yaml(stack)
pactkit update → deployer → config.auto_merge_config_file() → config._rewrite_yaml()
pactkit redetect-stack → config.update_yaml_stack() → config._rewrite_yaml()
pactkit {next-id,audit,doctor,observe,lint,...} → config.load_config()
    ← find_pactkit_yaml() (PACTKIT_YAML_CANDIDATES 优先级: opencode > codex > copilot > classic)
    ← get_default_config() + DEEP_MERGE_KEYS 深合并
pactkit schema config (新) → CONFIG_SCHEMA + load_config() 生效值解析
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/config.py` | 引入 CONFIG_SCHEMA registry（每键 default/deep_merge/comment/validator） | None | Medium |
| 2 | `src/pactkit/config.py` | get_default_config / validate_config 改为 schema 驱动；先固化现有 fixture 的 merge 快照作为 golden 基准 | Step 1 | High（行为回归风险，靠 AC3 golden 测试兜底） |
| 3 | `src/pactkit/config.py` | 渲染器收敛：schema 驱动 render_config_yaml()，_rewrite_yaml / generate_default_yaml 复用；init 输出砍到 stack+developer | Step 1 | Medium |
| 4 | `src/pactkit/schemas.py` + `cli.py` | schema 命令新增 config 类型（键/默认值/生效值/来源） | Step 1-2 | Low |
| 5 | `src/pactkit/generators/deployer.py` | init/update 同步写所有已存在副本 | Step 3 | Medium |
| 6 | `src/pactkit/doctor.py` | 新增副本漂移检测 | Step 5 | Low |
| 7 | `tests/unit/` | CONFIG_SCHEMA 单测 + AC3 golden 测试 + AC5 漂移检测测试 | Step 1-6 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | 重构配置加载逻辑，须保证合法/非法 yaml 输入行为不回归（golden 测试覆盖） |
| SEC-2 | Yes | pactkit.yaml 是用户可控输入；必须继续使用 `yaml.safe_load`，禁止引入 `yaml.load` |
| SEC-3 | N/A | 无数据库相关（sec-scope 命中为关键词误报） |
| SEC-4 | N/A | 无前端文件 |
| SEC-5 | N/A | 无认证/会话逻辑（sec-scope 命中为关键词误报） |
| SEC-6 | N/A | 无 API/路由变更 |
| SEC-7 | Yes | yaml 解析失败、副本写入失败的错误处理路径须在重构后保持优雅降级 |
| SEC-8 | N/A | 无依赖变更 |

## Out of Scope

- 不改 `find_pactkit_yaml()` 的优先级顺序本身（只要求可见性 + 副本一致，重排优先级是另一个决策）
- 不为配置项做分层覆盖机制（global ~/.claude yaml vs project yaml 的覆盖语义维持现状）
- 不迁移存量项目的 94 行老 yaml（它们继续有效；用户可手动精简，`schema config` 提供指引）
- `pactkit deps` 外部依赖一键安装（codegraph/gh/node）——单独建卡，不在本故事
