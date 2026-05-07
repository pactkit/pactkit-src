"""Interface summary extraction — AST-based, outputs signatures only (STORY-slim-113).

Produces a compact interface view of Python (and optionally TS/Go) source files,
showing only class/function signatures + docstrings + top-level constants.
"""
import ast
from pathlib import Path

MAX_FILE_BYTES = 1_048_576


def generate_summary(file_paths: list[Path]) -> str:
    """Generate interface summaries for the given files."""
    sections = []
    for path in file_paths:
        sections.append(_summarize_file(path))
    return "\n\n".join(sections)


def _summarize_file(path: Path) -> str:
    """Produce interface summary for a single file."""
    header = f"# {path.name} — Interface Summary"

    if not path.exists():
        return f"{header}\n\n# (file not found)"

    ext = path.suffix.lower()
    if ext == ".py":
        return _summarize_python(path, header)
    elif ext in (".ts", ".tsx", ".js", ".jsx"):
        return f"{header}\n\n# (TypeScript/JavaScript — analyzer unavailable, skipping)"
    elif ext == ".go":
        return f"{header}\n\n# (Go — analyzer unavailable, skipping)"
    else:
        return f"{header}\n\n# (Unsupported or unavailable analyzer for {ext})"


def _summarize_python(path: Path, header: str) -> str:
    """Extract Python interface using stdlib ast."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return f"{header}\n\n# (file too large, skipped)"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        return f"{header}\n\n# (Parse error: {e})"
    except (OSError, UnicodeDecodeError) as e:
        return f"{header}\n\n# (Read error: {e})"

    lines = [header, ""]
    constants = _extract_constants(tree, source)
    if constants:
        for c in constants:
            lines.append(c)
        lines.append("")

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            lines.extend(_format_class(node, source))
            lines.append("")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.extend(_format_function(node, source, indent=""))
            lines.append("")

    return "\n".join(lines).rstrip()


def _is_public_constant(name: str) -> bool:
    """Check if a name is a public constant (UPPER_CASE, not starting with _)."""
    return not name.startswith("_") and name.replace("_", "").isupper() and len(name) > 0


def _extract_constants(tree: ast.Module, source: str) -> list[str]:
    """Extract top-level UPPER_CASE assignments."""
    constants = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and _is_public_constant(target.id):
                    value_repr = _safe_value_repr(node.value)
                    constants.append(f"{target.id} = {value_repr}")
        elif isinstance(node, ast.AnnAssign) and node.target:
            if isinstance(node.target, ast.Name) and _is_public_constant(node.target.id):
                ann = ast.get_source_segment(source, node.annotation) or "..."
                value_repr = ""
                if node.value:
                    value_repr = f" = {_safe_value_repr(node.value)}"
                constants.append(f"{node.target.id}: {ann}{value_repr}")
    return constants


def _safe_value_repr(node: ast.expr) -> str:
    """Get a short repr of a constant value, or '...' for complex expressions."""
    if isinstance(node, ast.Constant):
        r = repr(node.value)
        return r if len(r) <= 60 else r[:57] + "..."
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
        return "..."
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return f"{node.func.id}(...)"
        return "..."
    return "..."


def _format_class(node: ast.ClassDef, source: str) -> list[str]:
    """Format a class definition with methods."""
    bases = [ast.get_source_segment(source, b) or "?" for b in node.bases]
    bases_str = f"({', '.join(bases)})" if bases else ""
    lines = [f"class {node.name}{bases_str}:"]

    docstring = ast.get_docstring(node)
    if docstring:
        first_line = docstring.split("\n")[0].strip()
        lines.append(f'    """{first_line}"""')

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.extend(_format_function(item, source, indent="    "))

    return lines


def _format_function(node, source: str, indent: str) -> list[str]:
    """Format a function/method signature with docstring."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    sig = _build_signature(node, source)
    returns = ""
    if node.returns:
        ret_src = ast.get_source_segment(source, node.returns)
        if ret_src:
            returns = f" -> {ret_src}"

    lines = [f"{indent}{prefix} {node.name}({sig}){returns}:"]

    docstring = ast.get_docstring(node)
    if docstring:
        first_line = docstring.split("\n")[0].strip()
        lines.append(f'{indent}    """{first_line}"""')

    return lines


def _build_signature(node, source: str) -> str:
    """Build parameter signature string from function args."""
    args = node.args
    parts = []

    # positional args
    defaults_offset = len(args.args) - len(args.defaults)
    for i, arg in enumerate(args.args):
        part = arg.arg
        if arg.annotation:
            ann = ast.get_source_segment(source, arg.annotation)
            if ann:
                part = f"{arg.arg}: {ann}"
        default_idx = i - defaults_offset
        if default_idx >= 0:
            default_val = ast.get_source_segment(source, args.defaults[default_idx])
            if default_val and len(default_val) <= 30:
                part = f"{part} = {default_val}"
            elif default_val:
                part = f"{part} = ..."
        parts.append(part)

    # *args
    if args.vararg:
        va = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            ann = ast.get_source_segment(source, args.vararg.annotation)
            if ann:
                va = f"*{args.vararg.arg}: {ann}"
        parts.append(va)
    elif args.kwonlyargs:
        parts.append("*")

    # keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        part = arg.arg
        if arg.annotation:
            ann = ast.get_source_segment(source, arg.annotation)
            if ann:
                part = f"{arg.arg}: {ann}"
        if i < len(args.kw_defaults) and args.kw_defaults[i]:
            default_val = ast.get_source_segment(source, args.kw_defaults[i])
            if default_val and len(default_val) <= 30:
                part = f"{part} = {default_val}"
        parts.append(part)

    # **kwargs
    if args.kwarg:
        kw = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            ann = ast.get_source_segment(source, args.kwarg.annotation)
            if ann:
                kw = f"**{args.kwarg.arg}: {ann}"
        parts.append(kw)

    return ", ".join(parts)
