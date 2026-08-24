# Test Cases: STORY-slim-20260823d854b0cf1875 — Portable Methods 与宿主能力分层工作流架构

> Spec: `docs/specs/STORY-slim-20260823d854b0cf1875.md`
> Core tests: `tests/unit/test_story_slim_work_units.py` and `tests/e2e/cli/test_cli_e2e.py`
> Codex adapter tests: `../pactkit-codex/tests/unit/test_story015_work_units.py` and `../pactkit-codex/tests/unit/test_story016_app_server_bridge.py`

## TC-1: Core is the only workflow authority (R1, AC1)

- **Given** a leased Plan WorkUnit and a Codex turn that reaches a terminal event
- **When** the adapter records that terminal event without an accepted Receipt
- **Then** the attempt is recorded with its Unit/version and opaque thread/turn references, while the WorkflowRun remains running
- **And** only `WorkflowEngine.submit()` can advance the current WorkUnit

Verified by: `test_receipt_is_reverified_and_agent_final_does_not_complete_run`, `test_terminal_attempt_rejects_non_serializable_or_invalid_host_metadata`, `test_terminal_attempt_rejects_invalid_terminal_status_before_state_changes`, `test_terminal_attempt_rejects_boolean_unit_version_before_state_changes`, `test_corrupt_attempt_record_fails_closed_before_transition`, `test_work_unit_adapter_acquires_core_unit_and_records_turn_terminal`.

## TC-2: WorkUnit lease and transition boundaries are enforced (R2, AC2)

- **Given** a versioned WorkUnit with an owner and a finite lease
- **When** another owner, an expired lease, an out-of-scope write, or a reused conflicting idempotency key is submitted
- **Then** Core rejects the operation with a stable reason code and preserves the authoritative run state

Verified by: `test_work_unit_lease_owner_expiry_and_idempotent_submit`, `test_explicit_reject_expire_retry_and_write_scope`, `test_malformed_candidate_receipt_is_audited_and_recoverable`, `test_submit_idempotency_cannot_replay_across_units`, `test_acquire_and_retry_idempotency_keys_are_owner_and_unit_bound`, `test_acquire_rejects_invalid_persisted_identity_inputs_before_state_changes`, `test_start_rejects_invalid_goal_before_creating_a_run`, `test_acquire_rejects_invalid_timestamp_before_state_changes`, `test_engine_rejects_invalid_lease_duration`, `test_run_paths_reject_invalid_run_id_values`, `test_unit_operations_reject_invalid_unit_id_values`, `test_story_operations_reject_invalid_story_id_values`, `test_corrupt_run_state_fails_closed_before_transition`, `test_corrupt_unit_record_fails_closed_before_transition`, `test_corrupt_recovery_metadata_fails_closed_before_unrelated_transition`, `test_recovery_rejects_a_state_that_skips_a_required_work_unit`, `test_native_run_rejects_forged_terminal_state`, `test_story_identity_cannot_succeed_before_core_binds_a_story`, `test_run_path_and_durable_run_id_must_match_before_transition`, `test_idempotency_snapshot_must_reference_a_durable_unit`, `test_submit_idempotency_result_must_reference_its_durable_attempt`, `test_submit_idempotency_rejects_unknown_malformed_receipt_digest`, `test_retry_idempotency_key_cannot_replay_a_different_unit`, `test_acquire_and_retry_idempotency_replays_return_immutable_snapshots`, `test_expire_cannot_rewrite_a_terminal_unit`, `test_reject_requires_the_current_unexpired_lease`, `test_failure_must_retry_the_same_unit_instead_of_acquiring_parallel_work`.

## TC-3: Candidate evidence is independently revalidated (R3, AC3)

- **Given** a Receipt containing agent claims and file fingerprints
- **When** Core finds a missing/mismatched file, invalid guard, placeholder Spec, or failed canonical spec lint
- **Then** it records a rejected Attempt, returns the WorkUnit to retry, and does not advance the WorkflowRun

Verified by: `test_preflight_rereads_project_guard_instead_of_trusting_receipt_claim`, `test_spec_lint_validator_rereads_repository`, `test_receipt_is_reverified_and_agent_final_does_not_complete_run`, `test_terminal_attempt_requires_current_owner_lease_and_is_not_repeatable`, `test_receipt_rejects_non_finite_nested_json_evidence`, `test_receipt_rejects_boolean_protocol_versions`, `test_receipt_rejects_boolean_started_at`, `test_runner_releases_unit_when_receipt_template_cannot_be_bound`, `test_runner_records_malformed_attempt_for_unreadable_or_invalid_receipt_template`.

## TC-4: Capability declarations are versioned and truthfully degraded (R4, AC4, AC9)

- **Given** native, guided, resumable, managed, and incompatible HostCapabilities
- **When** Core selects an execution mode
- **Then** protocol incompatibility fails closed and unverified Codex thread resume remains `guided`
- **And** the adapter does not claim host E2E validation from protocol unit tests

Verified by: `test_capability_negotiation_is_truthful_and_protocol_fails_closed`, `test_manifest_workflow_guarantee_matches_the_declared_host_capability`, `test_doctor_derives_guarantee_from_project_deployment_capability`, `test_copilot_preserves_terminal_cli_for_manual_resume`, `test_copilot_deploys_methods_and_truthful_manual_resume`, `test_app_server_bridge_never_claims_e2e_validation_from_protocol_unit_test`, `test_adapter_version_comes_from_its_own_distribution`, `test_default_deploy_has_portable_methods_and_no_pactkit_stop_hook`, `test_adapter_records_awaiting_approval_as_recoverable_attempt`.

## TC-5: Portable Methods have one canonical source and thin host deployment (R5, AC5)

- **Given** the canonical Portable Methods registry
- **When** a supported host package is deployed
- **Then** every declared method has one versioned skill body and platform packages receive only discoverable wrappers/metadata
- **And** no deployed method is allowed to own workflow completion logic

Verified by: `test_portable_methods_are_canonical_and_deployed_once`, `test_default_deploy_has_portable_methods_and_no_pactkit_stop_hook`.

## TC-6: Plan finalization is locked, journaled, and recoverable (R6, AC6)

- **Given** all non-final Plan WorkUnits have been accepted and Spec/HLD are valid
- **When** finalization crashes after Story creation and is retried with the same idempotency key
- **Then** Core rolls the journal forward, writes one Story fact, rebuilds Board/context, fingerprints outputs, and marks the run completed only at the end

Verified by: `test_project_plan_units_are_bounded_and_finalize_is_recoverable`, `test_completed_plan_finalize_replays_its_original_result`, `test_completed_run_without_finalize_journal_fails_closed`, `test_completed_run_with_unfinished_journal_only_recovers_via_finalizer`, `test_completed_run_rejects_non_object_finalize_journal`, `test_completed_run_rejects_incomplete_finalize_journal`, `test_completed_run_rejects_tampered_finalize_projection`, `test_completed_finalize_replay_rejects_tampered_projection`, `test_later_finalize_keeps_prior_completed_run_readable`, `test_completed_run_survives_later_story_and_hld_evolution`, `test_completed_run_accepts_core_verified_in_progress_hld_change`, `test_completed_run_ignores_corrupt_unrelated_run_during_hld_authorization_scan`, `test_recovery_rejects_malformed_attempt_file_fingerprints`, `test_completed_run_rejects_story_contract_rewrite`, `test_concurrent_finalizers_serialize_global_projections`, `test_context_stage_recovery_rejects_changed_snapshot`, `test_doctor_rejects_completed_run_with_tampered_projection`, `test_finalizer_rejects_completed_run_with_pre_context_journal`, `test_finalizer_acquires_story_lock_before_run_lock`, `test_finalize_rejects_a_forged_completed_journal`, `test_plan_run_cannot_be_completed_outside_journaled_finalizer`.

## TC-7: Resume works without a Stop hook (R7, AC7)

- **Given** an active Story-bound run and no PactKit Codex Stop hook
- **When** the host ends a turn or the user requests resume/status
- **Then** Core returns the sole active run and its next WorkUnit without treating hook installation as a correctness prerequisite

Verified by: `test_story_resume_discovers_one_active_run_without_mutating_it`, `test_resume_fails_closed_for_a_corrupt_active_story_run`, `test_doctor_reports_semantically_corrupt_work_unit_state`, `test_completed_work_unit_run_supersedes_legacy_act_checkpoint_diagnostics`, `test_active_or_malformed_generic_act_run_cannot_supersede_legacy_checkpoint`, `test_legacy_state_import_is_non_destructive_and_stop_hook_is_optional`, `test_default_deploy_has_portable_methods_and_no_pactkit_stop_hook`, `test_stop_handler_is_advisory_for_incomplete_and_unmanaged_projects`, `test_unique_active_fallback_is_observed_without_binding_or_resuming`, `test_hook_records_sanitized_advisory_observation_without_continuation`.

## TC-8: Legacy continuation state is imported without destructive reinterpretation (R8, AC8)

- **Given** schema v1/v2 in-progress, blocked, and completed continuation fixtures
- **When** they are imported by the new WorkflowEngine
- **Then** source files remain byte-for-byte unchanged, completed never reopens, and blocked stays non-acquirable with its blocker preserved

Verified by: `test_legacy_state_import_is_non_destructive_and_stop_hook_is_optional`, `test_completed_work_unit_run_supersedes_legacy_act_checkpoint_diagnostics`, `test_active_or_malformed_generic_act_run_cannot_supersede_legacy_checkpoint`, `test_completed_legacy_state_is_imported_without_regression`, `test_legacy_blocked_state_is_preserved_and_cannot_be_acquired`.

## TC-9: Codex App Server handoff requires explicit structured evidence (R1, R3, AC1, AC3)

- **Given** an App Server thread/turn reaches `turn/completed`
- **When** the caller supplies an explicit `EvidenceReceipt` factory
- **Then** the adapter records the terminal Attempt and submits only that candidate Receipt to Core for canonical validation
- **And** model prose is never interpreted as successful evidence by the adapter

Verified by: `test_work_unit_adapter_submits_only_explicit_structured_receipt`, `test_runner_cli_executes_the_production_adapter_path`, `test_runner_returns_nonzero_when_core_rejects_candidate_receipt`, `test_adapter_records_host_error_attempt_when_app_server_fails_after_acquire`, `test_runner_releases_unit_when_receipt_template_cannot_be_bound`.

## TC-10: Failure Attempts are audit-complete and recoverable (R3, R8)

- **Given** App Server transport fails, a Receipt template is invalid/unreadable, Core rejects
  out-of-scope evidence, or App Server requests human approval
- **When** the adapter or Core ends that execution attempt
- **Then** the Attempt persists host/unit/version/decision/reason/latency/adapter-version data
  without prompt text, secrets, or raw session identifiers
- **And** the affected WorkUnit is available only through Core's versioned retry path

Verified by: `test_attempt_terminal_records_sanitized_capabilities_results_and_failure`, `test_submit_attempt_persists_decision_latency_and_adapter_version`, `test_explicit_reject_persists_complete_audit_shape`, `test_malformed_candidate_receipt_is_audited_and_recoverable`, `test_terminal_attempt_requires_current_owner_lease_and_is_not_repeatable`, `test_adapter_records_host_error_attempt_when_app_server_fails_after_acquire`, `test_adapter_records_awaiting_approval_as_recoverable_attempt`, `test_runner_releases_unit_when_receipt_template_cannot_be_bound`, `test_adapter_releases_unit_when_receipt_factory_cannot_construct_candidate`, `test_runner_records_malformed_attempt_for_unreadable_or_invalid_receipt_template`.
