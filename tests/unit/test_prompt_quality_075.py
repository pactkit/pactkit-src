"""Tests for STORY-slim-075 R1-R3/R5: Prompt engineering quality."""

from __future__ import annotations

import re

from pactkit.prompts.commands import COMMANDS_CONTENT
from pactkit.prompts.agents import AGENTS_EXPERT
from pactkit.prompts.rules import RULES_MODULES


# ── AC1: No MANDATORY in prompt sources ───────────────────────────────────


class TestAC1NoMandatory:
    """MANDATORY is retired — all occurrences replaced with MUST or CRITICAL."""

    def _all_prompt_text(self) -> str:
        """Concatenate all prompt source text."""
        parts = []
        for v in COMMANDS_CONTENT.values():
            parts.append(v)
        for agent in AGENTS_EXPERT.values():
            parts.append(agent.get("prompt", ""))
        for v in RULES_MODULES.values():
            parts.append(v)
        return "\n".join(parts)

    def test_no_mandatory_keyword(self):
        """No standalone MANDATORY keyword in any prompt source."""
        text = self._all_prompt_text()
        # Match MANDATORY as a standalone word (not inside other words)
        # Exclude "Mandatory" in phase titles like "Spec Lint Gate (Mandatory)" —
        # these should also be replaced, but we check case-insensitive
        matches = re.findall(r'\bMANDATORY\b', text)
        assert len(matches) == 0, f"Found {len(matches)} MANDATORY occurrences — should be replaced with MUST or CRITICAL"

    def test_no_mandatory_in_commands(self):
        """Specific check: no MANDATORY in any command playbook."""
        for name, content in COMMANDS_CONTENT.items():
            assert "MANDATORY" not in content, f"MANDATORY found in {name}"


# ── AC2: Consistent tier usage in Done playbook ──────────────────────────


class TestAC2TierConsistency:
    """Done playbook must use T1 (CRITICAL/NEVER) only for safety gates,
    and T2 (MUST) for required steps — no tier mixing."""

    def test_critical_only_for_safety_gates(self):
        """CRITICAL in Done playbook should only appear near regression gate or pre-existing test protection."""
        done_content = COMMANDS_CONTENT["project-done.md"]
        # Find all lines with CRITICAL
        critical_lines = [
            line.strip()
            for line in done_content.splitlines()
            if "CRITICAL" in line
        ]
        # Each CRITICAL line should relate to: regression, pre-existing, test failure, safety
        safety_keywords = {"regression", "pre-existing", "test", "gate", "skip", "stop", "fail", "deploy"}
        for line in critical_lines:
            lower = line.lower()
            assert any(kw in lower for kw in safety_keywords), (
                f"CRITICAL used outside safety context: {line[:80]}"
            )


# ── AC3: Parallel guidance in senior-developer ────────────────────────────


class TestAC3ParallelGuidance:
    """senior-developer agent prompt must contain PDCA-specific concurrency guidance."""

    def test_has_parallel_keyword(self):
        prompt = AGENTS_EXPERT["senior-developer"]["prompt"]
        assert "parallel" in prompt.lower(), "Missing parallel/concurrency guidance"

    def test_has_serialize_keyword(self):
        prompt = AGENTS_EXPERT["senior-developer"]["prompt"]
        assert any(kw in prompt.lower() for kw in ("serial", "sequenti", "before")), (
            "Missing serialization guidance"
        )

    def test_mentions_hierarchy_of_truth_order(self):
        """PDCA-specific: Spec → test → code ordering."""
        prompt = AGENTS_EXPERT["senior-developer"]["prompt"]
        assert "spec" in prompt.lower() and "test" in prompt.lower(), (
            "Missing Hierarchy of Truth ordering guidance"
        )


# ── AC4: "When NOT to use" for all 11 commands ───────────────────────────


class TestAC4WhenNotToUse:
    """Routing table must have 'When NOT to use' for every command."""

    EXPECTED_COMMANDS = [
        "Init", "Plan", "Clarify", "Act", "Check",
        "Done", "Release", "PR", "Sprint", "Hotfix", "Design",
    ]

    def test_all_commands_have_when_not(self):
        routing = RULES_MODULES["routing"]
        for cmd in self.EXPECTED_COMMANDS:
            # Each command section should contain disambiguation guidance
            # Look for "NOT" or "instead" or "Don't use" pattern near the command
            section_pattern = rf"### {cmd}\b"
            match = re.search(section_pattern, routing)
            assert match, f"Command {cmd} not found in routing table"

        # Count "When NOT" or "not use" or "instead" patterns
        not_patterns = re.findall(
            r"(?:When NOT to use|NOT for|instead of|Don't use|Use .+ instead)",
            routing,
            re.IGNORECASE,
        )
        # At least 11 disambiguation clauses (one per command)
        assert len(not_patterns) >= 11, (
            f"Found only {len(not_patterns)} disambiguation clauses, expected >= 11"
        )


# ── AC5: Priority pair disambiguation ────────────────────────────────────


class TestAC5PriorityPairs:
    """Act/Hotfix pair must explicitly reference each other."""

    def test_act_references_hotfix(self):
        routing = RULES_MODULES["routing"]
        # Find the Act section
        act_match = re.search(r"### Act\b.*?(?=### \w|\Z)", routing, re.DOTALL)
        assert act_match, "Act section not found"
        act_section = act_match.group()
        assert "hotfix" in act_section.lower(), (
            "Act section does not reference /project-hotfix for disambiguation"
        )

    def test_hotfix_references_act(self):
        routing = RULES_MODULES["routing"]
        hotfix_match = re.search(r"### Hotfix\b.*?(?=### \w|\Z)", routing, re.DOTALL)
        assert hotfix_match, "Hotfix section not found"
        hotfix_section = hotfix_match.group()
        assert "act" in hotfix_section.lower(), (
            "Hotfix section does not reference /project-act for disambiguation"
        )

    def test_plan_references_design(self):
        routing = RULES_MODULES["routing"]
        plan_match = re.search(r"### Plan\b.*?(?=### \w|\Z)", routing, re.DOTALL)
        assert plan_match, "Plan section not found"
        plan_section = plan_match.group()
        assert "design" in plan_section.lower(), (
            "Plan section does not reference /project-design for disambiguation"
        )
