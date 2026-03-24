#!/usr/bin/env python3
"""Standalone version for IDE support. Deployed with _SHARED_HEADER."""
import abc
import argparse
import ast
import os
from pathlib import Path


def nl(): return chr(10)


# === SCRIPT BODY ===

# --- ARCH ---
def init_architecture():
    root = Path.cwd() / 'docs/architecture'
    (root/'graphs').mkdir(parents=True, exist_ok=True)
    (root/'governance').mkdir(parents=True, exist_ok=True)
    hld = root / 'graphs/system_design.mmd'
    if not hld.exists(): hld.write_text('graph TD' + nl() + '    User --> System', encoding='utf-8')
    lld = root / 'graphs/code_graph.mmd'
    if not lld.exists(): lld.write_text('classDiagram' + nl() + '    %% Empty', encoding='utf-8')
    return '✅ Init: Structure Complete'

# --- SCAN HELPERS (shared across modes) ---
SCAN_EXCLUDES = {
    'venv', '_venv', '.venv', '.env', 'env', '__pycache__', '.git', '.claude',
    'tests', 'docs', 'node_modules', 'site-packages', 'dist', 'build',
    'skills', 'commands', 'rules', 'agents',  # PactKit marketplace dirs (BUG-006)
}

MAX_SCAN_FILES = 500  # STORY-060: file count ceiling to prevent hangs on large repos

# Canonical: src/pactkit/cleaners.py _STACK_MARKERS
_STACK_MARKERS = [
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("setup.cfg", "python"),
    ("package.json", "node"),
    ("go.mod", "go"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
]

# Canonical: src/pactkit/prompts/workflows.py LANG_PROFILES[*].file_ext
_LANG_FILE_EXT = {
    "python": ".py",
    "node": ".ts",
    "go": ".go",
    "java": ".java",
}


def _load_scan_excludes(root):
    """Load scan_excludes from pactkit.yaml if present. Returns list or None.

    Searches .claude/pactkit.yaml then .opencode/pactkit.yaml.
    Guarded by try/except so standalone script fails gracefully if yaml unavailable.
    """
    candidates = [
        root / '.claude' / 'pactkit.yaml',
        root / '.opencode' / 'pactkit.yaml',
    ]
    for path in candidates:
        if path.exists():
            try:
                import yaml as _yaml
                data = _yaml.safe_load(path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    viz = data.get('visualize', {})
                    if isinstance(viz, dict) and 'scan_excludes' in viz:
                        excludes = viz['scan_excludes']
                        if isinstance(excludes, list):
                            return excludes
            except Exception:
                pass
    return None


def _detect_file_ext(root):
    """Detect the source file extension for the project at root.

    Priority:
    1. pactkit.yaml 'stack' field (if not 'auto' and known in _LANG_FILE_EXT)
    2. Marker-file detection via _STACK_MARKERS
    3. Default: '.py'
    """
    # 1. Try reading stack from pactkit.yaml
    candidates = [
        root / '.claude' / 'pactkit.yaml',
        root / '.opencode' / 'pactkit.yaml',
    ]
    for path in candidates:
        if path.exists():
            try:
                import yaml as _yaml
                data = _yaml.safe_load(path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    stack = data.get('stack', 'auto')
                    if stack and stack != 'auto' and stack in _LANG_FILE_EXT:
                        return _LANG_FILE_EXT[stack]
            except Exception:
                pass

    # 2. Marker-file detection
    for marker, stack in _STACK_MARKERS:
        if (root / marker).exists():
            return _LANG_FILE_EXT.get(stack, '.py')

    # 3. Default
    return '.py'


def _scan_files(root, scan_excludes=None, file_ext='.py'):
    import sys as _sys
    excludes = set(scan_excludes) if scan_excludes is not None else SCAN_EXCLUDES
    all_files = []
    module_index = {}
    file_to_node = {}

    for p in root.rglob(f'*{file_ext}'):
        if any(part in excludes for part in p.parts): continue
        if len(all_files) >= MAX_SCAN_FILES:
            print(f"⚠️ Scan truncated at {MAX_SCAN_FILES} files. Use --focus <module> to narrow scope.", file=_sys.stderr)
            break
        all_files.append(p)
        node_id = str(p.relative_to(root)).replace(os.sep, '_').replace('.', '_').replace('-', '_')
        file_to_node[p] = node_id
        try:
            rel_path = p.relative_to(root)
            module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
            module_index[module_name] = p
            if len(rel_path.parts) > 1 and rel_path.parts[0] == 'src':
                short_name = '.'.join(rel_path.parts[1:]).replace('.py', '')
                module_index[short_name] = p
            if p.name == '__init__.py':
                pkg_name = str(rel_path.parent).replace(os.sep, '.')
                module_index[pkg_name] = p
                if len(rel_path.parts) > 2 and rel_path.parts[0] == 'src':
                     short_pkg = '.'.join(rel_path.parts[1:-1])
                     module_index[short_pkg] = p
        except (SyntaxError, UnicodeDecodeError, ValueError): pass
    return all_files, module_index, file_to_node

# --- LANGUAGE ADAPTER (STORY-slim-030) ---
class LanguageAnalyzer(abc.ABC):
    @abc.abstractmethod
    def extract_imports(self, file_path) -> list:
        """Return list of imported module name strings."""
        ...

    @abc.abstractmethod
    def extract_functions_and_calls(self, file_path) -> tuple:
        """Return (func_registry, call_edges) for one file."""
        ...


class PythonAnalyzer(LanguageAnalyzer):
    def extract_imports(self, file_path):
        """Parse a Python file and return a list of imported module name strings."""
        try:
            tree = ast.parse(file_path.read_text(encoding='utf-8'))
            imported_modules = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    for alias in n.names:
                        imported_modules.append(alias.name)
                elif isinstance(n, ast.ImportFrom):
                    if n.module:
                        imported_modules.append(n.module)
            return imported_modules
        except (SyntaxError, UnicodeDecodeError, ValueError):
            return []

    def extract_functions_and_calls(self, file_path):
        """Parse a Python file and return (func_registry, call_edges) for that file."""
        try:
            tree = ast.parse(file_path.read_text(encoding='utf-8'))
            rel = file_path.stem
            func_registry = {}
            call_edges = {}
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = node.name
                    func_registry[qname] = rel
                    call_edges[qname] = _extract_calls(node, current_class=None)
                elif isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            qname = f'{node.name}.{item.name}'
                            func_registry[qname] = rel
                            call_edges[qname] = _extract_calls(item, current_class=node.name)
            return func_registry, call_edges
        except (SyntaxError, UnicodeDecodeError, ValueError):
            return {}, {}


# --- MODE: FILE (v1.3.0) ---
def _build_file_graph(root, all_files, module_index, file_to_node, focus, depth=0, max_nodes=0, analyzer=None):
    if analyzer is None:
        analyzer = PythonAnalyzer()
    nodes = []
    edges = []
    for f in all_files:
        nid = file_to_node[f]
        rel_str = str(f.relative_to(root))
        nodes.append(f'    {nid}["{f.name}"]')
        nodes.append(f'    click {nid} href "{rel_str}"')
    seen_edges = set()
    adjacency = {}  # node -> set of neighbor nodes (for depth limiting)
    for p in all_files:
        consumer_id = file_to_node[p]
        for imported_module in analyzer.extract_imports(p):
            tf = module_index.get(imported_module)
            if not tf:
                parts = imported_module.split('.')
                for i in range(len(parts), 0, -1):
                    sub = '.'.join(parts[:i])
                    if sub in module_index: tf = module_index[sub]; break
            if tf and tf != p:
                pid = file_to_node.get(tf)
                if pid:
                    edge = (consumer_id, pid)
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        edges.append(edge)
                    adjacency.setdefault(consumer_id, set()).add(pid)
                    adjacency.setdefault(pid, set()).add(consumer_id)

    final_lines = ['graph TD']
    if focus:
        target_ids = set()
        for f, nid in file_to_node.items():
            if focus in str(f.relative_to(root)): target_ids.add(nid)
        if not target_ids:
            return None, f"❌ Focus target '{focus}' not found. (Scanned {len(all_files)} files)"
        relevant_ids = set(target_ids)
        relevant_edges = []
        for src, dst in edges:
            if src in target_ids or dst in target_ids:
                relevant_edges.append(f'    {src} --> {dst}')
                relevant_ids.add(src); relevant_ids.add(dst)
        for line in nodes:
            if any(rid in line for rid in relevant_ids): final_lines.append(line)
        final_lines.extend(relevant_edges)
        dest = root / 'docs/architecture/graphs/focus_file_graph.mmd'
    else:
        # Apply depth limiting via BFS if depth > 0
        if depth > 0:
            # Find root nodes (nodes with no incoming edges)
            all_node_ids = set(file_to_node.values())
            has_incoming = set()
            for src, dst in edges:
                has_incoming.add(dst)
            root_nodes = all_node_ids - has_incoming
            if not root_nodes:
                root_nodes = all_node_ids  # fallback: use all

            # BFS from root nodes up to depth levels
            allowed = set()
            frontier = set(root_nodes)
            for _ in range(depth + 1):
                allowed |= frontier
                next_frontier = set()
                for nid in frontier:
                    for neighbor in adjacency.get(nid, set()):
                        if neighbor not in allowed:
                            next_frontier.add(neighbor)
                frontier = next_frontier

            # Filter nodes and edges
            for line in nodes:
                if any(nid in line for nid in allowed):
                    final_lines.append(line)
            for src, dst in edges:
                if src in allowed and dst in allowed:
                    final_lines.append(f'    {src} --> {dst}')
        else:
            final_lines.extend(nodes)
            for src, dst in edges: final_lines.append(f'    {src} --> {dst}')

        # Apply max_nodes truncation
        if max_nodes > 0:
            # Count actual node definition lines (contain "[" but not "click")
            node_lines = [line for line in final_lines[1:] if '[' in line and 'click' not in line]
            if len(node_lines) > max_nodes:
                truncated_count = len(node_lines) - max_nodes
                # Keep only the first max_nodes node IDs
                keep_ids = set()
                for line in node_lines[:max_nodes]:
                    nid = line.strip().split('[')[0].strip()
                    keep_ids.add(nid)
                filtered = ['graph TD']
                for line in final_lines[1:]:
                    if '[' in line or 'click' in line:
                        if any(nid in line for nid in keep_ids):
                            filtered.append(line)
                    elif '-->' in line:
                        parts = line.strip().split('-->')
                        src = parts[0].strip()
                        dst = parts[1].strip()
                        if src in keep_ids and dst in keep_ids:
                            filtered.append(line)
                filtered.append(f'    NOTE["... and {truncated_count} more nodes (use --max-nodes to adjust)"]')
                final_lines = filtered

        dest = root / 'docs/architecture/graphs/code_graph.mmd'
    return dest, nl().join(final_lines)

# --- MODE: CLASS (classDiagram) ---
def _build_class_graph(root, all_files, focus):
    classes = []  # (file, class_name, bases, methods)

    for p in all_files:
        try:
            tree = ast.parse(p.read_text(encoding='utf-8'))
            rel = str(p.relative_to(root))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = []
                    for b in node.bases:
                        if isinstance(b, ast.Name): bases.append(b.id)
                        elif isinstance(b, ast.Attribute): bases.append(b.attr)
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            prefix = '+' if not item.name.startswith('_') else '-'
                            args = [a.arg for a in item.args.args if a.arg != 'self']
                            sig = f"{prefix}{item.name}({', '.join(args)})"
                            methods.append(sig)
                    classes.append((rel, node.name, bases, methods))
        except (SyntaxError, UnicodeDecodeError, ValueError): pass

    # Filter by focus
    if focus:
        classes = [(f, cn, bases, ms) for f, cn, bases, ms in classes if focus in f]

    lines = ['classDiagram']
    seen_classes = set()
    for rel, cname, bases, methods in classes:
        if cname in seen_classes: continue
        seen_classes.add(cname)
        lines.append(f'    class {cname} {{')
        for m in methods: lines.append(f'        {m}')
        lines.append('    }')
        for b in bases:
            lines.append(f'    {b} <|-- {cname}')

    dest = root / 'docs/architecture/graphs/class_graph.mmd'
    if focus: dest = root / 'docs/architecture/graphs/focus_class_graph.mmd'
    return dest, nl().join(lines)

# --- MODE: CALL (function-level call graph) ---
def _build_call_graph(root, all_files, focus, entry, analyzer=None):
    if analyzer is None:
        analyzer = PythonAnalyzer()
    func_registry = {}  # {qualified_name: file}
    call_edges = {}  # {caller_qualified: [callee_qualified]}

    for p in all_files:
        fr, ce = analyzer.extract_functions_and_calls(p)
        func_registry.update(fr)
        call_edges.update(ce)

    # Pass 3: Resolve short names to qualified names where possible
    all_func_names = set(func_registry.keys())

    # Pass 4: If --entry, do BFS for transitive closure
    if entry:
        # Find the entry function (try exact match, then partial)
        start = None
        for fn in all_func_names:
            if fn == entry or fn.endswith(f'.{entry}'): start = fn; break
        if not start:
            for fn in all_func_names:
                if entry in fn: start = fn; break
        if not start:
            return root / 'docs/architecture/graphs/call_graph.mmd', f'graph TD{nl()}    ❌_not_found["{entry} not found"]'

        # BFS — only follow edges to project-defined functions (BUG-012)
        visited = set()
        queue = [start]
        reachable_edges = []
        while queue:
            current = queue.pop(0)
            if current in visited: continue
            visited.add(current)
            for callee in call_edges.get(current, []):
                resolved = _resolve_callee(callee, all_func_names)
                if resolved:
                    reachable_edges.append((current, resolved))
                    if resolved not in visited: queue.append(resolved)

        lines = ['graph TD']
        safe = lambda s: s.replace('.', '_')
        for fn in visited:
            lines.append(f'    {safe(fn)}["{fn}"]')
        for src, dst in reachable_edges:
            lines.append(f'    {safe(src)} --> {safe(dst)}')
    else:
        # Full call graph — only edges where both endpoints are in func_registry (BUG-012)
        lines = ['graph TD']
        safe = lambda s: s.replace('.', '_')
        relevant = set()
        rel_edges = []

        for caller, callees in call_edges.items():
            if focus and focus not in func_registry.get(caller, ''): continue
            for callee in callees:
                resolved = _resolve_callee(callee, all_func_names)
                if resolved:
                    relevant.add(caller)
                    relevant.add(resolved)
                    rel_edges.append((caller, resolved))

        for fn in sorted(relevant): lines.append(f'    {safe(fn)}["{fn}"]')
        for src, dst in rel_edges: lines.append(f'    {safe(src)} --> {safe(dst)}')

    dest = root / 'docs/architecture/graphs/call_graph.mmd'
    if focus: dest = root / 'docs/architecture/graphs/focus_call_graph.mmd'
    return dest, nl().join(lines)

_BUILTIN_CALLEES = {
    'isinstance', 'len', 'sorted', 'set', 'dict', 'type', 'print', 'any',
    'str', 'int', 'float', 'bool', 'list', 'tuple', 'range', 'enumerate',
    'zip', 'map', 'filter', 'super', 'hasattr', 'getattr', 'setattr',
    'repr', 'min', 'max', 'abs', 'round', 'open', 'all', 'id', 'hash',
    'callable', 'vars', 'dir', 'hex', 'oct', 'bin', 'ord', 'chr', 'iter',
    'next', 'reversed', 'slice', 'frozenset', 'bytes', 'bytearray',
    'memoryview', 'property', 'staticmethod', 'classmethod', 'input',
    'breakpoint', 'compile', 'eval', 'exec', 'format', 'globals', 'locals',
    'object', 'issubclass', 'pow', 'divmod', 'sum', 'complex', 'delattr',
    'NotImplementedError', 'ValueError', 'TypeError', 'KeyError',
    'AttributeError', 'IndexError', 'RuntimeError', 'FileNotFoundError',
    'OSError', 'IOError', 'StopIteration', 'Exception', 'ImportError',
}

def _extract_calls(func_node, current_class=None):
    # Extract function/method calls from a function body (BUG-012: filtered).
    callees = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in _BUILTIN_CALLEES:
                    callees.append(name)
            elif isinstance(node.func, ast.Attribute):
                # self.method() → ClassName.method (retain)
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'self' and current_class:
                        callees.append(f'{current_class}.{node.func.attr}')
                    # Skip non-self local variable method calls (e.g., lines.append)
    return callees

def _resolve_callee(callee, all_func_names):
    # Try to resolve a callee string to a known qualified function name.
    if callee in all_func_names: return callee
    # Try matching by suffix
    for fn in all_func_names:
        if fn.endswith(f'.{callee}') or fn == callee: return fn
    return None

# --- MODE: REVERSE CALLER BFS (STORY-053) ---
def _scan_call_edges(root, all_files, analyzer=None):
    """Shared helper: build func_registry and call_edges from source. Used by forward and reverse BFS."""
    if analyzer is None:
        analyzer = PythonAnalyzer()
    func_registry = {}  # {qualified_name: stem}
    call_edges = {}  # {caller: [callees]}
    for p in all_files:
        fr, ce = analyzer.extract_functions_and_calls(p)
        func_registry.update(fr)
        call_edges.update(ce)
    return func_registry, call_edges


def _find_entry_func(entry, all_func_names):
    """Find the entry function by exact match, suffix match, or substring match."""
    if not entry: return None
    for fn in all_func_names:
        if fn == entry or fn.endswith(f'.{entry}'): return fn
    for fn in all_func_names:
        if entry in fn: return fn
    return None


def _build_reverse_graph(func_registry, call_edges, entry):
    """BFS backwards through caller graph from entry. Returns (visited_funcs, reverse_edges)."""
    all_func_names = set(func_registry.keys())
    # Build reverse map: {callee: [callers]}
    reverse_map = {}
    for caller, callees in call_edges.items():
        for callee in callees:
            resolved = _resolve_callee(callee, all_func_names)
            if resolved:
                reverse_map.setdefault(resolved, []).append(caller)

    start = _find_entry_func(entry, all_func_names)
    if not start: return set(), []

    visited = set()
    queue = [start]
    reverse_edges = []
    while queue:
        current = queue.pop(0)
        if current in visited: continue
        visited.add(current)
        for caller in reverse_map.get(current, []):
            reverse_edges.append((caller, current))
            if caller not in visited: queue.append(caller)
    return visited, reverse_edges


# --- impact() subcommand (STORY-053) ---
def impact(target='.', entry=None):
    """Find test files impacted by a changed function (reverse BFS + test mapping).
    Returns a space-separated list of test file paths, or empty string if none found.
    """
    if not entry: return ''
    root = Path(target).resolve()
    scan_excludes = _load_scan_excludes(root)
    file_ext = _detect_file_ext(root)
    all_files, module_index, file_to_node = _scan_files(root, scan_excludes=scan_excludes, file_ext=file_ext)
    analyzer = PythonAnalyzer()  # TODO: select based on file_ext for Go/Java/TS (STORY-slim-032+)
    func_registry, call_edges = _scan_call_edges(root, all_files, analyzer=analyzer)

    visited, _ = _build_reverse_graph(func_registry, call_edges, entry)
    if not visited: return ''

    test_files = set()
    for func_name in visited:
        stem = func_registry.get(func_name)
        if stem:
            # Python pattern: src/pactkit/config.py → tests/unit/test_config.py
            test_path = root / 'tests' / 'unit' / f'test_{stem}.py'
            if test_path.exists():
                test_files.add(str(test_path.relative_to(root)))
    return ' '.join(sorted(test_files))


# --- MAIN VISUALIZE (v1.3.0 Multi-Mode) ---
def visualize(target='.', focus=None, mode='file', entry=None, depth=0, max_nodes=0, reverse=False):
    root = Path(target).resolve()
    scan_excludes = _load_scan_excludes(root)
    file_ext = _detect_file_ext(root)
    all_files, module_index, file_to_node = _scan_files(root, scan_excludes=scan_excludes, file_ext=file_ext)
    analyzer = PythonAnalyzer()  # TODO: select based on file_ext for Go/Java/TS (STORY-slim-032+)

    if mode == 'class':
        dest, content = _build_class_graph(root, all_files, focus)
    elif mode == 'call':
        if entry and reverse:
            # Reverse BFS: find all callers of the entry function
            func_registry, call_edges = _scan_call_edges(root, all_files, analyzer=analyzer)
            visited, reverse_edges = _build_reverse_graph(func_registry, call_edges, entry)
            lines = ['graph TD']
            safe = lambda s: s.replace('.', '_')
            for fn in visited:
                lines.append(f'    {safe(fn)}["{fn}"]')
            for src, dst in reverse_edges:
                lines.append(f'    {safe(src)} --> {safe(dst)}')
            dest = root / 'docs/architecture/graphs/call_graph.mmd'
            if focus: dest = root / 'docs/architecture/graphs/focus_call_graph.mmd'
            content = nl().join(lines)
        else:
            dest, content = _build_call_graph(root, all_files, focus, entry, analyzer=analyzer)
    else:
        dest, content = _build_file_graph(root, all_files, module_index, file_to_node, focus, depth=depth, max_nodes=max_nodes, analyzer=analyzer)
        if dest is None: return content  # error message

    if not dest.parent.exists(): dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')
    return f'✅ Graph: {dest}'

def list_rules(): return 'Rules defined in ~/.claude/CLAUDE.md'

# --- CLI ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init_arch')
    sub.add_parser('list_rules')
    p_viz = sub.add_parser('visualize')
    p_viz.add_argument('--focus')
    p_viz.add_argument('--mode', choices=['file', 'class', 'call'], default='file')
    p_viz.add_argument('--entry')
    p_viz.add_argument('--depth', type=int, default=0, help='Limit graph traversal to N levels (0=unlimited)')
    p_viz.add_argument('--max-nodes', type=int, default=0, help='Truncate graph to N nodes (0=unlimited)')
    p_viz.add_argument('--reverse', action='store_true', default=False, help='Reverse BFS: find callers of entry function (STORY-053)')
    p_impact = sub.add_parser('impact', help='Find test files impacted by a changed function (STORY-053)')
    p_impact.add_argument('--entry', required=True, help='Changed function name')

    a = parser.parse_args()
    if a.cmd == 'init_arch': print(init_architecture())
    elif a.cmd == 'visualize': print(visualize('.', a.focus, a.mode, a.entry, depth=a.depth, max_nodes=a.max_nodes, reverse=a.reverse))
    elif a.cmd == 'impact': print(impact('.', a.entry))
    elif a.cmd == 'list_rules': print(list_rules())
