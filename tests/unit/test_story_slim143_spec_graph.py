"""Tests for STORY-slim-143: Spec Dependency Surface & Story DAG (spec-graph).

Covers AC1-AC7:
- AC1: scaffolded spec carries Dependency Surface
- AC2: dangling depends-on -> E010 ERROR
- AC3: missing section -> W011 WARNING
- AC4: waves + same-wave conflict matrix
- AC5: cycle detection -> non-zero exit with cycle path
- AC6: deterministic output
"""

from __future__ import annotations

import textwrap

import pytest

from pactkit import schemas
from pactkit.skills import spec_linter
from pactkit.skills.scaffold import create_spec

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _spec_text(
    story_id: str = "STORY-slim-900",
    status: str = "Draft",
    dep_surface: str | None = None,
) -> str:
    """Build a minimal valid spec body, optionally with a Dependency Surface."""
    body = textwrap.dedent(
        f"""\
        # {story_id}: Demo

        | Field | Value |
        |-------|-------|
        | ID | {story_id} |
        | Status | {status} |
        | Priority | P1 |
        | Release | 2.19.0 |

        ## Background

        demo

        ## Requirements

        ### R1: X (MUST)

        MUST do x.

        ## Acceptance Criteria

        ### AC1: X (R1)

        - **Given** a
        - **When** b
        - **Then** c

        ## Security Scope

        | Check | Applicable | Reason |
        |-------|------------|--------|
        | SEC-1 | N/A | tests only |
        """
    )
    if dep_surface is not None:
        body += f"\n## Dependency Surface\n\n{dep_surface}\n"
    return body


def _surface_table(depends: str = "None", provides: str = "None",
                   touches: str = "`a.py`", risk: str = "LOW") -> str:
    return textwrap.dedent(
        f"""\
        | Field | Value |
        |-------|-------|
        | Depends on | {depends} |
        | Provides | {provides} |
        | Touches | {touches} |
        | Conflict risk | {risk} |"""
    )


def _write_spec(tmp_path, story_id, **kw):
    specs = tmp_path / "specs"
    specs.mkdir(exist_ok=True)
    p = specs / f"{story_id}.md"
    p.write_text(_spec_text(story_id, **kw), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# AC1: scaffold + schema constants
# ---------------------------------------------------------------------------


class TestSchema:
    def test_constants_exist(self):
        assert schemas.DEP_SURFACE_SECTION == "Dependency Surface"
        assert schemas.DEP_SURFACE_FIELDS == ("Depends on", "Provides", "Touches", "Conflict risk")
        assert "LOW" in schemas.DEP_SURFACE_RISK_LEVELS

    def test_section_in_optional_sections(self):
        assert "## Dependency Surface" in schemas.SPEC_OPTIONAL_SECTIONS

    def test_template_contains_section(self):
        assert "## Dependency Surface" in schemas.SPEC_TEMPLATE
        for field_name in schemas.DEP_SURFACE_FIELDS:
            assert field_name in schemas.SPEC_TEMPLATE

    def test_scaffold_generates_surface(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_spec("STORY-slim-901", "demo")
        content = (tmp_path / "docs/specs/STORY-slim-901.md").read_text()
        assert "## Dependency Surface" in content
        for field_name in schemas.DEP_SURFACE_FIELDS:
            assert field_name in content
        result = spec_linter.validate_spec(str(tmp_path / "docs/specs/STORY-slim-901.md"))
        rule_ids = {i.rule_id for i in result.errors + result.warnings}
        assert "E010" not in rule_ids
        assert "W011" not in rule_ids


# ---------------------------------------------------------------------------
# AC2 / AC3: linter rules
# ---------------------------------------------------------------------------


class TestLinterRules:
    def test_dangling_dependency_is_error(self, tmp_path):
        spec = _write_spec(
            tmp_path, "STORY-slim-902",
            dep_surface=_surface_table(depends="STORY-slim-999"),
        )
        result = spec_linter.validate_spec(str(spec))
        e010 = [e for e in result.errors if e.rule_id == "E010"]
        assert e010, "expected E010 for dangling depends-on"
        assert "STORY-slim-999" in e010[0].message
        assert not result.passed

    def test_existing_dependency_ok(self, tmp_path):
        _write_spec(tmp_path, "STORY-slim-903", dep_surface=_surface_table())
        spec = _write_spec(
            tmp_path, "STORY-slim-904",
            dep_surface=_surface_table(depends="STORY-slim-903 (needs: nothing)"),
        )
        result = spec_linter.validate_spec(str(spec))
        assert not [e for e in result.errors if e.rule_id == "E010"]

    def test_missing_section_is_warning(self, tmp_path):
        spec = _write_spec(tmp_path, "STORY-slim-905", dep_surface=None)
        result = spec_linter.validate_spec(str(spec))
        w011 = [w for w in result.warnings if w.rule_id == "W011"]
        assert w011, "expected W011 for missing Dependency Surface"
        assert result.passed

    def test_missing_field_is_warning(self, tmp_path):
        bad_table = "| Field | Value |\n|-------|-------|\n| Depends on | None |"
        spec = _write_spec(tmp_path, "STORY-slim-906", dep_surface=bad_table)
        result = spec_linter.validate_spec(str(spec))
        w011 = [w for w in result.warnings if w.rule_id == "W011"]
        assert w011
        assert "Touches" in w011[0].message or "Provides" in w011[0].message


# ---------------------------------------------------------------------------
# AC4-AC6: spec_graph core
# ---------------------------------------------------------------------------

spec_graph = pytest.importorskip("pactkit.spec_graph")


class TestSpecGraph:
    def test_waves_and_conflict(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-910.md").write_text(
            _spec_text("STORY-slim-910", dep_surface=_surface_table(touches="`a.py`")))
        (specs / "STORY-slim-911.md").write_text(
            _spec_text("STORY-slim-911", dep_surface=_surface_table(
                depends="STORY-slim-910", touches="`b.py`")))
        (specs / "STORY-slim-912.md").write_text(
            _spec_text("STORY-slim-912", dep_surface=_surface_table(touches="`a.py`")))

        graph = spec_graph.load_story_graph(specs)
        waves = spec_graph.compute_waves(graph)
        assert waves == [["STORY-slim-910", "STORY-slim-912"], ["STORY-slim-911"]]

        conflicts = spec_graph.compute_conflicts(graph, waves)
        assert len(conflicts) == 1
        c = conflicts[0]
        assert c.story_a == "STORY-slim-910" and c.story_b == "STORY-slim-912"
        assert "a.py" in c.shared
        assert c.same_wave is True

    def test_done_story_edge_excluded(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-920.md").write_text(
            _spec_text("STORY-slim-920", status="Done", dep_surface=_surface_table()))
        (specs / "STORY-slim-921.md").write_text(
            _spec_text("STORY-slim-921", dep_surface=_surface_table(depends="STORY-slim-920")))
        graph = spec_graph.load_story_graph(specs)
        waves = spec_graph.compute_waves(graph)
        assert waves == [["STORY-slim-921"]]

    def test_cycle_detection(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-930.md").write_text(
            _spec_text("STORY-slim-930", dep_surface=_surface_table(depends="STORY-slim-931")))
        (specs / "STORY-slim-931.md").write_text(
            _spec_text("STORY-slim-931", dep_surface=_surface_table(depends="STORY-slim-930")))
        graph = spec_graph.load_story_graph(specs)
        with pytest.raises(spec_graph.DependencyCycleError) as exc:
            spec_graph.compute_waves(graph)
        assert "STORY-slim-930" in str(exc.value) and "STORY-slim-931" in str(exc.value)

    def test_deterministic_output(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        for i, dep in enumerate(["None", "STORY-slim-940", "None"]):
            sid = f"STORY-slim-94{i}"
            (specs / f"{sid}.md").write_text(
                _spec_text(sid, dep_surface=_surface_table(
                    depends=dep, touches=f"`f{i}.py`")))
        out1 = spec_graph.render(spec_graph.load_story_graph(specs))
        out2 = spec_graph.render(spec_graph.load_story_graph(specs))
        assert out1 == out2

    def test_cli_exit_codes(self, tmp_path, capsys):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-950.md").write_text(
            _spec_text("STORY-slim-950", dep_surface=_surface_table()))
        assert spec_graph.main(["--specs-dir", str(specs)]) == 0
        out = capsys.readouterr().out
        assert "Wave 1" in out and "STORY-slim-950" in out

        (specs / "STORY-slim-951.md").write_text(
            _spec_text("STORY-slim-951", dep_surface=_surface_table(depends="STORY-slim-952")))
        (specs / "STORY-slim-952.md").write_text(
            _spec_text("STORY-slim-952", dep_surface=_surface_table(depends="STORY-slim-951")))
        assert spec_graph.main(["--specs-dir", str(specs)]) == 1
        err = capsys.readouterr().err
        assert "STORY-slim-951" in err or "STORY-slim-952" in err

    def test_cli_write_graph(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "STORY-slim-960.md").write_text(
            _spec_text("STORY-slim-960", dep_surface=_surface_table()))
        graph_out = tmp_path / "graphs" / "story_graph.mmd"
        rc = spec_graph.main(["--specs-dir", str(specs), "--write-graph",
                              "--graph-path", str(graph_out)])
        assert rc == 0
        content = graph_out.read_text()
        assert "graph" in content and "STORY-slim-960" in content

    def test_malformed_surface_tolerated(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        # No Dependency Surface at all -> node with no deps, no crash
        (specs / "STORY-slim-970.md").write_text(_spec_text("STORY-slim-970"))
        # Garbage table -> treated as empty
        (specs / "STORY-slim-971.md").write_text(
            _spec_text("STORY-slim-971", dep_surface="not a table at all"))
        graph = spec_graph.load_story_graph(specs)
        waves = spec_graph.compute_waves(graph)
        assert sorted(waves[0]) == ["STORY-slim-970", "STORY-slim-971"]
