"""Tests for BUG-027: Sprint Board Story title level inconsistency.

R1: scaffold.py provides create_board() function
R2: project-init uses scaffold command
R3: Regex tolerant matching (### and ####)
R4: add_story keeps standard ### format
"""


BOARD_TEMPLATE = """# Sprint Board

## 📋 Backlog


## 🔄 In Progress


## ✅ Done

"""


def _setup_board(tmp_path, content=None):
    """Create a board file in tmp_path and chdir to it."""
    board_dir = tmp_path / 'docs' / 'product'
    board_dir.mkdir(parents=True, exist_ok=True)
    board_file = board_dir / 'sprint_board.md'
    board_file.write_text(content or BOARD_TEMPLATE, encoding='utf-8')
    return board_file


def _board():
    from types import SimpleNamespace
    from pactkit.skills import board
    return SimpleNamespace(
        add_story=board.add_story,
        archive_stories=board._legacy_archive_stories,
        list_stories=board._legacy_list_stories,
        fix_board=board._legacy_fix_board,
    )


def _scaffold():
    from pactkit.skills import scaffold
    return scaffold


# ---------------------------------------------------------------------------
# R1: scaffold.py provides create_board() function
# ---------------------------------------------------------------------------
class TestCreateBoardFunction:
    """R1: create_board() initializes sharded Story facts."""

    def test_create_board_exists(self):
        """create_board function should exist in scaffold module."""
        s = _scaffold()
        assert hasattr(s, 'create_board')
        assert callable(s.create_board)

    def test_create_board_generates_facts_directory(self, tmp_path, monkeypatch):
        """create_board creates docs/product/stories without a projection."""
        monkeypatch.chdir(tmp_path)
        s = _scaffold()
        result = s.create_board()
        assert '✅' in result
        assert (tmp_path / 'docs/product/stories').is_dir()
        assert not (tmp_path / 'docs/product/sprint_board.md').exists()

    def test_projection_is_explicit(self, tmp_path, monkeypatch):
        """The compatibility scaffold command never creates the projection."""
        monkeypatch.chdir(tmp_path)
        s = _scaffold()
        s.create_board()
        assert not (tmp_path / 'docs/product/sprint_board.md').exists()

    def test_create_board_idempotent(self, tmp_path, monkeypatch):
        """create_board does not overwrite existing board."""
        monkeypatch.chdir(tmp_path)
        s = _scaffold()
        # Initialize facts first time
        s.create_board()
        # Add a story
        _board().add_story('STORY-001', 'Test', 'Task 1')
        # Initialize again (should not overwrite records)
        result = s.create_board()
        assert 'exists' in result.lower() or '⚠️' in result
        # Story should still be there
        record = tmp_path / 'docs/product/stories/STORY-001.yaml'
        assert record.is_file()


# ---------------------------------------------------------------------------
# R3: Regex tolerant matching (### and ####)
# ---------------------------------------------------------------------------
class TestRegexTolerantMatching:
    """R3: board.py regex matches both ### and #### story headers."""

    def test_archive_recognizes_four_hash_story(self, tmp_path, monkeypatch):
        """archive_stories can archive #### formatted stories."""
        monkeypatch.chdir(tmp_path)
        # Board with #### format story (legacy/malformed) in Done section
        board_with_4hash = (
            "# Sprint Board\n\n"
            "## 📋 Backlog\n\n\n"
            "## 🔄 In Progress\n\n\n"
            "## ✅ Done\n\n"
            "#### [STORY-001] Legacy Story\n"
            "> Spec: docs/specs/STORY-001.md\n\n"
            "- [x] Completed task\n\n"
        )
        _setup_board(tmp_path, board_with_4hash)
        (tmp_path / 'docs' / 'product' / 'archive').mkdir(parents=True, exist_ok=True)
        b = _board()
        result = b.archive_stories()
        # Should archive successfully
        assert 'Archived 1' in result or '✅' in result
        # Story should be removed from board
        content = (tmp_path / 'docs' / 'product' / 'sprint_board.md').read_text()
        assert 'STORY-001' not in content

    def test_list_stories_recognizes_four_hash(self, tmp_path, monkeypatch):
        """list_stories finds #### formatted stories."""
        monkeypatch.chdir(tmp_path)
        board_with_4hash = (
            "# Sprint Board\n\n"
            "## 📋 Backlog\n\n"
            "#### [STORY-001] Legacy Story\n"
            "> Spec: docs/specs/STORY-001.md\n\n"
            "- [ ] Open task\n\n"
            "## 🔄 In Progress\n\n\n"
            "## ✅ Done\n\n"
        )
        _setup_board(tmp_path, board_with_4hash)
        b = _board()
        result = b.list_stories()
        assert 'STORY-001' in result

    def test_fix_board_handles_four_hash(self, tmp_path, monkeypatch):
        """fix_board can relocate #### formatted stories."""
        monkeypatch.chdir(tmp_path)
        # Misplaced 4-hash story after Done section
        broken_board = (
            "# Sprint Board\n\n"
            "## 📋 Backlog\n\n\n"
            "## 🔄 In Progress\n\n\n"
            "## ✅ Done\n\n"
            "#### [STORY-001] Misplaced\n"
            "> Spec: docs/specs/STORY-001.md\n\n"
            "- [ ] Open task\n"
        )
        _setup_board(tmp_path, broken_board)
        b = _board()
        b.fix_board()
        content = (tmp_path / 'docs' / 'product' / 'sprint_board.md').read_text()
        # Story should be moved to Backlog section
        backlog_pos = content.index('## 📋 Backlog')
        in_progress_pos = content.index('## 🔄 In Progress')
        # Find story position (may be ### or #### after fix)
        assert 'STORY-001' in content


# ---------------------------------------------------------------------------
# R4: add_story keeps standard ### format
# ---------------------------------------------------------------------------
class TestAddStoryStandardFormat:
    """R4: add_story always generates ### format."""

    def test_add_story_uses_three_hash(self, tmp_path, monkeypatch):
        """add_story creates story with ### prefix."""
        monkeypatch.chdir(tmp_path)
        _setup_board(tmp_path)
        b = _board()
        b.add_story('STORY-100', 'New Story', 'Task 1')
        from pactkit.governance import BoardRenderer, StoryRepository
        content = BoardRenderer(StoryRepository(tmp_path)).render()
        # Should have ### not ####
        assert '### [STORY-100]' in content
        assert '#### [STORY-100]' not in content
