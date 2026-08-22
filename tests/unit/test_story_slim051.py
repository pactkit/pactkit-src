"""Tests for STORY-slim-051: Skill scripts robustness hardening.

19 Acceptance Criteria covering scaffold.py, board.py, spec_linter.py, visualize.py.
"""
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from pactkit.skills.scaffold import (
    _inject_developer_prefix,
    create_e2e,
    create_spec,
    create_test_file,
    git_start,
)
from pactkit.skills.board import (
    _parse_story_blocks,
    _write_board,
    add_story,
    _legacy_archive_stories as archive_stories,
    _legacy_fix_board as fix_board,
    _legacy_move_story as move_story,
)
from pactkit.skills.spec_linter import (
    _check_metadata,
    LintResult,
    validate_spec,
)
from pactkit.skills.visualize import (
    _build_bridge_edges,
    _load_scan_excludes,
    visualize,
    workflow_impact,
    WorkflowGraph,
    WorkflowNode,
)


def nl():
    return chr(10)


# ============================================================
# Helper: create a board file for board.py tests
# ============================================================
def _make_board(tmp_path, content):
    board_dir = tmp_path / "docs" / "product"
    board_dir.mkdir(parents=True, exist_ok=True)
    board_path = board_dir / "sprint_board.md"
    board_path.write_text(content, encoding="utf-8")
    return board_path


# ============================================================
# AC1: create_spec does not overwrite existing spec (R1)
# ============================================================
class TestAC1CreateSpecGuard:
    def test_create_spec_does_not_overwrite(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        spec_dir = tmp_path / "docs" / "specs"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "STORY-slim-099.md"
        original = "# Original content\nDo not overwrite me."
        spec_file.write_text(original, encoding="utf-8")
        # Disable developer prefix injection
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "")
        result = create_spec("STORY-slim-099", "title")
        assert "already exists" in result.lower() or "❌" in result
        assert spec_file.read_text(encoding="utf-8") == original


# ============================================================
# AC2: create_test_file does not overwrite existing tests (R2)
# ============================================================
class TestAC2CreateTestFileGuard:
    def test_create_test_file_does_not_overwrite(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test_story_slim099.py"
        original = "def test_real(): assert 1 == 1"
        test_file.write_text(original, encoding="utf-8")
        result = create_test_file("src/story_slim099.py")
        assert "already exists" in result.lower() or "❌" in result
        assert test_file.read_text(encoding="utf-8") == original


# ============================================================
# AC3: create_e2e does not overwrite existing e2e tests (R2)
# ============================================================
class TestAC3CreateE2eGuard:
    def test_create_e2e_does_not_overwrite(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "")
        e2e_dir = tmp_path / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        e2e_file = e2e_dir / "test_STORY-slim-099_some_test.py"
        original = "def test_e2e_real(): assert True"
        e2e_file.write_text(original, encoding="utf-8")
        result = create_e2e("STORY-slim-099", "some test")
        assert "already exists" in result.lower() or "❌" in result
        assert e2e_file.read_text(encoding="utf-8") == original


# ============================================================
# AC4: git_start reports branch failure (R3)
# ============================================================
class TestAC4GitStartError:
    def test_git_start_reports_failure(self, monkeypatch):
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "")
        # Mock subprocess.run to raise CalledProcessError
        import subprocess
        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(128, "git", stderr="fatal: branch already exists")
        monkeypatch.setattr("pactkit.skills.scaffold.subprocess.run", mock_run)
        result = git_start("STORY-slim-099")
        assert "❌" in result
        assert "fail" in result.lower() or "error" in result.lower() or "already exists" in result.lower()


# ============================================================
# AC5: _write_board does not call fix_board (R4)
# ============================================================
class TestAC5WriteBoardNoFixBoard:
    def test_write_board_no_fix_board_call(self, tmp_path, monkeypatch):
        """AC5: _write_board does NOT call fix_board() as side-effect."""
        monkeypatch.chdir(tmp_path)
        board_path = _make_board(tmp_path, textwrap.dedent("""\
            # Sprint Board

            ## 📋 Backlog

            ## 🔄 In Progress

            ### [STORY-slim-099] Test story
            > Spec: docs/specs/STORY-slim-099.md

            - [ ] Task 1

            ## ✅ Done
        """))
        fix_board_called = []
        monkeypatch.setattr("pactkit.skills.board.fix_board", lambda: fix_board_called.append(1) or "✅")
        content = board_path.read_text(encoding="utf-8")
        _write_board(board_path, content)
        assert len(fix_board_called) == 0, "fix_board should NOT be called by _write_board"


# ============================================================
# AC6: fix_board uses position-based removal (R5)
# ============================================================
class TestAC6FixBoardPositionRemoval:
    def test_fix_board_similar_blocks_survive(self, tmp_path, monkeypatch):
        """AC6: Two stories with similar text both survive fix_board correctly."""
        monkeypatch.chdir(tmp_path)
        # Create board with two stories that have similar block text
        board_content = textwrap.dedent("""\
            # Sprint Board

            ## 📋 Backlog

            ### [STORY-slim-001] Auth module
            > Spec: docs/specs/STORY-slim-001.md

            - [ ] Implement auth

            ### [STORY-slim-002] Auth module v2
            > Spec: docs/specs/STORY-slim-002.md

            - [x] Implement auth v2

            ## 🔄 In Progress

            ## ✅ Done
        """)
        _make_board(tmp_path, board_content)
        result = fix_board()
        assert "✅" in result
        board_after = (tmp_path / "docs/product/sprint_board.md").read_text(encoding="utf-8")
        # Both stories must survive
        assert "STORY-slim-001" in board_after
        assert "STORY-slim-002" in board_after
        # STORY-slim-001 (all unchecked) should be in Backlog
        # STORY-slim-002 (all checked) should be in Done
        backlog_idx = board_after.find("## 📋 Backlog")
        done_idx = board_after.find("## ✅ Done")
        story1_idx = board_after.find("STORY-slim-001")
        story2_idx = board_after.find("STORY-slim-002")
        assert backlog_idx < story1_idx < done_idx, "STORY-slim-001 should be in Backlog"
        assert story2_idx > done_idx, "STORY-slim-002 should be in Done"


# ============================================================
# AC7: move_story uses position-based removal (R5)
# ============================================================
class TestAC7MoveStoryPositionRemoval:
    def test_move_story_position_based(self, tmp_path, monkeypatch):
        """AC7: move_story removes by parsed position, not str.find()."""
        monkeypatch.chdir(tmp_path)
        board_content = textwrap.dedent("""\
            # Sprint Board

            ## 📋 Backlog

            ### [STORY-slim-010] First story
            > Spec: docs/specs/STORY-slim-010.md

            - [ ] Task A

            ## 🔄 In Progress

            ## ✅ Done
        """)
        _make_board(tmp_path, board_content)
        result = move_story("STORY-slim-010", "done")
        assert "✅" in result
        board_after = (tmp_path / "docs/product/sprint_board.md").read_text(encoding="utf-8")
        done_idx = board_after.find("## ✅ Done")
        story_idx = board_after.find("STORY-slim-010")
        assert story_idx > done_idx, "Story should be in Done section"


# ============================================================
# AC8: add_story rejects duplicates (R6)
# ============================================================
class TestAC8AddStoryDuplicateGuard:
    def test_add_story_rejects_duplicate(self, tmp_path, monkeypatch):
        """AC8: add_story returns error if story already on board."""
        monkeypatch.chdir(tmp_path)
        board_content = textwrap.dedent("""\
            # Sprint Board

            ## 📋 Backlog

            ### [STORY-slim-099] Existing story
            > Spec: docs/specs/STORY-slim-099.md

            - [ ] Task 1

            ## 🔄 In Progress

            ## ✅ Done
        """)
        board_path = _make_board(tmp_path, board_content)
        original = board_path.read_text(encoding="utf-8")
        assert "✅" in add_story("STORY-slim-099", "Existing story", "Task 1")
        result = add_story("STORY-slim-099", "Duplicate", "Task X")
        assert "❌" in result
        assert "already exists" in result.lower()
        assert board_path.read_text(encoding="utf-8") == original


# ============================================================
# AC9: archive_stories uses ITEM_ID_RE (R7)
# ============================================================
class TestAC9ArchiveUsesItemIdRe:
    def test_archive_regex_uses_item_id_re(self):
        """AC9: archive_stories split regex uses ITEM_ID_RE, not hardcoded prefixes."""
        import inspect
        source = inspect.getsource(archive_stories)
        # Should NOT contain hardcoded "STORY|HOTFIX|BUG" in the re.split
        assert "STORY|HOTFIX|BUG" not in source, \
            "archive_stories should use ITEM_ID_RE instead of hardcoded prefix list"
        # Should reference ITEM_ID_RE
        assert "ITEM_ID_RE" in source


# ============================================================
# AC11: _parse_story_blocks returns positions (R9)
# ============================================================
class TestAC11ParseStoryBlocksPositions:
    def test_parse_story_blocks_returns_positions(self):
        """AC11: _parse_story_blocks returns tuples with start_pos and end_pos."""
        content = textwrap.dedent("""\
            # Sprint Board

            ## 📋 Backlog

            ### [STORY-slim-001] First
            > Spec: docs/specs/STORY-slim-001.md

            - [ ] Task A

            ### [STORY-slim-002] Second
            > Spec: docs/specs/STORY-slim-002.md

            - [ ] Task B

            ## 🔄 In Progress

            ## ✅ Done
        """)
        blocks = _parse_story_blocks(content)
        assert len(blocks) == 2
        # Each block should be a 4-tuple: (sid, block_text, start, end)
        for block in blocks:
            assert len(block) == 4, f"Expected 4-tuple, got {len(block)}-tuple: {block[:2]}"
            sid, block_text, start, end = block
            assert isinstance(start, int)
            assert isinstance(end, int)
            # Verify positions match content
            assert content[start:end].strip() == block_text.strip()


# ============================================================
# AC12: spec_linter detects wrong heading level (R10)
# ============================================================
class TestAC12WrongHeadingLevel:
    def test_wrong_heading_level_reported(self, tmp_path):
        """AC12: spec_linter detects ### used instead of ## and reports 'wrong heading level'."""
        spec = textwrap.dedent("""\
            # STORY-slim-099: Test

            | Field | Value |
            |-------|-------|
            | ID | STORY-slim-099 |
            | Status | Draft |
            | Priority | P1 |
            | Release | 2.5.0 |

            ## Background

            Some background.

            ## Requirements

            ### R1: Test (MUST)

            Something MUST work.

            ## Acceptance Criteria

            ### AC1: Test (R1)

            - **Given** a thing
            - **When** tested
            - **Then** works

            ### Security Scope

            | Check | Applicable | Reason |
            |-------|------------|--------|
            | SEC-1 | N/A | Test |

            ## Out of Scope

            - Nothing
        """)
        spec_path = tmp_path / "test_spec.md"
        spec_path.write_text(spec, encoding="utf-8")
        result = validate_spec(str(spec_path))
        # Should have a message about wrong heading level for Security Scope
        all_messages = [e.message for e in result.errors] + [w.message for w in result.warnings]
        has_wrong_level = any("wrong heading level" in m.lower() for m in all_messages)
        assert has_wrong_level, f"Expected 'wrong heading level' warning, got: {all_messages}"


# ============================================================
# AC13: spec_linter handles missing files and filters non-specs (R11)
# ============================================================
class TestAC13SpecLinterFiltering:
    def test_all_mode_skips_template(self, tmp_path):
        """AC13: --all mode skips TEMPLATE.md and doesn't crash on missing files."""
        specs_dir = tmp_path / "docs" / "specs"
        specs_dir.mkdir(parents=True)
        # Create TEMPLATE.md (should be skipped)
        (specs_dir / "TEMPLATE.md").write_text("# Template\nNot a real spec.", encoding="utf-8")
        # Create a valid spec
        valid_spec = textwrap.dedent("""\
            # STORY-slim-001: Valid

            | Field | Value |
            |-------|-------|
            | ID | STORY-slim-001 |
            | Status | Draft |
            | Priority | P1 |
            | Release | 2.5.0 |

            ## Background

            Something.

            ## Requirements

            ### R1: Test (MUST)

            MUST work.

            ## Acceptance Criteria

            ### AC1: Test (R1)

            - **Given** a thing
            - **When** tested
            - **Then** works

            ## Security Scope

            | Check | Applicable | Reason |
            |-------|------------|--------|
            | SEC-1 | N/A | Test |

            ## Out of Scope

            - Nothing
        """)
        (specs_dir / "STORY-slim-001.md").write_text(valid_spec, encoding="utf-8")
        from pactkit.skills.spec_linter import main
        exit_code = main(["--all", "--specs-dir", str(specs_dir)])
        # Should succeed (valid spec passes), TEMPLATE.md skipped
        assert exit_code == 0


# ============================================================
# AC14: metadata parser filters separator rows (R12)
# ============================================================
class TestAC14MetadataSeparatorFilter:
    def test_separator_row_not_in_fields(self):
        """AC14: _check_metadata filters out separator rows from parsed fields."""
        text = textwrap.dedent("""\
            | Field | Value |
            |-------|-------|
            | ID | STORY-slim-099 |
            | Status | Draft |
            | Priority | P1 |
            | Release | 2.5.0 |
        """)
        result = LintResult()
        fields = _check_metadata(text, result)
        # Separator row "-------" should NOT be in fields
        for key in fields:
            assert "---" not in key, f"Separator row leaked into fields: {key}"
        assert "ID" in fields
        assert "Status" in fields


# ============================================================
# AC15: bridge edges use exact matching (R13)
# ============================================================
class TestAC15BridgeEdgeExactMatch:
    def test_bridge_edges_no_substring_match(self):
        """AC15: 'auth' skill does NOT match 'oauth2_client.py' via substring."""
        func_registry = {
            "handle_auth": "auth_handler",
            "get_token": "oauth2_client",
        }
        topology_graph = WorkflowGraph()
        topology_graph.add_node(WorkflowNode(id="auth", kind="skill", label="auth"))

        unified_graph = WorkflowGraph()
        # Add function nodes so edges can reference them
        unified_graph.add_node(WorkflowNode(id="handle_auth", kind="function", label="handle_auth"))
        unified_graph.add_node(WorkflowNode(id="get_token", kind="function", label="get_token"))
        unified_graph.add_node(WorkflowNode(id="auth", kind="skill", label="auth"))

        _build_bridge_edges(func_registry, topology_graph, unified_graph)

        # Check edges: handle_auth (in auth_handler) should link to "auth"
        edge_targets = [(e.source, e.target) for e in unified_graph.edges]
        assert ("handle_auth", "auth") in edge_targets, "auth_handler should bridge to 'auth' skill"
        # oauth2_client should NOT match "auth"
        assert ("get_token", "auth") not in edge_targets, "oauth2_client should NOT bridge to 'auth' skill"


# ============================================================
# AC16: reverse call graph has separate output (R14)
# ============================================================
class TestAC16ReverseCallGraphOutput:
    def test_reverse_writes_to_separate_file(self, tmp_path, monkeypatch):
        """AC16: reverse call graph writes to reverse_call_graph.mmd, not call_graph.mmd."""
        monkeypatch.chdir(tmp_path)
        # Create minimal project
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"', encoding="utf-8")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text("def foo(): bar()\ndef bar(): pass\n", encoding="utf-8")
        graphs_dir = tmp_path / "docs" / "architecture" / "graphs"
        graphs_dir.mkdir(parents=True)
        # Pre-create call_graph.mmd so we can verify it's not overwritten
        original_cg = "graph TD\n    original[\"original\"]"
        (graphs_dir / "call_graph.mmd").write_text(original_cg, encoding="utf-8")

        result = visualize(str(tmp_path), mode="call", entry="bar", reverse=True)
        assert "✅" in result
        # reverse_call_graph.mmd should exist
        reverse_path = graphs_dir / "reverse_call_graph.mmd"
        assert reverse_path.exists(), "reverse_call_graph.mmd should be created"
        # Original call_graph.mmd should be untouched
        assert (graphs_dir / "call_graph.mmd").read_text(encoding="utf-8") == original_cg


# ============================================================
# AC17: workflow_impact shows full node list (R15)
# ============================================================
class TestAC17WorkflowImpactFullNodeList:
    def test_invalid_entry_shows_all_nodes(self, tmp_path):
        """AC17: workflow_impact with invalid entry shows all available nodes, not truncated to 20."""
        # Build a graph with 50+ nodes
        graph = WorkflowGraph()
        for i in range(55):
            graph.add_node(WorkflowNode(id=f"node_{i:03d}", kind="skill", label=f"node_{i:03d}"))

        with patch("pactkit.skills.visualize.build_workflow_graph", return_value=graph):
            result = workflow_impact(str(tmp_path), entry="invalid_entry")

        assert "not found" in result.lower()
        # All 55 nodes should be listed, not truncated to 20
        node_count = sum(1 for i in range(55) if f"node_{i:03d}" in result)
        assert node_count == 55, f"Expected all 55 nodes listed, got {node_count}"


# ============================================================
# AC18: YAML parse failure logs warning (R16)
# ============================================================
class TestAC18YamlParseWarning:
    def test_yaml_parse_failure_logs_warning(self, tmp_path, capsys):
        """AC18: When pyyaml unavailable or YAML malformed, a visible warning is logged."""
        yaml_dir = tmp_path / ".claude"
        yaml_dir.mkdir()
        # Write malformed YAML
        (yaml_dir / "pactkit.yaml").write_text(": : : invalid yaml [\n", encoding="utf-8")
        # _load_scan_excludes should warn, not silently pass
        result = _load_scan_excludes(tmp_path)
        captured = capsys.readouterr()
        # Either returns None (no excludes found) or warns
        # The key assertion: if YAML failed, stderr should have a warning
        assert result is None  # graceful fallback
        # Check stderr for warning (after our fix)
        assert "warning" in captured.err.lower() or "yaml" in captured.err.lower() or captured.err != "", \
            f"Expected warning on stderr for malformed YAML, got: '{captured.err}'"


# ============================================================
# AC19: developer prefix injection validates rest segment (R17)
# ============================================================
class TestAC19DeveloperPrefixValidation:
    def test_ambiguous_input_not_double_prefixed(self, monkeypatch):
        """AC19: STORY-slim2-001 with dev=slim does NOT become STORY-slim-slim2-001."""
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "slim")
        result = _inject_developer_prefix("STORY-slim2-001")
        # Must NOT produce STORY-slim-slim2-001
        assert result != "STORY-slim-slim2-001", \
            f"Double prefix detected: {result}"
        # Should either pass through unchanged or reject
        assert result == "STORY-slim2-001"

    def test_already_prefixed_unchanged(self, monkeypatch):
        """Existing prefix should not be duplicated."""
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "slim")
        result = _inject_developer_prefix("STORY-slim-001")
        assert result == "STORY-slim-001"

    def test_numeric_only_gets_prefix(self, monkeypatch):
        """Pure numeric rest should get prefix injected."""
        monkeypatch.setattr("pactkit.skills.scaffold._read_developer_prefix", lambda: "slim")
        result = _inject_developer_prefix("STORY-042")
        assert result == "STORY-slim-042"
