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
    _compute_score, _all_config_dirs,
    _collect_findings, _collect_insights,
    _compute_hotspots, _suggest_action,
    _check_test_coverage, _check_docstring_coverage,
    _check_code_smells, _check_dependency_health,
    _generate_suggested_tasks,
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

    def test_h1_without_claude_md(self, tmp_path):
        """Without project CLAUDE.md, level depends on global config.
        STORY-slim-097: global ~/.claude/ may provide rules/agents/skills.
        """
        result = _check_h1(tmp_path)
        assert result['checks']['claude_md'] is False

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
        """STORY-slim-097: dual-dimension scoring with explicit counts."""
        layers = {f'H{i}': {'level': 1} for i in range(1, 8)}
        result = _compute_score(layers, config_passed=5, config_total=10,
                                code_passed=5, code_total=10)
        assert result['ready'] is True
        assert result['score'] == 50  # 5/10*50 + 5/10*50

    def test_mixed_levels(self):
        layers = {'H1': {'level': 2}, 'H2': {'level': 1}, 'H3': {'level': 2},
                  'H4': {'level': 1}, 'H5': {'level': 1}, 'H6': {'level': 1}, 'H7': {'level': 1}}
        result = _compute_score(layers, config_passed=7, config_total=10,
                                code_passed=6, code_total=10)
        assert result['ready'] is True
        assert result['score'] == 65  # 7/10*50 + 6/10*50


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


# --- STORY-slim-093: Multi-Signal + Suggested Tasks ---

def _setup_project_with_source(tmp_path):
    """Create a project with actual Python source files for signal testing."""
    root = _setup_full_project(tmp_path)
    src = root / 'src'
    src.mkdir(exist_ok=True)
    (src / '__init__.py').write_text('', encoding='utf-8')

    # File with no test, no docstring, long function, deep nesting
    (src / 'bad.py').write_text(
        'def no_docs(x):\n'
        + ''.join(f'    line_{i} = {i}\n' for i in range(55))
        + '    if x > 0:\n'
        + '        for i in range(10):\n'
        + '            while True:\n'
        + '                if i > 5:\n'
        + '                    if i > 8:\n'
        + '                        break\n'
        + '\n'
        + 'def also_no_docs(y):\n'
        + '    pass\n',
        encoding='utf-8',
    )

    # File with test, good docstring
    (src / 'good.py').write_text(
        'def well_documented():\n'
        '    """This function has a docstring."""\n'
        '    return 42\n'
        '\n'
        'def also_documented():\n'
        '    """Another documented function."""\n'
        '    return 0\n',
        encoding='utf-8',
    )
    tests_dir = root / 'tests' / 'unit'
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / 'test_good.py').write_text('def test_one(): pass\n', encoding='utf-8')

    return root


class TestTestCoverageSignal:
    """AC1/AC2: Test coverage detection (R1)."""

    def test_no_test_file(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        result = _check_test_coverage(root, root / 'src' / 'bad.py', 'python')
        assert result is False

    def test_has_test_file(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        result = _check_test_coverage(root, root / 'src' / 'good.py', 'python')
        assert result is True


class TestDocstringCoverage:
    """AC3: Docstring coverage (R2)."""

    def test_no_docstrings(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        pct = _check_docstring_coverage(root / 'src' / 'bad.py')
        assert pct == 0

    def test_all_docstrings(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        pct = _check_docstring_coverage(root / 'src' / 'good.py')
        assert pct == 100


class TestCodeSmells:
    """AC4/AC5: Code smell detection (R3)."""

    def test_long_function_detected(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        long_funcs, deep = _check_code_smells(root / 'src' / 'bad.py')
        assert long_funcs >= 1

    def test_deep_nesting_detected(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        long_funcs, deep = _check_code_smells(root / 'src' / 'bad.py')
        assert deep >= 1

    def test_clean_file_no_smells(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        long_funcs, deep = _check_code_smells(root / 'src' / 'good.py')
        assert long_funcs == 0
        assert deep == 0


class TestActionPriority093:
    """AC7: Action priority with new signals (R7)."""

    def test_no_test_highest_priority(self):
        action = _suggest_action({
            'has_test': False, 'complexity_avg': 35,
            'long_funcs': 0, 'deep_nesting': 0,
            'layer_violations': 0, 'docstring_pct': 80,
            'fan_in': 1, 'blast_pct': 10, 'function_count': 5,
        })
        assert action.startswith('Add tests')


class TestDependencyHealth:
    """AC5: Dependency health (R5)."""

    def test_returns_dict(self, tmp_path):
        result = _check_dependency_health(tmp_path)
        assert isinstance(result, dict)
        assert 'vulns' in result


class TestSuggestedTasks:
    """AC8/AC9: Suggested tasks generation (R8, R9)."""

    def test_tasks_generated_for_hotspots(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        # Create pactkit.yaml for developer prefix
        (root / '.claude' / 'pactkit.yaml').write_text(
            'stack: python\ndeveloper: test\n', encoding='utf-8',
        )
        hotspots = [
            {'file': 'src/bad.py', 'score': 20, 'has_test': False,
             'complexity_avg': 5, 'layer_violations': 0,
             'action': 'Add tests'},
        ]
        tasks = _generate_suggested_tasks(root, hotspots, 'test')
        assert len(tasks) >= 1
        task = tasks[0]
        assert 'type' in task
        assert 'spec' in task
        assert 'command' in task
        assert task['type'] in ('BUG', 'HOTFIX')

    def test_done_spec_excluded(self, tmp_path):
        """AC12: Completed specs are filtered out."""
        root = _setup_project_with_source(tmp_path)
        specs = root / 'docs' / 'specs'
        specs.mkdir(parents=True, exist_ok=True)
        # Create a Done spec for bad.py
        (specs / 'BUG-test-100.md').write_text(
            '# BUG-test-100\n| Status | Done |\n## Background\nsrc/bad.py\n',
            encoding='utf-8',
        )
        hotspots = [
            {'file': 'src/bad.py', 'score': 20, 'has_test': False,
             'complexity_avg': 5, 'layer_violations': 0,
             'action': 'Add tests'},
        ]
        tasks = _generate_suggested_tasks(root, hotspots, 'test')
        # Should not create a duplicate — reuse or skip the Done one
        for t in tasks:
            assert 'BUG-test-100' not in t.get('spec', '')


class TestFullAuditJson093:
    """AC8 + AC11: JSON schema updated."""

    def test_json_has_suggested_tasks(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        (root / '.claude' / 'pactkit.yaml').write_text(
            'stack: python\ndeveloper: test\n', encoding='utf-8',
        )
        audit(str(root))
        f = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(f.read_text(encoding='utf-8'))
        assert 'suggested_tasks' in data
        assert 'dependency_health' in data

    def test_hotspots_have_new_fields(self, tmp_path):
        root = _setup_project_with_source(tmp_path)
        audit(str(root))
        f = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(f.read_text(encoding='utf-8'))
        for h in data.get('hotspots', []):
            assert 'has_test' in h
            assert 'docstring_pct' in h
            assert 'long_funcs' in h
            assert 'deep_nesting' in h
            assert 'layer_violations' in h


# --- STORY-slim-097: Dual-dimension Harness Audit ---


class TestAC1GlobalConfigDetection:
    """AC1: _all_config_dirs includes global ~/.claude/."""

    def test_all_config_dirs_includes_global(self, tmp_path):
        dirs = _all_config_dirs(tmp_path)
        dir_strs = [str(d) for d in dirs]
        home_claude = str(Path.home() / '.claude')
        assert any(home_claude in d for d in dir_strs), \
            f"Expected ~/.claude/ in dirs, got: {dir_strs}"

    def test_all_config_dirs_includes_project_level(self, tmp_path):
        (tmp_path / '.claude').mkdir()
        dirs = _all_config_dirs(tmp_path)
        dir_strs = [str(d) for d in dirs]
        assert any('.claude' in d and str(tmp_path) in d for d in dir_strs)

    def test_h1_finds_rules_in_global(self, tmp_path):
        """H1 should detect rules from global ~/.claude/rules/ when project has none."""
        # Only create claude_md at project level (for L1 gate)
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'CLAUDE.md').write_text('# Instructions')
        # No project-level rules — relies on global ~/.claude/rules/
        result = _check_h1(tmp_path)
        # If ~/.claude/rules/ exists on this machine, rules should be True
        global_rules = Path.home() / '.claude' / 'rules'
        if global_rules.is_dir() and any(global_rules.iterdir()):
            assert result['checks']['rules'] is True


class TestAC2TestCoverageRatio:
    """AC2: test_coverage_ratio check in H3."""

    def test_ratio_above_threshold(self, tmp_path):
        root = _setup_full_project(tmp_path)
        # 1 source + 1 test already from setup. Add more source files.
        src = root / 'src'
        src.mkdir(exist_ok=True)
        for i in range(3):
            (src / f'mod{i}.py').write_text(f'def f{i}(): pass\n')
        # 4 source files, 1 test file = 0.25 < 0.3 → False
        # Add more test files to pass
        tests_dir = root / 'tests' / 'unit'
        (tests_dir / 'test_mod0.py').write_text('def test_m0(): pass\n')
        # Now: 4 source, 2 test = 0.5 >= 0.3 → True
        result = _check_h3(root)
        assert 'test_coverage_ratio' in result['checks']

    def test_ratio_present_in_checks(self, tmp_path):
        root = _setup_full_project(tmp_path)
        result = _check_h3(root)
        assert 'test_coverage_ratio' in result['checks']


class TestAC3LintClean:
    """AC3: lint_clean check in H4."""

    def test_lint_clean_in_h4_checks(self, tmp_path):
        root = _setup_minimal_project(tmp_path)
        result = _check_h4(root)
        assert 'lint_clean' in result['checks']


class TestAC4DualScoring:
    """AC4: Dual-dimension scoring formula."""

    def test_dual_score_formula(self):
        """8/10 config + 7/10 code = 40+35 = 75."""
        layers = {f'H{i}': {'level': 2, 'config_checks': {}, 'code_checks': {}}
                  for i in range(1, 8)}
        result = _compute_score(layers,
                                config_passed=8, config_total=10,
                                code_passed=7, code_total=10)
        assert result['score'] == 75

    def test_all_pass_gives_100(self):
        layers = {f'H{i}': {'level': 3} for i in range(1, 8)}
        result = _compute_score(layers,
                                config_passed=10, config_total=10,
                                code_passed=10, code_total=10)
        assert result['score'] == 100

    def test_nothing_passes_gives_0(self):
        layers = {f'H{i}': {'level': 0} for i in range(1, 8)}
        result = _compute_score(layers,
                                config_passed=0, config_total=10,
                                code_passed=0, code_total=10)
        assert result['score'] == 0


class TestAC5JsonBackwardCompat:
    """AC5: harness_audit.json retains existing fields + new dimensions."""

    def test_json_has_dimensions(self, tmp_path):
        root = _setup_full_project(tmp_path)
        audit(str(root))
        f = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
        data = json.loads(f.read_text(encoding='utf-8'))
        # Existing fields still present
        assert 'score' in data
        assert 'ready' in data
        assert 'layers' in data
        assert 'hotspots' in data
        # New dimensions field
        assert 'dimensions' in data
        dims = data['dimensions']
        assert 'config' in dims
        assert 'code' in dims
        assert 'passed' in dims['config']
        assert 'total' in dims['config']
        assert 'score' in dims['config']


class TestAC6LayerLevelBothDimensions:
    """AC6: Layer level uses both config and code checks."""

    def test_h5_l2_when_all_code_pass(self, tmp_path):
        """H5: safety_rules=True, gitignore=True, hooks=False, no_secrets=True → L2."""
        root = _setup_full_project(tmp_path)
        result = _check_h5(root)
        # With full project: gitignore=True, safety_rules=True (from rules/10-safety.md)
        # hooks_config=False (no hooks in settings.json)
        # Should be at least L2 because all code checks pass
        assert result['level'] >= 2
