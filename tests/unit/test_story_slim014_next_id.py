"""Tests for pactkit next-id, including STORY-slim-148 decentralized IDs."""
from pactkit.id_generator import ITEM_ID_RE, next_story_id


class TestNextStoryId:
    """Scenario 2 from spec: pactkit next-id replaces manual ID generation."""

    def test_next_id_with_existing_stories(self, tmp_path):
        """Existing sequential specs do not constrain a decentralized ID."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)
        (specs / "STORY-slim-010.md").write_text("# S10")
        (specs / "STORY-slim-013.md").write_text("# S13")
        (specs / "STORY-slim-007.md").write_text("# S7")

        result = next_story_id(specs_dir=specs, developer="slim")
        assert ITEM_ID_RE.fullmatch(result)
        assert result.startswith("STORY-slim-")
        assert result != "STORY-slim-014"

    def test_next_id_no_existing_stories(self, tmp_path):
        """An empty snapshot still yields an entropy-bearing ID."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)

        result = next_story_id(specs_dir=specs, developer="slim")
        assert ITEM_ID_RE.fullmatch(result)
        assert result.startswith("STORY-slim-")

    def test_next_id_no_developer(self, tmp_path):
        """Developer-less IDs retain the STORY prefix."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)

        result = next_story_id(specs_dir=specs, developer="")
        assert ITEM_ID_RE.fullmatch(result)
        assert result.startswith("STORY-")

    def test_next_id_no_developer_with_existing(self, tmp_path):
        """Existing developer-less IDs do not create a central counter."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)
        (specs / "STORY-005.md").write_text("# S5")
        (specs / "STORY-003.md").write_text("# S3")

        result = next_story_id(specs_dir=specs, developer="")
        assert ITEM_ID_RE.fullmatch(result)
        assert result != "STORY-006"

    def test_next_id_ignores_other_prefixes(self, tmp_path):
        """Given HOTFIX and BUG specs exist, only count STORY prefix."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)
        (specs / "STORY-slim-002.md").write_text("# S")
        (specs / "HOTFIX-slim-010.md").write_text("# H")
        (specs / "BUG-slim-020.md").write_text("# B")

        result = next_story_id(specs_dir=specs, developer="slim")
        assert ITEM_ID_RE.fullmatch(result)
        assert result.startswith("STORY-slim-")

    def test_next_id_ignores_other_developers(self, tmp_path):
        """Given stories from other developers, only count own stories."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)
        (specs / "STORY-slim-005.md").write_text("# S")
        (specs / "STORY-bob-020.md").write_text("# S")

        result = next_story_id(specs_dir=specs, developer="slim")
        assert ITEM_ID_RE.fullmatch(result)
        assert result.startswith("STORY-slim-")

    def test_next_id_specs_dir_missing(self, tmp_path):
        """A missing specs directory does not prevent ID allocation."""
        specs = tmp_path / "docs" / "specs"
        # Don't create the directory

        result = next_story_id(specs_dir=specs, developer="slim")
        assert ITEM_ID_RE.fullmatch(result)

    def test_next_id_is_unique_from_same_snapshot(self, tmp_path):
        """Repeated allocation from one snapshot must not collide."""
        specs = tmp_path / "docs" / "specs"
        specs.mkdir(parents=True)

        values = {next_story_id(specs_dir=specs, developer="slim") for _ in range(1000)}
        assert len(values) == 1000
        assert all(ITEM_ID_RE.fullmatch(value) for value in values)

    def test_historical_sequential_ids_remain_readable(self):
        assert ITEM_ID_RE.fullmatch("STORY-slim-014")
        assert ITEM_ID_RE.fullmatch("STORY-001")
