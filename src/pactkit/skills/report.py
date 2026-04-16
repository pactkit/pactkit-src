#!/usr/bin/env python3
"""PactKit Report Skill — Interactive HTML from .mmd files (STORY-slim-090).

Parses Mermaid graph files and generates single-file D3 force-directed HTML reports.
"""
import argparse
import html as _html_mod
import json
import re
from datetime import datetime, timezone
from pathlib import Path


# --- MMD Parser (R1) ---


def _parse_mmd(mmd_content):
    """Parse a Mermaid .mmd file into {nodes, edges, groups}.

    Supports graph TD/LR and classDiagram formats.
    """
    lines = mmd_content.strip().splitlines()
    if not lines:
        return {'nodes': [], 'edges': [], 'groups': []}

    first = lines[0].strip().lower()
    if first.startswith('classdiagram'):
        return _parse_class_diagram(lines)
    return _parse_graph_td(lines)


def _parse_graph_td(lines):
    """Parse graph TD/LR format."""
    nodes = {}  # id -> {id, label, group?, href?}
    edges = []
    groups = []
    hrefs = {}  # node_id -> href from click lines
    link_styles = {}  # edge_index -> style

    current_group = None
    edge_index = 0

    # Regex patterns
    # Node: A["label"] or A["label with spaces"]
    re_node = re.compile(r'^\s*(\w+)\["([^"]+)"\]')
    # Edge: A --> B  or  A -->|label| B  or  A -.-> B  or  A -.->\|label\| B
    re_edge = re.compile(r'^\s*(\w+)\s+(-->|-.->)(?:\|([^|]*)\|)?\s*(\w+)')
    # Click: click nodeId href "path"
    re_click = re.compile(r'^\s*click\s+(\w+)\s+href\s+"([^"]+)"')
    # Subgraph: subgraph "Name" or subgraph Name
    re_subgraph = re.compile(r'^\s*subgraph\s+"?([^"]+?)"?\s*$')
    # linkStyle N stroke:red...
    re_linkstyle = re.compile(r'^\s*linkStyle\s+(\d+)\s+.*stroke\s*:\s*red')

    for line in lines:
        stripped = line.strip()

        # Skip header
        if stripped.lower().startswith('graph '):
            continue

        # Subgraph start
        m = re_subgraph.match(stripped)
        if m:
            current_group = m.group(1).strip()
            if current_group not in groups:
                groups.append(current_group)
            continue

        # Subgraph end
        if stripped == 'end':
            current_group = None
            continue

        # Click href
        m = re_click.match(stripped)
        if m:
            hrefs[m.group(1)] = m.group(2)
            continue

        # linkStyle
        m = re_linkstyle.match(stripped)
        if m:
            link_styles[int(m.group(1))] = 'violation'
            continue

        # Node definition
        m = re_node.match(stripped)
        if m:
            nid, label = m.group(1), m.group(2)
            if nid not in nodes:
                nodes[nid] = {'id': nid, 'label': label}
            else:
                nodes[nid]['label'] = label
            if current_group:
                nodes[nid]['group'] = current_group
            continue

        # Edge
        m = re_edge.match(stripped)
        if m:
            src, arrow, label, dst = m.group(1), m.group(2), m.group(3), m.group(4)
            edge = {'source': src, 'target': dst}
            if label:
                edge['label'] = label
            if arrow == '-.->':
                edge['style'] = 'dashed'
            # Ensure nodes exist
            if src not in nodes:
                nodes[src] = {'id': src, 'label': src}
            if dst not in nodes:
                nodes[dst] = {'id': dst, 'label': dst}
            if current_group:
                if 'group' not in nodes[src]:
                    nodes[src]['group'] = current_group
                if 'group' not in nodes[dst]:
                    nodes[dst]['group'] = current_group
            edges.append(edge)
            edge_index += 1
            continue

        # Style lines (ignored) or NOTE lines (ignored)

    # Apply click hrefs
    for nid, href in hrefs.items():
        if nid in nodes:
            nodes[nid]['href'] = href

    # Apply linkStyle overrides
    for idx, style in link_styles.items():
        if idx < len(edges):
            edges[idx]['style'] = style

    return {'nodes': list(nodes.values()), 'edges': edges, 'groups': groups}


def _parse_class_diagram(lines):
    """Parse classDiagram format."""
    nodes = {}
    edges = []

    # Regex patterns
    re_class = re.compile(r'^\s*class\s+(\w+)')
    re_member = re.compile(r'^\s+([+\-#])(\w+)')
    re_inherit = re.compile(r'^\s*(\w+)\s+<\|--\s+(\w+)')
    re_assoc = re.compile(r'^\s*(\w+)\s+-->\s+(\w+)')

    current_class = None
    current_members = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower() == 'classdiagram':
            continue

        # Class definition start
        m = re_class.match(stripped)
        if m:
            # Flush previous class
            if current_class and current_class in nodes:
                nodes[current_class]['members'] = current_members
            current_class = m.group(1)
            current_members = []
            if current_class not in nodes:
                nodes[current_class] = {'id': current_class, 'label': current_class}
            continue

        # Class member
        m = re_member.match(line)  # Use original line for indentation
        if m and current_class:
            current_members.append(line.strip())
            continue

        # Closing brace
        if stripped == '}' and current_class:
            nodes[current_class]['members'] = current_members
            current_class = None
            current_members = []
            continue

        # Inheritance: Base <|-- Derived
        m = re_inherit.match(stripped)
        if m:
            base, derived = m.group(1), m.group(2)
            if base not in nodes:
                nodes[base] = {'id': base, 'label': base}
            if derived not in nodes:
                nodes[derived] = {'id': derived, 'label': derived}
            edges.append({'source': base, 'target': derived, 'label': 'extends', 'style': 'dashed'})
            continue

        # Association: A --> B
        m = re_assoc.match(stripped)
        if m:
            src, dst = m.group(1), m.group(2)
            if src not in nodes:
                nodes[src] = {'id': src, 'label': src}
            if dst not in nodes:
                nodes[dst] = {'id': dst, 'label': dst}
            edges.append({'source': src, 'target': dst})
            continue

    # Flush last class
    if current_class and current_class in nodes:
        nodes[current_class]['members'] = current_members

    return {'nodes': list(nodes.values()), 'edges': edges, 'groups': []}


# --- HTML Renderer (R2, R3, R4, R5, R6) ---

_D3_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root { --bg: #ffffff; --fg: #1a1a2e; --node: #4d9fff; --edge: #888; --panel: #f5f5f5; --border: #ddd; }
.dark { --bg: #1a1a2e; --fg: #e0e0e0; --node: #6db3f8; --edge: #555; --panel: #16213e; --border: #333; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--fg); transition: background .3s, color .3s; }
#toolbar { position: fixed; top: 0; left: 0; right: 0; z-index: 10; display: flex; align-items: center; gap: 12px; padding: 8px 16px; background: var(--panel); border-bottom: 1px solid var(--border); }
#toolbar h1 { font-size: 14px; flex-shrink: 0; }
#search { padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--bg); color: var(--fg); font-size: 13px; width: 220px; }
#match-count { font-size: 12px; color: #888; min-width: 80px; }
.btn { padding: 4px 10px; border: 1px solid var(--border); border-radius: 4px; background: var(--panel); color: var(--fg); cursor: pointer; font-size: 12px; }
.btn:hover { background: var(--border); }
#stats { font-size: 12px; color: #888; margin-left: auto; }
svg { width: 100%; height: calc(100vh - 42px); margin-top: 42px; }
.node-circle { cursor: grab; }
.node-circle:active { cursor: grabbing; }
.node-label { font-size: 11px; pointer-events: none; fill: var(--fg); }
.link { stroke: var(--edge); stroke-width: 1.5; fill: none; marker-end: url(#arrow); }
.link.dashed { stroke-dasharray: 5 3; }
.link.violation { stroke: #e74c3c; stroke-width: 2.5; }
.faded { opacity: 0.1; }
.highlight { animation: pulse .6s ease-in-out 3; }
@keyframes pulse { 0%,100% { r: 8; } 50% { r: 14; } }
#detail { position: fixed; bottom: 16px; right: 16px; padding: 12px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; font-size: 12px; display: none; max-width: 300px; }
footer { position: fixed; bottom: 4px; left: 16px; font-size: 10px; color: #888; }
</style>
</head>
<body>
<div id="toolbar">
  <h1>{{TITLE}}</h1>
  <input id="search" type="text" placeholder="Search nodes...">
  <span id="match-count"></span>
  <button class="btn" id="theme-toggle">Dark</button>
  <button class="btn" id="fullscreen-btn">Fullscreen</button>
  <span id="stats">{{STATS}}</span>
</div>
<svg id="graph">
  <defs>
    <marker id="arrow" viewBox="0 0 10 6" refX="20" refY="3" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 3 L 0 6 Z" fill="var(--edge)"/>
    </marker>
  </defs>
</svg>
<div id="detail"></div>
<footer>{{FOOTER}}</footer>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script>
const DATA = {{GRAPH_JSON}};
const OVERLAY = {{OVERLAY_JSON}};
const GROUPS = DATA.groups || [];
const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
const groupColor = (g) => g ? colorScale(GROUPS.indexOf(g) % 10) : 'var(--node)';

// Overlay: complexity color scale
const cxScale = d3.scaleLinear().domain([1, 10, 20, 30]).range(['#27ae60', '#f1c40f', '#e67e22', '#e74c3c']).clamp(true);
function nodeColor(d) {
  if (OVERLAY && OVERLAY.length) {
    const match = OVERLAY.find(o => d.label && d.label.includes(o.function));
    if (match) return cxScale(match.complexity);
  }
  return groupColor(d.group);
}

const svg = d3.select('#graph');
const g = svg.append('g');

// Zoom + Pan (R3)
const zoom = d3.zoom().scaleExtent([0.1, 8]).on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom);
svg.on('dblclick.zoom', () => svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity));

const sim = d3.forceSimulation(DATA.nodes)
  .force('link', d3.forceLink(DATA.edges).id(d => d.id).distance(80))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(window.innerWidth / 2, (window.innerHeight - 42) / 2))
  .force('collide', d3.forceCollide(20));

const link = g.selectAll('.link').data(DATA.edges).join('line')
  .attr('class', d => 'link' + (d.style === 'dashed' ? ' dashed' : '') + (d.style === 'violation' ? ' violation' : ''));

const nodeG = g.selectAll('.node-g').data(DATA.nodes).join('g').attr('class', 'node-g');
const circle = nodeG.append('circle').attr('class', 'node-circle').attr('r', 8).attr('fill', nodeColor);
const label = nodeG.append('text').attr('class', 'node-label').attr('dx', 12).attr('dy', 4).text(d => d.label || d.id);

// Drag (R3)
nodeG.call(d3.drag().on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
  .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
  .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

sim.on('tick', () => {
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  nodeG.attr('transform', d => `translate(${d.x},${d.y})`);
});

// Hover highlight (R3)
nodeG.on('mouseover', (e, d) => {
  const neighbors = new Set();
  DATA.edges.forEach(l => { if (l.source.id === d.id) neighbors.add(l.target.id); if (l.target.id === d.id) neighbors.add(l.source.id); });
  neighbors.add(d.id);
  nodeG.classed('faded', n => !neighbors.has(n.id));
  link.classed('faded', l => l.source.id !== d.id && l.target.id !== d.id);
}).on('mouseout', () => { nodeG.classed('faded', false); link.classed('faded', false); });

// Click detail (R3)
nodeG.on('click', (e, d) => {
  const det = document.getElementById('detail');
  const conns = DATA.edges.filter(l => l.source.id === d.id || l.target.id === d.id).length;
  det.innerHTML = `<strong>${d.label || d.id}</strong><br>Group: ${d.group || 'none'}<br>Connections: ${conns}` + (d.href ? `<br>Path: ${d.href}` : '');
  det.style.display = 'block';
});
svg.on('click', e => { if (e.target.tagName === 'svg') document.getElementById('detail').style.display = 'none'; });

// Search (R4)
const searchInput = document.getElementById('search');
const matchCount = document.getElementById('match-count');
searchInput.addEventListener('input', () => {
  const q = searchInput.value.toLowerCase();
  if (!q) { nodeG.classed('faded', false); link.classed('faded', false); circle.classed('highlight', false); matchCount.textContent = ''; return; }
  let count = 0;
  nodeG.classed('faded', d => { const match = (d.label || d.id).toLowerCase().includes(q); if (match) count++; return !match; });
  link.classed('faded', true);
  circle.classed('highlight', d => (d.label || d.id).toLowerCase().includes(q));
  matchCount.textContent = `${count} of ${DATA.nodes.length} nodes`;
});
searchInput.addEventListener('keydown', e => { if (e.key === 'Escape') { searchInput.value = ''; searchInput.dispatchEvent(new Event('input')); } });

// Theme (R5)
const toggle = document.getElementById('theme-toggle');
if (localStorage.getItem('pactkit-theme') === 'dark') { document.body.classList.add('dark'); toggle.textContent = 'Light'; }
toggle.addEventListener('click', () => {
  document.body.classList.toggle('dark');
  const isDark = document.body.classList.contains('dark');
  toggle.textContent = isDark ? 'Light' : 'Dark';
  localStorage.setItem('pactkit-theme', isDark ? 'dark' : 'light');
});

// Fullscreen (R3)
document.getElementById('fullscreen-btn').addEventListener('click', () => {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen();
  else document.exitFullscreen();
});
</script>
</body>
</html>'''


def _render_html(graph_data, mode='file', project='', overlay=None):
    """Render graph data into a self-contained HTML string.

    SEC-4: All user-derived labels are HTML-escaped before embedding.
    """
    # Escape all node labels for XSS prevention
    safe_data = {
        'nodes': [],
        'edges': graph_data.get('edges', []),
        'groups': graph_data.get('groups', []),
    }
    for node in graph_data.get('nodes', []):
        safe_node = dict(node)
        safe_node['label'] = _html_mod.escape(node.get('label', node.get('id', '')))
        if 'href' in safe_node:
            safe_node['href'] = _html_mod.escape(safe_node['href'])
        safe_data['nodes'].append(safe_node)

    title = f'{_html_mod.escape(project)} \u2014 {mode} Graph' if project else f'{mode} Graph'
    n_nodes = len(safe_data['nodes'])
    n_edges = len(safe_data['edges'])
    stats = f'{n_nodes} nodes, {n_edges} edges'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    footer = f'Generated by PactKit &middot; {now}'

    overlay_json = json.dumps(overlay if overlay else [])

    html = _D3_HTML_TEMPLATE
    html = html.replace('{{TITLE}}', title)
    html = html.replace('{{STATS}}', stats)
    html = html.replace('{{FOOTER}}', footer)
    html = html.replace('{{GRAPH_JSON}}', json.dumps(safe_data))
    html = html.replace('{{OVERLAY_JSON}}', overlay_json)
    return html


# --- Overlay Support (R8) ---


def _load_overlay(overlay_path):
    """Load overlay JSON (complexity, blast_radius, or layers)."""
    try:
        data = json.loads(Path(overlay_path).read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


# --- Entry Point (R7) ---


def generate(target='.', input_file=None, output_file=None, all_mode=False, overlay_file=None):
    """Generate HTML report from .mmd file(s)."""
    overlay = _load_overlay(overlay_file) if overlay_file else None

    if all_mode:
        root = Path(target).resolve()
        graphs_dir = root / 'docs' / 'architecture' / 'graphs'
        if not graphs_dir.is_dir():
            return f'No graphs directory found at {graphs_dir}'
        results = []
        for mmd_file in sorted(graphs_dir.glob('*.mmd')):
            html_dest = mmd_file.with_suffix('.html')
            _generate_one(mmd_file, html_dest, overlay)
            results.append(str(html_dest))
        return f'Generated {len(results)} HTML reports'

    if not input_file:
        return 'Error: --input or --all is required'

    mmd_path = Path(input_file).resolve()
    if not mmd_path.exists():
        return f'Error: {input_file} not found'

    html_dest = Path(output_file) if output_file else mmd_path.with_suffix('.html')
    _generate_one(mmd_path, html_dest, overlay)
    return f'Generated: {html_dest}'


def _generate_one(mmd_path, html_dest, overlay=None):
    """Generate a single HTML report from a .mmd file."""
    mmd_content = mmd_path.read_text(encoding='utf-8')
    graph = _parse_mmd(mmd_content)

    # Infer mode from filename
    stem = mmd_path.stem.lower()
    if 'class' in stem:
        mode = 'class'
    elif 'call' in stem:
        mode = 'call'
    elif 'module' in stem:
        mode = 'module'
    elif 'workflow' in stem:
        mode = 'workflow'
    elif 'unified' in stem:
        mode = 'unified'
    else:
        mode = 'file'

    # Infer project name from path
    project = ''
    try:
        # Walk up to find a directory that isn't docs/architecture/graphs
        for parent in mmd_path.parents:
            if parent.name not in ('graphs', 'architecture', 'docs'):
                project = parent.name
                break
    except Exception:
        pass

    html = _render_html(graph, mode=mode, project=project, overlay=overlay)
    html_dest.parent.mkdir(parents=True, exist_ok=True)
    html_dest.write_text(html, encoding='utf-8')


# --- CLI ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PactKit Report — Interactive HTML from .mmd')
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_gen = sub.add_parser('generate', help='Generate HTML report from .mmd')
    p_gen.add_argument('--input', help='Input .mmd file path')
    p_gen.add_argument('--output', help='Output .html file path (default: same name as input)')
    p_gen.add_argument('--all', dest='all_mode', action='store_true', help='Convert all .mmd in docs/architecture/graphs/')
    p_gen.add_argument('--overlay', help='Overlay JSON file (complexity/blast_radius/layers)')

    a = parser.parse_args()
    if a.cmd == 'generate':
        result = generate(input_file=a.input, output_file=a.output, all_mode=a.all_mode, overlay_file=a.overlay)
        if result:
            print(result)
