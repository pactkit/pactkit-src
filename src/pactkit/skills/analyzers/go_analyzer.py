"""Go language analyzer — tree-sitter based."""
import os
import re

from pactkit.skills.analyzers import TreeSitterAnalyzer  # dev-time only

# === SCRIPT BODY ===

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

# Well-known Go stdlib top-level packages (single-segment imports)
_GO_STDLIB_ROOTS = frozenset({
    'archive', 'bufio', 'builtin', 'bytes', 'cmp', 'compress', 'container',
    'context', 'crypto', 'database', 'debug', 'embed', 'encoding', 'errors',
    'expvar', 'flag', 'fmt', 'go', 'hash', 'html', 'image', 'index', 'io',
    'iter', 'log', 'maps', 'math', 'mime', 'net', 'os', 'path', 'plugin',
    'reflect', 'regexp', 'runtime', 'slices', 'sort', 'strconv', 'strings',
    'structs', 'sync', 'syscall', 'testing', 'text', 'time', 'unicode',
    'unique', 'unsafe',
})


class GoAnalyzer(TreeSitterAnalyzer):
    """Go language analyzer using tree-sitter-go."""
    def __init__(self):
        from tree_sitter import Language as _TSLanguage, Parser as _TSParser, Query as _TSQuery
        import tree_sitter_go as _tsg
        self._re = re
        self._lang = _TSLanguage(_tsg.language())
        self._parser = _TSParser(self._lang)
        self._import_query = _TSQuery(self._lang, _GO_IMPORT_QUERY)
        self._func_query = _TSQuery(self._lang, _GO_FUNC_QUERY)
        self._method_query = _TSQuery(self._lang, _GO_METHOD_QUERY)
        self._call_query = _TSQuery(self._lang, _GO_CALL_QUERY)
        self._comment_query = _TSQuery(self._lang, '(comment) @comment')
        self._go_mod_cache = {}

    # --- Shared tree-sitter helpers (delegated from TreeSitterAnalyzer) ---

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
                qname = names[0].text.decode()
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        for _, match_dict in self._matches(self._method_query, tree.root_node):
            names = match_dict.get('name', [])
            receivers = match_dict.get('receiver_type', [])
            bodies = match_dict.get('body', [])
            if names and bodies:
                receiver_type = ''
                if receivers:
                    raw = receivers[0].text.decode()
                    receiver_type = self._re.sub(r'[*& \[\]]', '', raw).strip()
                func_name = names[0].text.decode()
                qname = f'{receiver_type}.{func_name}' if receiver_type else func_name
                func_registry[qname] = stem
                call_edges[qname] = self._extract_calls_from_body(bodies[0])

        # STORY-slim-069 R2: struct embedding → inheritance edges
        struct_bases = {}
        for node in tree.root_node.children:
            if node.type == 'type_declaration':
                for child in node.children:
                    if child.type == 'type_spec':
                        name_node = child.child_by_field_name('name')
                        type_node = child.child_by_field_name('type')
                        if name_node and type_node and type_node.type == 'struct_type':
                            struct_name = name_node.text.decode()
                            embedded = []
                            for field_list in type_node.children:
                                if field_list.type == 'field_declaration_list':
                                    for field in field_list.children:
                                        if field.type == 'field_declaration':
                                            has_field_id = any(
                                                c.type == 'field_identifier' for c in field.children
                                            )
                                            if not has_field_id:
                                                for c in field.children:
                                                    if c.type == 'type_identifier':
                                                        embedded.append(c.text.decode())
                                                    elif c.type == 'pointer_type':
                                                        for pc in c.children:
                                                            if pc.type == 'type_identifier':
                                                                embedded.append(pc.text.decode())
                            if embedded:
                                struct_bases[struct_name] = embedded

        for sub_name, bases in struct_bases.items():
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
        """Extract struct/interface definitions from a Go file using tree-sitter."""
        classes = []
        try:
            source = file_path.read_bytes()
            tree = self._parser.parse(source)
            rel = str(file_path.relative_to(root))

            method_map = {}
            for _, match_dict in self._matches(self._method_query, tree.root_node):
                names = match_dict.get('name', [])
                receivers = match_dict.get('receiver_type', [])
                if names:
                    func_name = names[0].text.decode()
                    receiver_type = ''
                    if receivers:
                        raw = receivers[0].text.decode()
                        receiver_type = self._re.sub(r'[*& \[\]]', '', raw).strip()
                    if receiver_type:
                        prefix = '+' if not func_name.startswith('_') else '-'
                        sig = f"{prefix}{func_name}()"
                        method_map.setdefault(receiver_type, []).append(sig)

            for node in tree.root_node.children:
                if node.type == 'type_declaration':
                    for child in node.children:
                        if child.type == 'type_spec':
                            name_node = child.child_by_field_name('name')
                            type_node = child.child_by_field_name('type')
                            if not name_node or not type_node:
                                continue
                            struct_name = name_node.text.decode()
                            bases = []
                            if type_node.type == 'struct_type':
                                for field_list in type_node.children:
                                    if field_list.type == 'field_declaration_list':
                                        for field in field_list.children:
                                            if field.type == 'field_declaration':
                                                has_field_id = any(
                                                    c.type == 'field_identifier' for c in field.children
                                                )
                                                if not has_field_id:
                                                    for c in field.children:
                                                        if c.type == 'type_identifier':
                                                            bases.append(c.text.decode())
                                                        elif c.type == 'pointer_type':
                                                            for pc in c.children:
                                                                if pc.type == 'type_identifier':
                                                                    bases.append(pc.text.decode())
                            methods = method_map.get(struct_name, [])
                            classes.append((rel, struct_name, bases, methods))
        except Exception:
            pass
        return classes

    # --- R1: build_module_keys (STORY-slim-078) ---

    def build_module_keys(self, rel_path, root) -> list:
        """Return Go-style module_index keys: slash-separated + package-level."""
        keys = []
        # Slash-separated file path without extension
        slash_key = str(rel_path.with_suffix('')).replace(os.sep, '/')
        keys.append(slash_key)
        # Package-level key (directory path)
        pkg_key = str(rel_path.parent).replace(os.sep, '/')
        if pkg_key != '.':
            keys.append(pkg_key)
        # Without top-level dir
        parts = rel_path.with_suffix('').parts
        if len(parts) > 1:
            keys.append('/'.join(parts[1:]))
        # Package without top-level
        pkg_parts = rel_path.parent.parts
        if len(pkg_parts) > 1:
            keys.append('/'.join(pkg_parts[1:]))
        # Dot-separated for backward compat
        dot_key = str(rel_path.with_suffix('')).replace(os.sep, '.')
        keys.append(dot_key)
        return keys

    # --- R2: normalize_import (STORY-slim-078) ---

    def normalize_import(self, import_str, consumer_path, root):
        """Normalize Go import path to match module_index keys.

        Returns None for stdlib/external imports.
        """
        # Single-segment import → stdlib (fmt, os, etc.)
        if '/' not in import_str:
            return None
        # Multi-segment stdlib (net/http, encoding/json, etc.)
        top = import_str.split('/')[0]
        if top in _GO_STDLIB_ROOTS:
            return None
        # Known external prefixes
        if import_str.startswith('golang.org/') or import_str.startswith('google.golang.org/'):
            return None
        # Try to strip module prefix from nearest go.mod
        mod_prefix, go_mod_dir = self._find_nearest_go_mod(consumer_path, root)
        if mod_prefix and import_str.startswith(mod_prefix):
            rel = import_str[len(mod_prefix):].lstrip('/')
            if rel and go_mod_dir:
                # Prepend go.mod's directory relative to root
                try:
                    dir_rel = go_mod_dir.relative_to(root)
                    dir_prefix = str(dir_rel).replace(os.sep, '/')
                    if dir_prefix and dir_prefix != '.':
                        return dir_prefix + '/' + rel
                except ValueError:
                    pass
            return rel if rel else None
        # Check if first component matches a local directory
        parts = import_str.split('/')
        if (root / parts[0]).is_dir():
            return import_str
        return None

    # --- R5: Go module prefix detection (STORY-slim-078, STORY-slim-080) ---

    def _find_nearest_go_mod(self, file_path, root):
        """Walk from file_path's parent up to root, find nearest go.mod.

        Returns (module_prefix, go_mod_dir) or (None, None).
        """
        if not hasattr(self, '_go_mod_cache'):
            self._go_mod_cache = {}

        root_resolved = root.resolve()
        current = file_path.parent
        go_mod_path = None
        while True:
            candidate = current / 'go.mod'
            if candidate.exists():
                go_mod_path = candidate
                break
            try:
                if current.resolve() == root_resolved or current == current.parent:
                    break
            except (OSError, ValueError):
                break
            current = current.parent

        if go_mod_path is None:
            return None, None

        cache_key = str(go_mod_path)
        if cache_key in self._go_mod_cache:
            return self._go_mod_cache[cache_key], go_mod_path.parent

        try:
            for line in go_mod_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith('module '):
                    prefix = line[len('module '):].strip()
                    self._go_mod_cache[cache_key] = prefix
                    return prefix, go_mod_path.parent
        except (OSError, UnicodeDecodeError):
            pass
        self._go_mod_cache[cache_key] = None
        return None, None
