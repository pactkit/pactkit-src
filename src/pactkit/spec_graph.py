"""Story dependency graph — DAG, topological waves, and file-conflict matrix.

Parses the `## Dependency Surface` section of every Spec (STORY-slim-143) and
computes, deterministically and entirely in code (LLM != Calculator):

- execution waves: wave N depends only on waves < N; same-wave stories are
  parallelizable;
- a conflict matrix: story pairs whose `Touches` globs overlap, flagged
  unsafe-parallel when they share a wave;
- a Mermaid graph for docs/architecture/graphs/story_graph.mmd.

Usage:
    pactkit spec-graph [--specs-dir docs/specs] [--write-graph] [--graph-path PATH]
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pactkit.schemas import DEP_SURFACE_FIELDS, DEP_SURFACE_SECTION, ITEM_ID_PATTERN
from pactkit.skills.spec_linter import section_text, strip_code_blocks

_ITEM_ID_RE = re.compile(ITEM_ID_PATTERN)
_ITEM_FILE_RE = re.compile(rf"^{ITEM_ID_PATTERN}\.md$")
_TABLE_ROW_RE = re.compile(r"^\|\s*(\w[\w\s]*\w|\w)\s*\|\s*(.+?)\s*\|", re.MULTILINE)
_META_HEADER_RE = re.compile(r"^\|\s*Field\s*\|\s*Value\s*\|", re.MULTILINE | re.IGNORECASE)

DEFAULT_GRAPH_PATH = "docs/architecture/graphs/story_graph.mmd"


class DependencyCycleError(Exception):
    """Raised when Depends-on edges form a cycle — the Specs are contradictory."""


@dataclass
class StoryNode:
    story_id: str
    status: str = "Draft"
    depends_on: list[str] = field(default_factory=list)
    provides: str = ""
    touches: list[str] = field(default_factory=list)
    conflict_risk: str = ""


@dataclass
class Conflict:
    story_a: str
    story_b: str
    shared: str
    same_wave: bool


@dataclass
class StoryGraph:
    nodes: dict[str, StoryNode] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_field_table(text: str) -> dict[str, str]:
    """Parse `| Field | Value |` style rows from a text block."""
    fields: dict[str, str] = {}
    for m in _TABLE_ROW_RE.finditer(text):
        key = m.group(1).strip()
        if key.lower() == "field" or re.match(r"^-+$", key):
            continue
        fields[key] = m.group(2).strip()
    return fields


def _parse_touches(raw: str) -> list[str]:
    """Split a Touches cell into normalized path entries (order-stable, deduped)."""
    out: list[str] = []
    for part in raw.split(","):
        p = part.strip().strip("`").strip()
        if p and p.lower() != "none" and p not in out:
            out.append(p)
    return out


def parse_story(spec_path: Path) -> StoryNode | None:
    """Parse one Spec file into a StoryNode. Returns None for non-spec files."""
    if not _ITEM_FILE_RE.match(spec_path.name):
        return None
    story_id = spec_path.stem
    raw = spec_path.read_text(encoding="utf-8")
    text = strip_code_blocks(raw)

    # Status comes from the top metadata table (before the first ## heading)
    head = text.split("\n## ", 1)[0]
    status = _parse_field_table(head).get("Status", "Draft") if _META_HEADER_RE.search(head) else "Draft"

    node = StoryNode(story_id=story_id, status=status)
    body = section_text(text, DEP_SURFACE_SECTION)
    if body is None:
        return node
    fields = _parse_field_table(body)
    if not all(f in fields for f in DEP_SURFACE_FIELDS):
        return node  # malformed table — treat as undeclared (SEC-2: tolerate bad input)
    depends_raw = fields["Depends on"]
    if depends_raw.lower() != "none":
        node.depends_on = sorted(set(_ITEM_ID_RE.findall(depends_raw)))
    node.provides = fields["Provides"]
    node.touches = _parse_touches(fields["Touches"])
    node.conflict_risk = fields["Conflict risk"]
    return node


def load_story_graph(specs_dir: str | Path) -> StoryGraph:
    """Load all Specs in a directory into a StoryGraph (sorted by story ID)."""
    graph = StoryGraph()
    specs_path = Path(specs_dir)
    if not specs_path.is_dir():
        return graph
    for spec_file in sorted(specs_path.glob("*.md")):
        node = parse_story(spec_file)
        if node is not None:
            graph.nodes[node.story_id] = node
    return graph


# ---------------------------------------------------------------------------
# Waves (topological layers)
# ---------------------------------------------------------------------------


def compute_waves(graph: StoryGraph) -> list[list[str]]:
    """Group active (non-Done) stories into execution waves.

    Wave N contains every story whose remaining dependencies all land in
    waves < N. Edges to Done stories are satisfied and dropped; Done stories
    themselves are excluded. Raises DependencyCycleError on cycles.
    """
    active = {sid: n for sid, n in graph.nodes.items() if n.status != "Done"}
    remaining: dict[str, set[str]] = {
        sid: {d for d in n.depends_on if d in active} for sid, n in active.items()
    }
    waves: list[list[str]] = []
    placed: set[str] = set()
    while remaining:
        ready = sorted(sid for sid, deps in remaining.items() if deps <= placed)
        if not ready:
            cycle = sorted(remaining)
            raise DependencyCycleError(
                "Dependency cycle detected among: " + " -> ".join(cycle + [cycle[0]])
            )
        waves.append(ready)
        placed.update(ready)
        for sid in ready:
            del remaining[sid]
    return waves


# ---------------------------------------------------------------------------
# Conflict matrix
# ---------------------------------------------------------------------------


def _paths_overlap(a: str, b: str) -> bool:
    """Heuristic glob overlap: equal, or either fnmatches the other.

    Glob-vs-glob partial intersection (e.g. `src/*.py` vs `src/x/*.py`) is
    intentionally not solved — exactness is not worth the complexity; the
    matrix is an advisory signal, and same literal/glob coverage catches the
    common cases.
    """
    return a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a)


def compute_conflicts(graph: StoryGraph, waves: list[list[str]]) -> list[Conflict]:
    """All story pairs (active nodes only) with overlapping Touches, sorted."""
    wave_of = {sid: i for i, wave in enumerate(waves) for sid in wave}
    active = [sid for sid in sorted(graph.nodes) if sid in wave_of]
    conflicts: list[Conflict] = []
    for i, a in enumerate(active):
        for b in active[i + 1 :]:
            shared = sorted(
                pa for pa in graph.nodes[a].touches
                for pb in graph.nodes[b].touches
                if _paths_overlap(pa, pb)
            )
            if shared:
                conflicts.append(
                    Conflict(a, b, ", ".join(shared), same_wave=wave_of[a] == wave_of[b])
                )
    return conflicts


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_mermaid(graph: StoryGraph, waves: list[list[str]]) -> str:
    lines = ["graph LR"]
    wave_of = {sid: i for i, wave in enumerate(waves) for sid in wave}
    for sid in sorted(graph.nodes):
        if sid not in wave_of:
            continue
        for dep in graph.nodes[sid].depends_on:
            if dep in wave_of:
                lines.append(f"    {dep} --> {sid}")
    for i, wave in enumerate(waves, start=1):
        lines.append(f"    subgraph wave{i}[Wave {i}]")
        for sid in wave:
            lines.append(f"        {sid}")
        lines.append("    end")
    return "\n".join(lines) + "\n"


def render(graph: StoryGraph) -> str:
    """Full stdout rendering: waves + conflict matrix. Deterministic."""
    waves = compute_waves(graph)
    lines = ["## Execution Waves", ""]
    if not waves:
        lines.append("(no active stories)")
    for i, wave in enumerate(waves, start=1):
        lines.append(f"Wave {i}: {', '.join(wave)}")
    conflicts = compute_conflicts(graph, waves)
    lines += ["", "## Conflict Matrix", ""]
    if not conflicts:
        lines.append("(no file overlaps)")
    for c in conflicts:
        tag = "SAME WAVE — UNSAFE parallel" if c.same_wave else "different waves — safe"
        lines.append(f"{c.story_a} <-> {c.story_b}: {c.shared} [{tag}]")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Story dependency graph: execution waves + file-conflict matrix"
    )
    parser.add_argument("--specs-dir", default="docs/specs", help="Directory containing spec files")
    parser.add_argument("--write-graph", action="store_true", help="Write Mermaid graph to --graph-path")
    parser.add_argument("--graph-path", default=DEFAULT_GRAPH_PATH, help="Mermaid output path")
    args = parser.parse_args(argv)

    graph = load_story_graph(args.specs_dir)
    try:
        sys.stdout.write(render(graph))
        waves = compute_waves(graph)
    except DependencyCycleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.write_graph:
        out = Path(args.graph_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_mermaid(graph, waves), encoding="utf-8")
        print(f"\nGraph written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
