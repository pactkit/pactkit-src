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

    def extract_functions_and_calls(self, file_path):
        """Parse a Python file and return (func_registry, call_edges) for that file."""
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                import sys as _sys
                print(f"\u26a0\ufe0f Skipping large file: {file_path} ({file_path.stat().st_size} bytes)", file=_sys.stderr)
                return {}, {}
            source_text = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source_text)
            rel = file_path.stem
            func_registry = {}
            call_edges = {}
            class_defs = {}
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = node.name
                    func_registry[qname] = rel
                    call_edges[qname] = _extract_calls(node, current_class=None, source_text=source_text)
                elif isinstance(node, ast.ClassDef):
                    class_defs[node.name] = node
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            qname = f'{node.name}.{item.name}'
                            func_registry[qname] = rel
                            call_edges[qname] = _extract_calls(item, current_class=node.name, source_text=source_text)
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
            return func_registry, call_edges
        except (SyntaxError, UnicodeDecodeError, ValueError):
            return {}, {}

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


def _extract_calls(func_node, current_class=None, source_text=None):
    """Extract function/method calls from a function body (BUG-012: filtered)."""
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
