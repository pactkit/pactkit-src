# Test Cases: STORY-slim-202609037a7d4be200e7 — Guide 实践层第二批

> 实现位置:`tests/unit/test_story_202609037a_practice_batch2.py`(62 断言)。

## TC-1: API 域锚点 (R1)

**Given** 渲染后的 api-integration / event-driven / backwards-compatibility
**When** 参数化锚点检查
**Then** api-integration 含 cursor/idempotency key/error code/version;event-driven 含 at-least-once/dead-letter/idempotent;backwards-compatibility 含 deprecat/dual-write/enum
**Impl** `test_guide_practice_anchors[api-integration.md]` 等三个参数化用例

## TC-2: 数据域锚点 (R2)

**Given** 渲染后的 database / caching / data-consistency
**When** 参数化锚点检查
**Then** database 含 expansion/rollback/external call;caching 含 TTL/stampede/invalidation;data-consistency 含 eventual/compensat/optimistic
**Impl** `test_guide_practice_anchors[database.md]` 等三个参数化用例

## TC-3: 并发域锚点 (R3)

**Given** 渲染后的六个并发/运行时域 guide
**When** 参数化锚点检查
**Then** concurrency 含 I/O-bound/bounded/message passing;async-patterns 含 block/cancel/timeout;memory-management 含 generator/bound/stream;performance-antipatterns 含 measure/N+1/premature;resilience 含 circuit breaker/bulkhead/degrad;graceful-shutdown 含 SIGTERM/drain/kill
**Impl** `test_guide_practice_anchors[concurrency.md]` 等六个参数化用例

## TC-4: 质量域锚点 (R4)

**Given** 渲染后的 testing-strategy / code-review-first / component-reuse
**When** 参数化锚点检查
**Then** testing-strategy 含 pyramid/flaky/factory;code-review-first 含 correctness/self-review/justify;component-reuse 含 stdlib/wrapper/grep
**Impl** `test_guide_practice_anchors[testing-strategy.md]` 等三个参数化用例

## TC-5: 运维域锚点 (R5)

**Given** 渲染后的 configuration / operational-readiness / dependency-supply-chain / write-safety / ui-state-accessibility
**When** 参数化锚点检查
**Then** configuration 含 layer/fail-fast/redact;operational-readiness 含 liveness/readiness/rollback;dependency-supply-chain 含 lockfile/license/transitive;write-safety 含 manifest/candidate/did not generate;ui 含 loading/focus/contrast
**Impl** `test_guide_practice_anchors[configuration.md]` 等五个参数化用例

## TC-6: 全量覆盖与体量纪律 (R6)

**Given** GUIDE_DEFINITIONS 全部 23 个条目
**When** 全量 practice 检查 + 50 行预算测试 + verbatim 渲染检查
**Then** 23/23 有 practice;全部 ≤50 行(存量预算测试零改动);practice 原样渲染无变形;每 guide 至少一个判据表或红线
**Impl** `test_all_23_guides_have_practice_after_batch2` / `test_guide_practice_has_table_or_redline[*]` / `test_guide_practice_renders_verbatim[*]` + 存量 `test_each_guide_under_50_lines`
