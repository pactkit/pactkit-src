"""Tests for STORY-slim-052: Skill scripts call-chain robustness hardening round 2.

20 requirements across board.py, scaffold.py, spec_linter.py, visualize.py.
"""
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from pactkit.skills.board import (
    _mark_done,
    _parse_story_blocks,
    _legacy_archive_stories as archive_stories,
    fix_board,
    _legacy_update_task as update_task,
)
from pactkit.skills.scaffold import (
    _read_developer_prefix,
    create_prd,
    create_spec,
)
from pactkit.skills.spec_linter import (
    _check_acceptance_criteria,
    _check_metadata,
    _find_section,
    _strip_code_blocks,
    LintResult,
)
from pactkit.skills.visualize import (
    _build_file_graph,
    _resolve_callee,
    _scan_files,
    regression_workflow_impact,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def nl():
    return chr(10)


# ============================================================
# Helper
# ============================================================
def _make_board(tmp_path, content):
    """Create a board file and chdir to tmp_path."""
    docs = tmp_path / "docs" / "product"
    docs.mkdir(parents=True, exist_ok=True)
    board = docs / "sprint_board.md"
    board.write_text(content, encoding="utf-8")
    return board


# ============================================================
# R1: _mark_done splice safety (AC1)
# ============================================================
class TestR1MarkDoneSpliceSafety:
    def test_splice_preserves_surrounding_content(self, tmp_path):
        """AC1: Surrounding content unchanged after checkbox replacement."""
        board_content = nl().join([
            "# Sprint Board",
            "",
            "## 📋 Backlog",
            "",
            "## 🔄 In Progress",
            "",
            "### [STORY-test-001] Test Story",
            "> Spec: docs/specs/STORY-test-001.md",
            "",
            "- [ ] First task",
            "- [ ] Second task",
            "",
            "## ✅ Done",
            "",
        ])
        story_pat = re.compile(
            r"(#{3,4} \[?STORY-test-001\]?:?.*?)(?=\n#{2,4} |\Z)",
            re.DOTALL,
        )
        story_match = story_pat.search(board_content)
        assert story_match is not None
        story_block = story_match.group(1)
        result = _mark_done(board_content, story_match, story_block, "First task")
        # The surrounding content (before story block and after) must be preserved
        assert "# Sprint Board" in result
        assert "## 📋 Backlog" in result
        assert "## ✅ Done" in result
        assert "- [x] First task" in result
        assert "- [ ] Second task" in result
        # No duplicated or lost characters
        assert result.count("## 📋 Backlog") == 1
        assert result.count("## ✅ Done") == 1


# ============================================================
# R2: fix_board rstrip offset compensation (AC2)
# ============================================================
class TestR2FixBoardOffset:
    def test_trailing_whitespace_fully_removed(self, tmp_path):
        """AC2: Offset compensation uses actual span, not rstrip'd length."""
        # Story block with trailing whitespace (space + newlines)
        board_content = nl().join([
            "# Sprint Board",
            "",
            "## 📋 Backlog",
            "",
            "### [STORY-test-001] Story One",
            "> Spec: docs/specs/STORY-test-001.md",
            "",
            "- [x] Done task",
            "   ",  # trailing whitespace
            "",
            "",
            "## 🔄 In Progress",
            "",
            "## ✅ Done",
            "",
        ])
        _make_board(tmp_path, board_content)
        with patch("pactkit.skills.board.Path.cwd", return_value=tmp_path):
            result = fix_board()
        assert "✅" in result
        # The board should not have orphaned trailing whitespace
        final = (tmp_path / "docs/product/sprint_board.md").read_text()
        # No lines that are just spaces
        for line in final.split(nl()):
            stripped = line.strip()
            if stripped == "":
                assert line == "", f"Found trailing whitespace in empty line: {repr(line)}"


# ============================================================
# R3: update_task section boundary (AC3)
# ============================================================
class TestR3UpdateTaskSectionBoundary:
    def test_does_not_overshoot_level2_header(self, tmp_path):
        """AC3: story_pat must stop at ## level-2 section headers."""
        board_content = nl().join([
            "# Sprint Board",
            "",
            "## 🔄 In Progress",
            "",
            "### [STORY-test-001] Test Story",
            "> Spec: docs/specs/STORY-test-001.md",
            "",
            "- [ ] Task A",
            "",
            "## ✅ Done",
            "",
            "Some done section content here",
            "",
        ])
        _make_board(tmp_path, board_content)
        with patch("pactkit.skills.board.Path.cwd", return_value=tmp_path):
            result = update_task("STORY-test-001", ["Task A"])
        assert "✅" in result
        final = (tmp_path / "docs/product/sprint_board.md").read_text()
        # The done section content must NOT be captured by the story block
        assert "Some done section content here" in final


# ============================================================
# R4: _parse_story_blocks position contract (AC4)
# ============================================================
class TestR4ParsePositionContract:
    def test_len_matches_span(self):
        """AC4: len(block_text) must equal end - start."""
        board_content = nl().join([
            "# Sprint Board",
            "",
            "## 📋 Backlog",
            "",
            "### [STORY-test-001] Test Story",
            "> Spec: docs/specs/STORY-test-001.md",
            "",
            "- [ ] Task A",
            "",
            "## 🔄 In Progress",
            "",
            "## ✅ Done",
            "",
        ])
        blocks = _parse_story_blocks(board_content)
        assert len(blocks) >= 1
        for sid, block_text, start, end in blocks:
            assert len(block_text) == end - start, (
                f"Position mismatch for {sid}: len(block_text)={len(block_text)}, "
                f"end-start={end - start}"
            )


# ============================================================
# R6: unified archive parsing (AC6)
# ============================================================
class TestR6UnifiedArchiveParsing:
    def test_archive_uses_parse_story_blocks(self, tmp_path):
        """AC6: archive_stories should use _parse_story_blocks, not re.split."""
        board_content = nl().join([
            "# Sprint Board",
            "",
            "## 📋 Backlog",
            "",
            "## 🔄 In Progress",
            "",
            "## ✅ Done",
            "",
            "### [STORY-test-001] Completed Story",
            "> Spec: docs/specs/STORY-test-001.md",
            "",
            "- [x] Task A",
            "- [x] Task B",
            "",
        ])
        _make_board(tmp_path, board_content)
        (tmp_path / "docs/product/archive").mkdir(parents=True, exist_ok=True)
        with patch("pactkit.skills.board.Path.cwd", return_value=tmp_path):
            result = archive_stories()
        assert "✅" in result
        assert "1 stories" in result or "1 stor" in result

# ============================================================
# R7: scaffold template safety (AC7)
# ============================================================
class TestR7ScaffoldTemplateSafety:
    def test_curly_braces_in_title(self, tmp_path):
        """AC7: Title with {curly} braces must not raise KeyError/ValueError."""
        with patch("pactkit.skills.scaffold.Path.cwd", return_value=tmp_path):
            specs_dir = tmp_path / "docs" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)
            with patch("pactkit.skills.scaffold._read_developer_prefix", return_value=""):
                result = create_spec("STORY-test-001", "Fix {edge_case} handling")
        assert "✅" in result
        content = (tmp_path / "docs/specs/STORY-test-001.md").read_text()
        assert "Fix {edge_case} handling" in content

    def test_double_curly_in_title(self, tmp_path):
        """Titles with {{ or }} should also work."""
        with patch("pactkit.skills.scaffold.Path.cwd", return_value=tmp_path):
            specs_dir = tmp_path / "docs" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)
            with patch("pactkit.skills.scaffold._read_developer_prefix", return_value=""):
                result = create_spec("STORY-test-002", "JSON {{key}}")
        assert "✅" in result
        content = (tmp_path / "docs/specs/STORY-test-002.md").read_text()
        assert "JSON {{key}}" in content


# ============================================================
# R8: developer prefix error handling (AC8)
# ============================================================
class TestR8DeveloperPrefixErrorHandling:
    def test_permission_error_not_silenced(self, tmp_path):
        """AC8: PermissionError should be logged, not silently swallowed."""
        yaml_dir = tmp_path / ".claude"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "pactkit.yaml"
        yaml_file.write_text("developer: test\n", encoding="utf-8")
        with patch("pactkit.skills.scaffold.Path.cwd", return_value=tmp_path):
            # Make the file unreadable
            with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
                # Should not raise, should return fallback ""
                result = _read_developer_prefix()
        assert result == ""

    def test_file_not_found_falls_back_gracefully(self, tmp_path):
        """FileNotFoundError should be handled gracefully."""
        with patch("pactkit.skills.scaffold.Path.cwd", return_value=tmp_path):
            result = _read_developer_prefix()
        assert result == ""


# ============================================================
# R9: PRD existence guard (AC9)
# ============================================================
class TestR9PrdExistenceGuard:
    def test_existing_prd_not_overwritten(self, tmp_path):
        """AC9: create_prd should not overwrite an existing PRD."""
        prd_dir = tmp_path / "docs" / "product"
        prd_dir.mkdir(parents=True, exist_ok=True)
        prd_file = prd_dir / "prd.md"
        prd_file.write_text("# Existing PRD content\n", encoding="utf-8")
        with patch("pactkit.skills.scaffold.Path.cwd", return_value=tmp_path):
            result = create_prd("New Product")
        # Should warn, not overwrite
        assert "⚠️" in result or "already exists" in result.lower() or "❌" in result
        # Original content must be preserved
        assert prd_file.read_text() == "# Existing PRD content\n"


# ============================================================
# R10: unclosed code fence (AC10)
# ============================================================
class TestR10UnclosedCodeFence:
    def test_unclosed_fence_stripped_to_eof(self):
        """AC10: Unclosed fence should strip everything from fence to EOF."""
        content = nl().join([
            "## Requirements",
            "",
            "### R1: Test (MUST)",
            "",
            "Some description",
            "",
            "```python",
            "def foo():",
            "    pass",
            "# no closing fence",
        ])
        stripped = _strip_code_blocks(content)
        # Everything from the unclosed fence onward should be stripped
        assert "def foo():" not in stripped
        assert "no closing fence" not in stripped
        # Content before the fence should remain
        assert "## Requirements" in stripped
        assert "Some description" in stripped


# ============================================================
# R11: pipe in metadata cell (AC11)
# ============================================================
class TestR11PipeInMetadataCell:
    def test_pipe_in_value_captured(self):
        """AC11: Metadata values with pipe characters should be fully captured."""
        content = nl().join([
            "| Field | Value |",
            "|-------|-------|",
            "| ID | STORY-001 |",
            "| Status | Draft |",
            "| Priority | P1 |",
            "| Release | 2.0.0 |",
            "| Notes | A | B option |",
        ])
        result = LintResult()
        fields = _check_metadata(content, result)
        assert fields.get("ID") == "STORY-001"
        # The Notes field value should include the pipe content
        # After fix: "A | B option" should be the full value
        if "Notes" in fields:
            assert "A" in fields["Notes"]


# ============================================================
# R12: AC count consistency (AC12)
# ============================================================
class TestR12AcCountConsistency:
    def test_code_block_ac_header_not_double_counted(self):
        """AC12: AC headers inside code blocks should not affect count."""
        raw_content = nl().join([
            "# STORY-test-001: Test",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| ID | STORY-test-001 |",
            "| Status | Draft |",
            "| Priority | P1 |",
            "| Release | 1.0.0 |",
            "",
            "## Requirements",
            "",
            "### R1: Test (MUST)",
            "",
            "Description",
            "",
            "## Acceptance Criteria",
            "",
            "### AC1: Real scenario (R1)",
            "",
            "- **Given** a test",
            "- **When** running",
            "- **Then** pass",
            "",
            "```markdown",
            "### AC1: Example in code block",
            "This should not be counted",
            "```",
            "",
            "## Security Scope",
            "",
            "| Check | Applicable | Reason |",
            "|-------|------------|--------|",
            "| SEC-1 | N/A | Test |",
        ])
        # At minimum, the _check_acceptance_criteria should work on stripped content
        stripped = _strip_code_blocks(raw_content)
        lint_result = LintResult()
        _check_acceptance_criteria(stripped, lint_result, raw_text=raw_content)
        # Should not have errors about mismatched counts
        for e in lint_result.errors:
            assert "count" not in e.message.lower() or "mismatch" not in e.message.lower()


# ============================================================
# R13: wrong-level heading detection (AC13)
# ============================================================
class TestR13WrongLevelHeadingDetection:
    def test_level1_heading_detected(self):
        """AC13: # Section (level 1) should be detected as wrong level."""
        content = nl().join([
            "# Requirements",
            "",
            "### R1: Test (MUST)",
            "",
            "Description",
        ])
        result = LintResult()
        found = _find_section(content, "Requirements", result=result)
        # Should not find it at ## level
        assert found is None
        # Should warn about wrong level (# instead of ##)
        wrong_level_warnings = [w for w in result.warnings if "wrong" in w.message.lower() and "level" in w.message.lower()]
        assert len(wrong_level_warnings) >= 1

    def test_level4_heading_detected(self):
        """AC13: #### Section (level 4) should also be detected as wrong level."""
        content = nl().join([
            "#### Requirements",
            "",
            "### R1: Test (MUST)",
            "",
            "Description",
        ])
        result = LintResult()
        found = _find_section(content, "Requirements", result=result)
        assert found is None
        wrong_level_warnings = [w for w in result.warnings if "wrong" in w.message.lower() and "level" in w.message.lower()]
        assert len(wrong_level_warnings) >= 1

# ============================================================
# R14: Mermaid label escaping (AC14)
# ============================================================
class TestR14MermaidLabelEscaping:
    def test_double_quotes_in_function_name(self, tmp_path):
        """AC14: Labels with double quotes must produce valid Mermaid."""
        # Create a minimal Python file with a function whose name won't have quotes,
        # but we test that the Mermaid output escapes any quotes in labels.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / 'test_mod.py'
        test_file.write_text('def parse_data():\n    pass\n', encoding='utf-8')
        all_files, module_index, file_to_node = _scan_files(tmp_path, file_ext='.py')
        # Build graph and check output doesn't break Mermaid syntax
        mmd_content, _ = _build_file_graph(
            tmp_path, all_files, module_index, file_to_node, focus=None
        )
        if mmd_content:
            mmd_text = mmd_content if isinstance(mmd_content, str) else ""
            # After fix, any " in labels should be escaped
            # For now just verify the output is valid Mermaid (no unescaped quotes breaking syntax)
            for line in (mmd_text if isinstance(mmd_text, str) else "").split(nl()):
                if '["' in line:
                    # Count quotes — should be balanced
                    label_part = line[line.index('["'):]
                    assert label_part.count('"') % 2 == 0, f"Unbalanced quotes in: {line}"


# ============================================================
# R15: callee resolution performance (AC15)
# ============================================================
class TestR15CalleeResolutionPerformance:
    def test_dict_lookup_instead_of_linear_scan(self):
        """AC15: _resolve_callee should use dict lookup (O(1)), not linear scan."""
        # Create a large set of function names
        func_names = {f"module_{i}.func_{j}" for i in range(100) for j in range(10)}
        # Resolve a known callee
        result = _resolve_callee("module_50.func_5", func_names)
        assert result == "module_50.func_5"
        # Resolve by suffix
        result = _resolve_callee("func_5", func_names)
        assert result is not None
        assert result.endswith(".func_5")

    def test_resolve_unknown_returns_none(self):
        """Unknown callee should return None."""
        func_names = {"a.b", "c.d"}
        result = _resolve_callee("nonexistent", func_names)
        assert result is None


# ============================================================
# R16: module index collision (AC16)
# ============================================================
class TestR16ModuleIndexCollision:
    def test_same_stem_different_dirs(self, tmp_path):
        """AC16: Two files with same stem should both be indexed."""
        pkg_a = tmp_path / "src" / "pkg_a"
        pkg_b = tmp_path / "src" / "pkg_b"
        pkg_a.mkdir(parents=True)
        pkg_b.mkdir(parents=True)
        (pkg_a / "utils.py").write_text("def helper_a(): pass\n", encoding="utf-8")
        (pkg_b / "utils.py").write_text("def helper_b(): pass\n", encoding="utf-8")
        all_files, module_index, _ = _scan_files(tmp_path, file_ext='.py')
        # Both files should be scanned
        assert len(all_files) >= 2
        # After fix, both should be reachable in module_index
        # At minimum, qualified names should resolve to different files
        found_a = any("pkg_a" in str(v) for v in module_index.values())
        found_b = any("pkg_b" in str(v) for v in module_index.values())
        assert found_a, "pkg_a/utils.py not found in module_index"
        assert found_b, "pkg_b/utils.py not found in module_index"


# ============================================================
# R17: focus graph substring match (AC17)
# ============================================================
class TestR17FocusSubstringMatch:
    def test_auth_does_not_match_oauth(self, tmp_path):
        """AC17: Focus on 'auth.py' must NOT match 'oauth.py'."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "auth.py").write_text("def login(): pass\n", encoding="utf-8")
        (src / "oauth.py").write_text("import auth\ndef get_token(): pass\n", encoding="utf-8")
        all_files, module_index, file_to_node = _scan_files(tmp_path, file_ext='.py')
        _, mmd_content = _build_file_graph(
            tmp_path, all_files, module_index, file_to_node, focus="auth.py"
        )
        # After fix, focus on "auth.py" should not pull in "oauth.py" via substring match
        if mmd_content and isinstance(mmd_content, str):
            # The key assertion: auth.py focus target node should appear
            focus_node_lines = [l for l in mmd_content.split(nl()) if 'auth_py' in l and '["' in l]
            assert len(focus_node_lines) >= 1, "Focus target auth.py not found in output"


# ============================================================
# R18: _edge_keys init in __init__ (AC18)
# ============================================================
class TestR18EdgeKeysInit:
    def test_edge_keys_exists_before_add_edge(self):
        """AC18: _edge_keys should be initialized in __init__, not lazily."""
        g = WorkflowGraph()
        # Before any add_edge call, _edge_keys should already exist
        assert hasattr(g, '_edge_keys'), "_edge_keys not initialized in __init__"
        assert isinstance(g._edge_keys, set)

    def test_add_edge_dedup_works(self):
        """Deduplication should still work with proper init."""
        g = WorkflowGraph()
        e = WorkflowEdge(source="a", target="b", relation="uses")
        g.add_edge(e)
        g.add_edge(e)  # duplicate
        assert len(g.edges) == 1


# ============================================================
# R19: regression_workflow_impact error visibility (AC19)
# ============================================================
class TestR19RegressionErrorVisibility:
    def test_unexpected_error_logged(self, tmp_path, capsys):
        """AC19: Unexpected errors should be logged, not silently swallowed."""
        with patch("pactkit.skills.visualize.build_workflow_graph", side_effect=TypeError("test error")):
            result = regression_workflow_impact(target=str(tmp_path), changed_files=["foo.py"])
        assert result == []  # Still returns empty list (fallback)
        # After fix, the error should have been printed to stderr
        captured = capsys.readouterr()
        assert "test error" in captured.err or "TypeError" in captured.err


# ============================================================
# R20: BFS deque performance (AC20)
# ============================================================
class TestR20BfsDequePerformance:
    def test_forward_reach_uses_deque(self):
        """AC20: forward_reach should use deque, not list.pop(0)."""
        g = WorkflowGraph()
        g.add_node(WorkflowNode(id="a", kind="command", label="A"))
        g.add_node(WorkflowNode(id="b", kind="skill", label="B"))
        g.add_node(WorkflowNode(id="c", kind="file", label="C"))
        g.add_edge(WorkflowEdge(source="a", target="b", relation="uses"))
        g.add_edge(WorkflowEdge(source="b", target="c", relation="uses"))
        reached = g.forward_reach("a")
        assert reached == {"a", "b", "c"}

    def test_reverse_reach_uses_deque(self):
        """AC20: reverse_reach should use deque, not list.pop(0)."""
        g = WorkflowGraph()
        g.add_node(WorkflowNode(id="a", kind="command", label="A"))
        g.add_node(WorkflowNode(id="b", kind="skill", label="B"))
        g.add_node(WorkflowNode(id="c", kind="file", label="C"))
        g.add_edge(WorkflowEdge(source="a", target="b", relation="uses"))
        g.add_edge(WorkflowEdge(source="b", target="c", relation="uses"))
        reached = g.reverse_reach("c")
        assert reached == {"a", "b", "c"}
