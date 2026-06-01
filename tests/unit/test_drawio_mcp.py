"""
STORY-013: Draw.io MCP Integration — pactkit-draw 接入官方 MCP 实现即时预览.

Tests verify that Draw.io MCP conditional instructions are present in
relevant prompt templates (skills, agents, workflows).
Note: MCP rules trimmed to Context7+Memory only; Draw.io rule tests removed.
"""

from pactkit.prompts import agents, skills, workflows


class TestDrawioMcpSkill:
    """R2: pactkit-draw skill must include conditional MCP mode."""

    def test_skill_contains_mcp_mode_section(self):
        assert 'MCP Mode' in skills.SKILL_DRAW_MD

    def test_skill_contains_open_drawio_xml(self):
        assert 'open_drawio_xml' in skills.SKILL_DRAW_MD

    def test_skill_contains_open_drawio_mermaid(self):
        assert 'open_drawio_mermaid' in skills.SKILL_DRAW_MD

    def test_skill_contains_fallback_instruction(self):
        skill_text = skills.SKILL_DRAW_MD.lower()
        assert 'fallback' in skill_text or 'not available' in skill_text


class TestDrawioMcpAgent:
    """R3: visual-architect agent must be MCP-aware."""

    def test_agent_prompt_mentions_drawio_mcp(self):
        agent = agents.AGENTS_EXPERT['visual-architect']
        assert 'Draw.io MCP' in agent['prompt'] or 'open_drawio_xml' in agent['prompt']

    def test_agent_prompt_conditional_mcp(self):
        agent = agents.AGENTS_EXPERT['visual-architect']
        prompt = agent['prompt'].lower()
        assert 'conditional' in prompt or 'if' in prompt


class TestDrawioMcpWorkflow:
    """R4: DRAW_PROMPT_TEMPLATE must include MCP output step."""

    def test_draw_prompt_contains_mcp_output(self):
        assert 'open_drawio_xml' in workflows.DRAW_PROMPT_TEMPLATE

    def test_draw_prompt_contains_mcp_conditional(self):
        template = workflows.DRAW_PROMPT_TEMPLATE.lower()
        assert 'mcp' in template

    def test_draw_prompt_preserves_file_write(self):
        """File write must remain as primary output (MCP is additive)."""
        assert '.drawio' in workflows.DRAW_PROMPT_TEMPLATE
