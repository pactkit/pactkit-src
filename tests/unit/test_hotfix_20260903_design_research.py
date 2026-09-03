"""Hotfix 2026-09-03: design-time best-practice research step in Plan.

User rule: when designing, the agent must consult current industry practice
instead of relying on training knowledge alone. R6 shipped API-signature
verification (Act) but the Plan phase — where design happens — had no
research step.
"""

from pactkit.prompts.commands import COMMANDS_CONTENT


def test_plan_has_best_practice_research_step():
    plan = COMMANDS_CONTENT["project-plan.md"]
    assert "Best-Practice Research" in plan
    lowered = plan.lower()
    assert "context7" in lowered or "web search" in lowered
    assert "cite" in lowered or "reference" in lowered


def test_plan_flags_unreferenced_designs():
    plan = COMMANDS_CONTENT["project-plan.md"].lower()
    assert "unreferenced" in plan or "training-memory" in plan or "training memory" in plan
