"""Codebase quality patrol — entropy detection (STORY-slim-070).

Scans for dead code, stale documentation, and pattern duplication.
Follows the doctor.py pure-function pattern: each check accepts
``project_root`` and returns a structured dict.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_scope(project_root: Path, scope: Path | None) -> Path | None:
    """Validate and resolve scope path. Returns None if no scope."""
    if scope is None:
        return None
    resolved = (project_root / scope).resolve()
    if not str(resolved).startswith(str(project_root.resolve())):
        return None  # signal invalid
    return resolved


def _python_files(root: Path, scope: Path | None) -> list[Path]:
    """Collect .py files under scope (or entire project src/)."""
    if scope is not None:
        base = scope
    else:
        # Scan all directories that look like source
        bases = []
        for candidate in ("src", "lib", "app"):
            p = root / candidate
            if p.is_dir():
                bases.append(p)
        if not bases:
            bases = [root]
        files = []
        for base in bases:
            files.extend(
                f for f in base.rglob("*.py")
                if "__pycache__" not in str(f)
            )
        return files

    if not base.is_dir():
        return []
    return [
        f for f in base.rglob("*.py")
        if "__pycache__" not in str(f)
    ]


_IMPORT_RE = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)
_FROM_IMPORT_RE = re.compile(
    r"^from\s+[\w.]+\s+import\s+(.+)", re.MULTILINE,
)
_FUNC_DEF_RE = re.compile(r"^def\s+(\w+)\(([^)]*)\)", re.MULTILINE)
_EXCEPT_PASS_RE = re.compile(
    r"except[^:]*:\s*\n\s+pass\s*$", re.MULTILINE,
)
_CANONICAL_RE = re.compile(
    r"#\s*Canonical:\s*(\S+)\s+(\w+)",
)


# ---------------------------------------------------------------------------
# R1: Dead Code Detection
# ---------------------------------------------------------------------------

def check_dead_imports(project_root: Path, scope: Path | None) -> dict:
    """Detect unused imports and empty except:pass blocks.

    Returns ``{"findings": [...]}``.
    """
    resolved_scope = _resolve_scope(project_root, scope)
    if scope is not None and resolved_scope is None:
        return {"findings": []}

    files = _python_files(project_root, resolved_scope)
    findings: list[dict] = []

    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(fpath.relative_to(project_root))

        # Unused imports (simple heuristic: import X but X never used elsewhere)
        for m in _IMPORT_RE.finditer(text):
            module = m.group(1).split(".")[-1]  # e.g. os.path → path
            line_no = text[: m.start()].count("\n") + 1
            # Check if the module name appears elsewhere in the file
            rest = text[: m.start()] + text[m.end() :]
            if not re.search(rf"\b{re.escape(module)}\b", rest):
                findings.append({
                    "type": "DEAD-IMPORT",
                    "file": rel,
                    "line": line_no,
                    "message": f"unused import '{module}'",
                })

        # from X import a, b — check each name
        for m in _FROM_IMPORT_RE.finditer(text):
            names_str = m.group(1)
            line_no = text[: m.start()].count("\n") + 1
            names = [n.strip().split(" as ")[-1].strip()
                     for n in names_str.split(",")]
            rest = text[: m.start()] + text[m.end() :]
            for name in names:
                if name and name != "*" and not re.search(rf"\b{re.escape(name)}\b", rest):
                    findings.append({
                        "type": "DEAD-IMPORT",
                        "file": rel,
                        "line": line_no,
                        "message": f"unused import '{name}'",
                    })

        # Empty except: pass
        for m in _EXCEPT_PASS_RE.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            findings.append({
                "type": "EMPTY-EXCEPT",
                "file": rel,
                "line": line_no,
                "message": "empty except:pass block",
            })

    return {"findings": findings}


# ---------------------------------------------------------------------------
# R2: Stale Documentation Detection
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(r"\|\s*Status\s*\|\s*(\w+)\s*\|")
_FILE_REF_RE = re.compile(r"`(src/[^`]+\.py)`")
_CONTEXT_DATE_RE = re.compile(
    r"Last updated:\s*(\S+)",
)
_ITEM_ID_RE = re.compile(r"((?:STORY|BUG|HOTFIX)(?:-[\w]+)?-\d+)")


def check_stale_docs(project_root: Path, scope: Path | None) -> dict:
    """Detect stale documentation signals.

    Returns ``{"findings": [...]}``.
    """
    findings: list[dict] = []

    # STORY-slim-146: surface corrupt, stale, or blocked checkpoint state.
    try:
        from pactkit.continuation import ContinuationStore

        for warning in ContinuationStore(project_root).diagnostics(include_completed=True):
            findings.append({
                "type": "STALE-CONTINUATION",
                "file": ".pactkit/continuations",
                "line": None,
                "message": warning,
            })
    except Exception:
        pass

    # --- Done specs referencing deleted files ---
    specs_dir = project_root / "docs" / "specs"
    if specs_dir.is_dir():
        for spec in specs_dir.glob("*.md"):
            try:
                text = spec.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            status_m = _STATUS_RE.search(text)
            if not status_m or status_m.group(1) != "Done":
                continue

            # Check file references in Implementation Steps
            for ref_m in _FILE_REF_RE.finditer(text):
                ref_path = ref_m.group(1)
                if not (project_root / ref_path).exists():
                    findings.append({
                        "type": "STALE-DOC",
                        "file": str(spec.relative_to(project_root)),
                        "line": None,
                        "message": f"references non-existent file '{ref_path}'",
                    })

    # --- Orphaned test cases ---
    tc_dir = project_root / "docs" / "test_cases"
    if tc_dir.is_dir():
        spec_ids: set[str] = set()
        if specs_dir.is_dir():
            for s in specs_dir.glob("*.md"):
                m = _ITEM_ID_RE.match(s.stem)
                if m:
                    spec_ids.add(m.group(1))

        for tc in tc_dir.glob("*_case.md"):
            m = _ITEM_ID_RE.match(tc.stem)
            if m and m.group(1) not in spec_ids:
                findings.append({
                    "type": "STALE-DOC",
                    "file": str(tc.relative_to(project_root)),
                    "line": None,
                    "message": f"test case references non-existent spec '{m.group(1)}'",
                })

    # --- Stale context.md ---
    from pactkit.context_gen import context_output_path

    ctx_path = context_output_path(project_root)
    if not ctx_path.exists():
        # Read-only migration compatibility. New writes always target .pactkit.
        legacy_ctx = project_root / "docs" / "product" / "context.md"
        if legacy_ctx.exists():
            ctx_path = legacy_ctx
    if ctx_path.exists():
        try:
            ctx_text = ctx_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            ctx_text = ""

        date_m = _CONTEXT_DATE_RE.search(ctx_text)
        if date_m:
            try:
                date_str = date_m.group(1)
                # Handle ISO format with timezone
                updated = datetime.fromisoformat(date_str)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_ago = (now - updated).days
                if days_ago > 7:
                    findings.append({
                        "type": "STALE-CTX",
                        "file": str(ctx_path.relative_to(project_root)),
                        "line": None,
                        "message": f"last updated {days_ago} days ago (threshold: 7 days)",
                    })
            except (ValueError, TypeError):
                pass

    return {"findings": findings}


# ---------------------------------------------------------------------------
# R3: Pattern Duplication Detection
# ---------------------------------------------------------------------------

def check_pattern_duplication(project_root: Path, scope: Path | None) -> dict:
    """Detect duplicate function signatures and stale canonical copies.

    Returns ``{"findings": [...]}``.
    """
    resolved_scope = _resolve_scope(project_root, scope)
    if scope is not None and resolved_scope is None:
        return {"findings": []}

    files = _python_files(project_root, resolved_scope)
    findings: list[dict] = []

    # --- Duplicate function signatures (same name + param count) ---
    # key: (func_name, param_count) → [(file, line)]
    sig_map: dict[tuple[str, int], list[tuple[str, int]]] = {}

    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(fpath.relative_to(project_root))

        for m in _FUNC_DEF_RE.finditer(text):
            name = m.group(1)
            if name.startswith("_"):
                continue  # Skip private/dunder
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            # Exclude 'self' and 'cls'
            params = [p for p in params if p not in ("self", "cls")]
            param_count = len(params)
            line_no = text[: m.start()].count("\n") + 1
            key = (name, param_count)
            sig_map.setdefault(key, []).append((rel, line_no))

        # --- Stale canonical copies ---
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            cm = _CANONICAL_RE.search(line)
            if not cm:
                continue

            source_path = cm.group(1)
            var_name = cm.group(2)

            # Read canonical source
            canonical_file = project_root / source_path
            if not canonical_file.exists():
                findings.append({
                    "type": "STALE-CANONICAL",
                    "file": rel,
                    "line": i,
                    "message": f"canonical source '{source_path}' does not exist",
                })
                continue

            try:
                source_text = canonical_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find the value in the canonical source
            canon_m = re.search(
                rf'^{re.escape(var_name)}\s*=\s*(.+)$',
                source_text,
                re.MULTILINE,
            )
            if not canon_m:
                continue

            canonical_value = canon_m.group(1).strip()

            # Find the local copy value (next line after the comment)
            if i < len(lines):
                local_line = lines[i]  # 0-indexed: lines[i] is line i+1
                local_m = re.search(r'=\s*(.+)$', local_line)
                if local_m:
                    local_value = local_m.group(1).strip()
                    if local_value != canonical_value:
                        findings.append({
                            "type": "STALE-CANONICAL",
                            "file": rel,
                            "line": i + 1,
                            "message": (
                                f"inline copy of {var_name} differs from "
                                f"canonical source ({source_path})"
                            ),
                        })

    # Report duplicate signatures
    for (name, _pcount), locations in sig_map.items():
        if len(locations) >= 2:
            loc_strs = [f"{f}:{ln}" for f, ln in locations]
            findings.append({
                "type": "DUP-FUNC",
                "file": locations[0][0],
                "line": locations[0][1],
                "message": f"{name} — found in {' and '.join(loc_strs)}",
            })

    return {"findings": findings}


# ---------------------------------------------------------------------------
# R4: Orchestrator
# ---------------------------------------------------------------------------

def run_garden(
    project_root: Path,
    scope: Path | None = None,
    json_output: bool = False,
) -> tuple[str, int]:
    """Run all garden checks and format output.

    Returns (output_string, exit_code).
    """
    # SEC-1 + SEC-6: validate scope
    if scope is not None:
        resolved = (project_root / scope).resolve()
        if not str(resolved).startswith(str(project_root.resolve())):
            msg = f"Error: scope '{scope}' resolves outside project root"
            if json_output:
                return json.dumps({"error": msg, "findings": [], "total": 0}), 1
            return msg, 1

    all_findings: list[dict] = []

    r1 = check_dead_imports(project_root, scope)
    all_findings.extend(r1["findings"])

    r2 = check_stale_docs(project_root, scope)
    all_findings.extend(r2["findings"])

    r3 = check_pattern_duplication(project_root, scope)
    all_findings.extend(r3["findings"])

    total = len(all_findings)

    if json_output:
        return json.dumps({"findings": all_findings, "total": total}, indent=2), (1 if total else 0)

    if total == 0:
        return "Garden: all clear — no findings", 0

    lines = []
    for f in all_findings:
        loc = f["file"]
        if f.get("line"):
            loc += f":{f['line']}"
        lines.append(f"  [{f['type']}] {loc} — {f['message']}")
    lines.append(f"\nGarden: {total} finding(s)")
    return "\n".join(lines), 1
