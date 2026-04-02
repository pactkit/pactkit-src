# STORY-049: GitHub Community Standards — Security Policy, Code of Conduct & Dependabot

| Field     | Value |
|-----------|-------|
| ID        | STORY-049 |
| Status    | Draft |
| Priority  | Low |
| Release   | 1.4.0 |
| Author    | System Architect |
| Source    | User Request: GitHub Community Standards 缺失 SECURITY.md、CODE_OF_CONDUCT.md、Dependabot |

## Background

PactKit 已开源并在 GitHub 上开放了 Community（Issues + Discussions）。当前 Community Profile health 为 75%，缺少两个 GitHub 推荐的标准文件：

1. **Security Policy** (`SECURITY.md`) — 告知用户如何报告安全漏洞
2. **Code of Conduct** (`CODE_OF_CONDUCT.md`) — 社区行为准则

GitHub 的 Community Standards 检查会自动检测这两个文件。补齐后 health 预期达到 100%。

此外，`CONTRIBUTING.md` 中的 Code of Conduct 部分目前只有一句话 "Be respectful, constructive, and collaborative"，应更新为指向独立的 CODE_OF_CONDUCT.md 文件。

另外，GitHub Dependency Graph 提示 "Dependabot version updates aren't configured yet"。PactKit 的依赖有两个生态系统需要监控：

1. **pip** (Python 包)：runtime `pyyaml>=6.0`，dev `pytest`、`ruff`、`hatchling`
2. **github-actions**：`actions/checkout@v4`、`actions/setup-python@v5` 等 CI action 版本

配置 Dependabot 可以自动创建 PR 来升级过时依赖，与已有的 CI workflow 配合确保升级安全。

## Requirements

### R1: CODE_OF_CONDUCT.md (MUST)

在项目根目录创建 `CODE_OF_CONDUCT.md`，采用 Contributor Covenant v2.1 标准：

- MUST 包含标准的 Contributor Covenant v2.1 全文
- MUST 在 Enforcement 部分使用 GitHub 推荐的联系方式
- MUST 被 GitHub 自动识别为有效的 Code of Conduct（GitHub 官方支持 Contributor Covenant 格式自动检测）

### R2: SECURITY.md (MUST)

在项目根目录创建 `SECURITY.md`，包含以下 sections：

1. **Supported Versions** — 列出当前受支持的版本范围（当前最新 release）
2. **Reporting a Vulnerability** — 指引用户通过 GitHub Security Advisory 私密报告漏洞
3. **Scope** — 说明 PactKit 的安全关注范围（供应链依赖、prompt injection 防护、部署文件安全）
4. **Disclosure Policy** — 说明漏洞披露时间线和流程

MUST NOT 包含个人邮箱地址——使用 GitHub Security Advisory 作为唯一的漏洞报告渠道。

### R3: CONTRIBUTING.md 更新 (SHOULD)

更新 `CONTRIBUTING.md` 的 "Code of Conduct" section，添加指向 `CODE_OF_CONDUCT.md` 的链接。

### R4: Dependabot 配置 (MUST)

在 `.github/dependabot.yml` 创建 Dependabot 配置，监控两个生态系统：

1. **pip** (package-ecosystem: "pip")
   - 目录: "/" (根据 `pyproject.toml` 位置)
   - 检查频率: weekly
   - target-branch: main

2. **github-actions** (package-ecosystem: "github-actions")
   - 目录: "/"
   - 检查频率: weekly
   - target-branch: main

配置 SHOULD 设置合理的 PR 数量限制（`open-pull-requests-limit`），避免一次性产生过多 PR。

## Acceptance Criteria

### AC1: GitHub 自动识别 Code of Conduct
**Given** CODE_OF_CONDUCT.md 已提交到 main 分支
**When** 查看 GitHub Community Profile
**Then** code_of_conduct 字段不为 null
**And** Community health 提升

### AC2: GitHub 自动识别 Security Policy
**Given** SECURITY.md 已提交到 main 分支
**When** 查看 GitHub Community Profile
**Then** security 字段不为 null
**And** Community health 提升至 100%

### AC3: Security Policy 不含个人信息
**Given** SECURITY.md 内容
**When** 检查文件内容
**Then** 不包含任何个人邮箱地址
**And** 漏洞报告指向 GitHub Security Advisory

### AC4: CONTRIBUTING.md 引用 Code of Conduct
**Given** CONTRIBUTING.md 已更新
**When** 查看 Code of Conduct section
**Then** 包含指向 CODE_OF_CONDUCT.md 的链接

### AC5: Dependabot 配置生效
**Given** `.github/dependabot.yml` 已提交到 main 分支
**When** 查看 GitHub Dependency Graph 页面
**Then** Dependabot 提示消失
**And** Dependabot 开始按 weekly 频率检查依赖更新

### AC6: Dependabot 覆盖双生态
**Given** dependabot.yml 内容
**When** 解析配置
**Then** 包含 `pip` 和 `github-actions` 两个 package-ecosystem 条目

## Out of Scope

- GitHub Discussions 的 category 配置
- Dependabot security alerts 配置（GitHub 默认启用，无需额外配置）
- 自定义 Dependabot auto-merge workflow
