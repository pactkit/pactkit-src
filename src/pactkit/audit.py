"""PactKit Harness Audit — H1-H7 AI Readiness Assessment (STORY-slim-091).

Scans project structure and code against the 7-layer AI Coding Harness model.
Each layer scores L0-L3 (None → Basic → Structured → Advanced).
Harness Score = sum(all 7 levels) / 21 × 100.
AI Ready = min(all 7 levels) ≥ L1.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_LEVEL_NAMES = {0: 'None', 1: 'Basic', 2: 'Structured', 3: 'Advanced'}


# --- H1: Prompt Engineering (Auto-scan) ---

_CONFIG_DIRS = ['.claude', '.opencode', '.codex']


def _has_dir_with_files(root, subdir):
    """Check if any config dir has a non-empty subdirectory."""
    return any(
        (root / d / subdir).is_dir() and any((root / d / subdir).iterdir())
        for d in _CONFIG_DIRS if (root / d / subdir).is_dir()
    )


def _check_h1(root):
    """Check H1: System prompts, rules, agent roles."""
    root = Path(root)
    checks = {}
    checks['claude_md'] = any(
        (root / d / 'CLAUDE.md').exists() for d in [*_CONFIG_DIRS, '.']
    )
    checks['rules'] = _has_dir_with_files(root, 'rules')
    checks['agents'] = _has_dir_with_files(root, 'agents')
    checks['commands'] = any(
        (root / d / 'commands').is_dir()
        and len(list((root / d / 'commands').glob('*.md'))) >= 3
        for d in _CONFIG_DIRS if (root / d / 'commands').is_dir()
    )
    # TODO: signal strength check for L3

    level = 0
    if checks['claude_md']:
        level = 1
    if level >= 1 and checks['rules'] and checks['agents']:
        level = 2
    if level >= 2 and checks['commands']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H2: Context Engineering (Auto-scan) ---

def _check_h2(root):
    """Check H2: Project context, memory, hierarchy of truth."""
    root = Path(root)
    checks = {}
    checks['context_md'] = (root / 'docs' / 'product' / 'context.md').exists()
    checks['specs_exist'] = (root / 'docs' / 'specs').is_dir() and any((root / 'docs' / 'specs').glob('*.md'))
    checks['hierarchy_of_truth'] = any(
        any(f.read_text(encoding='utf-8', errors='ignore').lower().count('hierarchy') > 0
            for f in (root / d / 'rules').glob('*.md'))
        for d in ['.claude', '.opencode', '.codex']
        if (root / d / 'rules').is_dir()
    )
    checks['memory_config'] = (
        (root / '.claude' / 'projects').is_dir()
        or any((root / d / 'MEMORY.md').exists() for d in ['.claude', '.opencode', '.codex'])
    )
    # Context freshness: updated within 7 days
    ctx = root / 'docs' / 'product' / 'context.md'
    checks['context_fresh'] = False
    if ctx.exists():
        import time
        age_days = (time.time() - ctx.stat().st_mtime) / 86400
        checks['context_fresh'] = age_days <= 7

    level = 0
    if checks['context_md']:
        level = 1
    if level >= 1 and checks['specs_exist'] and checks['hierarchy_of_truth']:
        level = 2
    if level >= 2 and checks['context_fresh'] and checks['memory_config']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H3: Process Governance (Auto-scan) ---

def _check_h3(root):
    """Check H3: PDCA workflow, TDD, quality gates."""
    root = Path(root)
    checks = {}
    checks['sprint_board'] = (root / 'docs' / 'product' / 'sprint_board.md').exists()
    checks['tests_exist'] = (root / 'tests').is_dir() and any((root / 'tests').rglob('test_*.py'))
    checks['ci_config'] = (
        (root / '.github' / 'workflows').is_dir()
        or (root / '.gitlab-ci.yml').exists()
        or (root / 'Jenkinsfile').exists()
    )
    # L3: spec-lint, quality gate config
    checks['spec_lint'] = False
    try:
        from pactkit.skills.spec_linter import lint_spec  # noqa: F401
        checks['spec_lint'] = True
    except ImportError:
        pass
    checks['quality_gate'] = False
    for d in ['.claude', '.opencode', '.codex']:
        cfg = root / d / 'pactkit.yaml'
        if cfg.exists():
            try:
                content = cfg.read_text(encoding='utf-8')
                if 'lint_blocking' in content:
                    checks['quality_gate'] = True
            except Exception:
                pass

    level = 0
    if checks['sprint_board']:
        level = 1
    if level >= 1 and checks['tests_exist'] and checks['ci_config']:
        level = 2
    if level >= 2 and checks['spec_lint'] and checks['quality_gate']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H4: Tool Governance (Partial auto-scan) ---

def _check_h4(root, manual=None):
    """Check H4: MCP config, permissions, tool whitelist."""
    root = Path(root)
    checks = {}
    checks['pactkit_yaml'] = any((root / d / 'pactkit.yaml').exists() for d in ['.claude', '.opencode', '.codex'])
    # settings.json (Claude Code) or equivalent
    checks['settings_json'] = (
        (root / '.claude' / 'settings.json').exists()
        or (root / '.claude' / 'settings.local.json').exists()
    )
    # MCP config
    checks['mcp_config'] = False
    for d in ['.claude', '.opencode', '.codex']:
        settings = root / d / 'settings.json'
        if settings.exists():
            try:
                content = settings.read_text(encoding='utf-8')
                if 'mcpServers' in content or 'mcp' in content:
                    checks['mcp_config'] = True
            except Exception:
                pass
    # Manual overrides
    if manual:
        checks.update(manual)

    level = 0
    if checks['pactkit_yaml']:
        level = 1
    if level >= 1 and checks['settings_json']:
        level = 2
    if level >= 2 and checks['mcp_config']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H5: Safety & Guardrails (Auto-scan) ---

def _check_h5(root):
    """Check H5: .gitignore, safety rules, hooks."""
    root = Path(root)
    checks = {}
    checks['gitignore'] = (root / '.gitignore').exists()
    # Safety rules: scan rules for keywords
    checks['safety_rules'] = False
    _safety_keywords = {'secret', 'password', 'token', 'data loss', 'never print', 'credential'}
    for d in ['.claude', '.opencode', '.codex']:
        rules_dir = root / d / 'rules'
        if rules_dir.is_dir():
            for f in rules_dir.glob('*.md'):
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore').lower()
                    if any(kw in content for kw in _safety_keywords):
                        checks['safety_rules'] = True
                        break
                except Exception:
                    pass
    # Hooks
    checks['hooks_config'] = False
    for d in ['.claude', '.opencode', '.codex']:
        for name in ['settings.json', 'settings.local.json']:
            sf = root / d / name
            if sf.exists():
                try:
                    content = sf.read_text(encoding='utf-8')
                    if 'hook' in content.lower():
                        checks['hooks_config'] = True
                except Exception:
                    pass

    level = 0
    if checks['gitignore']:
        level = 1
    if level >= 1 and checks['safety_rules']:
        level = 2
    if level >= 2 and checks['hooks_config']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H6: Observability (Partial auto-scan) ---

def _check_h6(root, manual=None):
    """Check H6: Logging, cost tracking, lessons, self-audit."""
    root = Path(root)
    checks = {}
    checks['lessons_md'] = (root / 'docs' / 'architecture' / 'governance' / 'lessons.md').exists()
    # Self-audit rule
    checks['self_audit_rule'] = False
    for d in ['.claude', '.opencode', '.codex']:
        rules_dir = root / d / 'rules'
        if rules_dir.is_dir():
            for f in rules_dir.glob('*.md'):
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore').lower()
                    if 'self-audit' in content or 'operational discipline' in content:
                        checks['self_audit_rule'] = True
                        break
                except Exception:
                    pass
    # Retro history
    checks['retro_exists'] = False
    for pattern in ['retro*.md', 'retro-*.md']:
        for d in ['.claude/projects', 'docs']:
            search_dir = root / d
            if search_dir.is_dir():
                if any(search_dir.rglob(pattern)):
                    checks['retro_exists'] = True
                    break
    if manual:
        checks.update(manual)

    level = 0
    if checks['lessons_md']:
        level = 1
    if level >= 1 and checks['self_audit_rule']:
        level = 2
    if level >= 2 and checks['retro_exists']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- H7: Evolution (Auto-scan) ---

def _check_h7(root):
    """Check H7: Version management, changelog, automation."""
    root = Path(root)
    checks = {}
    # Version in pyproject.toml or package.json
    checks['version_managed'] = False
    for name in ['pyproject.toml', 'package.json']:
        vf = root / name
        if vf.exists():
            try:
                content = vf.read_text(encoding='utf-8')
                if 'version' in content:
                    checks['version_managed'] = True
            except Exception:
                pass
    checks['changelog'] = (root / 'CHANGELOG.md').exists()
    # Git tags
    checks['git_tags'] = False
    try:
        result = subprocess.run(['git', 'tag', '--list'], capture_output=True, text=True, cwd=str(root), timeout=5)
        checks['git_tags'] = bool(result.stdout.strip())
    except Exception:
        pass
    # CI/CD publish workflow
    checks['ci_publish'] = False
    wf_dir = root / '.github' / 'workflows'
    if wf_dir.is_dir():
        for f in wf_dir.glob('*.yml'):
            try:
                content = f.read_text(encoding='utf-8', errors='ignore').lower()
                if 'publish' in content or 'release' in content or 'deploy' in content:
                    checks['ci_publish'] = True
                    break
            except Exception:
                pass

    level = 0
    if checks['version_managed']:
        level = 1
    if level >= 1 and checks['changelog'] and checks['git_tags']:
        level = 2
    if level >= 2 and checks['ci_publish']:
        level = 3
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks}


# --- Scoring (R8) ---

def _compute_score(layers):
    """Compute Harness Score and AI Ready status."""
    total = sum(v['level'] for v in layers.values())
    max_total = len(layers) * 3  # 7 layers × 3 max = 21
    score = round(total / max_total * 100) if max_total > 0 else 0
    ready = all(v['level'] >= 1 for v in layers.values())
    min_layer = min(layers.items(), key=lambda x: x[1]['level'])
    return {
        'score': score,
        'ready': ready,
        'weakest': min_layer[0] if not ready else None,
    }


# --- Findings (R9) ---

def _collect_findings(root):
    """Aggregate findings from layers, garden, complexity, sec_scope."""
    root = Path(root)
    findings = []

    # Architecture: layer violations
    try:
        from pactkit.skills.visualize import layers as _layers_fn
        result = json.loads(_layers_fn(str(root)))
        for v in result.get('violations', []):
            findings.append({
                'severity': 'high',
                'category': 'architecture',
                'message': (
                    f"Layer violation: {v['importer']} ({v['importer_layer']})"
                    f" imports {v['importee']} ({v['importee_layer']})"
                ),
                'file': v['importer'],
            })
    except Exception:
        pass

    # Code: high complexity functions
    try:
        from pactkit.skills.visualize import complexity as _complexity_fn
        result = json.loads(_complexity_fn(str(root), threshold=20, fmt='json', show_all=True))
        for entry in result:
            sev = 'critical' if entry['complexity'] > 30 else 'high'
            findings.append({
                'severity': sev,
                'category': 'code',
                'message': f"High complexity: {entry['function']} = {entry['complexity']} ({entry['classification']})",
                'file': entry['file'],
            })
    except Exception:
        pass

    # Code: dead code via garden
    try:
        from pactkit.garden import check_dead_imports
        result = check_dead_imports(root, scope=None)
        for item in result.get('findings', []):
            findings.append({
                'severity': 'low',
                'category': 'code',
                'message': item.get('message', 'Dead import detected'),
                'file': item.get('file', ''),
            })
    except Exception:
        pass

    # Sort by severity
    _sev_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    findings.sort(key=lambda f: _sev_order.get(f['severity'], 9))
    return findings


# --- Insights (R10) ---

def _collect_insights(root):
    """Collect code insights: fan-in, blast top10, circular deps, god objects."""
    root = Path(root)
    insights = {
        'high_fan_in': [],
        'blast_top10': [],
        'circular_deps': [],
        'god_objects': [],
    }

    # Parse code_graph.mmd for file-level edges
    code_graph = root / 'docs' / 'architecture' / 'graphs' / 'code_graph.mmd'
    if not code_graph.exists():
        return insights

    try:
        import re
        content = code_graph.read_text(encoding='utf-8')
        # Parse edges: A --> B
        re_edge = re.compile(r'^\s*(\w+)\s+-->\s*(\w+)', re.MULTILINE)
        # Parse node labels: A["filename.py"]
        re_node = re.compile(r'^\s*(\w+)\["([^"]+)"\]', re.MULTILINE)

        node_labels = {m.group(1): m.group(2) for m in re_node.finditer(content)}
        edges = [(m.group(1), m.group(2)) for m in re_edge.finditer(content)]

        # Fan-in: count incoming edges per node
        fan_in = {}
        fan_out = {}
        adj_forward = {}
        adj_reverse = {}
        for src, dst in edges:
            fan_in[dst] = fan_in.get(dst, 0) + 1
            fan_out[src] = fan_out.get(src, 0) + 1
            adj_forward.setdefault(src, set()).add(dst)
            adj_reverse.setdefault(dst, set()).add(src)

        # High fan-in (≥5)
        for nid, count in sorted(fan_in.items(), key=lambda x: -x[1]):
            if count >= 5:
                insights['high_fan_in'].append({
                    'file': node_labels.get(nid, nid),
                    'fan_in': count,
                })

        # Blast radius top 10: BFS from each node, count reachable
        blast = []
        all_nodes = set(node_labels.keys())
        for nid in all_nodes:
            visited = set()
            queue = [nid]
            while queue:
                cur = queue.pop(0)
                if cur in visited:
                    continue
                visited.add(cur)
                for nb in adj_forward.get(cur, set()) | adj_reverse.get(cur, set()):
                    if nb not in visited:
                        queue.append(nb)
            blast.append((nid, len(visited) - 1))  # exclude self
        blast.sort(key=lambda x: -x[1])
        insights['blast_top10'] = [
            {'file': node_labels.get(nid, nid), 'affected': count}
            for nid, count in blast[:10]
        ]

        # Circular dependencies: DFS cycle detection on directed graph
        visited_global = set()
        in_stack = set()
        cycles = []

        def _dfs(node, path):
            if node in in_stack:
                # Found cycle — extract it
                cycle_start = path.index(node)
                cycle = [node_labels.get(n, n) for n in path[cycle_start:]]
                cycles.append(cycle)
                return
            if node in visited_global:
                return
            visited_global.add(node)
            in_stack.add(node)
            path.append(node)
            for neighbor in adj_forward.get(node, set()):
                _dfs(neighbor, path)
            path.pop()
            in_stack.discard(node)

        for node in all_nodes:
            if node not in visited_global:
                _dfs(node, [])
        insights['circular_deps'] = cycles

        # God objects: files with >15 functions (from call_graph if available)
        call_graph = root / 'docs' / 'architecture' / 'graphs' / 'call_graph.mmd'
        if call_graph.exists():
            cg_content = call_graph.read_text(encoding='utf-8')
            # Count function nodes per subgraph/file
            re_subgraph = re.compile(r'subgraph\s+"?([^"\n]+)"?')
            re_func_node = re.compile(r'^\s+\w+\["[^"]+"\]', re.MULTILINE)
            current_file = None
            file_func_count = {}
            for line in cg_content.splitlines():
                sm = re_subgraph.match(line.strip())
                if sm:
                    current_file = sm.group(1)
                    file_func_count.setdefault(current_file, 0)
                elif current_file and re_func_node.match(line):
                    file_func_count[current_file] = file_func_count.get(current_file, 0) + 1
                elif line.strip() == 'end':
                    current_file = None
            for fname, count in sorted(file_func_count.items(), key=lambda x: -x[1]):
                if count > 15:
                    insights['god_objects'].append({'file': fname, 'function_count': count})
    except Exception:
        pass

    return insights


# --- File Output (R11) ---

def _write_audit_json(result, root):
    """Write audit result to docs/architecture/governance/harness_audit.json."""
    root = Path(root)
    dest = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return dest


# --- Entry Point (R14) ---

def audit(target='.', layer=None, json_only=False, append=False):
    """Run the H1-H7 harness audit."""
    root = Path(target).resolve()

    # Run layer checks
    if layer:
        # Single layer mode
        check_map = {
            'H1': _check_h1, 'H2': _check_h2, 'H3': _check_h3,
            'H4': _check_h4, 'H5': _check_h5, 'H6': _check_h6, 'H7': _check_h7,
        }
        fn = check_map.get(layer.upper())
        if not fn:
            return json.dumps({'error': f'Unknown layer: {layer}'})
        layers = {layer.upper(): fn(root)}
        # Fill others as L0
        for k in check_map:
            if k not in layers:
                layers[k] = {'level': 0, 'name': 'None', 'checks': {}}
    else:
        layers = {
            'H1': _check_h1(root),
            'H2': _check_h2(root),
            'H3': _check_h3(root),
            'H4': _check_h4(root),
            'H5': _check_h5(root),
            'H6': _check_h6(root),
            'H7': _check_h7(root),
        }

    scoring = _compute_score(layers)

    # Collect findings and insights (skip in single-layer and append modes for speed)
    if layer or append:
        findings = []
        insights = {}
    else:
        findings = _collect_findings(root)
        insights = _collect_insights(root)

    # Get commit hash
    commit = ''
    try:
        result_proc = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=str(root), timeout=5,
        )
        commit = result_proc.stdout.strip()
    except Exception:
        pass

    result = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'commit': commit,
        'score': scoring['score'],
        'ready': scoring['ready'],
        'weakest': scoring.get('weakest'),
        'layers': layers,
        'findings': findings,
        'insights': insights,
    }

    # Write JSON file
    dest = _write_audit_json(result, root)

    if json_only:
        return json.dumps(result, indent=2, ensure_ascii=False)

    # Human-readable report
    lines = []
    lines.append(f'Harness Score: {scoring["score"]}/100')
    lines.append(f'AI Ready: {"YES" if scoring["ready"] else "NO"}')
    if not scoring['ready']:
        lines.append(f'Weakest Layer: {scoring["weakest"]}')
    lines.append('')
    _layer_names = {
        'H1': 'Prompt Engineering', 'H2': 'Context Engineering',
        'H3': 'Process Governance', 'H4': 'Tool Governance',
        'H5': 'Safety & Guardrails', 'H6': 'Observability', 'H7': 'Evolution',
    }
    for k in ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7']:
        v = layers[k]
        bar = '█' * v['level'] + '░' * (3 - v['level'])
        lines.append(f"  {k} {_layer_names.get(k, k):<24} [{bar}] L{v['level']} {v['name']}")
    lines.append('')

    if findings:
        lines.append(f'Findings ({len(findings)}):')
        for f in findings[:10]:
            lines.append(f"  [{f['severity'].upper():>8}] {f['category']}: {f['message']}")
        if len(findings) > 10:
            lines.append(f'  ... and {len(findings) - 10} more')
        lines.append('')

    if insights:
        if insights.get('circular_deps'):
            lines.append(f"Circular Dependencies: {len(insights['circular_deps'])} cycles detected")
        if insights.get('god_objects'):
            lines.append(f"God Objects: {len(insights['god_objects'])} files with >15 functions")
        if insights.get('high_fan_in'):
            lines.append(f"High Fan-In: {len(insights['high_fan_in'])} files with ≥5 importers")

    lines.append(f'\nAudit saved: {dest}')
    return '\n'.join(lines)
