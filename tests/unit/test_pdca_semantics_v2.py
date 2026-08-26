

def test_on_demand_rules_have_specific_metadata():
    """No on-demand rule ships generic boilerplate trigger/evidence.

    doctor's resolve_rule_context warns on generic metadata; this pins the
    registry so the warnings cannot regress silently.
    """
    from pactkit.prompts.rules import RULE_DEFINITIONS

    generic = [
        rid
        for rid, d in RULE_DEFINITIONS.items()
        if d.trigger == "when referenced by the active PactKit skill"
        or "active instruction artifact" in " ".join(d.evidence)
    ]
    assert not generic, f"rules with generic metadata: {generic}"
