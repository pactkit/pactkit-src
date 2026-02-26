# STORY-047: Enterprise Configuration Flags

| Field     | Value |
|-----------|-------|
| ID        | STORY-047 |
| Status    | Draft |
| Priority  | Low |
| Release   | 1.4.0 |
| Author    | System Architect |
| Source    | Gap Analysis: SpecKit enterprise flags |

## Background

SpecKit 提供企业环境配置选项：`--no-git`, `--no-tls`, `--github-token`, `--debug`。PactKit 当前假设开发者在标准 git 环境下工作，无法适应企业场景的特殊约束：

- **Air-gapped 环境**：无法访问外部 npm/pip registry，MCP 服务不可用
- **TLS inspection**：企业代理可能导致 HTTPS 证书验证失败
- **CI/CD 集成**：无交互式终端，需要非交互模式
- **权限受限**：无法执行 git push、gh CLI、或文件系统写入到特定路径

## Requirements

### R1: pactkit.yaml Enterprise Section (MUST)

在 `pactkit.yaml` 中新增 `enterprise` section：
```yaml
enterprise:
  no_git: false          # 禁用所有 git 操作
  no_external: false     # 禁用外部网络访问（MCP, gh CLI, pip install）
  non_interactive: false # 非交互模式（CI/CD 场景，自动接受默认值）
  debug: false           # 详细日志输出
```

### R2: CLI Flag Override (MUST)

支持命令行 flag 覆盖 yaml 配置：
```bash
pactkit init --no-git
pactkit update --no-external --non-interactive
```

CLI flags 优先级高于 yaml 配置。

### R3: Command Playbook 条件逻辑 (MUST)

所有涉及 git/external 的 playbook 步骤必须检查 enterprise flags：
- `no_git: true` → 跳过所有 git 操作（commit, push, branch, tag）
- `no_external: true` → 跳过 MCP 调用、gh CLI、外部包安装
- `non_interactive: true` → 所有确认步骤自动选择默认值

### R4: 优雅降级 (MUST)

当 enterprise flag 导致某个步骤被跳过时：
- 输出 INFO 级别日志说明跳过原因
- 不输出 ERROR 或 WARNING（这是配置行为，不是异常）

## Acceptance Criteria

### AC1: no_git 模式
**Given** `pactkit.yaml` 设置 `enterprise.no_git: true`
**When** 执行 `/project-done`
**Then** Phase 4 (Git Commit) 被跳过
**And** 输出 "ℹ️ Git operations disabled (enterprise.no_git)"

### AC2: CLI Flag 覆盖
**Given** `pactkit.yaml` 设置 `enterprise.no_git: false`
**When** 运行 `pactkit init --no-git`
**Then** git 操作被跳过（CLI flag 生效）

### AC3: 非交互模式
**Given** `enterprise.non_interactive: true`
**When** 任何 command 遇到需要用户确认的步骤
**Then** 自动选择默认值
**And** 输出选择日志

## Out of Scope

- SSO/SAML 集成
- 审计日志持久化
- 企业 license 管理
- 自定义 proxy 配置（可通过标准环境变量 `HTTP_PROXY` 处理）
