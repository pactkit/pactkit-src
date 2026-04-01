"""Java language analyzer — tree-sitter based."""
import os

from pactkit.skills.analyzers import TreeSitterAnalyzer  # dev-time only

# === SCRIPT BODY ===

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
        from tree_sitter import Language as _TSLanguage, Parser as _TSParser, Query as _TSQuery
        import tree_sitter_java as _tsj
        import re as _re
        self._re = _re
        self._lang = _TSLanguage(_tsj.language())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _JAVA_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _JAVA_FUNC_QUERY)
        self._constructor_query = _TSQuery(self._lang, _JAVA_CONSTRUCTOR_QUERY)
        self._call_query = _TSQuery(self._lang, _JAVA_CALL_QUERY)
        self._method_query = None
        self._comment_query = _TSQuery(self._lang, '[(line_comment)(block_comment)] @comment')

    def _captures(self, query, node):
        from tree_sitter import QueryCursor as _TSQueryCursor
        cursor = _TSQueryCursor(query)
        return cursor.captures(node)

    def _matches(self, query, node):
        from tree_sitter import QueryCursor as _TSQueryCursor
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

    def _extract_calls_from_body(self, body_node):
        calls = []
        captures = self._captures(self._call_query, body_node)
        callees = [n.text.decode() for n in captures.get('callee', [])]
        calls.extend(callees)
        objs = [n.text.decode() for n in captures.get('obj', [])]
        methods = [n.text.decode() for n in captures.get('method', [])]
        for obj, method in zip(objs, methods):
            calls.append(f'{obj}.{method}')
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

        for _, match_dict in self._matches(self._constructor_query, tree.root_node):
            names = match_dict.get('name', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                name_node = names[0]
                ctor_name = name_node.text.decode()
                qname = f'{ctor_name}.{ctor_name}'
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        # STORY-slim-069 R3: extends/implements → inheritance edges
        class_bases = {}
        for node in tree.root_node.children:
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    continue
                cls_name = name_node.text.decode()
                bases = []
                superclass = node.child_by_field_name('superclass')
                if superclass:
                    for c in superclass.children:
                        if c.type == 'type_identifier':
                            bases.append(c.text.decode())
                for child in node.children:
                    if child.type == 'super_interfaces':
                        for c in child.children:
                            if c.type == 'type_list':
                                for ti in c.children:
                                    if ti.type == 'type_identifier':
                                        bases.append(ti.text.decode())
                if bases:
                    class_bases[cls_name] = bases

        for sub_name, bases in class_bases.items():
            sub_methods = {k.split('.', 1)[1] for k in func_registry if k.startswith(f'{sub_name}.')}
            for base_name in bases:
                base_methods = {k.split('.', 1)[1] for k in func_registry if k.startswith(f'{base_name}.')}
                for method in sub_methods & base_methods:
                    base_qname = f'{base_name}.{method}'
                    sub_qname = f'{sub_name}.{method}'
                    if base_qname in call_edges:
                        call_edges[base_qname].append(sub_qname)
                    else:
                        call_edges[base_qname] = [sub_qname]

        return func_registry, call_edges

    def extract_classes(self, file_path, root):
        """Extract class definitions from a Java file using tree-sitter."""
        classes = []
        try:
            source = file_path.read_bytes()
            tree = self._parser.parse(source)
            rel = str(file_path.relative_to(root))

            for node in tree.root_node.children:
                if node.type == 'class_declaration':
                    name_node = node.child_by_field_name('name')
                    if not name_node:
                        continue
                    cls_name = name_node.text.decode()
                    bases = []
                    superclass = node.child_by_field_name('superclass')
                    if superclass:
                        for c in superclass.children:
                            if c.type == 'type_identifier':
                                bases.append(c.text.decode())
                    for child in node.children:
                        if child.type == 'super_interfaces':
                            for c in child.children:
                                if c.type == 'type_list':
                                    for ti in c.children:
                                        if ti.type == 'type_identifier':
                                            bases.append(ti.text.decode())
                    methods = []
                    body_node = node.child_by_field_name('body')
                    if body_node:
                        for member in body_node.children:
                            if member.type == 'method_declaration':
                                mname_node = member.child_by_field_name('name')
                                if mname_node:
                                    mname = mname_node.text.decode()
                                    prefix = '+' if not mname.startswith('_') else '-'
                                    methods.append(f"{prefix}{mname}()")
                    classes.append((rel, cls_name, bases, methods))
        except Exception:
            pass
        return classes

    # --- R1: build_module_keys (STORY-slim-078) ---

    def build_module_keys(self, rel_path, root) -> list:
        """Return Java-style module_index keys: qualified name + full path."""
        keys = []
        # Full path dot-separated
        dot_key = str(rel_path.with_suffix('')).replace(os.sep, '.')
        keys.append(dot_key)
        # Extract qualified name: find 'java' in path, take everything after
        parts = rel_path.with_suffix('').parts
        for i, part in enumerate(parts):
            if part == 'java':
                qualified = '.'.join(parts[i + 1:])
                keys.append(qualified)
                break
        # src-strip
        if len(parts) > 1 and parts[0] == 'src':
            keys.append('.'.join(parts[1:]))
        return keys

    # --- R2: normalize_import (STORY-slim-078) ---

    def normalize_import(self, import_str, consumer_path, root):
        """Normalize Java import to match module_index keys.

        Returns None for java stdlib imports.
        """
        if import_str.startswith('java.') or import_str.startswith('javax.'):
            return None
        if import_str.startswith('android.'):
            return None
        # Skip wildcard imports
        if import_str.endswith('.*'):
            return None
        return import_str
