"""Tests for STORY-slim-094 — Unified HTML Report."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pactkit.skills.report import _parse_mmd, generate


_CODE_MMD = 'graph TD\n    A["cli.py"]\n    B["config.py"]\n    A --> B\n'
_CLASS_MMD = 'classDiagram\n    class Base\n    class Child\n    Base <|-- Child\n'
_CALL_MMD = 'graph TD\n    F1["main()"]\n    F2["run()"]\n    F1 --> F2\n'

_AUDIT_DATA = {
    "timestamp": "2026-04-16T00:00:00Z",
    "commit": "abc1234",
    "score": 76,
    "ready": True,
    "weakest": None,
    "layers": {
        "H1": {"level": 2, "name": "Structured"},
        "H2": {"level": 1, "name": "Basic"},
        "H3": {"level": 2, "name": "Structured"},
        "H4": {"level": 2, "name": "Structured"},
        "H5": {"level": 1, "name": "Basic"},
        "H6": {"level": 1, "name": "Basic"},
        "H7": {"level": 2, "name": "Structured"},
    },
    "hotspots": [
        {
            "file": "src/big_module.py",
            "score": 42,
            "complexity_avg": 15.3,
            "blast_pct": 60,
            "fan_in": 8,
            "function_count": 25,
            "has_test": False,
            "action": "Add tests + refactor",
        }
    ],
}


def _setup_graphs(tmp_path):
    """Create test .mmd files and audit JSON."""
    graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
    graphs.mkdir(parents=True)
    (graphs / 'code_graph.mmd').write_text(_CODE_MMD)
    (graphs / 'class_graph.mmd').write_text(_CLASS_MMD)
    (graphs / 'call_graph.mmd').write_text(_CALL_MMD)
    return graphs


def _setup_audit(tmp_path):
    """Create harness_audit.json."""
    gov = tmp_path / 'docs' / 'architecture' / 'governance'
    gov.mkdir(parents=True, exist_ok=True)
    (gov / 'harness_audit.json').write_text(
        json.dumps(_AUDIT_DATA, indent=2)
    )


# --- AC1: Unified HTML Generated (R1) ---

class TestAC1UnifiedOutput:
    def test_all_mode_produces_single_report_html(self, tmp_path):
        graphs = _setup_graphs(tmp_path)
        result = generate(target=str(tmp_path), all_mode=True)
        report = graphs / 'report.html'
        assert report.exists(), "report.html should be created"
        # Should NOT create individual .html files
        assert not (graphs / 'code_graph.html').exists()
        assert not (graphs / 'class_graph.html').exists()
        assert 'report.html' in result

    def test_report_contains_all_graph_data(self, tmp_path):
        graphs = _setup_graphs(tmp_path)
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert 'cli.py' in html
        assert 'Base' in html or 'Child' in html
        assert 'main()' in html or 'run()' in html


# --- AC2: Tab Switching (R1) ---

class TestAC2TabSwitching:
    def test_tabs_present_in_html(self, tmp_path):
        _setup_graphs(tmp_path)
        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert 'code_graph' in html
        assert 'class_graph' in html
        assert 'call_graph' in html


# --- AC3: Audit Data Displayed (R2) ---

class TestAC3AuditData:
    def test_audit_score_in_html(self, tmp_path):
        _setup_graphs(tmp_path)
        _setup_audit(tmp_path)
        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert '76' in html  # score


# --- AC4: No Audit Fallback (R2) ---

class TestAC4NoAuditFallback:
    def test_no_audit_shows_placeholder(self, tmp_path):
        _setup_graphs(tmp_path)
        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert 'pactkit audit' in html.lower()


# --- AC5: Hotspot Click (R3) ---

class TestAC5HotspotData:
    def test_hotspot_data_embedded(self, tmp_path):
        _setup_graphs(tmp_path)
        _setup_audit(tmp_path)
        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert 'big_module.py' in html


# --- AC6: Single File Mode Unchanged (R4) ---

class TestAC6SingleFileMode:
    def test_single_file_produces_individual_html(self, tmp_path):
        graphs = _setup_graphs(tmp_path)
        mmd_file = graphs / 'code_graph.mmd'
        result = generate(input_file=str(mmd_file))
        assert (graphs / 'code_graph.html').exists()
        assert 'report.html' not in result


# --- AC7: Self-Contained (R5) ---

class TestAC7SelfContained:
    def test_no_cdn_references(self, tmp_path):
        _setup_graphs(tmp_path)
        graphs = tmp_path / 'docs' / 'architecture' / 'graphs'
        generate(target=str(tmp_path), all_mode=True)
        html = (graphs / 'report.html').read_text()
        assert 'cdn.jsdelivr.net' not in html
        assert 'unpkg.com' not in html
        assert '<script>' in html  # D3 should be inline
