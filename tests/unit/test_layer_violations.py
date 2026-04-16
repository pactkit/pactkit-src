"""Tests for layer violation detection — STORY-slim-089 R5/R6."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _exec_visualize():
    from pactkit.prompts import VISUALIZE_SOURCE
    g = {}
    exec(VISUALIZE_SOURCE, g)
    return g


def _create_layered_project(tmp_path):
    """Create a project with clear architectural layers and one violation."""
    # UI layer
    ui = tmp_path / 'src' / 'ui'
    ui.mkdir(parents=True)
    (ui / '__init__.py').write_text('', encoding='utf-8')
    (ui / 'views.py').write_text(
        'from src.services.api import fetch_data\n'
        '\n'
        'def render():\n'
        '    data = fetch_data()\n'
        '    return data\n',
        encoding='utf-8'
    )

    # Services layer
    svc = tmp_path / 'src' / 'services'
    svc.mkdir(parents=True)
    (svc / '__init__.py').write_text('', encoding='utf-8')
    (svc / 'api.py').write_text(
        'from src.utils.helper import format_data\n'
        '\n'
        'def fetch_data():\n'
        '    return format_data({})\n',
        encoding='utf-8'
    )

    # Utils layer — VIOLATION: imports from services (lower importing higher)
    utils = tmp_path / 'src' / 'utils'
    utils.mkdir(parents=True)
    (utils / '__init__.py').write_text('', encoding='utf-8')
    (utils / 'helper.py').write_text(
        'from src.services.api import fetch_data\n'
        '\n'
        'def format_data(data):\n'
        '    return str(data)\n',
        encoding='utf-8'
    )

    # Init files
    (tmp_path / 'src' / '__init__.py').write_text('', encoding='utf-8')
    return tmp_path


class TestLayerViolationDefaultModel:
    """AC7: Layer violation — default model (R5)."""

    def test_detects_utils_importing_services(self, tmp_path):
        """utils/helper.py importing services/api.py should be flagged."""
        root = _create_layered_project(tmp_path)
        g = _exec_visualize()
        result = g['layers'](str(root))
        data = json.loads(result)

        assert data['total_count'] >= 1
        violations = data['violations']
        found = False
        for v in violations:
            if 'helper' in v['importer'] and 'api' in v['importee']:
                assert v['importer_layer'] == 'utils'
                assert v['importee_layer'] == 'services'
                found = True
        assert found, f"Expected violation utils→services not found in {violations}"

    def test_valid_imports_not_flagged(self, tmp_path):
        """ui importing services (higher→lower) should NOT be flagged."""
        root = _create_layered_project(tmp_path)
        g = _exec_visualize()
        result = g['layers'](str(root))
        data = json.loads(result)

        for v in data['violations']:
            assert not ('views' in v['importer'] and 'api' in v['importee']), \
                "ui→services is a valid import and should not be flagged"

    def test_layer_summary_present(self, tmp_path):
        """Output should include layer_summary with file counts per layer."""
        root = _create_layered_project(tmp_path)
        g = _exec_visualize()
        result = g['layers'](str(root))
        data = json.loads(result)

        assert 'layer_summary' in data
        summary = data['layer_summary']
        assert isinstance(summary, dict)


class TestLayerViolationCustomConfig:
    """AC8: Layer violation — custom config (R5)."""

    def test_custom_layers_from_yaml(self, tmp_path):
        """Custom layers in pactkit.yaml should override defaults."""
        root = _create_layered_project(tmp_path)

        # Write custom pactkit.yaml with only 2 layers
        claude_dir = root / '.claude'
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / 'pactkit.yaml').write_text(
            'stack: python\n'
            'visualize:\n'
            '  layers:\n'
            '    - name: frontend\n'
            '      patterns: ["*/ui/*"]\n'
            '    - name: backend\n'
            '      patterns: ["*/services/*", "*/utils/*"]\n',
            encoding='utf-8'
        )

        g = _exec_visualize()
        result = g['layers'](str(root))
        data = json.loads(result)

        # With this custom model, utils and services are in the SAME layer,
        # so utils→services is NOT a violation
        for v in data['violations']:
            assert not (v.get('importer_layer') == 'backend' and v.get('importee_layer') == 'backend'), \
                "Same-layer imports should not be flagged"


class TestLayerViolationMermaidAnnotation:
    """AC10: Layer violation Mermaid annotation (R6)."""

    def test_file_graph_with_layers_has_red_styles(self, tmp_path):
        """visualize --mode file --layers should annotate violations in red."""
        root = _create_layered_project(tmp_path)
        g = _exec_visualize()
        result = g['visualize'](str(root), mode='file', show_layers=True)

        # Read the generated mmd file
        mmd_path = root / 'docs' / 'architecture' / 'graphs' / 'code_graph.mmd'
        assert mmd_path.exists(), f"Expected {mmd_path} to be created"
        content = mmd_path.read_text(encoding='utf-8')

        assert 'linkStyle' in content, "Should have linkStyle for violation edges"
        assert 'stroke:red' in content, "Violation edges should be styled red"

    def test_file_graph_with_layers_has_legend(self, tmp_path):
        """visualize --mode file --layers should include a layer model legend."""
        root = _create_layered_project(tmp_path)
        g = _exec_visualize()
        g['visualize'](str(root), mode='file', show_layers=True)

        mmd_path = root / 'docs' / 'architecture' / 'graphs' / 'code_graph.mmd'
        content = mmd_path.read_text(encoding='utf-8')

        assert 'Layer Model' in content, "Should have legend subgraph"
        assert '_legend_' in content, "Should have legend nodes"


class TestLayerViolationNoConfig:
    """AC9: Layer violation — no config (R5)."""

    def test_default_model_used_without_yaml(self, tmp_path):
        """Without pactkit.yaml, the 5-layer default should be used."""
        root = _create_layered_project(tmp_path)
        # No .claude/pactkit.yaml exists
        g = _exec_visualize()
        result = g['layers'](str(root))
        data = json.loads(result)

        # Should still work and detect violations
        assert isinstance(data['violations'], list)
        assert data['total_count'] >= 1
