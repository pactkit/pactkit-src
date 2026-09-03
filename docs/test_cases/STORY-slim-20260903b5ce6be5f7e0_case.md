# Test Cases: STORY-slim-20260903b5ce6be5f7e0 — Guide 实践层(第一批)

> 实现位置:`tests/unit/test_story_20260903b5_practice_guides.py`(17 断言)。

## TC-1: Practice 段机制 (R1, AC1)

**Given** GuideDefinition(practice=表格文本) / practice=""
**When** render()
**Then** 非空:Defaults 后出现 `## Practice` 且表格 verbatim(无 bullet 前缀);为空:无该段;22 个旧 guide 渲染不变
**Impl** `TestPracticeMechanism::*`

## TC-2: observability 日志管理锚点 (R2, AC2)

**Given** 渲染后的 observability.md
**When** 检查 Practice
**Then** ERROR/WARN/INFO/DEBUG 四级别各就位;correlation+snake_case/event= 约定;loop 禁打+redaction 红线;log-and-rethrow 反模式
**Impl** `TestObservabilityPractice::*`

## TC-3: module-design 拆分判据锚点 (R3, AC3)

**Given** 渲染后的 module-design.md
**When** 检查 Practice
**Then** single-sentence responsibility 测试、500 行评估线、domain/infrastructure 分层、circular=违规、premature abstraction 判别
**Impl** `TestModuleDesignPractice::*`

## TC-4: error-recovery 错误分类学锚点 (R4, AC4)

**Given** 渲染后的 error-recovery.md
**When** 检查 Practice
**Then** transient/permanent/programming 三分类、user-facing/log 分离、backoff+idempoten 边界、recovery strateg 分类
**Impl** `TestErrorRecoveryPractice::*`

## TC-5: 结构与体量纪律 (R5, AC5)

**Given** 全部 23 个 guide
**When** 七段测试+50 行预算测试运行
**Then** 七段必需段全在;三个富化 guide ≤50 行;Practice 内容 verbatim 无变形
**Impl** `TestSevenSectionStructureExtended::*` + 存量 `test_each_guide_under_50_lines`
