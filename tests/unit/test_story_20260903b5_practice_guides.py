"""Tests for STORY-slim-20260903b5ce6be5f7e0: Guide Practice layer.

R1 Practice section mechanism (optional field, verbatim render),
R2-R4 enriched content for observability / module-design / error-recovery,
R5 content anchor assertions against drift.
"""

from pactkit.prompts.guides import GUIDE_DEFINITIONS, GuideDefinition


# ---------------------------------------------------------------------------
# R1: Practice section mechanism
# ---------------------------------------------------------------------------


class TestPracticeMechanism:
    def test_practice_renders_verbatim_after_defaults(self):
        guide = GuideDefinition(
            title="T", trigger="t",
            questions=("q?",), safe_invariants=("inv",), defaults=("def",),
            alternatives=("alt",), evidence=("ev",), non_applicable=("na",),
            practice="| a | b |\n|---|---|\n| 1 | 2 |",
        )
        rendered = guide.render()
        assert "## Practice" in rendered
        # verbatim: table rows carry no bullet prefix
        assert "\n| a | b |\n" in rendered
        assert "- | a | b |" not in rendered
        # position: after Defaults, before Alternatives
        assert rendered.index("## Defaults") < rendered.index("## Practice") < rendered.index("## Alternatives")

    def test_no_practice_section_when_empty(self):
        guide = GuideDefinition(
            title="T", trigger="t",
            questions=("q?",), safe_invariants=("inv",), defaults=("def",),
            alternatives=("alt",), evidence=("ev",), non_applicable=("na",),
        )
        assert "## Practice" not in guide.render()

    def test_existing_guides_unchanged_without_practice(self):
        # 22 guides have no practice; three enriched ones do
        with_practice = [name for name, g in GUIDE_DEFINITIONS.items() if g.practice]
        assert set(with_practice) == {
            "observability.md", "module-design.md", "error-recovery.md",
        }, f"unexpected practice set: {with_practice}"


# ---------------------------------------------------------------------------
# R2-R4: enriched content anchors (drift guards)
# ---------------------------------------------------------------------------


class TestObservabilityPractice:
    def test_log_level_criteria_table_present(self):
        rendered = GUIDE_DEFINITIONS["observability.md"].render()
        for level in ("ERROR", "WARN", "INFO", "DEBUG"):
            assert level in rendered, level

    def test_structured_field_conventions(self):
        rendered = GUIDE_DEFINITIONS["observability.md"].render()
        lowered = rendered.lower()
        assert "correlation" in lowered
        assert "snake_case" in lowered or "event=" in lowered

    def test_volume_red_lines(self):
        rendered = GUIDE_DEFINITIONS["observability.md"].render().lower()
        assert "loop" in rendered  # 循环内禁打
        assert "redaction" in rendered or "redact" in rendered

    def test_antipatterns_with_consequences(self):
        rendered = GUIDE_DEFINITIONS["observability.md"].render().lower()
        assert "log-and-rethrow" in rendered

    def test_practice_size_within_budget(self):
        practice = GUIDE_DEFINITIONS["observability.md"].practice
        assert 20 <= len(practice.splitlines()) <= 80


class TestModuleDesignPractice:
    def test_splitting_criteria(self):
        rendered = GUIDE_DEFINITIONS["module-design.md"].render().lower()
        assert "single-sentence responsibility" in rendered or "one sentence" in rendered
        assert "500" in rendered  # 行数评估线

    def test_layering_rules(self):
        rendered = GUIDE_DEFINITIONS["module-design.md"].render().lower()
        assert "domain" in rendered and "infrastructure" in rendered
        assert "circular" in rendered

    def test_premature_abstraction_discriminator(self):
        rendered = GUIDE_DEFINITIONS["module-design.md"].render().lower()
        assert "premature" in rendered


class TestErrorRecoveryPractice:
    def test_error_taxonomy(self):
        rendered = GUIDE_DEFINITIONS["error-recovery.md"].render().lower()
        for kind in ("transient", "permanent", "programming"):
            assert kind in rendered, kind

    def test_user_facing_vs_log_facing_separation(self):
        rendered = GUIDE_DEFINITIONS["error-recovery.md"].render().lower()
        assert "user-facing" in rendered or "user-facing" in rendered or "user-facing" in rendered
        assert "log" in rendered

    def test_retry_boundaries(self):
        rendered = GUIDE_DEFINITIONS["error-recovery.md"].render().lower()
        assert "backoff" in rendered
        assert "idempoten" in rendered

    def test_classification_by_recovery_strategy(self):
        rendered = GUIDE_DEFINITIONS["error-recovery.md"].render().lower()
        assert "recovery strateg" in rendered or "by recovery" in rendered


# ---------------------------------------------------------------------------
# R5: seven-section test still holds for all guides (Practice optional)
# ---------------------------------------------------------------------------


class TestSevenSectionStructureExtended:
    def test_all_guides_keep_required_sections(self):
        required = (
            "## Trigger", "## Questions", "## Safe Invariants",
            "## Defaults", "## Alternatives", "## Evidence",
            "## Non-applicable",
        )
        for name, guide in GUIDE_DEFINITIONS.items():
            rendered = guide.render()
            for section in required:
                assert section in rendered, f"{name}: {section}"

    def test_practice_section_when_present_is_verbatim(self):
        for name, guide in GUIDE_DEFINITIONS.items():
            if guide.practice:
                rendered = guide.render()
                # practice content appears without mutation
                assert guide.practice.strip() in rendered, name
