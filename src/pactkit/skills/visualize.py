#!/usr/bin/env python3
"""Standalone version for IDE support. Deployed with _SHARED_HEADER."""
import abc
import argparse
import ast
import os
import re
from dataclasses import dataclass
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

# Canonical: src/pactkit/prompts/workflows.py LANG_PROFILES[*].test_map_pattern
_TEST_MAP_PATTERNS = {
    "python": "tests/unit/test_{module}.py",
    "node": "__tests__/{module}.test.ts",
    "go": "{package}/{module}_test.go",
    "java": "src/test/java/{package}/{module}Test.java",
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


def _detect_stack(root):
    """Detect the stack name for the project at root.

    Priority:
    1. pactkit.yaml 'stack' field (if not 'auto' and known in _LANG_FILE_EXT)
    2. Marker-file detection via _STACK_MARKERS
    3. Default: 'python'
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
                        return stack
            except Exception:
                pass

    # 2. Marker-file detection
    for marker, stack in _STACK_MARKERS:
        if (root / marker).exists():
            return stack

    # 3. Default
    return 'python'


def _detect_file_ext(root):
    """Detect the source file extension for the project at root.

    Thin wrapper around _detect_stack() that returns the file extension.
    """
    return _LANG_FILE_EXT.get(_detect_stack(root), '.py')


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


# --- TREE-SITTER ADAPTER (STORY-slim-032) ---
# Guard imports: tree-sitter is optional (multilang extra)
try:
    from tree_sitter import Language as _TSLanguage, Parser as _TSParser, Query as _TSQuery, QueryCursor as _TSQueryCursor
    _HAS_TREE_SITTER = True
except ImportError:
    _HAS_TREE_SITTER = False


class TreeSitterAnalyzer(LanguageAnalyzer):
    """Base class for tree-sitter-based language analyzers.

    Subclasses provide language grammar and queries; this base class handles
    parser init, file reading, error handling, and query execution.
    """
    def __init__(self, language, import_query, func_query, call_query, method_query=None):
        import re as _re
        self._re = _re
        self._lang = _TSLanguage(language)
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, import_query)
        self._func_query = _TSQuery(self._lang, func_query)
        self._call_query = _TSQuery(self._lang, call_query)
        self._method_query = _TSQuery(self._lang, method_query) if method_query else None

    def _captures(self, query, node):
        """Run a query against a node, return dict[str, list[Node]]."""
        cursor = _TSQueryCursor(query)
        return cursor.captures(node)

    def _matches(self, query, node):
        """Run a query against a node, return list[tuple[int, dict[str, list[Node]]]]."""
        cursor = _TSQueryCursor(query)
        return cursor.matches(node)

    def extract_imports(self, file_path):
        try:
            source = file_path.read_bytes()
            tree = self._parser.parse(source)
            captures = self._captures(self._import_query, tree.root_node)
            return [n.text.decode().strip('"\'') for n in captures.get('import', [])]
        except Exception:
            return []

    def extract_functions_and_calls(self, file_path):
        try:
            source = file_path.read_bytes()
            tree = self._parser.parse(source)
            return self._extract_funcs_and_calls(tree, file_path.stem)
        except Exception:
            return {}, {}

    def _extract_funcs_and_calls(self, tree, stem):
        """Override in subclasses for language-specific extraction logic."""
        return {}, {}

    def _extract_calls_from_body(self, body_node):
        """Extract call targets from a function/method body node."""
        calls = []
        captures = self._captures(self._call_query, body_node)
        callees = [n.text.decode() for n in captures.get('callee', [])]
        calls.extend(callees)

        objs = [n.text.decode() for n in captures.get('obj', [])]
        methods = [n.text.decode() for n in captures.get('method', [])]
        for obj, method in zip(objs, methods):
            calls.append(f'{obj}.{method}')
        return calls


# Go tree-sitter queries
_GO_IMPORT_QUERY = '(import_spec path: (interpreted_string_literal) @import)'

_GO_FUNC_QUERY = '(function_declaration name: (identifier) @name body: (block) @body)'

_GO_METHOD_QUERY = '''(method_declaration
    receiver: (parameter_list (parameter_declaration type: (_) @receiver_type))
    name: (field_identifier) @name
    body: (block) @body)'''

_GO_CALL_QUERY = '''[
  (call_expression function: (identifier) @callee)
  (call_expression function: (selector_expression
    operand: (_) @obj
    field: (field_identifier) @method))
]'''


class GoAnalyzer(TreeSitterAnalyzer):
    """Go language analyzer using tree-sitter-go."""
    def __init__(self):
        import tree_sitter_go as _tsg
        import re as _re
        self._re = _re
        self._lang = _TSLanguage(_tsg.language())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _GO_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _GO_FUNC_QUERY)
        self._method_query = _TSQuery(self._lang, _GO_METHOD_QUERY)
        self._call_query = _TSQuery(self._lang, _GO_CALL_QUERY)

    def _extract_funcs_and_calls(self, tree, stem):
        func_registry = {}
        call_edges = {}

        # Extract top-level functions
        for _, match_dict in self._matches(self._func_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                qname = names[0].text.decode()
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        # Extract method declarations
        for _, match_dict in self._matches(self._method_query, tree.root_node):
            names = match_dict.get('name', [])
            receivers = match_dict.get('receiver_type', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                receiver_type = ''
                if receivers:
                    raw = receivers[0].text.decode()
                    # Strip pointer (*), spaces, interface {}
                    receiver_type = self._re.sub(r'[*& \[\]]', '', raw).strip()
                func_name = names[0].text.decode()
                qname = f'{receiver_type}.{func_name}' if receiver_type else func_name
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        return func_registry, call_edges


# Java tree-sitter queries (STORY-slim-033)
_JAVA_IMPORT_QUERY = '(import_declaration (scoped_identifier) @import)'

_JAVA_FUNC_QUERY = '(method_declaration name: (identifier) @name body: (block) @body)'

_JAVA_CONSTRUCTOR_QUERY = '(constructor_declaration name: (identifier) @name body: (constructor_body) @body)'

_JAVA_CALL_QUERY = '''[
  (method_invocation name: (identifier) @callee)
  (method_invocation object: (_) @obj name: (identifier) @method)
]'''


def _find_enclosing_class(node):
    """Walk up the tree to find the enclosing class_declaration name."""
    current = node
    while current:
        if current.type == 'class_declaration':
            name_node = current.child_by_field_name('name')
            if name_node:
                return name_node.text.decode()
        current = current.parent
    return None


class JavaAnalyzer(TreeSitterAnalyzer):
    """Java language analyzer using tree-sitter-java (STORY-slim-033)."""
    def __init__(self):
        import tree_sitter_java as _tsj
        import re as _re
        self._re = _re
        self._lang = _TSLanguage(_tsj.language())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _JAVA_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _JAVA_FUNC_QUERY)
        self._constructor_query = _TSQuery(self._lang, _JAVA_CONSTRUCTOR_QUERY)
        self._call_query = _TSQuery(self._lang, _JAVA_CALL_QUERY)
        self._method_query = None  # Java uses _func_query + _constructor_query

    def _extract_funcs_and_calls(self, tree, stem):
        func_registry = {}
        call_edges = {}

        # Extract instance and static methods
        for _, match_dict in self._matches(self._func_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                name_node = names[0]
                func_name = name_node.text.decode()
                class_name = _find_enclosing_class(name_node)
                qname = f'{class_name}.{func_name}' if class_name else func_name
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        # Extract constructors (ClassName.ClassName pattern)
        for _, match_dict in self._matches(self._constructor_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                name_node = names[0]
                ctor_name = name_node.text.decode()
                qname = f'{ctor_name}.{ctor_name}'
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        return func_registry, call_edges


# TS/JS tree-sitter queries (STORY-slim-034)
_TS_IMPORT_QUERY = '''[
  (import_statement source: (string) @import)
  (export_statement source: (string) @import)
  (call_expression
    function: (identifier) @_func (#eq? @_func "require")
    arguments: (arguments (string) @import))
]'''

_TS_FUNC_QUERY = '''[
  (function_declaration name: (identifier) @name body: (statement_block) @body)
  (method_definition name: (property_identifier) @name body: (statement_block) @body)
  (lexical_declaration
    (variable_declarator
      name: (identifier) @name
      value: [(arrow_function body: (_) @body) (function_expression body: (statement_block) @body)]))
]'''

_TS_CALL_QUERY = '''[
  (call_expression function: (identifier) @callee)
  (call_expression function: (member_expression
    object: (_) @obj
    property: (property_identifier) @method))
]'''


class TSAnalyzer(TreeSitterAnalyzer):
    """TypeScript/JavaScript language analyzer using tree-sitter-typescript (STORY-slim-034)."""
    def __init__(self):
        import tree_sitter_typescript as _tsts
        self._lang = _TSLanguage(_tsts.language_typescript())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _TS_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _TS_FUNC_QUERY)
        self._call_query = _TSQuery(self._lang, _TS_CALL_QUERY)
        self._method_query = None

    def _extract_funcs_and_calls(self, tree, stem):
        func_registry = {}
        call_edges = {}

        for _, match_dict in self._matches(self._func_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                name_node = names[0]
                func_name = name_node.text.decode()
                class_name = _find_enclosing_class(name_node)
                qname = f'{class_name}.{func_name}' if class_name else func_name
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        return func_registry, call_edges


def _select_analyzer(stack):
    """Return the appropriate LanguageAnalyzer for the given stack.

    Falls back to PythonAnalyzer if tree-sitter is not installed or
    the language-specific grammar package is missing.
    """
    import sys as _sys
    if stack == 'python':
        return PythonAnalyzer()
    if not _HAS_TREE_SITTER:
        print(f"tree-sitter not installed; falling back to PythonAnalyzer for {stack}", file=_sys.stderr)
        return PythonAnalyzer()
    try:
        if stack == 'go':
            return GoAnalyzer()
        if stack == 'java':
            return JavaAnalyzer()
        if stack == 'node':
            return TSAnalyzer()
    except ImportError:
        print(f"tree-sitter-{stack} not installed; falling back to PythonAnalyzer for {stack}", file=_sys.stderr)
    return PythonAnalyzer()


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


def _resolve_test_path(root, stem, source_file, stack):
    """Resolve the test file path for a given source file using _TEST_MAP_PATTERNS.

    Returns a Path if the resolved test file exists, or None otherwise.
    """
    pattern = _TEST_MAP_PATTERNS.get(stack, "tests/unit/test_{module}.py")
    module = stem
    package = str(source_file.parent.relative_to(root)).replace(os.sep, '/')
    resolved = pattern.replace("{module}", module).replace("{package}", package)
    test_path = root / resolved
    return test_path if test_path.exists() else None


# --- impact() subcommand (STORY-053, STORY-slim-031) ---
def impact(target='.', entry=None):
    """Find test files impacted by a changed function (reverse BFS + test mapping).
    Returns a space-separated list of test file paths, or empty string if none found.
    """
    if not entry: return ''
    root = Path(target).resolve()
    scan_excludes = _load_scan_excludes(root)
    stack = _detect_stack(root)
    # Multi-extension scanning for Node projects (STORY-slim-034 R5)
    if stack == 'node':
        files_ts, mi_ts, ftn_ts = _scan_files(root, scan_excludes=scan_excludes, file_ext='.ts')
        files_js, mi_js, ftn_js = _scan_files(root, scan_excludes=scan_excludes, file_ext='.js')
        all_files = files_ts + files_js
        module_index = {**mi_ts, **mi_js}
        file_to_node = {**ftn_ts, **ftn_js}
    else:
        file_ext = _detect_file_ext(root)
        all_files, module_index, file_to_node = _scan_files(root, scan_excludes=scan_excludes, file_ext=file_ext)
    analyzer = _select_analyzer(stack)
    func_registry, call_edges = _scan_call_edges(root, all_files, analyzer=analyzer)

    # Build stem → source_file index for {package} resolution
    stem_to_file = {}
    for f in all_files:
        stem_to_file.setdefault(f.stem, f)

    visited, _ = _build_reverse_graph(func_registry, call_edges, entry)
    if not visited: return ''

    test_files = set()
    for func_name in visited:
        stem = func_registry.get(func_name)
        if not stem:
            continue
        source_file = stem_to_file.get(stem)
        if source_file:
            # Try pattern-based resolution first
            test_path = _resolve_test_path(root, stem, source_file, stack)
            if test_path:
                test_files.add(str(test_path.relative_to(root)))
                continue
        # Fallback: hardcoded Python convention
        fallback_path = root / 'tests' / 'unit' / f'test_{stem}.py'
        if fallback_path.exists():
            test_files.add(str(fallback_path.relative_to(root)))
    return ' '.join(sorted(test_files))


# --- MAIN VISUALIZE (v1.3.0 Multi-Mode) ---
def visualize(target='.', focus=None, mode='file', entry=None, depth=0, max_nodes=0, reverse=False, lazy=False):
    root = Path(target).resolve()

    # --- Workflow mode (STORY-slim-036) ---
    if mode == 'workflow':
        dest = root / 'docs' / 'architecture' / 'graphs' / 'workflow_graph.mmd'
        if lazy and dest.exists():
            # Check staleness: compare mmd mtime against command/skill/rule files
            mmd_mtime = dest.stat().st_mtime
            stale = False
            for check_dir_name in ['.claude/commands', '.claude/skills', '.claude/rules',
                                   'commands', 'skills', 'rules']:
                check_dir = root / check_dir_name
                if check_dir.is_dir():
                    for f in check_dir.rglob('*'):
                        if f.is_file() and f.stat().st_mtime > mmd_mtime:
                            stale = True
                            break
                if stale:
                    break
            if not stale:
                return f'Workflow graph up-to-date — skip regeneration: {dest}'
        graph = build_workflow_graph(root=root)
        content = graph.to_mermaid()
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding='utf-8')
        return f'✅ Graph: {dest}'

    scan_excludes = _load_scan_excludes(root)
    stack = _detect_stack(root)
    # Multi-extension scanning for Node projects (STORY-slim-034 R5)
    if stack == 'node':
        files_ts, mi_ts, ftn_ts = _scan_files(root, scan_excludes=scan_excludes, file_ext='.ts')
        files_js, mi_js, ftn_js = _scan_files(root, scan_excludes=scan_excludes, file_ext='.js')
        all_files = files_ts + files_js
        module_index = {**mi_ts, **mi_js}
        file_to_node = {**ftn_ts, **ftn_js}
    else:
        file_ext = _detect_file_ext(root)
        all_files, module_index, file_to_node = _scan_files(root, scan_excludes=scan_excludes, file_ext=file_ext)
    analyzer = _select_analyzer(stack)

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


# --- WORKFLOW GRAPH (STORY-slim-035) ---


@dataclass
class WorkflowNode:
    id: str
    kind: str   # 'command', 'agent', 'skill', 'file'
    label: str


@dataclass
class WorkflowEdge:
    source: str
    target: str
    relation: str  # 'invokes', 'depends_on', 'reads', 'writes', 'contains'


class WorkflowGraph:
    def __init__(self):
        self.nodes: dict[str, WorkflowNode] = {}
        self.edges: list[WorkflowEdge] = []

    def add_node(self, node: WorkflowNode):
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, edge: WorkflowEdge):
        key = (edge.source, edge.target, edge.relation)
        if not hasattr(self, '_edge_keys'):
            self._edge_keys = set()
        if key not in self._edge_keys:
            self._edge_keys.add(key)
            self.edges.append(edge)

    @staticmethod
    def _sanitize_id(raw: str) -> str:
        """Sanitize a string for use as a Mermaid node ID."""
        return re.sub(r'[^a-zA-Z0-9_]', '_', raw)

    def to_mermaid(self) -> str:
        lines = ['graph TD']
        kind_order = ['command', 'agent', 'skill', 'file']
        kind_labels = {'command': 'Commands', 'agent': 'Agents', 'skill': 'Skills', 'file': 'Files'}
        for kind in kind_order:
            nodes_of_kind = [n for n in self.nodes.values() if n.kind == kind]
            if not nodes_of_kind:
                continue
            lines.append(f'    subgraph {kind_labels[kind]}')
            for n in sorted(nodes_of_kind, key=lambda x: x.id):
                sid = self._sanitize_id(n.id)
                lines.append(f'        {sid}["{n.label}"]')
            lines.append('    end')
        for e in self.edges:
            src = self._sanitize_id(e.source)
            dst = self._sanitize_id(e.target)
            lines.append(f'    {src} -->|{e.relation}| {dst}')
        return nl().join(lines)

    def reverse_reach(self, entry_id: str) -> set[str]:
        """Reverse BFS from entry_id — follow edges backward (target→source)."""
        reverse_map: dict[str, list[str]] = {}
        for e in self.edges:
            reverse_map.setdefault(e.target, []).append(e.source)
        visited: set[str] = set()
        queue = [entry_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for src in reverse_map.get(current, []):
                if src not in visited:
                    queue.append(src)
        return visited


def _parse_commands(commands_dir, graph: WorkflowGraph):
    """Parse command markdown files and extract command→agent, command→skill edges (R2)."""
    if not commands_dir.is_dir():
        return
    agent_pattern = re.compile(r'\*\*Agent\*\*:\s*(.+)')
    role_pattern = re.compile(r'\*\*Role\*\*:\s*(.+)')
    skill_pattern = re.compile(r'pactkit-(\w+)')
    for md in sorted(commands_dir.glob('*.md')):
        cmd_name = md.stem  # e.g. 'project-act'
        content = md.read_text(encoding='utf-8')
        graph.add_node(WorkflowNode(id=cmd_name, kind='command', label=cmd_name))
        # Extract agent role
        for pat in (agent_pattern, role_pattern):
            m = pat.search(content)
            if m:
                agent_label = m.group(1).strip()
                agent_id = re.sub(r'[^a-zA-Z0-9]', '-', agent_label).strip('-').lower()
                graph.add_node(WorkflowNode(id=agent_id, kind='agent', label=agent_label))
                graph.add_edge(WorkflowEdge(source=cmd_name, target=agent_id, relation='invokes'))
                break
        # Extract skill references
        seen_skills = set()
        for m in skill_pattern.finditer(content):
            skill_name = f'pactkit-{m.group(1)}'
            if skill_name not in seen_skills:
                seen_skills.add(skill_name)
                graph.add_node(WorkflowNode(id=skill_name, kind='skill', label=skill_name))
                graph.add_edge(WorkflowEdge(source=cmd_name, target=skill_name, relation='depends_on'))


def _parse_routing_table(rules_dir, graph: WorkflowGraph):
    """Parse rules/04-routing-table.md to extract command→agent→playbook mappings (R3)."""
    rt_path = rules_dir / '04-routing-table.md' if rules_dir.is_dir() else None
    if not rt_path or not rt_path.exists():
        return
    content = rt_path.read_text(encoding='utf-8')
    # Pattern: ### Name (`/project-xxx`) \n - **Role**: Agent Role \n - **Playbook**: `path`
    block_pattern = re.compile(
        r'###\s+\w+[^(]*\(`/([^)]+)`\)\s*\n'
        r'(?:.*?\n)*?'
        r'-\s*\*\*Role\*\*:\s*(.+)',
        re.MULTILINE
    )
    for m in block_pattern.finditer(content):
        cmd_name = m.group(1).strip()
        agent_label = m.group(2).strip()
        agent_id = re.sub(r'[^a-zA-Z0-9]', '-', agent_label).strip('-').lower()
        graph.add_node(WorkflowNode(id=cmd_name, kind='command', label=cmd_name))
        graph.add_node(WorkflowNode(id=agent_id, kind='agent', label=agent_label))
        graph.add_edge(WorkflowEdge(source=cmd_name, target=agent_id, relation='invokes'))


def _scan_skill_files(skills_dir, graph: WorkflowGraph):
    """Discover skill directories and their script files (R4)."""
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_name = skill_dir.name
        graph.add_node(WorkflowNode(id=skill_name, kind='skill', label=skill_name))
        scripts_dir = skill_dir / 'scripts'
        if scripts_dir.is_dir():
            for script in sorted(scripts_dir.iterdir()):
                if script.is_file():
                    file_id = f'{skill_name}/{script.name}'
                    graph.add_node(WorkflowNode(id=file_id, kind='file', label=script.name))
                    graph.add_edge(WorkflowEdge(source=skill_name, target=file_id, relation='contains'))


def regression_workflow_impact(target='.', changed_files=None):
    """Workflow impact for regression gate — informational only (STORY-slim-038 R1-R4).

    Returns a list of impact description strings. Empty list if no matches or on failure.
    """
    if not changed_files:
        return []
    try:
        root = Path(target).resolve()
        graph = build_workflow_graph(root=root)
        if not graph.nodes:
            return []

        # Match changed files against graph nodes (file nodes)
        file_nodes = {n.id: n for n in graph.nodes.values() if n.kind == 'file'}
        matched_entries = set()
        for cf in changed_files:
            cf_basename = cf.rsplit('/', 1)[-1] if '/' in cf else cf
            for fid, fnode in file_nodes.items():
                if cf_basename == fnode.label or cf_basename in fid:
                    matched_entries.add(fid)
            # Also check skill names
            for nid, node in graph.nodes.items():
                if node.kind == 'skill' and node.label in cf:
                    matched_entries.add(nid)

        if not matched_entries:
            return []

        lines = []
        for entry_id in sorted(matched_entries):
            reached = graph.reverse_reach(entry_id)
            affected_cmds = sorted(
                n.label for nid, n in graph.nodes.items()
                if nid in reached and n.kind == 'command'
            )
            if affected_cmds:
                entry_label = graph.nodes.get(entry_id, WorkflowNode(id=entry_id, kind='file', label=entry_id)).label
                lines.append(f'Workflow Impact: {entry_label} changed → affects: {", ".join(affected_cmds)}')
        return lines
    except Exception:
        return []


def workflow_impact(target='.', entry=None, entries=None):
    """Find workflow nodes affected by a changed skill/file (STORY-slim-037).

    Returns a formatted string showing affected commands/agents/skills/files.
    """
    root = Path(target).resolve()
    graph = build_workflow_graph(root=root)

    # Collect all entry points
    entry_ids = []
    if entries:
        entry_ids.extend(entries)
    elif entry:
        entry_ids.append(entry)
    if not entry_ids:
        return 'Error: no entry point specified'

    # Validate entries
    all_node_ids = set(graph.nodes.keys())
    for eid in entry_ids:
        if eid not in all_node_ids:
            available = ', '.join(sorted(all_node_ids)[:20])
            return f'Error: "{eid}" not found in workflow graph. Available nodes: {available}'

    # Union of reverse reach for all entries
    all_reached = set()
    for eid in entry_ids:
        all_reached |= graph.reverse_reach(eid)

    # Group by kind
    grouped: dict[str, list[str]] = {}
    for nid in sorted(all_reached):
        node = graph.nodes.get(nid)
        if node:
            grouped.setdefault(node.kind, []).append(node.label)

    # Format output
    lines = [f'Workflow Impact for "{", ".join(entry_ids)}":']
    kind_labels = {'command': 'Commands', 'agent': 'Agents', 'skill': 'Skills', 'file': 'Files'}
    for kind in ['command', 'agent', 'skill', 'file']:
        items = grouped.get(kind, [])
        if items:
            lines.append(f'  {kind_labels[kind]}: {", ".join(items)}')
    return nl().join(lines)


def build_workflow_graph(root=None, commands_dir=None, rules_dir=None, skills_dir=None):
    """Build a complete WorkflowGraph from PactKit directory structure (R5).

    Accepts explicit dirs for testing, or discovers from root via well-known paths.
    """
    if root is not None:
        root = Path(root).resolve()
        # Try pactkit.yaml for custom paths, else well-known locations
        if commands_dir is None:
            for candidate in [root / '.claude' / 'commands', root / 'commands']:
                if candidate.is_dir():
                    commands_dir = candidate
                    break
            if commands_dir is None:
                # Try home-dir well-known path
                home_cmd = Path.home() / '.claude' / 'commands'
                if home_cmd.is_dir():
                    commands_dir = home_cmd
        if rules_dir is None:
            for candidate in [root / '.claude' / 'rules', root / 'rules']:
                if candidate.is_dir():
                    rules_dir = candidate
                    break
            if rules_dir is None:
                home_rules = Path.home() / '.claude' / 'rules'
                if home_rules.is_dir():
                    rules_dir = home_rules
        if skills_dir is None:
            for candidate in [root / '.claude' / 'skills', root / 'skills']:
                if candidate.is_dir():
                    skills_dir = candidate
                    break
            if skills_dir is None:
                home_skills = Path.home() / '.claude' / 'skills'
                if home_skills.is_dir():
                    skills_dir = home_skills

    graph = WorkflowGraph()
    if commands_dir:
        _parse_commands(commands_dir, graph)
    if rules_dir:
        _parse_routing_table(rules_dir, graph)
    if skills_dir:
        _scan_skill_files(skills_dir, graph)
    return graph


# --- CLI ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init_arch')
    sub.add_parser('list_rules')
    p_viz = sub.add_parser('visualize')
    p_viz.add_argument('--focus')
    p_viz.add_argument('--mode', choices=['file', 'class', 'call', 'workflow'], default='file')
    p_viz.add_argument('--entry')
    p_viz.add_argument('--depth', type=int, default=0, help='Limit graph traversal to N levels (0=unlimited)')
    p_viz.add_argument('--max-nodes', type=int, default=0, help='Truncate graph to N nodes (0=unlimited)')
    p_viz.add_argument('--reverse', action='store_true', default=False, help='Reverse BFS: find callers of entry function (STORY-053)')
    p_viz.add_argument('--lazy', action='store_true', default=False, help='Skip regeneration if graph is up-to-date')
    p_impact = sub.add_parser('impact', help='Find test files impacted by a changed function (STORY-053)')
    p_impact.add_argument('--entry', required=True, help='Changed function name')

    a = parser.parse_args()
    if a.cmd == 'init_arch': print(init_architecture())
    elif a.cmd == 'visualize': print(visualize('.', a.focus, a.mode, a.entry, depth=a.depth, max_nodes=a.max_nodes, reverse=a.reverse, lazy=a.lazy))
    elif a.cmd == 'impact': print(impact('.', a.entry))
    elif a.cmd == 'list_rules': print(list_rules())
