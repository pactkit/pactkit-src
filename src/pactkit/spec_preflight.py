"""Deterministically load Spec implementation inputs and issue receipts."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pactkit.utils import atomic_write

SCHEMA_VERSION = 1
MAX_INLINE_BYTES = 32_768
MAX_TOTAL_BYTES = 131_072
_INPUT_HEADING = re.compile(r"^##\s+Implementation Inputs\s*$", re.I | re.M)
_NEXT_H2 = re.compile(r"^##\s+", re.M)
_BACKTICK_REFERENCE = re.compile(r"`([^`\n]+)`")
_INLINE_RANGE = re.compile(r"^(?P<path>.+?):L?(?P<start>\d+)-(?P<end>\d+)$", re.I)
_CONSTRAINT = re.compile(r"^.*(?:\b(?:MUST(?: NOT)?|SHALL|REQUIRED|NEVER)\b|禁止|必须|不得|对齐).*$", re.I | re.M)
_CSS_TOKEN = re.compile(r"(?P<name>--[A-Za-z0-9_-]+)\s*:\s*(?P<value>[^;{}]+)")
_CODE_SUFFIXES = frozenset({".py", ".js", ".jsx", ".ts", ".tsx"})
_IGNORED_TREE_PARTS = frozenset({
    ".git", ".pactkit", "node_modules", ".venv", "worktrees",
})


class PreflightError(ValueError):
    """A deterministic Spec input could not be loaded safely."""


@dataclass(frozen=True)
class PreflightResult:
    rendered: str
    receipt_path: Path
    receipt: dict


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _section(raw: str) -> str:
    match = _INPUT_HEADING.search(raw)
    if not match:
        return ""
    following = raw[match.end():]
    next_heading = _NEXT_H2.search(following)
    return following[:next_heading.start()] if next_heading else following


def _parse_table(raw: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in _section(raw).splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [cell.strip().lower() for cell in lines[0].strip("|").split("|")]
    if "path" not in headers:
        return []
    entries: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            raise PreflightError(f"malformed Implementation Inputs row: {line}")
        row = dict(zip(headers, cells, strict=True))
        if row.get("path"):
            entries.append(row)
    return entries


def _discover_references(root: Path, spec_path: Path, raw: str) -> list[dict[str, str]]:
    declared = _parse_table(raw)
    known = {item["path"] for item in declared}
    for raw_value in _BACKTICK_REFERENCE.findall(raw):
        value = raw_value.split("#", 1)[0].strip()
        range_match = _INLINE_RANGE.fullmatch(value)
        requested_range = "all"
        if range_match:
            value = range_match.group("path")
            requested_range = f"{range_match.group('start')}-{range_match.group('end')}"
        if (
            value in known
            or any(ch in value for ch in "*?{}$ ")
            or value.startswith(("http://", "https://"))
            or not Path(value).suffix
        ):
            continue
        candidate = root / value
        if not candidate.is_file() and "/" not in value:
            matches = sorted(
                path for path in root.rglob(value)
                if path.is_file()
                and not any(
                    part in _IGNORED_TREE_PARTS
                    for part in path.parts
                )
            )
            if len(matches) > 1:
                # A bare basename in prose may describe an artifact kind (for
                # example ``SKILL.md``) rather than declare one exact input.
                # Only the Implementation Inputs table is authoritative when
                # multiple files share that name.
                continue
            if matches:
                candidate = matches[0]
                value = candidate.relative_to(root).as_posix()
        if candidate.is_file() and candidate.resolve() != spec_path.resolve():
            # A prose basename that resolves to a path the Implementation
            # Inputs table already declares (under any spelling) must not
            # be added a second time — the table is authoritative
            # (STORY-slim-20260826ac1f0bfe4148 R3).
            resolved_rel = (
                candidate.relative_to(root).as_posix()
                if _inside(root, candidate) else value
            )
            if resolved_rel in known or value in known:
                continue
            declared.append({
                "path": resolved_rel,
                "range": requested_range,
                "mode": "auto",
                "required": "SHOULD",
            })
            known.add(resolved_rel)
    return declared


def _python_interface(text: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            args = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args)]
            lines.append(f"{prefix} {node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}")
    return "\n".join(lines)


def _extract(path: Path, mode: str, requested_range: str, budget: int) -> str:
    data = path.read_bytes()
    if b"\0" in data[:4096]:
        return f"[binary: {len(data)} bytes]"
    text = data.decode("utf-8", errors="replace")
    if requested_range and requested_range.lower() not in {"all", "-"}:
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", requested_range)
        if not match:
            raise PreflightError(f"invalid line range {requested_range!r} for {path}")
        start, end = map(int, match.groups())
        lines = text.splitlines()
        if start < 1 or end < start or end > len(lines):
            raise PreflightError(f"line range {requested_range} is outside {path}")
        return "\n".join(f"{number}: {lines[number - 1]}" for number in range(start, end + 1))
    if mode == "css-tokens" or (mode == "auto" and path.suffix.lower() == ".css"):
        tokens = [f"{m.group('name')}: {m.group('value').strip()}" for m in _CSS_TOKEN.finditer(text)]
        return "\n".join(tokens)
    summarize_code = (
        mode == "auto"
        and path.suffix.lower() in _CODE_SUFFIXES
        and len(data) > MAX_INLINE_BYTES
    )
    if mode in {"public", "interface"} or summarize_code:
        if path.suffix.lower() == ".py":
            return _python_interface(text)
        exports = [line for line in text.splitlines() if re.match(r"\s*export\s+", line)]
        return "\n".join(exports)
    encoded = text.encode("utf-8")
    if len(encoded) > min(MAX_INLINE_BYTES, budget):
        raise PreflightError(f"input too large to inline without an explicit extraction mode: {path}")
    return text


def _receipt_dir(root: Path, story_id: str) -> Path:
    return root / ".pactkit" / "preflight" / story_id






def run_spec_preflight(
    project_root: Path | str, spec_path: Path | str
) -> PreflightResult:
    root = Path(project_root).resolve()
    spec = Path(spec_path)
    if not spec.is_absolute():
        spec = root / spec
    spec = spec.resolve()
    if not _inside(root, spec):
        raise PreflightError(f"Spec escapes project root: {spec}")
    if not spec.is_file():
        raise PreflightError(f"Spec does not exist: {spec}")
    raw_bytes = spec.read_bytes()
    raw = raw_bytes.decode("utf-8")
    story_id = spec.stem
    rows = _discover_references(root, spec, raw)
    inputs: list[dict] = []
    rendered_parts: list[str] = [f"# Spec preflight: {story_id}"]
    used = 0
    for row in rows:
        relative = row["path"].strip()
        unresolved = root / relative
        required = row.get("required", "MUST").upper()
        if not unresolved.exists():
            if required in {"MUST", "REQUIRED", "YES"}:
                raise PreflightError(f"required input does not exist: {relative}")
            rendered_parts.append(f"[WARN] optional input missing: {relative}")
            continue
        resolved = unresolved.resolve()
        if not _inside(root, resolved):
            raise PreflightError(f"input escapes project root: {relative}")
        if not resolved.is_file():
            raise PreflightError(f"input is not a file: {relative}")
        mode = row.get("mode", "auto").lower() or "auto"
        line_range = row.get("range", "all") or "all"
        try:
            content = _extract(resolved, mode, line_range, MAX_TOTAL_BYTES - used)
        except PreflightError as exc:
            if required in {"MUST", "REQUIRED", "YES"}:
                raise
            # An oversized reference discovered from prose (not declared in
            # the Implementation Inputs table) downgrades to a warning with
            # a declaration hint instead of aborting preflight
            # (STORY-slim-20260826ac1f0bfe4148 R3).
            rendered_parts.append(
                f"[WARN] skipped oversized prose reference: {relative} "
                f"— declare it in Implementation Inputs with an extraction mode ({exc})"
            )
            continue
        used += len(content.encode("utf-8"))
        if used > MAX_TOTAL_BYTES:
            raise PreflightError("preflight extraction exceeds total context budget")
        rendered_parts.append(f"## {relative} [{mode}; {line_range}]\n{content.rstrip()}")
        inputs.append({
            "path": resolved.relative_to(root).as_posix(),
            "sha256": _sha256(resolved.read_bytes()),
            "range": line_range,
            "mode": mode,
            "content_sha256": _sha256(content.encode("utf-8")),
            "required": required,
        })
    constraints = [match.group(0).strip() for match in _CONSTRAINT.finditer(raw)]
    if constraints:
        rendered_parts.append("## Constraints\n" + "\n".join(f"- {line}" for line in constraints))
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "project_root": str(root),
        "story_id": story_id,
        "spec_path": spec.relative_to(root).as_posix(),
        "spec_sha256": _sha256(raw_bytes),
        "inputs": inputs,
        "constraints": constraints,
    }
    receipt_path = _receipt_dir(root, story_id) / f"{receipt['spec_sha256']}.json"
    atomic_write(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    current_path = _receipt_dir(root, story_id) / "current.json"
    atomic_write(current_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return PreflightResult("\n\n".join(rendered_parts).rstrip() + "\n", receipt_path, receipt)







