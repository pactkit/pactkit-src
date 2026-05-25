"""Python language analyzer — AST-based, no tree-sitter dependency."""
import ast
import os
from pathlib import Path

from pactkit.skills.analyzers import LanguageAnalyzer  # dev-time only

# === SCRIPT BODY ===

MAX_FILE_BYTES = 1_048_576  # Canonical: visualize.py


class PythonAnalyzer(LanguageAnalyzer):
    """Python language analyzer using the stdlib ast module."""

    def extract_imports(self, file_path):
        """Parse a Python file and return a list of imported module name strings."""
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                import sys as _sys
                print(f"\u26a0\ufe0f Skipping large file: {file_path} ({file_path.stat().st_size} bytes)", file=_sys.stderr)
                return []
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

    def extract_functions_and_calls(self, file_path, include_complexity=False):
        """Parse a Python file and return (func_registry, call_edges) or 3-tuple with complexity_map."""
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                import sys as _sys
                print(f"\u26a0\ufe0f Skipping large file: {file_path} ({file_path.stat().st_size} bytes)", file=_sys.stderr)
                return ({}, {}, {}) if include_complexity else ({}, {})
            source_text = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source_text)
            rel = file_path.stem
            func_registry = {}
            call_edges = {}
            complexity_map = {}
            class_defs = {}

            # Build parent map for qname construction (R3: nested functions)
            parent_map = {}
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    parent_map[id(child)] = node

            def _get_qname(func_node):
                """Construct qualified name for a function, walking up the parent chain."""
                parts = [func_node.name]
                p = parent_map.get(id(func_node))
                while p is not None and not isinstance(p, ast.Module):
                    if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parts.append(p.name)
                    elif isinstance(p, ast.ClassDef):
                        parts.append(p.name)
                    p = parent_map.get(id(p))
                parts.reverse()
                return '.'.join(parts)

            def _get_current_class(func_node):
                """Return the class name if this function is a direct class method."""
                p = parent_map.get(id(func_node))
                if isinstance(p, ast.ClassDef):
                    return p.name
                return None

            # R3: use ast.walk to find all FunctionDef at any depth
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = _get_qname(node)
                    current_class = _get_current_class(node)
                    func_registry[qname] = rel
                    call_edges[qname] = _extract_calls(node, current_class=current_class, source_text=source_text)
                    if include_complexity:
                        complexity_map[qname] = _compute_python_complexity(node)
                elif isinstance(node, ast.ClassDef):
                    class_defs[node.name] = node

            # R2: capture module-level function references in list/tuple/assign
            module_refs = _extract_module_refs(tree)
            if module_refs:
                key = '__module__'
                call_edges.setdefault(key, []).extend(module_refs)
            # STORY-slim-068 R3: Add virtual edges for inheritance overrides
            for cls_name, cls_node in class_defs.items():
                sub_methods = {item.name for item in cls_node.body
                               if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
                for base in cls_node.bases:
                    base_name = None
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name and base_name in class_defs:
                        base_methods = {item.name for item in class_defs[base_name].body
                                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
                        for method in sub_methods & base_methods:
                            base_qname = f'{base_name}.{method}'
                            sub_qname = f'{cls_name}.{method}'
                            if base_qname in call_edges:
                                call_edges[base_qname].append(sub_qname)
                            else:
                                call_edges[base_qname] = [sub_qname]
            if include_complexity:
                return func_registry, call_edges, complexity_map
            return func_registry, call_edges
        except (SyntaxError, UnicodeDecodeError, ValueError):
            return ({}, {}, {}) if include_complexity else ({}, {})

    def extract_classes(self, file_path, root):
        """Extract class definitions from a Python file using ast."""
        classes = []
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                return []
            tree = ast.parse(file_path.read_text(encoding='utf-8'))
            rel = str(file_path.relative_to(root))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = []
                    for b in node.bases:
                        if isinstance(b, ast.Name):
                            bases.append(b.id)
                        elif isinstance(b, ast.Attribute):
                            bases.append(b.attr)
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            prefix = '+' if not item.name.startswith('_') else '-'
                            args = [a.arg for a in item.args.args if a.arg != 'self']
                            sig = f"{prefix}{item.name}({', '.join(args)})"
                            methods.append(sig)
                    classes.append((rel, node.name, bases, methods))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            pass
        return classes

    def build_module_keys(self, rel_path, root) -> list:
        """Return Python-style module_index keys (backward compatible)."""
        keys = []
        module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
        keys.append(module_name)
        if len(rel_path.parts) > 1 and rel_path.parts[0] == 'src':
            short = str(Path(*rel_path.parts[1:]).with_suffix(''))
            keys.append(short.replace(os.sep, '.'))
        if rel_path.name == '__init__.py':
            pkg_name = str(rel_path.parent).replace(os.sep, '.')
            keys.append(pkg_name)
            if len(rel_path.parts) > 2 and rel_path.parts[0] == 'src':
                short_pkg = '.'.join(rel_path.parts[1:-1])
                keys.append(short_pkg)
        return keys

    def normalize_import(self, import_str, consumer_path, root):
        """Python imports are already in dot notation — return as-is."""
        return import_str


def _compute_python_complexity(func_node):
    """Compute cyclomatic complexity for a Python function AST node.

    Counts: if, for, while, and, or, except, match/case. Base = 1.
    STORY-slim-089 R3.
    """
    count = 1  # base complexity
    for node in ast.walk(func_node):
        if isinstance(node, ast.If):
            count += 1
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            count += 1
        elif isinstance(node, (ast.While,)):
            count += 1
        elif isinstance(node, ast.BoolOp):
            # Each 'and'/'or' adds one per operator (n values = n-1 operators)
            count += len(node.values) - 1
        elif isinstance(node, ast.ExceptHandler):
            count += 1
        elif isinstance(node, ast.IfExp):  # ternary: x if cond else y
            count += 1
        # Python 3.10+ match/case
        elif hasattr(ast, 'Match') and isinstance(node, ast.Match):
            pass  # The match itself doesn't add; each case does
        elif hasattr(ast, 'match_case') and isinstance(node, ast.match_case):
            count += 1
    return count


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

_DISPATCH_HINT_PREFIX = '# pactkit-trace: dispatches_to '

_REF_BUILTINS_EXTRA = {'None', 'True', 'False', 'self', 'cls'}


def _is_func_ref_candidate(name: str) -> bool:
    """Return True if a bare name looks like a function reference (not a constant)."""
    if name in _BUILTIN_CALLEES or name in _REF_BUILTINS_EXTRA:
        return False
    if len(name) <= 1:
        return False
    if name.isupper():  # ALL_CAPS constants like MAX, TIMEOUT
        return False
    return True


def _extract_module_refs(tree) -> list:
    """Extract function references from module-level assignments and collection literals."""
    refs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            # TOOLS = [func_a, func_b] or TOOLS = (func_a,)
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Name) and _is_func_ref_candidate(elt.id):
                        refs.append(elt.id)
            # handler = process_event
            elif isinstance(node.value, ast.Name) and _is_func_ref_candidate(node.value.id):
                refs.append(node.value.id)
    return refs


def _extract_calls(func_node, current_class=None, source_text=None):
    """Extract function/method calls from a function body."""
    callees = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            try:
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name not in _BUILTIN_CALLEES:
                        callees.append(name)
                elif isinstance(node.func, ast.Attribute):
                    # R1: capture all obj.method() calls, not just self.method()
                    attr = node.func.attr
                    if attr not in _BUILTIN_CALLEES:
                        if isinstance(node.func.value, ast.Name):
                            if node.func.value.id == 'self' and current_class:
                                callees.append(f'{current_class}.{attr}')
                            else:
                                callees.append(attr)  # bare method name; _resolve_callee handles suffix match
                        else:
                            callees.append(attr)  # chained calls e.g. foo().bar()
            except AttributeError:
                pass
        # R2: function references in list/tuple literals and keyword arguments
        elif isinstance(node, (ast.List, ast.Tuple)):
            for elt in node.elts:
                if isinstance(elt, ast.Name) and _is_func_ref_candidate(elt.id):
                    callees.append(elt.id)
        elif isinstance(node, ast.keyword):
            if isinstance(node.value, ast.Name) and _is_func_ref_candidate(node.value.id):
                callees.append(node.value.id)
        elif isinstance(node, ast.Assign):
            # direct assignment: handler = process_event (bare name RHS)
            if isinstance(node.value, ast.Name) and _is_func_ref_candidate(node.value.id):
                callees.append(node.value.id)
    # STORY-slim-068 R2: Parse dispatch hint comments from source text
    if source_text:
        try:
            segment = ast.get_source_segment(source_text, func_node)
            if segment:
                for line in segment.splitlines():
                    stripped = line.strip()
                    if stripped.startswith(_DISPATCH_HINT_PREFIX):
                        targets = stripped[len(_DISPATCH_HINT_PREFIX):]
                        for t in targets.split(','):
                            t = t.strip()
                            if t:
                                callees.append(t)
        except Exception:
            pass
    return callees
