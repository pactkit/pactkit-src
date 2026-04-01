"""Script loader for PactKit skill scripts.

Scripts are stored as real Python files for IDE support.
At deploy time, the standalone header is stripped and replaced
with the canonical _SHARED_HEADER.
"""
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent

_SHARED_HEADER = r"""import abc, re, os, sys, json, datetime, argparse, subprocess, shutil, ast
from collections import deque
from dataclasses import dataclass
from pathlib import Path

def nl(): return chr(10)
"""

_BODY_MARKER = '# === SCRIPT BODY ==='


def _extract_body(content):
    """Extract the body portion below _BODY_MARKER, or return full content."""
    idx = content.find(_BODY_MARKER)
    if idx >= 0:
        newline_idx = content.index('\n', idx)
        return content[newline_idx + 1:]
    return content


# Ordered list of analyzer files to inline when deploying visualize.py.
# Order matters: ABC/base first, then concrete analyzers.
_ANALYZER_INLINE_ORDER = [
    'analyzers/__init__.py',
    'analyzers/python_analyzer.py',
    'analyzers/go_analyzer.py',
    'analyzers/ts_analyzer.py',
    'analyzers/java_analyzer.py',
]


def load_script(name):
    """Load a script file, strip standalone header, prepend _SHARED_HEADER.

    If the body contains ``from __future__ import annotations``, it is hoisted
    above _SHARED_HEADER (Python requires __future__ imports to be first).

    STORY-slim-078: When loading ``visualize.py``, analyzer module bodies
    from ``analyzers/*.py`` are inlined before the main body so the deployed
    script remains a single self-contained file.
    """
    content = (_SCRIPTS_DIR / name).read_text(encoding='utf-8')
    body = _extract_body(content)

    # STORY-slim-078: Inline analyzer files for visualize.py
    if name == 'visualize.py':
        analyzer_bodies = []
        for rel in _ANALYZER_INLINE_ORDER:
            analyzer_file = _SCRIPTS_DIR / rel
            if analyzer_file.exists():
                analyzer_bodies.append(_extract_body(
                    analyzer_file.read_text(encoding='utf-8')
                ))
        # Strip analyzer import lines from main body (single-line and multi-line)
        import re
        # Multi-line: from pactkit.skills.analyzers import (\n...\n)
        body = re.sub(
            r'^from pactkit\.skills\.analyzers[^\n]*\([^)]*\)\s*\n?',
            '',
            body,
            flags=re.MULTILINE | re.DOTALL,
        )
        # Single-line: from pactkit.skills.analyzers... import ...\n
        body = re.sub(
            r'^from pactkit\.skills\.analyzers[^\n]*\n',
            '',
            body,
            flags=re.MULTILINE,
        )
        # Strip relative imports from analyzer bodies (dev-time only, not needed in deployed script)
        stripped_bodies = []
        for ab in analyzer_bodies:
            ab = re.sub(
                r'^try:\n(?:\s+from \.[^\n]*\n)+except[^\n]*:\n\s*pass\n?',
                '',
                ab,
                flags=re.MULTILINE,
            )
            stripped_bodies.append(ab)
        # Prepend analyzer bodies before main body
        body = '\n'.join(stripped_bodies) + '\n' + body

    # Hoist `from __future__ import annotations` above _SHARED_HEADER
    future_line = 'from __future__ import annotations\n'
    prefix = ''
    if future_line in body:
        body = body.replace(future_line, '')
        prefix = future_line

    return prefix + _SHARED_HEADER + body
