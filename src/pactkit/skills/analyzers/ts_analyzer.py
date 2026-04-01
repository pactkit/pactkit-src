"""TypeScript/JavaScript language analyzer — tree-sitter based."""
import os

from pactkit.skills.analyzers import TreeSitterAnalyzer  # dev-time only

# === SCRIPT BODY ===

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


class TSAnalyzer(TreeSitterAnalyzer):
    """TypeScript/JavaScript language analyzer using tree-sitter-typescript (STORY-slim-034)."""
    def __init__(self):
        from tree_sitter import Language as _TSLanguage, Parser as _TSParser, Query as _TSQuery
        import tree_sitter_typescript as _tsts
        self._lang = _TSLanguage(_tsts.language_typescript())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _TS_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _TS_FUNC_QUERY)
        self._call_query = _TSQuery(self._lang, _TS_CALL_QUERY)
        self._method_query = None
        self._comment_query = _TSQuery(self._lang, '(comment) @comment')

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

        # STORY-slim-069 R4: class extends → inheritance edges
        class_bases = {}
        for node in tree.root_node.children:
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    continue
                cls_name = name_node.text.decode()
                bases = []
                for child in node.children:
                    if child.type == 'class_heritage':
                        for hc in child.children:
                            if hc.type == 'extends_clause':
                                for ec in hc.children:
                                    if ec.type in ('type_identifier', 'identifier'):
                                        bases.append(ec.text.decode())
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
        """Extract class definitions from a TypeScript file using tree-sitter."""
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
                    for child in node.children:
                        if child.type == 'class_heritage':
                            for hc in child.children:
                                if hc.type == 'extends_clause':
                                    for ec in hc.children:
                                        if ec.type in ('type_identifier', 'identifier'):
                                            bases.append(ec.text.decode())
                    methods = []
                    body_node = node.child_by_field_name('body')
                    if body_node:
                        for member in body_node.children:
                            if member.type == 'method_definition':
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
        """Return TS/JS-style module_index keys: slash-separated path variants."""
        keys = []
        no_ext = rel_path.with_suffix('')
        # Slash-separated relative path
        slash_key = str(no_ext).replace(os.sep, '/')
        keys.append(slash_key)
        # Without src prefix
        parts = no_ext.parts
        if len(parts) > 1 and parts[0] == 'src':
            keys.append('/'.join(parts[1:]))
        # Dot-separated for backward compat
        dot_key = str(no_ext).replace(os.sep, '.')
        keys.append(dot_key)
        # src-strip dot format
        if len(parts) > 1 and parts[0] == 'src':
            keys.append('.'.join(parts[1:]))
        # Index file: directory itself is importable
        if no_ext.name == 'index':
            dir_slash = str(no_ext.parent).replace(os.sep, '/')
            keys.append(dir_slash)
            if len(parts) > 2 and parts[0] == 'src':
                keys.append('/'.join(parts[1:-1]))
        return keys

    # --- R2: normalize_import (STORY-slim-078) ---

    def normalize_import(self, import_str, consumer_path, root):
        """Normalize TS/JS import to match module_index keys.

        Returns None for bare module imports (react, @scope/pkg).
        Resolves relative imports (./foo, ../bar) against consumer directory.
        """
        # Bare module imports are external packages
        if not import_str.startswith('.'):
            return None
        # Resolve relative import against consumer directory
        try:
            consumer_rel = consumer_path.relative_to(root)
        except ValueError:
            return None
        consumer_dir_parts = list(consumer_rel.parent.parts)
        # Split the import path
        import_parts = import_str.replace('\\', '/').split('/')
        # Start from consumer dir and resolve
        result = list(consumer_dir_parts)
        for p in import_parts:
            if p == '..':
                if result:
                    result.pop()
            elif p != '.':
                result.append(p)
        return '/'.join(result)
