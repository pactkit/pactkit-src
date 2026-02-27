"""
STORY-055: PDCA Quality Gates Enhancement — Commands prompt content tests

Verify:
- R1: Plan Phase 3 Spec template includes Implementation Steps guidance
- R2: Check Phase 1 has structured 8-item security checklist (SEC-1 to SEC-8)
- R2.2: Checklist items reference PASS/FAIL/N/A output format
- R2.3: FAIL on SEC-1..SEC-5 classified as P0
- R2.4: Results included in Phase 5 / Verdict
- R2.5: Checklist can be disabled via check.security_checklist config
- R3: Done Phase 3.3 has 5-dimension lesson quality scoring
- R3.3 + R3.4: Threshold gate with default 15
- R3.5: Log message when lesson skipped
- R3.6: Score appended to lesson row
- R3.7: P0/P1 findings receive bonus
"""
import importlib


def _commands():
    from pactkit.prompts import commands as cmd
    importlib.reload(cmd)
    return cmd


# ===========================================================================
# R1: Plan Phase — Implementation Steps template
# ===========================================================================

class TestPlanImplementationStepsTemplate:
    """Plan Phase 3 MUST guide the agent to add an Implementation Steps section."""

    def _plan(self) -> str:
        return _commands().COMMANDS_CONTENT['project-plan.md']

    def test_plan_mentions_implementation_steps(self):
        plan = self._plan()
        assert 'Implementation Steps' in plan, \
            "project-plan.md must mention 'Implementation Steps' section"

    def test_plan_implementation_steps_has_table_columns(self):
        """Spec table must include Dependencies and Risk columns."""
        plan = self._plan()
        assert 'Dependencies' in plan or 'Risk' in plan, \
            "Implementation Steps template must include Dependencies and/or Risk columns"


# ===========================================================================
# R2: Check Phase — Structured Security Checklist
# ===========================================================================

class TestCheckSecurityChecklist:
    """Check Phase 1 MUST have a structured 8-item security checklist."""

    def _check(self) -> str:
        return _commands().COMMANDS_CONTENT['project-check.md']

    def test_check_has_sec1_secrets(self):
        check = self._check()
        assert 'SEC-1' in check, "Check must include SEC-1 (Secrets check)"

    def test_check_has_sec2_input(self):
        check = self._check()
        assert 'SEC-2' in check, "Check must include SEC-2 (Input validation)"

    def test_check_has_sec3_sql(self):
        check = self._check()
        assert 'SEC-3' in check, "Check must include SEC-3 (SQL injection)"

    def test_check_has_sec4_xss(self):
        check = self._check()
        assert 'SEC-4' in check, "Check must include SEC-4 (XSS)"

    def test_check_has_sec5_auth(self):
        check = self._check()
        assert 'SEC-5' in check, "Check must include SEC-5 (Auth tokens)"

    def test_check_has_sec6_rate(self):
        check = self._check()
        assert 'SEC-6' in check, "Check must include SEC-6 (Rate limiting)"

    def test_check_has_sec7_error(self):
        check = self._check()
        assert 'SEC-7' in check, "Check must include SEC-7 (Error messages)"

    def test_check_has_sec8_deps(self):
        check = self._check()
        assert 'SEC-8' in check, "Check must include SEC-8 (Dependencies/CVEs)"

    def test_check_mentions_pass_fail_na(self):
        """R2.2: Each item must output PASS, FAIL, or N/A."""
        check = self._check()
        assert 'PASS' in check and 'FAIL' in check, \
            "Check security checklist must reference PASS and FAIL outputs"
        assert 'N/A' in check or 'N/A' in check, \
            "Check security checklist must reference N/A for non-applicable items"

    def test_check_sec1_to_sec5_fail_is_p0(self):
        """R2.3: FAIL on SEC-1..SEC-5 must be classified as P0."""
        check = self._check()
        assert 'P0' in check, \
            "Check must classify SEC-1..SEC-5 FAIL as P0 Critical"

    def test_check_results_in_verdict(self):
        """R2.4: Results must be included in Phase 5 Verdict."""
        check = self._check()
        assert 'Security Checklist' in check or 'security_checklist' in check, \
            "Check Verdict section must reference Security Checklist results"

    def test_check_can_be_disabled_via_config(self):
        """R2.5: Checklist must be disableable via check.security_checklist: false."""
        check = self._check()
        assert 'security_checklist' in check, \
            "Check must reference check.security_checklist config option"


# ===========================================================================
# R3: Done Phase — Lesson Quality Scoring
# ===========================================================================

class TestDoneLessonQualityScoring:
    """Done Phase 3.3 MUST include 5-dimension lesson quality scoring."""

    def _done(self) -> str:
        return _commands().COMMANDS_CONTENT['project-done.md']

    def test_done_has_5_dimensions(self):
        """R3.1: Must have 5 quality dimensions."""
        done = self._done()
        # Check for dimension names
        assert 'Specificity' in done or 'specificity' in done.lower(), \
            "Done must include Specificity dimension"
        assert 'Actionability' in done or 'actionability' in done.lower(), \
            "Done must include Actionability dimension"

    def test_done_has_scoring_scale(self):
        """R3.2: Dimensions must be scored 1-5."""
        done = self._done()
        assert '1-5' in done or ('score' in done.lower() and '5' in done), \
            "Done must reference 1-5 scoring scale"

    def test_done_has_quality_threshold(self):
        """R3.3 + R3.4: Must have threshold gate, default 15."""
        done = self._done()
        assert 'threshold' in done.lower() or 'lesson_quality_threshold' in done, \
            "Done must reference quality threshold"
        assert '15' in done, \
            "Done must reference default threshold of 15"

    def test_done_has_skip_log_message(self):
        """R3.5: Must log when lesson is skipped below threshold."""
        done = self._done()
        assert 'skipped' in done.lower() or 'Lesson skipped' in done, \
            "Done must log when lesson is skipped (score below threshold)"

    def test_done_lesson_row_includes_score(self):
        """R3.6: Appended lesson row must include score."""
        done = self._done()
        assert 'score' in done.lower() and '/25' in done, \
            "Done lesson row format must include score (e.g., 'score: 18/25')"

    def test_done_p0_p1_bonus(self):
        """R3.7: P0/P1 findings should receive +3 bonus."""
        done = self._done()
        assert '+3' in done or 'bonus' in done.lower(), \
            "Done must reference +3 bonus for P0/P1 findings"

    def test_done_max_score_is_25(self):
        """Total max score must be 25 (5 dimensions × max 5)."""
        done = self._done()
        assert '25' in done, \
            "Done must reference max score of 25"

    def test_done_configurable_threshold(self):
        """lesson_quality_threshold must be configurable via pactkit.yaml."""
        done = self._done()
        assert 'lesson_quality_threshold' in done, \
            "Done must reference lesson_quality_threshold config option"
