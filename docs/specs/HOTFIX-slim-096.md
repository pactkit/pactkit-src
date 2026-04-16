# HOTFIX-slim-096: Report --all should only include core PDCA graphs

| Field | Value |
|-------|-------|
| ID | HOTFIX-slim-096 |
| Status | In Progress |
| Priority | P2 |

## Background

`report.py generate(all_mode=True)` uses `graphs_dir.glob('*.mmd')` to include every .mmd file as a Tab in the unified dashboard. This produces 9 Tabs including focus_*, reverse_*, and workflow_* graphs that are manual ad-hoc artifacts — not part of the PDCA cycle. The result is information overload.

## Fix

### Fix 1: Filter --all to core PDCA graphs only
- Target: `src/pactkit/skills/report.py:911`
- Filter `--all` mode to only include core PDCA graphs: `code_graph`, `class_graph`, `call_graph`, `system_design`
- Define the core set as `_CORE_GRAPHS` constant for maintainability

### Fix 2: Strip Mermaid `<br/>` tags from node labels
- Target: `src/pactkit/skills/report.py:491,585` (both `_sanitize_for_json` and `_render_unified_html`)
- `system_design.mmd` uses `<br/>` for multi-line labels (Mermaid syntax)
- `_html_mod.escape()` converts `<br/>` to `&lt;br/&gt;`, displayed as raw text in SVG
- Fix: `re.sub(r'<br\s*/?>', ' ', label)` before escape — SVG text doesn't support HTML
