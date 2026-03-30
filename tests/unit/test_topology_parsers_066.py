"""Tests for STORY-slim-066: ApiCallParser + AgentParser + workflow gate."""

import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
API_FIXTURES = FIXTURES / "api_call_parser"
AGENT_FIXTURES = FIXTURES / "agent_parser"


# ---------------------------------------------------------------------------
# ApiCallParser tests (R1)
# ---------------------------------------------------------------------------

class TestApiCallParser:
    """AC1-AC3: tree-sitter-based API call extraction."""

    @pytest.fixture(autouse=True)
    def _skip_no_treesitter(self):
        try:
            from pactkit.skills.visualize import ApiCallParser, _HAS_TREE_SITTER  # noqa: F401
            if not _HAS_TREE_SITTER:
                pytest.skip("tree-sitter not installed")
        except ImportError:
            pytest.skip("ApiCallParser not yet implemented")

    def test_detect_with_frontend_markers(self, tmp_path):
        """ApiCallParser detects frontend projects with fetch calls."""
        from pactkit.skills.visualize import ApiCallParser
        (tmp_path / "next.config.ts").touch()
        src = tmp_path / "src"
        src.mkdir()
        (src / "page.tsx").write_text('apiFetch("/api/v1/test")')
        parser = ApiCallParser()
        assert parser.detect(tmp_path) is True

    def test_detect_no_frontend_markers(self, tmp_path):
        from pactkit.skills.visualize import ApiCallParser
        (tmp_path / "main.py").write_text("print('hello')")
        parser = ApiCallParser()
        assert parser.detect(tmp_path) is False

    def test_parse_static_calls(self):
        """AC1: Extract apiFetch calls with string path args."""
        from pactkit.skills.visualize import ApiCallParser
        parser = ApiCallParser()
        graph = parser.parse(API_FIXTURES)
        api_nodes = [n for n in graph.nodes.values() if n.kind == "api_call"]
        paths = {n.label for n in api_nodes}
        assert "/api/v1/rulesets" in paths

    def test_parse_method_style(self):
        """AC1: Extract axios.get/post style calls."""
        from pactkit.skills.visualize import ApiCallParser
        parser = ApiCallParser()
        graph = parser.parse(API_FIXTURES)
        api_nodes = [n for n in graph.nodes.values() if n.kind == "api_call"]
        paths = {n.label for n in api_nodes}
        assert any("/api/v1/dashboard" in p for p in paths)

    def test_parse_dynamic_paths(self):
        """AC3: Template literal paths marked as [dynamic]."""
        from pactkit.skills.visualize import ApiCallParser
        parser = ApiCallParser()
        graph = parser.parse(API_FIXTURES)
        api_nodes = [n for n in graph.nodes.values() if n.kind == "api_call"]
        dynamic = [n for n in api_nodes if "[dynamic]" in n.label]
        assert len(dynamic) >= 1

    def test_fetches_edges_created(self):
        """AC1: fetches edges from enclosing function to api_call."""
        from pactkit.skills.visualize import ApiCallParser
        parser = ApiCallParser()
        graph = parser.parse(API_FIXTURES)
        fetches = [e for e in graph.edges if e.relation == "fetches"]
        assert len(fetches) >= 1

# ---------------------------------------------------------------------------
# AgentParser tests (R2)
# ---------------------------------------------------------------------------

class TestAgentParserLangGraph:
    """AC4: Strategy 1 — LangGraph StateGraph via stdlib ast."""

    @pytest.fixture(autouse=True)
    def _skip_no_parser(self):
        try:
            from pactkit.skills.visualize import AgentParser  # noqa: F401
        except ImportError:
            pytest.skip("AgentParser not yet implemented")

    def test_detect_langgraph(self, tmp_path):
        """Detect project with LangGraph imports."""
        from pactkit.skills.visualize import AgentParser
        py_file = tmp_path / "app.py"
        py_file.write_text("from langgraph.graph import StateGraph\n")
        parser = AgentParser()
        assert parser.detect(tmp_path) is True

    def test_parse_langgraph_nodes_and_edges(self):
        """AC4: Extract agent nodes + orchestration edges from StateGraph."""
        from pactkit.skills.visualize import AgentParser
        parser = AgentParser()
        graph = parser.parse(AGENT_FIXTURES)
        agent_nodes = [n for n in graph.nodes.values() if n.kind == "agent_def"]
        names = {n.label for n in agent_nodes}
        assert "researcher" in names
        assert "writer" in names
        orch_edges = [e for e in graph.edges if e.relation == "orchestrates"]
        sources_targets = {(e.source, e.target) for e in orch_edges}
        assert ("researcher", "writer") in sources_targets

    def test_conditional_edges(self):
        """AC4: Conditional edges from add_conditional_edges."""
        from pactkit.skills.visualize import AgentParser
        parser = AgentParser()
        graph = parser.parse(AGENT_FIXTURES)
        agent_nodes = {n.label for n in graph.nodes.values() if n.kind == "agent_def"}
        assert "reviewer" in agent_nodes
        orch_edges = [e for e in graph.edges if e.relation == "orchestrates"]
        # reviewer → writer (revise path)
        assert any(e.source == "reviewer" and e.target == "writer" for e in orch_edges)

class TestAgentParserDeclarative:
    """AC4b: Strategy 2 — YAML agent definitions."""

    @pytest.fixture(autouse=True)
    def _skip_no_parser(self):
        try:
            from pactkit.skills.visualize import AgentParser  # noqa: F401
        except ImportError:
            pytest.skip("AgentParser not yet implemented")

    def test_detect_agents_dir(self, tmp_path):
        """Detect project with agents/ directory."""
        from pactkit.skills.visualize import AgentParser
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "worker.yaml").write_text("agent:\n  name: worker\n")
        parser = AgentParser()
        assert parser.detect(tmp_path) is True

    def test_parse_yaml_agents(self):
        """AC4b: Parse YAML agent definitions."""
        from pactkit.skills.visualize import AgentParser
        parser = AgentParser()
        graph = parser.parse(AGENT_FIXTURES)
        agent_nodes = [n for n in graph.nodes.values() if n.kind == "agent_def"]
        names = {n.label for n in agent_nodes}
        assert "researcher" in names
        assert "writer" in names

    def test_delegation_edges(self):
        """AC4b: delegates_to creates orchestrates edges."""
        from pactkit.skills.visualize import AgentParser
        parser = AgentParser()
        graph = parser.parse(AGENT_FIXTURES)
        orch_edges = [e for e in graph.edges if e.relation == "orchestrates"]
        # researcher delegates_to writer
        assert any(e.source == "researcher" and e.target == "writer" for e in orch_edges)

class TestAgentParserMcp:
    """AC4c: Strategy 3 — MCP config."""

    @pytest.fixture(autouse=True)
    def _skip_no_parser(self):
        try:
            from pactkit.skills.visualize import AgentParser  # noqa: F401
        except ImportError:
            pytest.skip("AgentParser not yet implemented")

    def test_detect_mcp_config(self, tmp_path):
        """Detect MCP settings file."""
        from pactkit.skills.visualize import AgentParser
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        import shutil
        shutil.copy(AGENT_FIXTURES / "mcp_settings.json", claude_dir / "settings.json")
        parser = AgentParser()
        assert parser.detect(tmp_path) is True

    def test_parse_mcp_servers(self, tmp_path):
        """AC4c: Parse MCP server definitions."""
        from pactkit.skills.visualize import AgentParser
        import shutil
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        shutil.copy(AGENT_FIXTURES / "mcp_settings.json", claude_dir / "settings.json")
        parser = AgentParser()
        graph = parser.parse(tmp_path)
        agent_nodes = [n for n in graph.nodes.values() if n.kind == "agent_def"]
        names = {n.label for n in agent_nodes}
        assert "context7" in names
        assert "memory" in names

class TestAgentParserMerge:
    """AC4d: Multi-strategy merge."""

    @pytest.fixture(autouse=True)
    def _skip_no_parser(self):
        try:
            from pactkit.skills.visualize import AgentParser  # noqa: F401
        except ImportError:
            pytest.skip("AgentParser not yet implemented")

    def test_dedup_across_strategies(self):
        """AC4d: Agents from multiple strategies are deduplicated by name."""
        from pactkit.skills.visualize import AgentParser
        parser = AgentParser()
        # AGENT_FIXTURES has both langgraph_app.py and agents_dir/ with overlapping names
        graph = parser.parse(AGENT_FIXTURES)
        agent_nodes = [n for n in graph.nodes.values() if n.kind == "agent_def"]
        names = [n.label for n in agent_nodes]
        # researcher and writer appear in both langgraph + yaml, should not be duplicated
        assert names.count("researcher") == 1
        assert names.count("writer") == 1

# ---------------------------------------------------------------------------
# Dimension registration (R3)
# ---------------------------------------------------------------------------

class TestDimensionRegistration:
    def test_api_call_dimension(self):
        """R3: api_call maps to API Topology."""
        from pactkit.skills.visualize import _KIND_TO_DIMENSION
        assert _KIND_TO_DIMENSION.get("api_call") == "API Topology"

    def test_agent_def_dimension(self):
        """R3: agent_def maps to Agent Topology."""
        from pactkit.skills.visualize import _KIND_TO_DIMENSION
        assert _KIND_TO_DIMENSION.get("agent_def") == "Agent Topology"

# ---------------------------------------------------------------------------
# API convention summary (R4)
# ---------------------------------------------------------------------------

class TestApiConventionSummary:
    @pytest.fixture(autouse=True)
    def _skip_no_treesitter(self):
        try:
            from pactkit.skills.visualize import api_convention_summary, _HAS_TREE_SITTER  # noqa: F401
            if not _HAS_TREE_SITTER:
                pytest.skip("tree-sitter not installed")
        except ImportError:
            pytest.skip("api_convention_summary not yet implemented")

    def test_convention_summary(self):
        """AC5: Summary includes path prefixes and fetch function names."""
        from pactkit.skills.visualize import api_convention_summary
        summary = api_convention_summary(API_FIXTURES)
        assert "/api/v1/" in summary["prefixes"]
        assert "apiFetch" in summary["fetch_functions"]
        assert summary["total_calls"] >= 3

# ---------------------------------------------------------------------------
# Config loading (R5)
# ---------------------------------------------------------------------------

class TestTraceConfig:
    def test_custom_fetch_functions(self, tmp_path):
        """AC6: Custom fetch function names from config."""
        try:
            from pactkit.skills.visualize import ApiCallParser, _HAS_TREE_SITTER  # noqa: F401
            if not _HAS_TREE_SITTER:
                pytest.skip("tree-sitter not installed")
        except ImportError:
            pytest.skip("ApiCallParser not yet implemented")
        parser = ApiCallParser(fetch_functions=["customFetch", "apiCall"])
        assert "customFetch" in parser._fetch_functions
        assert "apiCall" in parser._fetch_functions
        assert "apiFetch" not in parser._fetch_functions

    def test_defaults_without_config(self):
        """R5: Defaults work without config."""
        try:
            from pactkit.skills.visualize import ApiCallParser, _HAS_TREE_SITTER  # noqa: F401
            if not _HAS_TREE_SITTER:
                pytest.skip("tree-sitter not installed")
        except ImportError:
            pytest.skip("ApiCallParser not yet implemented")
        parser = ApiCallParser()
        assert "fetch" in parser._fetch_functions
        assert "apiFetch" in parser._fetch_functions
        assert "axios" in parser._fetch_functions
