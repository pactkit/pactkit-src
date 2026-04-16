"""Language analyzer registry for PactKit visualize.

Development-time: imports concrete analyzers for IDE support.
Deploy-time: bodies below _BODY_MARKER are inlined by load_script().
"""
from pathlib import Path as _Path

__all__ = [
    'LanguageAnalyzer', 'TreeSitterAnalyzer',
    'PythonAnalyzer', 'GoAnalyzer', 'TSAnalyzer', 'JavaAnalyzer',
    '_select_analyzer', '_select_analyzers',
]

# === SCRIPT BODY ===

import abc  # noqa: E402
import os  # noqa: E402

# Guard imports: tree-sitter is a core dependency but guard for standalone script usage
try:
    from tree_sitter import Language as _TSLanguage, Parser as _TSParser, Query as _TSQuery, QueryCursor as _TSQueryCursor
    _HAS_TREE_SITTER = True
except ImportError:
    _HAS_TREE_SITTER = False


class LanguageAnalyzer(abc.ABC):
    @abc.abstractmethod
    def extract_imports(self, file_path) -> list:
        """Return list of imported module name strings."""
        ...

    @abc.abstractmethod
    def extract_functions_and_calls(self, file_path, include_complexity=False) -> tuple:
        """Return (func_registry, call_edges) or (func_registry, call_edges, complexity_map) for one file.

        When include_complexity=False (default): returns 2-tuple for backward compatibility.
        When include_complexity=True: returns 3-tuple with complexity_map: dict[str, int].
        """
        ...

    @abc.abstractmethod
    def extract_classes(self, file_path, root) -> list:
        """Return list of (rel_path, class_name, bases, methods) tuples for one file."""
        ...

    def build_module_keys(self, rel_path, root) -> list:
        """Return list of module_index keys to register for a given file.

        Default implementation: Python-style dot-separated paths.
        Override in subclasses for language-specific key formats.
        """
        keys = []
        module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
        keys.append(module_name)
        if len(rel_path.parts) > 1 and rel_path.parts[0] == 'src':
            short = str(_Path(*rel_path.parts[1:]).with_suffix(''))
            keys.append(short.replace(os.sep, '.'))
        if rel_path.name == '__init__.py':
            pkg_name = str(rel_path.parent).replace(os.sep, '.')
            keys.append(pkg_name)
            if len(rel_path.parts) > 2 and rel_path.parts[0] == 'src':
                short_pkg = '.'.join(rel_path.parts[1:-1])
                keys.append(short_pkg)
        return keys

    def normalize_import(self, import_str, consumer_path, root):
        """Normalize an import string to match module_index keys.

        Returns None if the import is external/stdlib and should be skipped.
        Default implementation: return as-is (Python behavior).
        """
        return import_str


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

    def extract_functions_and_calls(self, file_path, include_complexity=False):
        try:
            source = file_path.read_bytes()
            tree = self._parser.parse(source)
            result = self._extract_funcs_and_calls(tree, file_path.stem)
            if include_complexity:
                func_registry, call_edges = result
                complexity_map = self._compute_complexity(tree)
                return func_registry, call_edges, complexity_map
            return result
        except Exception:
            return ({}, {}, {}) if include_complexity else ({}, {})

    def _extract_funcs_and_calls(self, tree, stem):
        """Override in subclasses for language-specific extraction logic."""
        return {}, {}

    def _compute_complexity(self, tree):
        """Compute cyclomatic complexity for all functions in the tree.

        Uses tree-sitter node types common to most languages.
        Subclasses can override for language-specific nodes.
        Returns dict[str, int] mapping qualified function name to complexity score.
        """
        _DECISION_TYPES = {
            'if_statement', 'else_clause',
            'for_statement', 'for_in_statement',
            'while_statement', 'do_statement',
            'catch_clause', 'except_clause',
            'case_clause', 'switch_case',
            'ternary_expression', 'conditional_expression',
            'binary_expression',  # handled below for && / ||
        }
        _BOOL_OPS = {'&&', '||', 'and', 'or'}

        complexity_map = {}

        for _, match_dict in self._matches(self._func_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if not names or not bodies:
                continue
            func_name = names[0].text.decode()
            # Check for enclosing class
            class_name = None
            parent = names[0].parent
            while parent:
                if parent.type in ('class_declaration', 'class_definition'):
                    name_node = parent.child_by_field_name('name')
                    if name_node:
                        class_name = name_node.text.decode()
                    break
                parent = parent.parent
            qname = f'{class_name}.{func_name}' if class_name else func_name

            count = 1  # base complexity
            stack = [bodies[0]]
            while stack:
                node = stack.pop()
                if node.type in _DECISION_TYPES:
                    if node.type == 'binary_expression':
                        op_node = node.child_by_field_name('operator')
                        if op_node and op_node.text and op_node.text.decode() in _BOOL_OPS:
                            count += 1
                    elif node.type == 'else_clause':
                        # Only count else-if, not plain else
                        has_if_child = any(c.type == 'if_statement' for c in node.children)
                        if has_if_child:
                            pass  # The nested if_statement will be counted
                        # Plain else does not add to complexity
                    else:
                        count += 1
                for child in node.children:
                    stack.append(child)
            complexity_map[qname] = count

        # Also handle methods if _method_query exists
        if self._method_query:
            for _, match_dict in self._matches(self._method_query, tree.root_node):
                names = match_dict.get('name', [])
                bodies = match_dict.get('body', [])
                receivers = match_dict.get('receiver_type', [])
                if not names or not bodies:
                    continue
                func_name = names[0].text.decode()
                receiver_type = ''
                if receivers:
                    raw = receivers[0].text.decode()
                    receiver_type = self._re.sub(r'[*& \[\]]', '', raw).strip()
                qname = f'{receiver_type}.{func_name}' if receiver_type else func_name

                count = 1
                stack = [bodies[0]]
                while stack:
                    node = stack.pop()
                    if node.type in _DECISION_TYPES:
                        if node.type == 'binary_expression':
                            op_node = node.child_by_field_name('operator')
                            if op_node and op_node.text and op_node.text.decode() in _BOOL_OPS:
                                count += 1
                        elif node.type == 'else_clause':
                            has_if_child = any(c.type == 'if_statement' for c in node.children)
                            if has_if_child:
                                pass
                        else:
                            count += 1
                    for child in node.children:
                        stack.append(child)
                complexity_map[qname] = count

        return complexity_map

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

        # STORY-slim-069 R1: Parse dispatch hint comments in body
        comment_query = getattr(self, '_comment_query', None)
        if comment_query:
            try:
                comment_captures = self._captures(comment_query, body_node)
                for node in comment_captures.get('comment', []):
                    text = node.text.decode().strip()
                    if text.startswith('//'):
                        text = text[2:].strip()
                    elif text.startswith('/*') and text.endswith('*/'):
                        text = text[2:-2].strip()
                    if text.startswith('pactkit-trace: dispatches_to '):
                        targets = text[len('pactkit-trace: dispatches_to '):]
                        for t in targets.split(','):
                            t = t.strip()
                            if t:
                                calls.append(t)
            except Exception:
                pass

        return calls


# Development-time re-exports — concrete analyzers inherit from base classes above.
# In deployed (exec'd) standalone script, relative imports don't exist, so skip silently.
try:
    from .python_analyzer import PythonAnalyzer  # noqa: F401
    from .go_analyzer import GoAnalyzer  # noqa: F401
    from .ts_analyzer import TSAnalyzer  # noqa: F401
    from .java_analyzer import JavaAnalyzer  # noqa: F401
except (ImportError, KeyError):
    pass
