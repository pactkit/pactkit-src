# Test Cases: STORY-slim-143 — Spec Dependency Surface & Story DAG (spec-graph)

## TC-1: Scaffolded spec carries Dependency Surface (AC1)

- **Given** pactkit 项目已初始化且新 schema 已部署
- **When** 运行 `scaffold.py create_spec "STORY-x-999" "demo"`
- **Then** 生成的 Spec 含 `## Dependency Surface` 及全部四个字段（Depends on / Provides / Touches / Conflict risk），且 `pactkit spec-lint` 无 E010/W011

## TC-2: Dangling dependency rejected (AC2)

- **Given** 某 Spec 的 Depends on 引用不存在的 `STORY-slim-999`
- **When** 运行 `pactkit spec-lint`
- **Then** 报告 E010（含该 ID）并以非零码退出

## TC-3: Missing section is a warning (AC3)

- **Given** 一个无 `## Dependency Surface` 的旧 Spec（其余部分合法）
- **When** 运行 `pactkit spec-lint`
- **Then** 报告 W011 但整体 PASS，既有规则不受影响

## TC-4: Waves and conflict matrix (AC4)

- **Given** A（Depends on: None, Touches: `a.py`）、B（Depends on: A, Touches: `b.py`）、C（Depends on: None, Touches: `a.py`）
- **When** 运行 `pactkit spec-graph`
- **Then** wave 1 = {A, C}、wave 2 = {B}，且 A↔C 被标记为同 wave 文件冲突（unsafe-parallel）

## TC-5: Cycle detection (AC5)

- **Given** 两个互相依赖的 Spec
- **When** 运行 `pactkit spec-graph`
- **Then** 以非零码退出并输出 cycle 路径

## TC-6: Deterministic output (AC6)

- **Given** 任意固定 Spec 集合
- **When** `pactkit spec-graph` 连续运行两次
- **Then** wave 列表与冲突矩阵字节一致

## TC-7: Plan playbook documents the step (AC7)

- **Given** 更新后的 project-plan 命令内容
- **When** 阅读 Phase 3.2a
- **Then** 存在 Dependency Surface 填写指引，且包含 E010 与 `pactkit spec-graph` 引用
