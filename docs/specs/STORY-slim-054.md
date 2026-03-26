# STORY-slim-054: Core library robustness: deployer.py template injection, config.py race conditions, profiles.py validation gaps

| Field | Value |
|-------|-------|
| ID | STORY-slim-054 |
| Status | Done |
| Priority | P1 |
| Release | 2.4.1 |

## Background

STORY-slim-053 修复了 visualize.py 中的潜伏 bug，本故事对核心库模块进行相同深度的审计。通过逐行阅读 `deployer.py`、`config.py`、`profiles.py` 和 `utils.py` 的实际代码，发现了以下 **3 个真实潜伏 bug**：

| Bug | 文件 | 触发条件 | 后果 |
|-----|------|---------|------|
| R1 `_rewrite_yaml` 非原子写 | `config.py` L707 | 进程在写入中途被中断 (kill -9, crash, disk full) | pactkit.yaml 被截断/损坏，用户配置丢失 |
| R2 `_deploy_ci` 变异调用方 dict | `deployer.py` L1067 | 同一 config dict 被传入多次（测试隔离、多步部署） | `_ghe_override` key 被消费后消失，第二次调用行为不一致 |
| R3 `atomic_write` .tmp 文件残留 | `utils.py` L6-8 | `tmp.write_text()` 成功但后续步骤抛异常 | 同目录下留下同名 `.tmp` 文件，下次部署时静默覆盖而非报错 |

**为什么必须现在修**：
- `_rewrite_yaml` 是 `auto_merge_config_file` 的唯一写入路径，每次 `pactkit deploy` 都会调用；磁盘满场景（CI/CD 环境）下必然触发 R1
- R2 已在多个测试中观察到隔离问题（`_ghe_override` 在 `_deploy_ci` 调用后从 config 消失，影响后续断言）
- `profiles.py` 经审计**没有发现真实 bug**（frozen dataclass + 明确 ValueError 防御，设计健壮）——不新增 requirement

## Requirements

### R1: Make `_rewrite_yaml` write atomically (MUST)

**当前代码（`config.py` L707）**：
```python
path.write_text("\n".join(lines), encoding="utf-8")
```

**问题**：`_rewrite_yaml` 是 `auto_merge_config_file` 的唯一写入路径，且是对 `pactkit.yaml` 的 **全量覆盖写**。如果进程在写入中途被中断（`kill -9`、磁盘满、CI 超时），文件内容会被截断，用户配置永久丢失。

相比之下，`deployer.py` 中所有文件写入都通过 `utils.atomic_write()` 完成（先写 `.tmp`，再 `os.replace()`），唯独 `config.py` 中的 `_rewrite_yaml` 遗漏了这一保护。

**修复方案**：将 `_rewrite_yaml` 的写入改为通过 `atomic_write(path, "\n".join(lines))`。由于 `config.py` 目前未导入 `atomic_write`，需要添加 import（`from pactkit.utils import atomic_write`）或内联实现等价逻辑：
```python
# 修复后
tmp = path.with_suffix(".tmp")
tmp.write_text("\n".join(lines), encoding="utf-8")
os.replace(tmp, path)
```

**影响范围**：仅 `config.py` 的 `_rewrite_yaml` L707（1 行变更 + 1 行 import）。`auto_merge_config_file` 和其所有调用方行为不变。

**验证方法**：测试中模拟写入中途异常（mock `os.replace` 抛出 `OSError`），验证原始文件完整保留；验证正常路径下 `.tmp` 文件在写入完成后不存在。

### R2: Fix `_deploy_ci` mutating caller's config dict (MUST)

**当前代码（`deployer.py` L1067）**：
```python
def _deploy_ci(provider, project_root, config):
    ...
    ci_config = config.get("ci", {})
    if not isinstance(ci_config, dict):
        ci_config = {}

    # GHE detection priority: _ghe_override (testing) > github_host (explicit) > auto-detect
    is_ghe = ci_config.pop("_ghe_override", None)   # ← 变异！
```

**问题**：`ci_config` 是 `config["ci"]` 的直接引用（Python dict 引用语义）。调用 `ci_config.pop("_ghe_override", None)` 会**永久修改**调用方的 `config["ci"]` dict，移除 `_ghe_override` key。后果：

1. **测试隔离破坏**：如果测试用 `config = {"ci": {"_ghe_override": True, ...}}` 调用 `_deploy_ci` 两次，第二次 `_ghe_override` 已消失，`is_ghe` 会走 auto-detect 分支，导致意外行为
2. **多步部署**：在同一次 deploy session 中多次调用 `_deploy_ci`（如 classic + opencode 双部署），第一次调用后 `_ghe_override` 被消费

**修复方案**：将 `pop()` 改为 `get()` + 本地变量删除，或先 `copy()` ci_config：
```python
# 修复方案 A（推荐）：不从原 dict 删除，仅读取
is_ghe = ci_config.get("_ghe_override")   # 读取但不删除
# 修复方案 B：浅拷贝后操作
ci_config = dict(ci_config)               # 拷贝，不影响原始 config
is_ghe = ci_config.pop("_ghe_override", None)
```

推荐方案 A，因为 `_ghe_override` 是内部测试 key，调用方不需要感知它被"消费"。

**影响范围**：`deployer.py` `_deploy_ci` L1067（1 行变更）。

**验证方法**：测试用同一个 config dict 连续调用 `_deploy_ci` 两次，验证第二次调用中 `config["ci"]` 仍包含 `_ghe_override` key；验证功能行为（GHE 检测结果）不变。

### R3: Clean up `.tmp` file on `atomic_write` failure (SHOULD)

**当前代码（`utils.py` L4-9）**：
```python
def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(content, encoding='utf-8')  # 成功
    os.replace(tmp, path)                       # 若此处失败 → .tmp 残留
    print(f'   -> Wrote {path.name}')
```

**问题**：若 `os.replace(tmp, path)` 抛出异常（跨设备移动、权限不足、目标是目录），`.tmp` 文件已存在且包含完整内容，但不会被清理。再次运行时同名 `.tmp` 文件被静默覆盖，不会触发任何告警。在批量部署 50+ 文件时（skills + agents + commands + rules），一次中途失败会在目录中留下多个 `.tmp` 残留文件。

**修复方案**：添加 `try/finally` 清理块：
```python
def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    try:
        tmp.write_text(content, encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    print(f'   -> Wrote {path.name}')
```

**影响范围**：`utils.py` `atomic_write`（4 行变更）。所有调用 `atomic_write` 的代码（deployer.py 中约 40 处调用）行为在正常路径下不变；仅异常路径有额外清理。

**验证方法**：mock `os.replace` 抛出 `OSError`，验证 `.tmp` 文件不残留（不存在于文件系统）；验证原始文件（若已存在）保持完整；验证异常被重新抛出（不吞掉）。

## Acceptance Criteria

### AC1: pactkit.yaml 写入失败时原文件保持完整 (R1)

- **Given** `pactkit.yaml` 存在且包含有效配置
- **When** `_rewrite_yaml` 在写入 `.tmp` 文件后调用 `os.replace()` 时抛出 `OSError`（mock 注入）
- **Then** 原始 `pactkit.yaml` 文件内容保持完整（未被截断），且 `.tmp` 文件不存在于目标目录

### AC2: _rewrite_yaml 正常路径产生原子写入 (R1)

- **Given** 一个合法的 pactkit.yaml 路径（文件存在或不存在）
- **When** `_rewrite_yaml(path, data)` 成功执行
- **Then** 目标文件被写入完整内容，且同目录下不存在 `{stem}.tmp` 文件

### AC3: 同一 config dict 可被 `_deploy_ci` 调用两次 (R2)

- **Given** `config = {"ci": {"provider": "github", "_ghe_override": True}, ...}`
- **When** `_deploy_ci("github", project_root, config)` 被调用两次（同一 config dict 实例）
- **Then** 两次调用后 `config["ci"]["_ghe_override"]` 仍为 `True`，且两次调用均使用 GHE 模式（而非第二次 fallback 到 auto-detect）

### AC4: atomic_write 异常时不残留 .tmp 文件 (R3)

- **Given** `atomic_write(path, content)` 被调用，写入目标目录存在
- **When** `os.replace` 抛出 `OSError`（mock 注入）
- **Then** `.tmp` 临时文件不存在于文件系统，且 `OSError` 被重新抛出（不被吞掉）

### AC5: atomic_write 正常路径行为不变 (R3)

- **Given** 任意有效路径和内容
- **When** `atomic_write` 成功执行
- **Then** 目标文件包含正确内容，不存在 `.tmp` 残留，行为与修改前完全一致

## Target Call Chain

```
R1: auto_merge_config_file(path) [config.py L405]
    → _rewrite_yaml(path, user_data) [config.py L485]
        → path.write_text(...) [config.py L707]  ← 非原子写，需换为 atomic pattern

R2: deploy() → _deploy_classic() / _deploy_opencode() [deployer.py L190/L355]
    → _deploy_ci(ci_provider, project_root, config) [deployer.py L1045]
        → ci_config = config.get("ci", {})       [deployer.py L1062]
        → ci_config.pop("_ghe_override", None)   [deployer.py L1067] ← 变异 config["ci"]

R3: (所有 deployer.py 中的) atomic_write(path, content) [utils.py L4]
    → tmp.write_text(content, encoding='utf-8') [utils.py L7]
    → os.replace(tmp, path) [utils.py L8]       ← 失败时 .tmp 残留

profiles.py — 审计结论: 无发现。frozen dataclass 防止字段缺失；
    get_profile() 明确抛出 ValueError；is_environment_format() 防御性检查。
    无需修改。
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `src/pactkit/utils.py` | 在 `atomic_write` 中添加 `try/finally` 清理 `.tmp` 文件 | None | Low |
| 2 | `src/pactkit/config.py` | 添加 `import os` 和原子写逻辑（或 `from pactkit.utils import atomic_write`），替换 `_rewrite_yaml` 末行 `path.write_text(...)` | Step 1 | Low |
| 3 | `src/pactkit/generators/deployer.py` | 将 `ci_config.pop("_ghe_override", None)` 改为 `ci_config.get("_ghe_override")` | None | Low |
| 4 | `tests/unit/test_utils.py` | 新增 R3 测试：mock `os.replace` 抛出异常，断言 `.tmp` 不残留 | Step 1 | Low |
| 5 | `tests/unit/test_config.py` | 新增 R1 测试：mock `os.replace` 抛出异常，验证原文件保持完整 | Step 2 | Low |
| 6 | `tests/unit/test_deployer.py` | 新增 R2 测试：同一 config dict 调用 `_deploy_ci` 两次，验证 `_ghe_override` 不被消费 | Step 3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input Validation | N/A | R1/R3 不涉及用户输入注入；`_render_prompt` 已使用安全的 `str.replace()` 方案（非 `str.format_map()`） |
| SEC-2 Path Traversal | Yes | R1 修复后 `_rewrite_yaml` 写入路径仍与修复前相同，不引入新的路径；R3 `.tmp` 路径由 `path.with_suffix('.tmp')` 派生，不受用户控制 |
| SEC-3 Secret Leakage | N/A | `pactkit.yaml` 不包含密钥；`atomic_write` 写入的是配置/提示文本 |
| SEC-4 Command Injection | N/A | 无 shell 命令执行在受影响路径 |
| SEC-5 Dependency | N/A | 仅使用 stdlib `os`，无新第三方依赖 |
| SEC-6 Auth/AuthZ | N/A | 无认证/授权逻辑变更 |
| SEC-7 Data Integrity | Yes | R1 直接修复数据完整性风险：pactkit.yaml 被截断 = 用户配置数据丢失 |
| SEC-8 Logging | N/A | `atomic_write` 的 `print(f'   -> Wrote {path.name}')` 保持不变 |

## Out of Scope

- `profiles.py` 的修改——审计确认该模块设计健壮，无需修改
- `_render_prompt` 的模板注入问题——已通过 `str.replace()` 方案正确实现（Architecture Principle #7），无问题
- `deployer.py` hook 模板的 `str.format()` 调用——`lint_command` 来源于 `LANG_PROFILES`（硬编码，非用户输入），不含 `{}`，不是真实 latent bug
- skill 脚本（board.py, scaffold.py, spec_linter.py, visualize.py）的加固——由 STORY-slim-052 和 STORY-slim-053 覆盖
- 文件 I/O 的并发安全（多线程/多进程同时写同一文件）——超出当前 PactKit CLI 的使用场景
- E2E 测试覆盖扩展——由 STORY-slim-056 覆盖
- `config.py` 中 `validate_config` 使用 `warnings.warn()` 的设计——这是有意为之（warn but not raise），不是 bug
