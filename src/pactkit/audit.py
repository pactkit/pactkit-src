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


def _all_config_dirs(root):
    """Return config directories to scan: project-level + user-global ~/.claude/.

    STORY-slim-097 R1: Claude Code uses ~/.claude/ for global rules/agents/commands.
    Audit checks both project-level and global configuration.
    """
    root = Path(root)
    dirs = [root / d for d in _CONFIG_DIRS]
    home_claude = Path.home() / '.claude'
    if home_claude.is_dir() and home_claude not in dirs:
        dirs.append(home_claude)
    return dirs


def _has_dir_with_files(root, subdir):
    """Check if any config dir (project or global) has a non-empty subdirectory."""
    return any(
        (d / subdir).is_dir() and any((d / subdir).iterdir())
        for d in _all_config_dirs(root)
    )


def _compute_layer_level(config_checks, code_checks):
    """Compute layer level from config + code checks (STORY-slim-097 R4).

    L0: no checks pass
    L1: any 1 check passes
    L2: all config checks pass OR all code checks pass
    L3: all config AND all code checks pass
    """
    all_config = all(config_checks.values()) if config_checks else True
    all_code = all(code_checks.values()) if code_checks else True
    any_pass = any(config_checks.values()) or any(code_checks.values()) if (config_checks or code_checks) else False

    if all_config and all_code:
        return 3
    if all_config or all_code:
        return 2
    if any_pass:
        return 1
    return 0


def _check_h1(root):
    """Check H1: System prompts, rules, agent roles.
    STORY-slim-097: Config-only layer — scans project + global dirs.
    """
    root = Path(root)
    config_checks = {}
    config_checks['claude_md'] = any(
        (root / d / 'CLAUDE.md').exists() for d in [*_CONFIG_DIRS, '.']
    )
    config_checks['rules'] = _has_dir_with_files(root, 'rules')
    config_checks['agents'] = _has_dir_with_files(root, 'agents')
    # Skills: check for skills dir in any config location
    config_checks['skills'] = any(
        (d / 'skills').is_dir() and any((d / 'skills').iterdir())
        for d in _all_config_dirs(root)
    )

    code_checks = {}  # H1 has no code checks

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H2: Context Engineering (Auto-scan) ---

def _check_h2(root):
    """Check H2: Project context, memory, hierarchy of truth.
    STORY-slim-097: Config (memory, hierarchy) + Code (specs, context_fresh).
    """
    root = Path(root)
    config_checks = {}
    config_checks['hierarchy_of_truth'] = any(
        any(f.read_text(encoding='utf-8', errors='ignore').lower().count('hierarchy') > 0
            for f in (d / 'rules').glob('*.md'))
        for d in _all_config_dirs(root)
        if (d / 'rules').is_dir()
    )
    config_checks['memory_config'] = any(
        (d / 'projects').is_dir() or (d / 'MEMORY.md').exists()
        for d in _all_config_dirs(root)
    )

    code_checks = {}
    code_checks['context_md'] = (root / 'docs' / 'product' / 'context.md').exists()
    code_checks['specs_exist'] = (root / 'docs' / 'specs').is_dir() and any((root / 'docs' / 'specs').glob('*.md'))
    ctx = root / 'docs' / 'product' / 'context.md'
    code_checks['context_fresh'] = False
    if ctx.exists():
        import time
        age_days = (time.time() - ctx.stat().st_mtime) / 86400
        code_checks['context_fresh'] = age_days <= 7

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H3: Process Governance (Auto-scan) ---

def _check_h3(root):
    """Check H3: PDCA workflow, TDD, quality gates.
    STORY-slim-097: Config (quality_gate) + Code (tests, CI, coverage ratio).
    """
    root = Path(root)
    config_checks = {}
    config_checks['quality_gate'] = False
    for d in _all_config_dirs(root):
        cfg = d / 'pactkit.yaml'
        if cfg.exists():
            try:
                content = cfg.read_text(encoding='utf-8')
                if 'lint_blocking' in content:
                    config_checks['quality_gate'] = True
            except Exception:
                pass

    code_checks = {}
    code_checks['sprint_board'] = (root / 'docs' / 'product' / 'sprint_board.md').exists()
    code_checks['tests_exist'] = (root / 'tests').is_dir() and any((root / 'tests').rglob('test_*.py'))
    code_checks['ci_config'] = (
        (root / '.github' / 'workflows').is_dir()
        or (root / '.gitlab-ci.yml').exists()
        or (root / 'Jenkinsfile').exists()
    )
    # Test coverage ratio: test files / source files >= 0.3
    code_checks['test_coverage_ratio'] = False
    src_count = 0
    test_count = 0
    for ext in ['*.py', '*.ts', '*.go', '*.java']:
        src_count += len([f for f in root.rglob(ext)
                         if 'test' not in str(f).lower() and 'node_modules' not in str(f)
                         and '.venv' not in str(f) and '__pycache__' not in str(f)])
        test_count += len([f for f in root.rglob(ext)
                          if 'test' in str(f).lower() and 'node_modules' not in str(f)
                          and '.venv' not in str(f)])
    if src_count > 0:
        code_checks['test_coverage_ratio'] = (test_count / src_count) >= 0.3

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H4: Tool Governance (Partial auto-scan) ---

def _check_h4(root, manual=None):
    """Check H4: MCP config, permissions, tool whitelist.
    STORY-slim-097: Config (yaml, settings, mcp) + Code (lint_clean).
    """
    root = Path(root)
    config_checks = {}
    config_checks['pactkit_yaml'] = any((root / d / 'pactkit.yaml').exists() for d in _CONFIG_DIRS)
    config_checks['settings_json'] = any(
        (d / 'settings.json').exists() or (d / 'settings.local.json').exists()
        for d in _all_config_dirs(root)
    )
    config_checks['mcp_config'] = False
    for d in _all_config_dirs(root):
        for name in ['settings.json', 'settings.local.json']:
            sf = d / name
            if sf.exists():
                try:
                    content = sf.read_text(encoding='utf-8')
                    if 'mcpServers' in content or 'enabledMcp' in content or 'mcp_servers' in content:
                        config_checks['mcp_config'] = True
                except Exception:
                    pass

    code_checks = {}
    # Lint clean: try ruff or eslint
    code_checks['lint_clean'] = False
    try:
        result = subprocess.run(
            ['ruff', 'check', 'src/', 'tests/', '--quiet'],
            capture_output=True, text=True, cwd=str(root), timeout=30,
        )
        code_checks['lint_clean'] = result.returncode == 0
    except Exception:
        pass

    if manual:
        config_checks.update(manual)

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H5: Safety & Guardrails (Auto-scan) ---

def _check_h5(root):
    """Check H5: Safety & Guardrails.
    STORY-slim-097: Config (safety_rules, hooks) + Code (gitignore, no_secrets).
    """
    root = Path(root)
    config_checks = {}
    config_checks['safety_rules'] = False
    _safety_keywords = {'secret', 'password', 'token', 'data loss', 'never print', 'credential'}
    for d in _all_config_dirs(root):
        rules_dir = d / 'rules'
        if rules_dir.is_dir():
            for f in rules_dir.glob('*.md'):
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore').lower()
                    if any(kw in content for kw in _safety_keywords):
                        config_checks['safety_rules'] = True
                        break
                except Exception:
                    pass
    config_checks['hooks_config'] = False
    for d in _all_config_dirs(root):
        for name in ['settings.json', 'settings.local.json']:
            sf = d / name
            if sf.exists():
                try:
                    content = sf.read_text(encoding='utf-8')
                    if 'hook' in content.lower():
                        config_checks['hooks_config'] = True
                except Exception:
                    pass

    code_checks = {}
    code_checks['gitignore'] = (root / '.gitignore').exists()
    # No secrets committed: check git for tracked .env/.key files
    code_checks['no_secrets'] = True
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '*.env', '.env*', '*.key', '*credentials*'],
            capture_output=True, text=True, cwd=str(root), timeout=5,
        )
        if result.stdout.strip():
            code_checks['no_secrets'] = False
    except Exception:
        pass

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H6: Observability (Partial auto-scan) ---

def _check_h6(root, manual=None):
    """Check H6: Observability.
    STORY-slim-097: Config (self_audit_rule) + Code (changelog, lessons, commit_recent).
    """
    root = Path(root)
    config_checks = {}
    config_checks['self_audit_rule'] = False
    for d in _all_config_dirs(root):
        rules_dir = d / 'rules'
        if rules_dir.is_dir():
            for f in rules_dir.glob('*.md'):
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore').lower()
                    if 'self-audit' in content or 'operational discipline' in content:
                        config_checks['self_audit_rule'] = True
                        break
                except Exception:
                    pass

    code_checks = {}
    code_checks['lessons_md'] = (root / 'docs' / 'architecture' / 'governance' / 'lessons.md').exists()
    code_checks['changelog'] = (root / 'CHANGELOG.md').exists()
    # Commit recent: any commit in last 7 days
    code_checks['commit_recent'] = False
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', '--since=7 days ago', '-1'],
            capture_output=True, text=True, cwd=str(root), timeout=5,
        )
        code_checks['commit_recent'] = bool(result.stdout.strip())
    except Exception:
        pass
    # Retro history
    code_checks['retro_exists'] = False
    search_dirs = [root / 'docs']
    for d in _all_config_dirs(root):
        if (d / 'projects').is_dir():
            search_dirs.append(d / 'projects')
    for pattern in ['retro*.md', 'retro-*.md']:
        for search_dir in search_dirs:
            if search_dir.is_dir() and any(search_dir.rglob(pattern)):
                code_checks['retro_exists'] = True
                break

    if manual:
        config_checks.update(manual)

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- H7: Evolution (Auto-scan) ---

def _check_h7(root):
    """Check H7: Version management, changelog, automation.
    STORY-slim-097: Code-only layer.
    """
    root = Path(root)
    config_checks = {}  # H7 has no config checks
    code_checks = {}
    code_checks['version_managed'] = False
    for name in ['pyproject.toml', 'package.json']:
        vf = root / name
        if vf.exists():
            try:
                content = vf.read_text(encoding='utf-8')
                if 'version' in content:
                    code_checks['version_managed'] = True
            except Exception:
                pass
    code_checks['git_tags'] = False
    try:
        result = subprocess.run(['git', 'tag', '--list'], capture_output=True, text=True, cwd=str(root), timeout=5)
        code_checks['git_tags'] = bool(result.stdout.strip())
    except Exception:
        pass
    code_checks['ci_publish'] = False
    wf_dir = root / '.github' / 'workflows'
    if wf_dir.is_dir():
        for f in wf_dir.glob('*.yml'):
            try:
                content = f.read_text(encoding='utf-8', errors='ignore').lower()
                if 'publish' in content or 'release' in content or 'deploy' in content:
                    code_checks['ci_publish'] = True
                    break
            except Exception:
                pass

    level = _compute_layer_level(config_checks, code_checks)
    checks = {**config_checks, **code_checks}
    return {'level': level, 'name': _LEVEL_NAMES[level], 'checks': checks,
            'config_checks': config_checks, 'code_checks': code_checks}


# --- Scoring (R8) ---

def _compute_score(layers, config_passed=None, config_total=None,
                   code_passed=None, code_total=None):
    """Compute Harness Score and AI Ready status.

    STORY-slim-097 R3: Dual-dimension scoring.
    If config/code counts provided: score = config_pct×50 + code_pct×50.
    Otherwise: fallback to legacy layer-level formula for backward compat.
    """
    ready = all(v['level'] >= 1 for v in layers.values())
    min_layer = min(layers.items(), key=lambda x: x[1]['level'])

    if config_total is not None and code_total is not None:
        config_pct = config_passed / config_total if config_total > 0 else 0
        code_pct = code_passed / code_total if code_total > 0 else 0
        score = round(config_pct * 50 + code_pct * 50)
    else:
        # Auto-aggregate from layer data
        all_config = {}
        all_code = {}
        for v in layers.values():
            all_config.update(v.get('config_checks', {}))
            all_code.update(v.get('code_checks', {}))
        cp = sum(1 for v in all_config.values() if v)
        ct = len(all_config) if all_config else 1
        cdp = sum(1 for v in all_code.values() if v)
        cdt = len(all_code) if all_code else 1
        score = round((cp / ct) * 50 + (cdp / cdt) * 50)
        config_passed, config_total = cp, ct
        code_passed, code_total = cdp, cdt

    return {
        'score': score,
        'ready': ready,
        'weakest': min_layer[0] if not ready else None,
        'dimensions': {
            'config': {'score': round((config_passed / config_total) * 50) if config_total else 0,
                       'passed': config_passed, 'total': config_total},
            'code': {'score': round((code_passed / code_total) * 50) if code_total else 0,
                     'passed': code_passed, 'total': code_total},
        },
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


# --- Signal Functions (STORY-slim-093 R1-R5) ---


def _check_test_coverage(root, source_file, stack='python'):
    """R1: Check if a source file has a corresponding test file."""
    root = Path(root)
    try:
        from pactkit.skills.visualize import _resolve_test_path
        test_path = _resolve_test_path(root, source_file.stem, source_file, stack)
        if test_path:
            return True
    except Exception:
        pass
    # Fallback: glob for test_{stem}
    for pattern in [f'tests/**/test_{source_file.stem}.py', f'tests/**/test_{source_file.stem}.*']:
        if list(root.glob(pattern)):
            return True
    return False


def _check_docstring_coverage(file_path):
    """R2: Return percentage of functions with docstrings (0-100)."""
    import ast as _ast
    try:
        tree = _ast.parse(Path(file_path).read_text(encoding='utf-8'))
        total = 0
        with_doc = 0
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                total += 1
                if _ast.get_docstring(node):
                    with_doc += 1
        return round(with_doc / total * 100) if total > 0 else 100
    except Exception:
        return 0


def _check_code_smells(file_path):
    """R3: Return (long_funcs_count, deep_nesting_count)."""
    import ast as _ast
    try:
        tree = _ast.parse(Path(file_path).read_text(encoding='utf-8'))
        long_funcs = 0
        deep_nesting = 0
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                # Long function: >50 lines
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    lines = node.end_lineno - node.lineno
                    if lines > 50:
                        long_funcs += 1
                # Deep nesting: count max depth of control flow
                max_depth = _max_nesting_depth(node, 0)
                if max_depth > 4:
                    deep_nesting += 1
        return long_funcs, deep_nesting
    except Exception:
        return 0, 0


def _max_nesting_depth(node, current):
    """Recursively compute max control flow nesting depth."""
    import ast as _ast
    _NESTING_TYPES = (_ast.If, _ast.For, _ast.While, _ast.With,
                      _ast.AsyncFor, _ast.AsyncWith, _ast.Try)
    if hasattr(_ast, 'TryStar'):
        _NESTING_TYPES = (*_NESTING_TYPES, _ast.TryStar)
    max_d = current
    for child in _ast.iter_child_nodes(node):
        if isinstance(child, _NESTING_TYPES):
            d = _max_nesting_depth(child, current + 1)
            max_d = max(max_d, d)
        else:
            d = _max_nesting_depth(child, current)
            max_d = max(max_d, d)
    return max_d


def _check_dependency_health(root):
    """R5: Project-level dependency vulnerability check."""
    root = Path(root)
    # Python: pip audit
    if (root / 'pyproject.toml').exists() or (root / 'requirements.txt').exists():
        try:
            result = subprocess.run(
                ['pip-audit', '--format', 'json'],
                capture_output=True, text=True, cwd=str(root), timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                vulns = data if isinstance(data, list) else []
                critical = sum(1 for v in vulns if v.get('fix_versions'))
                return {'vulns': len(vulns), 'critical': critical, 'details': vulns[:5]}
        except FileNotFoundError:
            return {'vulns': -1, 'error': 'pip-audit not installed'}
        except subprocess.TimeoutExpired:
            return {'vulns': -1, 'error': 'pip-audit timed out'}
        except Exception:
            return {'vulns': -1, 'error': 'pip-audit failed'}

    # Node: npm audit
    if (root / 'package-lock.json').exists():
        try:
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                capture_output=True, text=True, cwd=str(root), timeout=10,
            )
            data = json.loads(result.stdout)
            total = data.get('metadata', {}).get('vulnerabilities', {})
            vulns = sum(total.values()) if isinstance(total, dict) else 0
            critical = total.get('critical', 0) + total.get('high', 0)
            return {'vulns': vulns, 'critical': critical, 'details': []}
        except FileNotFoundError:
            return {'vulns': -1, 'error': 'npm not installed'}
        except Exception:
            return {'vulns': -1, 'error': 'npm audit failed'}

    return {'vulns': 0, 'critical': 0, 'details': []}


# --- Hotspot Aggregation (STORY-slim-092 R1, R2) ---


def _suggest_action(hotspot):
    """Generate actionable suggestion string from dominant risk signals.

    STORY-slim-093 R7: Priority order for combining top 2.
    """
    actions = []
    if not hotspot.get('has_test', True):
        actions.append('Add tests: no test file found')
    if hotspot.get('complexity_avg', 0) > 30:
        actions.append('Split: extract high-complexity functions')
    if hotspot.get('long_funcs', 0) > 0 or hotspot.get('deep_nesting', 0) > 0:
        parts = []
        if hotspot.get('long_funcs', 0) > 0:
            parts.append(f"{hotspot['long_funcs']} long functions")
        if hotspot.get('deep_nesting', 0) > 0:
            parts.append(f"{hotspot['deep_nesting']} deeply nested")
        actions.append(f"Refactor: {', '.join(parts)}")
    if hotspot.get('layer_violations', 0) > 0:
        actions.append(f"Fix layers: {hotspot['layer_violations']} violations")
    if hotspot.get('docstring_pct', 100) < 30:
        pct = 100 - hotspot.get('docstring_pct', 0)
        actions.append(f"Document: {pct}% lack docstrings")
    if hotspot.get('fan_in', 0) >= 5:
        actions.append(f"Stabilize: {hotspot['fan_in']} dependents")
    if hotspot.get('blast_pct', 0) > 50:
        actions.append(f"Isolate: blast radius {hotspot['blast_pct']}%")
    if hotspot.get('function_count', 0) > 15:
        actions.append(f"Decompose: {hotspot['function_count']} functions")
    if not actions:
        actions.append('Monitor: no critical signals')
    return ' + '.join(actions[:2])


def _compute_hotspots(root):
    """Compute file-level hotspots from complexity, blast radius, and fan-in."""
    root = Path(root)
    file_data = {}  # rel_path -> {complexity_sum, func_count, fan_in, blast_pct}

    # 1. Collect per-file complexity data
    try:
        from pactkit.skills.visualize import (  # noqa: I001
            _LANG_FILE_EXT, _detect_stacks, _load_scan_excludes,
            _scan_files, _select_analyzer,
        )
        scan_excludes = _load_scan_excludes(root)
        stacks = _detect_stacks(root)
        for stk in stacks:
            analyzer = _select_analyzer(stk)
            exts = [_LANG_FILE_EXT.get(stk, '.py')]
            if stk == 'node':
                exts.extend(['.js', '.tsx', '.jsx'])
            for ext in exts:
                files, _mi, _ftn = _scan_files(
                    root, scan_excludes=scan_excludes, file_ext=ext,
                )
                for f in files:
                    result = analyzer.extract_functions_and_calls(
                        f, include_complexity=True,
                    )
                    if len(result) == 3:
                        _fr, _ce, cm = result
                        if cm:
                            rel = str(f.relative_to(root))
                            entry = file_data.setdefault(rel, {
                                'complexity_sum': 0, 'func_count': 0,
                                'fan_in': 0, 'blast_pct': 0,
                            })
                            entry['complexity_sum'] += sum(cm.values())
                            entry['func_count'] += len(cm)
    except Exception:
        pass

    if not file_data:
        return []

    # 2. Collect fan-in from code_graph.mmd
    label_to_rel = {}
    re_edge = None
    content = ''
    code_graph = root / 'docs' / 'architecture' / 'graphs' / 'code_graph.mmd'
    if code_graph.exists():
        try:
            import re as _re
            content = code_graph.read_text(encoding='utf-8')
            re_edge = _re.compile(r'^\s*(\w+)\s+-->\s*(\w+)', _re.MULTILINE)
            re_node = _re.compile(r'^\s*(\w+)\["([^"]+)"\]', _re.MULTILINE)
            node_labels = {m.group(1): m.group(2) for m in re_node.finditer(content)}
            label_to_rel = {}
            for nid, label in node_labels.items():
                # Match label to file_data keys by filename
                for rel in file_data:
                    if rel.endswith(label) or label in rel:
                        label_to_rel[nid] = rel
                        break
            fan_in_count = {}
            for m in re_edge.finditer(content):
                dst = m.group(2)
                fan_in_count[dst] = fan_in_count.get(dst, 0) + 1
            for nid, count in fan_in_count.items():
                rel = label_to_rel.get(nid)
                if rel and rel in file_data:
                    file_data[rel]['fan_in'] = count
        except Exception:
            pass

    # 3. Compute blast_pct per file (simplified: fan_in based estimate)
    total_files = len(file_data)
    for rel, data in file_data.items():
        # Rough blast estimate: fan_in / total * 100
        if total_files > 1:
            data['blast_pct'] = round(data['fan_in'] / (total_files - 1) * 100)
        else:
            data['blast_pct'] = 0

    # 4. Collect new signals per file (R1-R4)
    try:
        from pactkit.skills.visualize import (  # noqa: I001
            _detect_stacks as _ds2, _load_layer_config, _classify_file,
        )
        stacks = _ds2(root)
        primary_stack = stacks[0] if stacks else 'python'
        layer_config = _load_layer_config(root)
    except Exception:
        primary_stack = 'python'
        layer_config = []

    # Build file-level edges for layer violation counting
    file_edges = []
    if re_edge and content:
        try:
            for m in re_edge.finditer(content):
                file_edges.append((m.group(1), m.group(2)))
        except Exception:
            pass

    for rel, data in file_data.items():
        source_file = root / rel
        data['has_test'] = _check_test_coverage(root, source_file, primary_stack)
        data['docstring_pct'] = _check_docstring_coverage(source_file)
        long_f, deep_n = _check_code_smells(source_file)
        data['long_funcs'] = long_f
        data['deep_nesting'] = deep_n
        # Layer violations: count edges where this file is importer into higher layer
        violations = 0
        if layer_config and label_to_rel:
            my_layer, my_idx = _classify_file(rel, layer_config)
            if my_idx >= 0:
                my_nids = [nid for nid, r in label_to_rel.items() if r == rel]
                for src_nid, dst_nid in file_edges:
                    if src_nid in my_nids:
                        dst_rel = label_to_rel.get(dst_nid)
                        if dst_rel:
                            _, dst_idx = _classify_file(dst_rel, layer_config)
                            if dst_idx >= 0 and my_idx > dst_idx:
                                violations += 1
        data['layer_violations'] = violations

    # 5. Compute weighted hotspot scores (R6)
    _W_COMPLEXITY = 0.25
    _W_DOCSTRING = 0.15
    _W_SMELLS = 0.15
    _W_LAYERS = 0.10
    _W_TEST = 0.20
    _W_BLAST = 0.15

    hotspots = []
    for rel, data in file_data.items():
        func_count = data['func_count']
        if func_count == 0:
            continue
        complexity_avg = round(data['complexity_sum'] / func_count, 1)
        fan_in = data['fan_in']
        blast_pct = data['blast_pct']
        docstring_pct = data.get('docstring_pct', 100)
        long_funcs = data.get('long_funcs', 0)
        deep_nesting = data.get('deep_nesting', 0)
        layer_violations = data.get('layer_violations', 0)
        has_test = data.get('has_test', True)

        score = (
            complexity_avg * _W_COMPLEXITY
            + (1 - docstring_pct / 100) * 10 * _W_DOCSTRING
            + (long_funcs + deep_nesting) * 3 * _W_SMELLS
            + layer_violations * 5 * _W_LAYERS
            + (0 if has_test else 10) * _W_TEST
            + blast_pct / 100 * max(fan_in, 1) * 10 * _W_BLAST
        )
        score = min(round(score), 100)

        hotspot = {
            'file': rel,
            'score': score,
            'complexity_avg': complexity_avg,
            'blast_pct': blast_pct,
            'fan_in': fan_in,
            'function_count': func_count,
            'has_test': has_test,
            'docstring_pct': docstring_pct,
            'long_funcs': long_funcs,
            'deep_nesting': deep_nesting,
            'layer_violations': layer_violations,
        }
        hotspot['action'] = _suggest_action(hotspot)
        hotspots.append(hotspot)

    hotspots.sort(key=lambda h: h['score'], reverse=True)
    return hotspots[:10]


# --- Suggested Tasks Generation (STORY-slim-093 R8, R9) ---


def _generate_suggested_tasks(root, hotspots, developer):
    """Generate BUG/HOTFIX tasks from hotspots, scaffold Specs."""
    root = Path(root)
    specs_dir = root / 'docs' / 'specs'
    specs_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    for hotspot in hotspots:
        if hotspot['score'] == 0 and hotspot.get('has_test', True):
            continue  # No action needed

        # Determine type
        task_type = 'BUG' if (hotspot['score'] >= 15 or hotspot.get('layer_violations', 0) > 0) else 'HOTFIX'
        severity = 'high' if hotspot['score'] >= 15 else ('medium' if hotspot['score'] >= 5 else 'low')

        # Check for existing spec for this file+type (idempotent, R8)
        existing_spec = _find_existing_spec(specs_dir, hotspot['file'], task_type)
        if existing_spec:
            # Check if Done — if so, skip (Done-completed filter)
            try:
                content = existing_spec.read_text(encoding='utf-8')
                if '| Status | Done |' in content:
                    continue  # Already fixed
            except Exception:
                pass
            spec_path = str(existing_spec.relative_to(root))
            spec_id = existing_spec.stem
        else:
            # Generate new spec
            try:
                from pactkit.id_generator import next_story_id
                raw_id = next_story_id(specs_dir=specs_dir, developer=developer)
                # Replace STORY prefix with BUG or HOTFIX
                num = raw_id.split('-')[-1]
                spec_id = f'{task_type}-{developer}-{num}'
                spec_path = f'docs/specs/{spec_id}.md'
                _scaffold_audit_spec(root, spec_id, hotspot)
            except Exception:
                continue

        title = hotspot['action'].split('+')[0].strip()
        file_name = hotspot['file'].rsplit('/', 1)[-1] if '/' in hotspot['file'] else hotspot['file']
        desc = f"{title} in {file_name}"

        cmd_prefix = '/project-act' if task_type == 'BUG' else '/project-hotfix'
        tasks.append({
            'type': task_type,
            'severity': severity,
            'title': f"{title}: {file_name}",
            'file': hotspot['file'],
            'signals': {
                k: hotspot[k] for k in [
                    'score', 'complexity_avg', 'fan_in', 'has_test',
                    'docstring_pct', 'long_funcs', 'deep_nesting', 'layer_violations',
                ] if k in hotspot
            },
            'spec': spec_path,
            'command': f'{cmd_prefix} {spec_id} {desc}',
        })

    return tasks


def _find_existing_spec(specs_dir, file_path, task_type):
    """Find an existing BUG/HOTFIX spec that references this file."""
    for spec in specs_dir.glob(f'{task_type}-*.md'):
        try:
            content = spec.read_text(encoding='utf-8', errors='ignore')
            if file_path in content:
                return spec
        except Exception:
            pass
    return None


def _scaffold_audit_spec(root, spec_id, hotspot):
    """Create a minimal spec file for an audit-generated task."""
    specs_dir = root / 'docs' / 'specs'
    dest = specs_dir / f'{spec_id}.md'
    action = hotspot.get('action', 'Fix issue')
    file_path = hotspot.get('file', 'unknown')
    signals = []
    if not hotspot.get('has_test', True):
        signals.append("- No test file found")
    if hotspot.get('complexity_avg', 0) > 20:
        signals.append(f"- High avg complexity: {hotspot['complexity_avg']}")
    if hotspot.get('long_funcs', 0) > 0:
        signals.append(f"- {hotspot['long_funcs']} functions exceed 50 lines")
    if hotspot.get('deep_nesting', 0) > 0:
        signals.append(f"- {hotspot['deep_nesting']} functions nested >4 levels")
    if hotspot.get('layer_violations', 0) > 0:
        signals.append(f"- {hotspot['layer_violations']} layer violations")
    if hotspot.get('docstring_pct', 100) < 50:
        signals.append(f"- Only {hotspot['docstring_pct']}% functions documented")
    signals_text = '\n'.join(signals) if signals else '- Hotspot score > threshold'

    content = (
        f"# {spec_id}: {action}\n\n"
        f"| Field | Value |\n|-------|-------|\n"
        f"| ID | {spec_id} |\n| Status | Draft |\n"
        f"| Priority | P2 |\n| Release | TBD |\n\n"
        f"## Background\n\n"
        f"Auto-generated by `pactkit audit`. Target file: `{file_path}`\n\n"
        f"Detected signals:\n{signals_text}\n\n"
        f"## Requirements\n\n"
        f"### R1: {action} (MUST)\n\n"
        f"Address the issues in `{file_path}` identified by audit.\n\n"
        f"## Acceptance Criteria\n\n"
        f"### AC1: Issue Resolved (R1)\n\n"
        f"- **Given** `{file_path}` with the detected signals\n"
        f"- **When** the fix is applied\n"
        f"- **Then** re-running `pactkit audit` shows improved score for this file\n\n"
        f"## Target Call Chain\n\n(See audit signals above)\n\n"
        f"## Implementation Steps\n\n"
        f"| Step | File | Action | Dependencies | Risk |\n"
        f"|------|------|--------|-------------|------|\n"
        f"| 1 | `{file_path}` | {action} | None | Low |\n\n"
        f"## Security Scope\n\n"
        f"| Check | Applicable | Reason |\n"
        f"|-------|------------|--------|\n"
        f"| SEC-1 | N/A | Auto-generated audit task |\n\n"
        f"## Out of Scope\n\n- Other files not flagged by this audit\n"
    )
    dest.write_text(content, encoding='utf-8')


# --- File Output (R11) ---

def _write_audit_json(result, root):
    """Write slim audit result to docs/architecture/governance/harness_audit.json.

    STORY-slim-092: Scorecard + layers (level/name) + hotspots.
    STORY-slim-093: + suggested_tasks + dependency_health.
    """
    root = Path(root)
    scorecard = {
        'timestamp': result['timestamp'],
        'commit': result['commit'],
        'story_id': result.get('story_id', ''),
        'score': result['score'],
        'ready': result['ready'],
        'weakest': result.get('weakest'),
        'layers': {
            k: {'level': v['level'], 'name': v['name']}
            for k, v in result['layers'].items()
        },
        'dimensions': result.get('dimensions', {}),
        'hotspots': result.get('hotspots', []),
        'suggested_tasks': result.get('suggested_tasks', []),
        'dependency_health': result.get('dependency_health', {}),
    }
    dest = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(scorecard, indent=2, ensure_ascii=False), encoding='utf-8')
    return dest


# --- Entry Point (R14) ---

def _should_refresh_audit(root, story_id=None):
    """Decide whether Done should refresh harness_audit.json.

    Returns True only when all three conditions are met:
    1. harness_audit.json exists (audit was run at least once)
    2. story_id is provided (Done knows which story it's closing)
    3. The JSON's story_id matches the current story (this story owns the audit)

    If the file doesn't exist or story_id doesn't match, Done skips —
    the audit belongs to a different story or was never run.
    """
    audit_file = root / 'docs' / 'architecture' / 'governance' / 'harness_audit.json'
    if not audit_file.exists():
        return False
    if not story_id:
        return False
    try:
        data = json.loads(audit_file.read_text(encoding='utf-8'))
        return data.get('story_id', '') == story_id
    except Exception:
        return False


def audit(target='.', layer=None, json_only=False, append=False, verbose=False,
          if_needed=False, story_id=None):
    """Run the H1-H7 harness audit.

    STORY-slim-092: Default output is concise (scorecard + hotspots).
    Use verbose=True for full findings/insights detail.
    if_needed=True: only refresh when harness_audit.json exists and its
    story_id matches the provided story_id (Done owns this audit).
    """
    root = Path(target).resolve()

    if if_needed and not _should_refresh_audit(root, story_id):
        return None

    # Run layer checks
    if layer:
        check_map = {
            'H1': _check_h1, 'H2': _check_h2, 'H3': _check_h3,
            'H4': _check_h4, 'H5': _check_h5, 'H6': _check_h6, 'H7': _check_h7,
        }
        fn = check_map.get(layer.upper())
        if not fn:
            return json.dumps({'error': f'Unknown layer: {layer}'})
        layers = {layer.upper(): fn(root)}
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

    # Compute hotspots (R11: --append now runs full re-audit)
    hotspots = [] if layer else _compute_hotspots(root)

    # Dependency health (R5)
    dep_health = {} if layer else _check_dependency_health(root)

    # Suggested tasks (R8) — generate specs + task entries
    suggested_tasks = []
    if not layer and hotspots:
        try:
            from pactkit.config import load_config
            cfg = load_config(root)
            developer = cfg.get('developer', '')
        except Exception:
            developer = ''
        if developer:
            suggested_tasks = _generate_suggested_tasks(root, hotspots, developer)

    # Verbose: collect full findings/insights
    findings = []
    insights = {}
    if verbose and not layer and not append:
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
        'story_id': story_id or '',
        'score': scoring['score'],
        'ready': scoring['ready'],
        'weakest': scoring.get('weakest'),
        'dimensions': scoring.get('dimensions', {}),
        'layers': layers,
        'hotspots': hotspots,
        'suggested_tasks': suggested_tasks,
        'dependency_health': dep_health,
    }
    # Verbose fields (not written to JSON file)
    if verbose:
        result['findings'] = findings
        result['insights'] = insights

    # Write slim JSON file
    dest = _write_audit_json(result, root)

    if json_only:
        if verbose:
            return json.dumps(result, indent=2, ensure_ascii=False)
        # Slim: same as file (includes suggested_tasks + dependency_health)
        scorecard = {
            'timestamp': result['timestamp'],
            'commit': result['commit'],
            'score': result['score'],
            'ready': result['ready'],
            'weakest': result.get('weakest'),
            'layers': {
                k: {'level': v['level'], 'name': v['name']}
                for k, v in layers.items()
            },
            'dimensions': scoring.get('dimensions', {}),
            'hotspots': hotspots,
            'suggested_tasks': suggested_tasks,
            'dependency_health': dep_health,
        }
        return json.dumps(scorecard, indent=2, ensure_ascii=False)

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
        lines.append(
            f"  {k} {_layer_names.get(k, k):<24} "
            f"[{bar}] L{v['level']} {v['name']}"
        )

    # Hotspots (default concise output)
    if hotspots:
        lines.append('')
        lines.append('Top Hotspots:')
        lines.append(
            f'  {"#":<3} {"File":<40} {"Score":>5} '
            f'{"Cx":>5} {"Blast":>6} {"Fan":>4}  Action'
        )
        for i, h in enumerate(hotspots, 1):
            fname = h['file']
            if len(fname) > 38:
                fname = '...' + fname[-35:]
            lines.append(
                f"  {i:<3} {fname:<40} {h['score']:>5} "
                f"{h['complexity_avg']:>5} {h['blast_pct']:>5}% "
                f"{h['fan_in']:>4}  {h['action']}"
            )

    # Verbose: full findings + insights
    if verbose and findings:
        lines.append('')
        lines.append(f'Findings ({len(findings)}):')
        for f in findings:
            lines.append(
                f"  [{f['severity'].upper():>8}] "
                f"{f['category']}: {f['message']}"
            )

    if verbose and insights:
        lines.append('')
        if insights.get('circular_deps'):
            lines.append(
                f"Circular Dependencies: "
                f"{len(insights['circular_deps'])} cycles"
            )
        if insights.get('god_objects'):
            lines.append(
                f"God Objects: "
                f"{len(insights['god_objects'])} files with >15 functions"
            )
        if insights.get('high_fan_in'):
            lines.append(
                f"High Fan-In: "
                f"{len(insights['high_fan_in'])} files with ≥5 importers"
            )

    lines.append(f'\nAudit saved: {dest}')
    return '\n'.join(lines)
