# Test Case: STORY-slim-141 — Deployment manifest content hash verification

> Spec: docs/specs/STORY-slim-141.md
> Unit tests: tests/unit/test_story_slim141_manifest_hash.py (11 tests)

## AC1: 部署后 manifest 包含逐文件 hash (R1, R5)

```gherkin
Given 一个干净的 deploy target 目录
When 执行 pactkit init 部署 classic format
Then .pactkit-deployed.json 含 "files" 字段
And 覆盖 skills/commands/agents/managed rules 的落盘文件
And 每个值为 64 位小写 hex sha256
And 不含 CLAUDE.md / .pactkit-version / .pactkit-deployed.json
```
Verified by: TestManifestFiles::test_write_includes_files_hash, test_hash_is_sha256_hex, test_manifest_keys_are_posix

## AC2: 内容漂移被 doctor 检出 (R2)

```gherkin
Given 已完成部署且 manifest 含 "files"
When 篡改 rules/pactkit.md 后运行 parity 检查
Then drift 为 True 且 details 包含该文件路径
And 退出码语义为 NEEDS ATTENTION（drift → doctor exit 1，由 slim-139 测试覆盖 wiring）
```
Verified by: TestContentParity::test_content_drift_detected, test_multi_drift_no_short_circuit

## AC3: 未漂移时 doctor 不误报 (R2, R4)

```gherkin
Given 部署后未改动任何 pactkit 文件
When 仅在 CLAUDE.md 末尾追加用户内容并运行 parity 检查
Then drift 为 False，无 Content drift 输出
```
Verified by: TestContentParity::test_no_false_positive_on_excluded_append

## AC4: 旧版 manifest 降级为 warning (R3)

```gherkin
Given 一个不含 "files" 字段的 pre-2.18 manifest
When 运行 parity 检查
Then drift 为 False
And warnings 包含 "content verification" 提示
```
Verified by: TestContentParity::test_old_manifest_without_files_warns

## AC5: 声明文件在磁盘缺失被检出 (R2)

```gherkin
Given 部署完成且 manifest 含 "files"
When 删除 manifest 声明的 skills/pactkit-board/SKILL.md
Then drift 为 True 且 details 包含 "missing on disk"
```
Verified by: TestContentParity::test_missing_declared_file_detected

## AC6: adapter 签名兼容 (R1)

```gherkin
Given 现有 write_deploy_manifest(deploy_root, format_name, config) 调用方
When 本 Story 完成后以位置参数调用
Then 函数签名不变，返回 manifest Path 且 payload 含 files 字段
```
Verified by: TestManifestFiles::test_signature_unchanged

## SEC-7 补充场景（评审后新增）

```gherkin
Given manifest 声明的文件被 chmod 0（不可读）
When 运行 parity 检查
Then 降级为 warning（"unreadable"），不 crash，drift 不受影响

Given manifest 的 "files" 字段类型损坏（list 而非 dict）
When 运行 parity 检查
Then 降级为 warning（"corrupt"），不 crash
```
Verified by: test_unreadable_file_warns_not_crashes, test_corrupt_files_field_warns_not_crashes
