"""Tests for pactkit-report skill — STORY-slim-090."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pactkit.skills.report import _parse_mmd, _render_html, generate


# --- AC1: Basic MMD to HTML (R1, R2) ---

class TestParseMmdGraphTD:
    """R1: Parse graph TD format."""

    def test_basic_nodes_and_edges(self):
        mmd = (
            'graph TD\n'
            '    A["module_a.py"]\n'
            '    B["module_b.py"]\n'
            '    A --> B\n'
        )
        result = _parse_mmd(mmd)
        nodes = {n['id'] for n in result['nodes']}
        assert 'A' in nodes
        assert 'B' in nodes
        assert len(result['edges']) >= 1
        edge = result['edges'][0]
        assert edge['source'] == 'A'
        assert edge['target'] == 'B'

    def test_node_labels_extracted(self):
        mmd = 'graph TD\n    svc["service.py"]\n'
        result = _parse_mmd(mmd)
        node = [n for n in result['nodes'] if n['id'] == 'svc'][0]
        assert node['label'] == 'service.py'

    def test_click_href_extracted(self):
        mmd = (
            'graph TD\n'
            '    A["a.py"]\n'
            '    click A href "src/a.py"\n'
        )
        result = _parse_mmd(mmd)
        node = [n for n in result['nodes'] if n['id'] == 'A'][0]
        assert node.get('href') == 'src/a.py'

    def test_edge_with_label(self):
        mmd = 'graph TD\n    A --> B\n    C -->|imports| D\n'
        result = _parse_mmd(mmd)
        labeled = [e for e in result['edges'] if e.get('label')]
        assert any(e['label'] == 'imports' for e in labeled)

    def test_dashed_edge(self):
        mmd = 'graph TD\n    A -.-> B\n'
        result = _parse_mmd(mmd)
        assert result['edges'][0].get('style') == 'dashed'


class TestParseMmdSubgraph:
    """R1: Subgraph grouping."""

    def test_subgraph_assigns_group(self):
        mmd = (
            'graph TD\n'
            '    subgraph Commands\n'
            '        A["plan"]\n'
            '        B["act"]\n'
            '    end\n'
            '    subgraph Skills\n'
            '        C["board"]\n'
            '    end\n'
        )
        result = _parse_mmd(mmd)
        a_node = [n for n in result['nodes'] if n['id'] == 'A'][0]
        c_node = [n for n in result['nodes'] if n['id'] == 'C'][0]
        assert a_node.get('group') == 'Commands'
        assert c_node.get('group') == 'Skills'
        assert 'Commands' in result.get('groups', [])


class TestParseMmdClassDiagram:
    """AC8: classDiagram support (R1)."""

    def test_class_diagram_parsed(self):
        mmd = (
            'classDiagram\n'
            '    class Animal {\n'
            '        +speak()\n'
            '        -name\n'
            '    }\n'
            '    class Dog {\n'
            '        +bark()\n'
            '    }\n'
            '    Animal <|-- Dog\n'
        )
        result = _parse_mmd(mmd)
        nodes = {n['id'] for n in result['nodes']}
        assert 'Animal' in nodes
        assert 'Dog' in nodes
        # Inheritance edge
        assert any(e['source'] == 'Animal' and e['target'] == 'Dog' for e in result['edges'])


class TestParseLinkStyle:
    """R1: linkStyle parsing for layer violation red edges."""

    def test_linkstyle_red_parsed(self):
        mmd = (
            'graph TD\n'
            '    A --> B\n'
            '    B --> C\n'
            '    linkStyle 1 stroke:red,stroke-width:2px\n'
        )
        result = _parse_mmd(mmd)
        # Edge at index 1 (B-->C) should have style 'violation'
        assert result['edges'][1].get('style') == 'violation'


# --- AC1, AC2: HTML Rendering (R2, R6) ---

class TestRenderHtml:
    """R2, R6: HTML template content."""

    def test_html_contains_d3_cdn(self):
        graph = {'nodes': [{'id': 'A', 'label': 'a.py'}], 'edges': [], 'groups': []}
        html = _render_html(graph, mode='file', project='test')
        assert 'cdn.jsdelivr.net/npm/d3@7' in html

    def test_html_contains_metadata(self):
        graph = {'nodes': [{'id': 'A', 'label': 'a.py'}], 'edges': [], 'groups': []}
        html = _render_html(graph, mode='file', project='myproject')
        assert 'myproject' in html
        assert 'PACTKIT' in html  # logo branding

    def test_html_contains_graph_data(self):
        graph = {
            'nodes': [{'id': 'A', 'label': 'a.py'}, {'id': 'B', 'label': 'b.py'}],
            'edges': [{'source': 'A', 'target': 'B'}],
            'groups': [],
        }
        html = _render_html(graph, mode='file', project='test')
        assert '"A"' in html
        assert '"B"' in html

    def test_xss_prevention(self):
        """SEC-4: Node labels from user code must be escaped."""
        graph = {
            'nodes': [{'id': 'X', 'label': '<script>alert("xss")</script>'}],
            'edges': [],
            'groups': [],
        }
        html = _render_html(graph, mode='file', project='test')
        assert '<script>alert' not in html


# --- AC7: Generate All (R7) ---

class TestGenerate:
    """R7: Skill entry point."""

    def test_generate_single_file(self, tmp_path):
        mmd = tmp_path / 'test_graph.mmd'
        mmd.write_text('graph TD\n    A["hello"]\n    B["world"]\n    A --> B\n', encoding='utf-8')
        generate(input_file=str(mmd))
        html = tmp_path / 'test_graph.html'
        assert html.exists()
        content = html.read_text(encoding='utf-8')
        assert 'hello' in content
        assert 'world' in content

    def test_generate_all(self, tmp_path):
        graphs_dir = tmp_path / 'docs' / 'architecture' / 'graphs'
        graphs_dir.mkdir(parents=True)
        (graphs_dir / 'a.mmd').write_text('graph TD\n    X["x"]\n', encoding='utf-8')
        (graphs_dir / 'b.mmd').write_text('graph TD\n    Y["y"]\n', encoding='utf-8')
        generate(target=str(tmp_path), all_mode=True)
        assert (graphs_dir / 'a.html').exists()
        assert (graphs_dir / 'b.html').exists()

    def test_generate_custom_output(self, tmp_path):
        mmd = tmp_path / 'input.mmd'
        mmd.write_text('graph TD\n    A["a"]\n', encoding='utf-8')
        out = tmp_path / 'custom.html'
        generate(input_file=str(mmd), output_file=str(out))
        assert out.exists()


# --- AC10: Overlay (R8) ---

class TestOverlay:
    """R8: Overlay integration."""

    def test_complexity_overlay_colors_nodes(self, tmp_path):
        mmd = tmp_path / 'graph.mmd'
        mmd.write_text('graph TD\n    A["func_a"]\n    B["func_b"]\n', encoding='utf-8')
        overlay = tmp_path / 'complexity.json'
        overlay.write_text(json.dumps([
            {'function': 'func_a', 'file': 'a.py', 'complexity': 25, 'classification': 'high'},
            {'function': 'func_b', 'file': 'b.py', 'complexity': 5, 'classification': 'low'},
        ]), encoding='utf-8')
        generate(input_file=str(mmd), overlay_file=str(overlay))
        html = (tmp_path / 'graph.html').read_text(encoding='utf-8')
        # Overlay data should be embedded
        assert 'overlay' in html.lower() or 'complexity' in html.lower() or 'high' in html
