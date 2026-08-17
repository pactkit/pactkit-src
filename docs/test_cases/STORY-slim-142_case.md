# Test Case: STORY-slim-142 — deploy format=all with target skips adapters + adapter skew guard

> Spec: docs/specs/STORY-slim-142.md
> Unit tests: tests/unit/test_story_slim142_all_target_isolation.py (6 tests)

## AC1: target 模式跳过 adapter (R1)

```gherkin
Given registry 中含 classic + opencode（spy deployer）
When 调用 deploy(format="all", target=tmp_path)
Then classic 以 target=tmp_path 调用
And adapter deploy() 从未被调用
And 输出含 "Skipping adapter formats (opencode): -t target only applies to classic"
```
Verified by: TestAllTargetSkipsAdapters::test_adapter_not_called_when_target_given

## AC2: 真实 init 行为不变 (R1, R4)

```gherkin
Given 同上 spy registry
When 调用 deploy(format="all", target=None)
Then classic 与 opencode 均以 target=None 被调用（各自部署到默认目录）
```
Verified by: TestAllTargetSkipsAdapters::test_adapter_called_when_no_target

## AC3: 全量套件自洁 (R1, R2, R4)

```gherkin
Given opencode 部署处于干净状态（doctor 无 content drift）
When 连续运行两次全量 pytest tests/unit/
Then 两次均全绿（4120 passed）
And 两次运行之间 opencode manifest 与磁盘零漂移
And test_story_slim056.py::TestDoctorCommand::test_doctor_runs 独立运行通过
```
Verified by: 2026-08-17 Act Phase 3 实测（双跑 + drift check NONE + 单测独立通过）

## AC4: adapter 版本偏斜 warning (R3)

```gherkin
Given 安装的 pactkit-opencode 为 2.9.1 而 core 为 2.17.0
When 调用 check_adapter_skew()
Then 返回含包名、双版本号与 pipx inject 升级提示的 warning
And adapter 版本与 core 一致时静默（空列表）
And adapter 未安装 / 元数据缺失时静默不 crash（SEC-7）
```
Verified by: TestAdapterSkew 4 tests（outdated/current/missing/no-entry-points）
