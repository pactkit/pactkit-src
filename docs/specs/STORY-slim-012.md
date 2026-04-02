# STORY-slim-012: Stack-Aware CI Pipeline Generation

| Field | Value |
|-------|-------|
| ID | STORY-slim-012 |
| Status | In Progress |
| Priority | P1 |
| Release | 2.2.0 |

## Background

当前 `_deploy_ci()` (deployer.py) 存在以下问题：

1. **模板硬编码 Python**：`actions/setup-python@v5`、`python:3.11`、`pip install pytest ruff` 写死在模板中，`LANG_PROFILES` 中丰富的 stack 信息（test_runner, package_file, lint_command）只用到了 `lint_command`
2. **无 CI 结果反馈**：`/project-done` 提交代码后无法知道 CI 是否通过，用户需手动去 GitHub 查看
3. **不支持 GHE**：模板使用 `actions/checkout@v4`、`actions/setup-python@v5` 等 GitHub.com marketplace actions，GHE Server 在无 GitHub Connect 的情况下可能无法访问这些 actions
4. **无 CI 配置自定义**：Python 版本、Node 版本、Go 版本等无法配置，`runs-on` 标签固定为 `ubuntu-latest`
5. **OpenCode 部署路径未调用 CI**：`_deploy_opencode()` 没有调用 `_deploy_ci()`，只有 Classic 路径会生成 CI 文件
6. **pactkit.yaml 不可见**：新增的 CI 配置字段（runner, language_version, actions_ref, github_host）不会出现在 `generate_default_yaml()` 的输出中，用户无法发现这些选项

### 现状分析

**`_deploy_ci()` 调用链**：
- `_deploy_classic()` → L252 `_deploy_ci(ci_provider, project_root, config)` ✅
- `_deploy_opencode()` → 无 CI 调用 ❌

**`LANG_PROFILES` 已有但 CI 未用的字段**：
- `test_runner`: pytest / npx jest / go test ./... / mvn test
- `test_dir`: tests/ / __tests__/ / *_test.go / src/test/java/
- `package_file`: pyproject.toml / package.json / go.mod / pom.xml
- `source_dirs`: src/ / lib/ / app/ 等

**GHE 环境**：
- 用户有 `git.i.mercedes-benz.com`（GHE Server 3.17.9）
- `gh` CLI 已配置双 host auth，能根据 remote URL 自动路由
- GHE Server 可能没有 GitHub Connect，无法直接使用 `actions/*@v4` marketplace actions

## Requirements

### R1: Stack-Aware 模板生成
MUST 根据 `LANG_PROFILES[stack]` 自动选择正确的 CI 模板：

| Stack | Setup Action | Install | Lint | Test |
|-------|-------------|---------|------|------|
| python | setup-python | pip install -e ".[dev]" | ruff check src/ tests/ | pytest tests/ -v |
| node | setup-node | npm ci | npx eslint . | npx jest |
| go | setup-go | go mod download | golangci-lint run | go test ./... |
| java | setup-java (temurin) | mvn dependency:resolve | mvn checkstyle:check | mvn test |

### R2: CI 模板参数化
MUST 支持以下参数通过 `pactkit.yaml` 的 `ci` 配置覆盖：

```yaml
ci:
  provider: github              # github | gitlab | none
  runner: ubuntu-latest         # runs-on label (GHE self-hosted: self-hosted, linux)
  language_version: "3.12"      # Python/Node/Go/Java version
  github_host: ""               # GHE 地址，如 "git.i.mercedes-benz.com"；空或不填 = github.com
  actions_ref: ""               # GHE actions 前缀，如 "my-org/"；空 = 默认 "actions/"
```

### R3: GHE 兼容性
MUST 支持 GitHub Enterprise Server 部署：
- **显式配置优先**：如果 `ci.github_host` 非空，视为 GHE 模式
- **自动检测兜底**：如果 `ci.github_host` 为空，则 `_detect_ghe()` 检测项目 remote URL 是否为非 github.com host
- GHE 模式效果：
  - workflow 顶部添加注释 `# NOTE: GHE detected — verify action availability on your instance`
  - 如果 `ci.actions_ref` 非空，所有 `actions/` 前缀替换为 `{actions_ref}actions/`（如 `my-org/actions/checkout@v4`）
  - 支持自定义 `runner` 标签（self-hosted runners 常见于 GHE）

### R4: CI 结果反馈集成
SHOULD 在 `/project-done` 的 Phase 4 (Git Commit) 后增加 CI 状态检查：
- push 后调用 `gh run list --limit 1` 检查最新 workflow run 状态
- 如果 CI provider 为 github 且有 `gh` CLI，等待并报告 CI 结果
- 显示格式：`CI: [pass/fail/pending] — {workflow_name} #{run_number}`
- CI 失败时提示用户但不阻塞 Done 流程（CI 可能有 flaky tests）

### R5: GitLab CI 同步更新
MUST 同步更新 GitLab CI 模板，使其也支持 stack-aware 生成（image、script 根据 stack 变化）。

### R6: 向后兼容
MUST 保持向后兼容：
- 如果 `pactkit.yaml` 中没有新字段（`runner`, `language_version`, `actions_ref`, `github_host`），使用默认值
- 默认行为与当前完全一致（Python 3.11, ubuntu-latest, actions/checkout@v4）
- 现有用户无感升级

### R7: OpenCode 部署路径 CI 支持
MUST 在 `_deploy_opencode()` 中调用 `_deploy_ci()`，使 OpenCode 用户也能生成 CI 文件。
- CI 文件（`.github/workflows/pactkit.yml` / `.gitlab-ci.yml`）是项目级别文件，与 AI 工具格式无关
- `_deploy_opencode()` 应使用 `Path.cwd()` 作为 `project_root`，与 Classic 一致

### R8: pactkit.yaml 配置可见性
MUST 在 `generate_default_yaml()` 中输出完整的 CI 配置字段（含注释），使用户能发现并配置所有选项：
```yaml
# CI/CD — set provider to github or gitlab to generate pipeline config
ci:
  provider: none
  # runner: ubuntu-latest           # GitHub Actions runner label
  # language_version: "3.11"        # Language version for CI
  # github_host: ""                 # GHE server address (empty = github.com)
  # actions_ref: ""                 # GHE actions prefix (empty = default "actions/")
```

### R9: actions_ref 前缀替换
MUST 实现 `ci.actions_ref` 配置：
- 当 `actions_ref` 非空时，workflow 中所有 `actions/` 引用替换为 `{actions_ref}actions/`
- 例如：`actions_ref: "my-org/"` → `my-org/actions/checkout@v4`, `my-org/actions/setup-python@v5`
- 当 `actions_ref` 为空（默认），保持原样 `actions/checkout@v4`

## Acceptance Criteria

### AC1: Python stack CI（默认行为不变）
Given stack=python, ci.provider=github, 无额外配置
When 运行 `pactkit init`
Then 生成的 `.github/workflows/pactkit.yml` 与当前输出完全一致

### AC2: Node stack CI
Given stack=node, ci.provider=github
When 运行 `pactkit init`
Then 生成的 workflow 包含 `actions/setup-node@v5`、`npm ci`、`npx eslint .`、`npx jest`

### AC3: Go stack CI
Given stack=go, ci.provider=github
When 运行 `pactkit init`
Then 生成的 workflow 包含 `actions/setup-go@v5`、`go mod download`、`golangci-lint run`、`go test ./...`

### AC4: Java stack CI
Given stack=java, ci.provider=github
When 运行 `pactkit init`
Then 生成的 workflow 包含 `actions/setup-java@v4` (temurin)、`mvn dependency:resolve`、`mvn checkstyle:check`、`mvn test`

### AC5: 自定义 Language Version
Given stack=python, ci.language_version="3.12"
When 运行 `pactkit init`
Then workflow 中 python-version 为 "3.12"（而非默认 "3.11"）

### AC6: 自定义 Runner
Given ci.runner="self-hosted, linux"
When 运行 `pactkit init`
Then workflow 中 runs-on 为 "self-hosted, linux"

### AC7: GHE 注释提示
Given 项目 remote URL 为非 github.com host（或 ci.github_host 非空）
When 运行 `pactkit init`
Then workflow 顶部包含注释：`# NOTE: GHE detected — verify action availability on your instance`

### AC8: GitLab CI Stack-Aware
Given stack=node, ci.provider=gitlab
When 运行 `pactkit init`
Then `.gitlab-ci.yml` 使用 `node:20` image、`npm ci`、`npx eslint .`、`npx jest`

### AC9: CI 结果反馈（project-done 集成）
Given ci.provider=github, `gh` CLI 可用
When `/project-done` push 后
Then 输出包含 CI 状态信息（pass/fail/pending）

### AC10: 向后兼容
Given 现有 pactkit.yaml 无 ci.runner / ci.language_version / ci.actions_ref / ci.github_host
When 运行 `pactkit init`
Then 行为与升级前完全一致

### AC11: OpenCode CI 部署
Given format=opencode, ci.provider=github, stack=python
When 运行 `pactkit init --format opencode`
Then `.github/workflows/pactkit.yml` 被生成（与 Classic 格式输出一致）

### AC12: GHE 显式配置
Given ci.github_host="git.i.mercedes-benz.com"
When 运行 `pactkit init`
Then workflow 顶部包含 GHE 注释（无需依赖 git remote 自动检测）

### AC13: actions_ref 前缀替换
Given ci.actions_ref="my-org/"
When 运行 `pactkit init`
Then workflow 中 `actions/checkout@v4` 变为 `my-org/actions/checkout@v4`
And `actions/setup-python@v5` 变为 `my-org/actions/setup-python@v5`

### AC14: pactkit.yaml 可见性
Given 新项目首次运行 `pactkit init`
When 查看生成的 `pactkit.yaml`
Then CI 区域包含注释形式的完整配置字段（runner, language_version, github_host, actions_ref）

## Implementation Steps

| Step | File | Action | Done |
|------|------|--------|------|
| 1 | `src/pactkit/prompts/workflows.py` | 新增 CI_PROFILES dict | ✅ |
| 2 | `src/pactkit/generators/deployer.py` | 重构 `_deploy_ci()` — 参数化 + `_detect_ghe()` + `_build_github_workflow()` + `_build_gitlab_ci()` | ✅ |
| 3 | `src/pactkit/prompts/commands.py` | project-done Phase 4 增加 CI 状态检查步骤 | ✅ |
| 4 | `tests/unit/test_story_slim012_ci.py` | AC1-AC10 测试（39 tests） | ✅ |
| 5 | `src/pactkit/generators/deployer.py` | `_deploy_opencode()` 加 `_deploy_ci()` 调用（R7） | |
| 6 | `src/pactkit/generators/deployer.py` | `_build_github_workflow()` 实现 `actions_ref` 前缀替换（R9） | |
| 7 | `src/pactkit/generators/deployer.py` | `_build_github_workflow()` 读取 `ci.github_host` 触发 GHE 模式（R3） | |
| 8 | `src/pactkit/config.py` | `generate_default_yaml()` 输出完整 CI 字段注释（R8） | |
| 9 | `tests/unit/test_story_slim012_ci.py` | 新增 AC11-AC14 测试 | |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 | Yes | CI 模板中不得包含任何 secrets/tokens，敏感值通过 `${{ secrets.* }}` 引用 |
| SEC-2 | Low | pactkit.yaml 配置值注入到 YAML 模板中，需防止 YAML injection（runner/actions_ref/github_host 值需 sanitize） |
| SEC-3 | No | 不涉及数据库 |
| SEC-4 | No | 不涉及前端渲染 |
| SEC-5 | No | 不涉及认证 |
| SEC-6 | No | 不涉及 API 端点 |
| SEC-7 | No | 不涉及错误处理 |
| SEC-8 | No | 不涉及依赖变更 |

## Out of Scope

- CI 模板的可视化编辑器
- 多 job 矩阵（matrix strategy）支持
- Docker-based CI（Dockerfile 生成）
- CI secrets 管理
- 非 GitHub/GitLab 的 CI 平台（如 CircleCI, Jenkins）
- `gh` CLI 安装（假设用户已有）
