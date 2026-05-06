"""STORY-slim-107: Integrate tech debt prevention patterns into framework rules."""
import pytest
from pactkit.prompts.rules import RULES_MODULES, RULES_MANAGED_PREFIXES


class TestArchitectureDualWrite:
    """R1: §1 DRY expanded with No Dual-Write sub-section."""

    def test_dual_write_subsection_exists(self):
        arch = RULES_MODULES["architecture"]
        assert "No Dual-Write" in arch

    def test_dual_write_anti_patterns(self):
        arch = RULES_MODULES["architecture"]
        assert "Memory + DB" in arch or "Memory+DB" in arch
        assert "Cache + Source" in arch or "Cache+Source" in arch

    def test_dual_write_fix_pattern(self):
        arch = RULES_MODULES["architecture"]
        assert "truth source" in arch.lower()


class TestArchitectureSecurityExpansion:
    """R2: §6 Defense-in-Depth expanded with 3 sub-sections."""

    def test_deny_by_default(self):
        arch = RULES_MODULES["architecture"]
        assert "Deny-by-Default" in arch

    def test_input_validation(self):
        arch = RULES_MODULES["architecture"]
        assert "Input Validation" in arch
        assert "SQL" in arch
        assert "SSRF" in arch or "file path" in arch.lower()

    def test_timing_consistency(self):
        arch = RULES_MODULES["architecture"]
        assert "Timing Consistency" in arch or "timing" in arch.lower()
        assert "side-channel" in arch.lower()


class TestArchitectureCodeEnforces:
    """R3: §10 Code Enforces, Prompt Instructs."""

    def test_section_exists(self):
        arch = RULES_MODULES["architecture"]
        assert "Code Enforces" in arch

    def test_litmus_test(self):
        arch = RULES_MODULES["architecture"]
        assert "litmus" in arch.lower() or "LLM ignores" in arch

    def test_llm_calculator(self):
        arch = RULES_MODULES["architecture"]
        assert "Calculator" in arch or "deterministic" in arch.lower()


class TestArchitectureConcurrency:
    """R4: §11 Concurrency & Async Safety."""

    def test_section_exists(self):
        arch = RULES_MODULES["architecture"]
        assert "Concurrency" in arch or "Async Safety" in arch

    def test_fire_and_forget(self):
        arch = RULES_MODULES["architecture"]
        assert "fire-and-forget" in arch.lower() or "silently fail" in arch.lower()

    def test_request_scoped_cleanup(self):
        arch = RULES_MODULES["architecture"]
        assert "finally" in arch.lower()


class TestArchitectureCacheLifecycle:
    """R5: §12 Cache Lifecycle."""

    def test_section_exists(self):
        arch = RULES_MODULES["architecture"]
        assert "Cache Lifecycle" in arch or "Cache" in arch

    def test_invalidation(self):
        arch = RULES_MODULES["architecture"]
        assert "invalidat" in arch.lower()


class TestArchitectureDeadCode:
    """R6: §13 Dead Code Hygiene."""

    def test_section_exists(self):
        arch = RULES_MODULES["architecture"]
        assert "Dead Code" in arch

    def test_categories(self):
        arch = RULES_MODULES["architecture"]
        assert "middleware" in arch.lower() or "unused" in arch.lower()


class TestSolutionStringEnum:
    """R7: String→Enum pattern in solution module."""

    def test_section_exists(self):
        sol = RULES_MODULES["solution"]
        assert "Enum" in sol

    def test_language_agnostic(self):
        sol = RULES_MODULES["solution"]
        assert "TypeScript" in sol or "as const" in sol

    def test_migration_checklist(self):
        sol = RULES_MODULES["solution"]
        assert "grep" in sol.lower() or "migration" in sol.lower()


class TestNoProjectSpecificReferences:
    """AC3: No pactsearch-specific terms in new content."""

    FORBIDDEN_TERMS = [
        "owlready2", "rdflib", "pactsearch",
        "BUG-172", "BUG-181", "BUG-187", "BUG-188", "BUG-189", "BUG-191",
        "STORY-182", "STORY-190", "STORY-191", "STORY-195",
        "STORY-207", "STORY-208",
    ]

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_architecture_no_forbidden_term(self, term):
        arch = RULES_MODULES["architecture"]
        assert term not in arch, f"Found project-specific term '{term}' in architecture module"

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_solution_no_forbidden_term(self, term):
        sol = RULES_MODULES["solution"]
        assert term not in sol, f"Found project-specific term '{term}' in solution module"


class TestManagedPrefixesUnchanged:
    """AC5: RULES_MANAGED_PREFIXES covers global rules only (STORY-slim-112 split).

    After STORY-slim-112, RULES_MANAGED_PREFIXES is an alias for RULES_GLOBAL_PREFIXES.
    On-demand prefixes (06-, 07-, 08-, 09-, 12-) are now in RULES_ONDEMAND_PREFIXES.
    """

    def test_prefixes_unchanged(self):
        # STORY-slim-112: RULES_MANAGED_PREFIXES now aliases RULES_GLOBAL_PREFIXES only
        from pactkit.prompts.rules import RULES_GLOBAL_PREFIXES
        assert RULES_MANAGED_PREFIXES == RULES_GLOBAL_PREFIXES
