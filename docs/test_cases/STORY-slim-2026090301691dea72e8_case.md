# Test Cases: STORY-slim-2026090301691dea72e8 — 规则遵循率实证修复

> 实现位置:`tests/unit/test_story_2026090301_rule_compliance.py`(W012 用真实
> validate_spec + tmp_path fixture specs;契约/playbook 用内容断言;adapter
> parity 用 FORMAT_PROFILES × `_render_prompt` 全格式渲染断言)。

## TC-1: W012 触发——依赖信号 + 缺子节 (R1, AC1)

**Given** Spec 含 `## Technical Design` 节,节内文本出现 `pyproject.toml`
**When** `pactkit spec-lint <spec>`(`validate_spec`)
**Then** warnings 含 W012,且 `LintResult.passed == True`(W 级非阻塞)
**And** 大小写不敏感:`FastAPI Framework` 同样触发
**Impl** `TestW012CapabilityAssessment::test_w012_fires_on_dependency_signal_without_subsection` / `test_w012_case_insensitive_framework_signal`

## TC-2: W012 不误报 (R1, AC2)

**Given** Technical Design 无依赖信号(纯内部逻辑),或已含 `### Capability Assessment` 子节,或 Spec 无 Technical Design 节
**When** `validate_spec`
**Then** 无 W012
**And** 已知局限(测试注释记录):否定句 "no frameworks involved" 含关键词仍触发——关键词门无法解析否定,这正是 W 级(非 E 级)的设计原因
**Impl** `test_w012_silent_without_dependency_signal` / `test_w012_silent_when_subsection_present` / `test_w012_silent_without_technical_design_section`

## TC-3: Plan playbook 域材料声明步骤 (R2, AC3)

**Given** 渲染后的 `COMMANDS_CONTENT["project-plan.md"]`
**When** 检查 Phase 2 文本
**Then** 含 Domain Material Declaration MUST 步骤且引用 `## Implementation Inputs` 与 spec-preflight 加载链路
**And** 四 adapter 格式渲染后步骤仍在(parity)
**Impl** `TestPlaybookSteps::test_plan_playbook_requires_domain_material_declaration` / `TestAdapterParity::test_plan_domain_step_renders_across_formats`

## TC-4: Check 契约三条验证语义 (R3, R4, AC4)

**Given** `PHASE_CONTRACTS["project-check"]`
**When** 检查 invariants 与 completion evidence
**Then** invariants 同时含 setup 对齐("actor")、环境同源("provenance"/"running code")、defect-class sweep("sweeps its class")
**And** 渲染后的 `PHASE_RULE_CONTENTS["phase-check"]` 同样含三条语义
**And** done 契约 evidence 的 "adequate" 含 actor 与 environment 维度
**Impl** `TestCheckContractVerificationSemantics::test_check_invariants_carry_three_semantics` / `test_check_completion_evidence_requires_provenance` / `test_done_evidence_adequate_covers_actor_and_environment` / `test_rendered_phase_check_contract_contains_semantics`

## TC-5: Check playbook 反模式与 sweep 步骤 (R3, R4, AC5)

**Given** 渲染后的 `COMMANDS_CONTENT["project-check.md"]`
**When** 检查 Phase 2 / 3.5 / 4
**Then** Phase 2 含 Defect-class sweep(MUST),Phase 3.5 含 Setup-actor mismatch(P1 反模式),Phase 4 含 Environment provenance(MUST)
**And** 四 adapter 渲染后三语义均存活
**Impl** `test_check_playbook_phase2_has_defect_class_sweep` / `test_check_playbook_phase35_has_setup_actor_mismatch` / `test_check_playbook_phase4_has_environment_provenance` / `TestAdapterParity::test_check_semantics_render_identically_across_formats`
