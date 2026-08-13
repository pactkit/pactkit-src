"""STORY-slim-136: mechanical archive-honesty verification for /project-done.

Converts the archive-time honesty checks from prompt-level instructions into
code-enforced verdicts. Each check emits a [PASS|FAIL|WARN] line with
evidence (file:line); any FAIL makes verify_story() return exit code 1.

Checks:
  R2  requirement evidence chain (Spec MUST R-items -> case file -> test files)
  R3  archive-checkbox honesty (all [x] but spec/case still has open markers)
  R4  wiring verification (new public symbols with zero production callers)
  R5  status-machine consistency (Spec Status vs Board vs archive)
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# R3: unresolved-declaration vocabulary (case-insensitive substring scan).
# Module-level constant per No Magic Values; may migrate to pactkit.yaml later.
BLOCKER_TERMS = (
    "rfc open",
    "todo",
    "fixme",
    "open question",
    "未解决",
    "待确认",
    "尚未实现",
    "待补充",
)

_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _strip_code_spans(text: str) -> str:
    """Remove fenced blocks and inline code before marker scanning.

    A spec that *discusses* blocker vocabulary (e.g. the done-verify spec
    itself lists `TODO` as a term) is not an unresolved declaration —
    only prose occurrences count.
    """
    return _INLINE_CODE_RE.sub("", _CODE_FENCE_RE.sub("", text))

# SEC-1: story IDs must match this shape — anything else (incl. path
# traversal attempts like "../x") is rejected before touching the filesystem.
STORY_ID_RE = re.compile(r"^(?:STORY|HOTFIX|BUG)(?:-[a-z]+)?-\d+$")

_REQ_RE = re.compile(r"^###\s+(R\d+):.*?\((MUST NOT|MUST|SHOULD|MAY)\)", re.MULTILINE)
_AC_RE = re.compile(r"^###\s+(AC\d+):.*?\((R\d+(?:\s*[-,]\s*R?\d+)*)\)", re.MULTILINE)
_STATUS_RE = re.compile(r"\|\s*Status\s*\|\s*([^|]+?)\s*\|")
_BACKTICK_PATH_RE = re.compile(r"`((?:src|tests)/[^`\s]+\.py)`")
_PUBLIC_DEF_RE = re.compile(r"^(?:def|class)\s+([A-Za-z]\w*)", re.MULTILINE)
_ADDED_DEF_RE = re.compile(r"^\+(?:def|class)\s+([A-Za-z]\w*)", re.MULTILINE)


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | WARN
    evidence: str

    def render(self) -> str:
        return f"[{self.status}] {self.name} — {self.evidence}"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _parse_requirements(spec_text: str) -> list[tuple[str, str]]:
    """Extract (R-id, level) pairs from a spec. Levels: MUST/MUST NOT/SHOULD/MAY."""
    return _REQ_RE.findall(spec_text)


def _parse_ac_to_reqs(spec_text: str) -> dict[str, list[str]]:
    """Map each AC id to the R-ids it covers, expanding ranges like R1-R4."""
    mapping: dict[str, list[str]] = {}
    for ac_id, req_expr in _AC_RE.findall(spec_text):
        reqs: list[str] = []
        range_match = re.fullmatch(r"R(\d+)\s*-\s*R?(\d+)", req_expr)
        if range_match:
            lo, hi = int(range_match.group(1)), int(range_match.group(2))
            reqs = [f"R{i}" for i in range(lo, hi + 1)]
        else:
            reqs = [f"R{n}" for n in re.findall(r"\d+", req_expr)]
        mapping[ac_id] = reqs
    return mapping


def _board_block(board_text: str, story_id: str) -> str | None:
    """Extract the story's block from the sprint board (reuse board.py parser)."""
    from pactkit.skills.board import _parse_story_blocks

    for sid, block_text, _start, _end in _parse_story_blocks(board_text):
        if sid == story_id:
            return block_text
    return None


def _spec_status(spec_text: str) -> str | None:
    m = _STATUS_RE.search(spec_text)
    return m.group(1).strip() if m else None


def _archived(project_root: Path, story_id: str) -> str | None:
    """Return the archive file name containing the story, or None."""
    archive_dir = project_root / "docs" / "product" / "archive"
    if not archive_dir.is_dir():
        return None
    for f in sorted(archive_dir.glob("*.md")):
        if story_id in _read(f):
            return f.name
    return None


# ---------------------------------------------------------------------------
# R2: requirement evidence chain
# ---------------------------------------------------------------------------


def check_requirement_evidence(story_id: str, project_root: Path) -> list[CheckResult]:
    spec_path = project_root / "docs" / "specs" / f"{story_id}.md"
    if not spec_path.exists():
        return [CheckResult("R2 evidence", "FAIL", f"spec missing: docs/specs/{story_id}.md")]

    spec_text = _read(spec_path)
    musts = [rid for rid, level in _parse_requirements(spec_text) if level in ("MUST", "MUST NOT")]
    if not musts:
        return [CheckResult("R2 evidence", "PASS", "no MUST requirements to evidence")]

    case_path = project_root / "docs" / "test_cases" / f"{story_id}_case.md"
    if not case_path.exists():
        return [
            CheckResult(
                "R2 evidence", "FAIL",
                f"test case missing: docs/test_cases/{story_id}_case.md (required by {', '.join(musts)})",
            )
        ]

    case_text = _read(case_path)
    ac_map = _parse_ac_to_reqs(spec_text)
    results: list[CheckResult] = []
    for rid in musts:
        covered_acs = [ac for ac, reqs in ac_map.items() if rid in reqs]
        hit = rid in case_text or any(ac in case_text for ac in covered_acs)
        if hit:
            via = rid if rid in case_text else "/".join(covered_acs)
            results.append(CheckResult(f"R2 evidence {rid}", "PASS", f"case references {via}"))
        else:
            results.append(
                CheckResult(f"R2 evidence {rid}", "FAIL", f"case file has no scenario referencing {rid}")
            )

    # (c) mapped test files must exist on disk
    src_files = [p for p in _BACKTICK_PATH_RE.findall(spec_text) if p.startswith("src/")]
    listed_tests = [p for p in _BACKTICK_PATH_RE.findall(spec_text) if p.startswith("tests/")]
    if src_files:
        try:
            from pactkit.test_mapper import map_to_tests

            mapped = map_to_tests(src_files, project_root).get("mapped", [])
        except Exception as exc:  # SEC-7: degrade single check, never crash
            results.append(CheckResult("R2 test files", "WARN", f"test-map failed: {exc}"))
            mapped = []
        candidates = list(dict.fromkeys([*mapped, *listed_tests]))
    else:
        candidates = listed_tests

    if candidates:
        missing = [t for t in candidates if not (project_root / t).exists()]
        if missing:
            results.append(CheckResult("R2 test files", "FAIL", f"mapped test file(s) missing: {', '.join(missing)}"))
        else:
            results.append(CheckResult("R2 test files", "PASS", f"{len(candidates)} mapped test file(s) exist"))
    else:
        results.append(CheckResult("R2 test files", "WARN", "no test files derivable from spec"))

    return results


# ---------------------------------------------------------------------------
# R3: archive-checkbox honesty
# ---------------------------------------------------------------------------


def check_archive_honesty(story_id: str, project_root: Path, board_block: str | None) -> list[CheckResult]:
    if board_block is None:
        return [CheckResult("R3 honesty", "FAIL", f"no board entry for {story_id}")]
    if "- [ ]" in board_block:
        return [CheckResult("R3 honesty", "WARN", "board has unchecked tasks — checkbox scan skipped")]

    hits: list[str] = []
    for rel in (f"docs/specs/{story_id}.md", f"docs/test_cases/{story_id}_case.md"):
        path = project_root / rel
        if not path.exists():
            continue
        for lineno, line in enumerate(_strip_code_spans(_read(path)).splitlines(), start=1):
            low = line.lower()
            for term in BLOCKER_TERMS:
                if term in low:
                    hits.append(f"{rel}:{lineno} contains {term.strip()!r}")
                    break
    if hits:
        return [CheckResult("R3 honesty", "FAIL", "; ".join(hits[:5]))]
    return [CheckResult("R3 honesty", "PASS", "board all [x] and no open markers in spec/case")]


# ---------------------------------------------------------------------------
# R4: wiring verification (zero production callers)
# ---------------------------------------------------------------------------


def _git(project_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(project_root), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout if proc.returncode == 0 else ""


def _changed_source_files(project_root: Path) -> list[str]:
    """New (untracked) + modified Python source files vs HEAD."""
    untracked = _git(project_root, "ls-files", "--others", "--exclude-standard")
    modified = _git(project_root, "diff", "HEAD", "--name-only")
    files = set()
    for line in (untracked + "\n" + modified).splitlines():
        line = line.strip()
        if line.startswith("src/") and line.endswith(".py"):
            files.add(line)
    return sorted(files)


def _new_public_symbols(project_root: Path, rel_path: str) -> list[str]:
    """Public def/class names introduced by this file.

    Untracked (new) file -> all public defs. Tracked file -> defs on added
    lines of the HEAD diff only.
    """
    is_tracked = bool(_git(project_root, "ls-files", "--", rel_path).strip())
    if is_tracked:
        diff = _git(project_root, "diff", "HEAD", "-U0", "--", rel_path)
        return _ADDED_DEF_RE.findall(diff)
    return _PUBLIC_DEF_RE.findall(_read(project_root / rel_path))


def _has_production_caller(project_root: Path, rel_path: str, symbol: str) -> bool:
    """Grep fallback: symbol referenced anywhere in src/ production code.

    Same-file references count (R4 targets pure-decoration components with
    zero callers *anywhere*; a helper used by other functions in its own
    module is wired by definition). Appearance in __all__ or cli.py
    registration also counts as wired.
    """
    src_dir = project_root / "src"
    if not src_dir.is_dir():
        return True  # nothing to grep against — do not cry wolf
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    for candidate in src_dir.rglob("*.py"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        if candidate.as_posix().endswith(rel_path):
            # Same file: the def/class line itself plus any usage reference.
            occurrences = len(pattern.findall(text))
            if occurrences >= 2:
                return True
            continue
        if pattern.search(text):
            return True
    return False


def check_wiring(project_root: Path) -> list[CheckResult]:
    try:
        files = _changed_source_files(project_root)
    except Exception as exc:  # SEC-7
        return [CheckResult("R4 wiring", "WARN", f"git inspection failed: {exc}")]
    if not files:
        return [CheckResult("R4 wiring", "PASS", "no source changes to verify")]

    orphans: list[str] = []
    for rel in files:
        for symbol in _new_public_symbols(project_root, rel):
            if not _has_production_caller(project_root, rel, symbol):
                orphans.append(f"{symbol} ({rel})")
    if orphans:
        listing = ", ".join(sorted(orphans)[:10])
        return [CheckResult("R4 wiring", "WARN", f"zero production callers: {listing}")]
    return [CheckResult("R4 wiring", "PASS", f"all new public symbols in {len(files)} file(s) have callers")]


# ---------------------------------------------------------------------------
# R5: status-machine consistency (runs AFTER spec-status flip — see Spec R6)
# ---------------------------------------------------------------------------


def check_status_consistency(story_id: str, project_root: Path, board_block: str | None) -> list[CheckResult]:
    spec_text = _read(project_root / "docs" / "specs" / f"{story_id}.md")
    status = _spec_status(spec_text)
    archived_in = _archived(project_root, story_id)

    if board_block is None:
        return [CheckResult("R5 status", "FAIL", f"no board entry for {story_id}")]

    board_done = "- [ ]" not in board_block and "- [x]" in board_block

    if board_done and status != "Done":
        return [
            CheckResult(
                "R5 status", "FAIL",
                f"board all [x] but spec Status is {status!r} (spec-status flip skipped?)",
            )
        ]
    if not board_done and status == "Done":
        return [CheckResult("R5 status", "FAIL", "spec Status is Done but board has unchecked tasks")]
    if archived_in and (not board_done or status != "Done"):
        return [
            CheckResult(
                "R5 status", "FAIL",
                f"story present in {archived_in} but board/spec incomplete",
            )
        ]
    evidence = f"spec Status={status!r}, board {'complete' if board_done else 'incomplete'}"
    if archived_in:
        evidence += f", archived in {archived_in}"
    return [CheckResult("R5 status", "PASS", evidence)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def verify_story(story_id: str, project_root: Path) -> tuple[list[CheckResult], int]:
    """Run all archive-honesty checks. Returns (results, exit_code)."""
    if not STORY_ID_RE.match(story_id):
        return [CheckResult("input", "FAIL", f"invalid story ID: {story_id!r}")], 1

    project_root = Path(project_root)
    board_text = _read(project_root / "docs" / "product" / "sprint_board.md")
    board_block = _board_block(board_text, story_id)

    results: list[CheckResult] = []
    for check in (
        lambda: check_requirement_evidence(story_id, project_root),
        lambda: check_archive_honesty(story_id, project_root, board_block),
        lambda: check_wiring(project_root),
        lambda: check_status_consistency(story_id, project_root, board_block),
    ):
        try:
            results.extend(check())
        except Exception as exc:  # SEC-7: a broken check degrades to WARN
            results.append(CheckResult("internal", "WARN", f"check raised {type(exc).__name__}: {exc}"))

    exit_code = 1 if any(r.status == "FAIL" for r in results) else 0
    return results, exit_code
