"""Tests for pactkit-audit skill — STORY-slim-091 H1-H7 AI Readiness Assessment."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pactkit.audit import (
    _check_h1, _check_h2, _check_h3, _check_h5, _check_h7,
    _check_h4, _check_h6,
    _compute_score,
    _collect_findings, _collect_insights,
    _compute_hotspots, _suggest_action,
    audit,
)


def _setup_minimal_project(tmp_path):
    """Create a minimal project that passes L1 on most layers."""
    # H1: Prompt Engineering
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    (claude_dir / 'CLAUDE.md').write_text('# Instructions', encoding='utf-8')

    # H2: Context Engineering
    docs = tmp_path / 'docs' / 'product'
    docs.mkdir(parents=True)
    (docs / 'context.md').write_text('# Context\n> Last updated: 2026-04-16', encoding='utf-8')

    # H3: Process Governance
    (docs / 'sprint_board.md').write_text('# Sprint Board\n## Backlog\n## Done\n', encoding='utf-8')

    # H5: Safety
    (tmp_path / '.gitignore').write_text('.env\n*.pyc\n', encoding='utf-8')

    # H6: Observability
    gov = tmp_path / 'docs' / 'architecture' / 'governance'
    gov.mkdir(parents=True)
    (gov / 'lessons.md').write_text('| Date | Lesson | Context |\n', encoding='utf-8')

    # H7: Evolution
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "test"\nversion = "1.0.0"\n', encoding='utf-8')

    # pactkit.yaml for H4
    (claude_dir / 'pactkit.yaml').write_text('stack: python\nversion: 2.10.0\n', encoding='utf-8')

    return tmp_path


def _setup_full_project(tmp_path):
    """Create a project that reaches L2+ on most layers."""
    root = _setup_minimal_project(tmp_path)
    claude_dir = root / '.claude'

    # H1 L2: rules + agents
    rules_dir = claude_dir / 'rules'
    rules_dir.mkdir()
    (rules_dir / '01-core.md').write_text('# Core', encoding='utf-8')
    agents_dir = claude_dir / 'agents'
    agents_dir.mkdir()
    (agents_dir / 'developer.md').write_text('# Developer', encoding='utf-8')

    # H2 L2: specs
    specs_dir = root / 'docs' / 'specs'
    specs_dir.mkdir(parents=True)
    (specs_dir / 'STORY-001.md').write_text('# STORY-001\n| Status | Done |', encoding='utf-8')

    # H3 L2: tests + CI
    tests_dir = root / 'tests' / 'unit'
    tests_dir.mkdir(parents=True)
    (tests_dir / 'test_example.py').write_text('def test_one(): pass\n', encoding='utf-8')
    ci_dir = root / '.github' / 'workflows'
    ci_dir.mkdir(parents=True)
    (ci_dir / 'ci.yml').write_text('name: CI\non: push\n', encoding='utf-8')

    # H5 L2: safety rules
    (rules_dir / '10-safety.md').write_text('# Safety\nSecrets: NEVER print passwords', encoding='utf-8')

    # H7 L2: CHANGELOG
    (root / 'CHANGELOG.md').write_text('# Changelog\n## 1.0.0\n', encoding='utf-8')

    return root


# --- AC1: Full Audit (R1, R2, R3, R5, R7, R8) ---

class TestLayerChecks:
    def test_h1_l1_with_claude_md(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h1(root)
        assert result['level'] >= 1
        assert result['checks']['claude_md'] is True

    def test_h1_l0_without_claude_md(self, tmp_path):
        result = _check_h1(tmp_path)
        assert result['level'] == 0

    def test_h2_l1_with_context(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h2(root)
        assert result['level'] >= 1

    def test_h3_l1_with_board(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h3(root)
        assert result['level'] >= 1

    def test_h5_l1_with_gitignore(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h5(root)
        assert result['level'] >= 1

    def test_h7_l1_with_version(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h7(root)
        assert result['level'] >= 1

    def test_h4_l1_with_pactkit_yaml(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h4(root)
        assert result['level'] >= 1

    def test_h6_l1_with_lessons(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h6(root)
        assert result['level'] >= 1


# --- AC2: AI Ready (R8) ---

class TestScoring:
    def test_all_l1_is_ready(self):
        layers = {f'H{i}': {'level': 1} for i in range(1, 8)}
        result = _compute_score(layers)
        assert result['ready'] is True
        assert result['score'] == round(7 / 21 * 100)

    def test_mixed_levels(self):
        layers = {'H1': {'level': 2}, 'H2': {'level': 1}, 'H3': {'level': 2},
                  'H4': {'level': 1}, 'H5': {'level': 1}, 'H6': {'level': 1}, 'H7': {'level': 1}}
        result = _compute_score(layers)
        assert result['ready'] is True
        assert result['score'] == round(9 / 21 * 100)


# --- AC3: Not Ready (R8) ---

class TestNotReady:
    def test_one_l0_means_not_ready(self):
        layers = {f'H{i}': {'level': 2} for i in range(1, 8)}
        layers['H6'] = {'level': 0}
        result = _compute_score(layers)
        assert result['ready'] is False

    def test_empty_project_not_ready(self, tmp_path):
        result = audit(str(tmp_path), json_only=True)
        data = json.loads(result)
        assert data['ready'] is False


# --- AC4: Findings (R9) ---

class TestFindings:
    def test_findings_is_list(self, tmp_path):
        root = _setup_full_project(tmp_path)
        findings = _collect_findings(root)
        assert isinstance(findings, list)
        for f in findings:
            assert 'severity' in f
            assert 'category' in f
            assert 'message' in f


# --- AC5: Insights (R10) ---

class TestInsights:
    def test_insights_structure(self, tmp_path):
        root = _setup_full_project(tmp_path)
        insights = _collect_insights(root)
        assert 'high_fan_in' in insights
        assert 'blast_top10' in insights
        assert 'circular_deps' in insights
        assert 'god_objects' in insights

    def test_circular_dep_detected(self, tmp_path):
        """Two files importing each other should be detected via code_graph.mmd."""
        root = _setup_full_project(tmp_path)
        graphs = root / 'docs' / 'architecture' / 'graphs'
        graphs.mkdir(parents=True, exist_ok=True)
        # Create a code_graph.mmd with circular dependency: A→B and B→A
        (graphs / 'code_graph.mmd').write_text(
            'graph TD\n'
            '    A["a.py"]\n'
            '    B["b.py"]\n'
            '    A --> B\n'
            '    B --> A\n',
            encoding='utf-8'
        )
        insights = _collect_insights(root)
        assert len(insights['circular_deps']) >= 1


# --- AC6: JSON File Written (R11) ---

class TestAuditFile:
    def test_json_file_written(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        audit(str(root))
        audit_file = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        assert audit_file.exists()
        data = json.loads(audit_file.read_text(encoding='utf-8'))
        assert 'timestamp' in data
        assert 'score' in data
        assert 'ready' in data
        assert 'layers' in data

    def test_json_output_mode(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = audit(str(root), json_only=True)
        data = json.loads(result)
        assert isinstance(data['score'], int)


# --- AC9: Layer-Specific Check (R14) ---

class TestLayerSpecific:
    def test_single_layer_check(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = audit(str(root), layer='H1', json_only=True)
        data = json.loads(result)
        assert 'H1' in data['layers']
        # Only H1 should be checked; others should be absent or L0
        assert data['layers']['H1']['level'] >= 1


# --- STORY-slim-092: Hotspot Aggregation ---

class TestHotspotAggregation:
    """AC1: File-level hotspot aggregation (R1)."""

    def test_hotspots_are_list(self, tmp_path):
        root = _setup_full_project(tmp_path)
        hotspots = _compute_hotspots(root)
        assert isinstance(hotspots, list)

    def test_hotspots_have_required_fields(self, tmp_path):
        root = _setup_full_project(tmp_path)
        # Add some source files with functions
        src = root / 'src'
        src.mkdir(exist_ok=True)
        (src / '__init__.py').write_text('', encoding='utf-8')
        (src / 'big.py').write_text(
            'def a():\n  if True:\n    if True:\n      pass\n'
            'def b():\n  for i in range(10):\n    while True:\n      break\n',
            encoding='utf-8'
        )
        hotspots = _compute_hotspots(root)
        for h in hotspots:
            assert 'file' in h
            assert 'score' in h
            assert 'complexity_avg' in h
            assert 'blast_pct' in h
            assert 'fan_in' in h
            assert 'action' in h

    def test_hotspots_max_10(self, tmp_path):
        root = _setup_full_project(tmp_path)
        hotspots = _compute_hotspots(root)
        assert len(hotspots) <= 10

    def test_hotspots_sorted_descending(self, tmp_path):
        root = _setup_full_project(tmp_path)
        hotspots = _compute_hotspots(root)
        if len(hotspots) >= 2:
            assert hotspots[0]['score'] >= hotspots[1]['score']


class TestSuggestAction:
    """AC2: Actionable suggestions (R2)."""

    def test_high_complexity_suggests_split(self):
        action = _suggest_action({'complexity_avg': 35, 'fan_in': 1, 'blast_pct': 10, 'function_count': 5})
        assert 'Split' in action

    def test_high_fan_in_suggests_stabilize(self):
        action = _suggest_action({'complexity_avg': 5, 'fan_in': 7, 'blast_pct': 10, 'function_count': 5})
        assert 'Stabilize' in action

    def test_high_blast_suggests_isolate(self):
        action = _suggest_action({'complexity_avg': 5, 'fan_in': 1, 'blast_pct': 60, 'function_count': 5})
        assert 'Isolate' in action

    def test_god_object_suggests_decompose(self):
        action = _suggest_action({'complexity_avg': 5, 'fan_in': 1, 'blast_pct': 10, 'function_count': 20})
        assert 'Decompose' in action


class TestSlimJson:
    """AC3: Slim JSON file (R3)."""

    def test_json_no_findings_key(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        audit(str(root))
        audit_file = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(audit_file.read_text(encoding='utf-8'))
        assert 'findings' not in data
        assert 'insights' not in data

    def test_json_has_hotspots(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        audit(str(root))
        audit_file = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(audit_file.read_text(encoding='utf-8'))
        assert 'hotspots' in data
        assert isinstance(data['hotspots'], list)

    def test_layers_slim_no_checks(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        audit(str(root))
        audit_file = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(audit_file.read_text(encoding='utf-8'))
        for layer_data in data['layers'].values():
            assert 'checks' not in layer_data
            assert 'level' in layer_data
            assert 'name' in layer_data


class TestVerboseMode:
    """AC4/AC5: Verbose vs concise (R4)."""

    def test_default_concise(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = audit(str(root))
        # Should NOT contain per-function detail lines
        assert 'CRITICAL' not in result or result.count('\n') < 30

    def test_verbose_shows_findings(self, tmp_path):
        root = _setup_full_project(tmp_path)
        result = audit(str(root), verbose=True)
        # Verbose should include findings section
        assert 'Findings' in result or 'findings' in result.lower()

    def test_json_default_slim(self, tmp_path):
        """AC7: --json without --verbose matches harness_audit.json format."""
        root = _setup_minimal_project(tmp_path)
        result = audit(str(root), json_only=True)
        data = json.loads(result)
        assert 'findings' not in data
        assert 'hotspots' in data

    def test_json_verbose_full(self, tmp_path):
        """AC6: --json --verbose includes findings + insights."""
        root = _setup_full_project(tmp_path)
        result = audit(str(root), json_only=True, verbose=True)
        data = json.loads(result)
        assert 'findings' in data
        assert 'insights' in data
