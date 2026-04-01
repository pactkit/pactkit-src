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


def load_script(name):
    """Load a script file, strip standalone header, prepend _SHARED_HEADER.

    If the body contains ``from __future__ import annotations``, it is hoisted
    above _SHARED_HEADER (Python requires __future__ imports to be first).
    """
    content = (_SCRIPTS_DIR / name).read_text(encoding='utf-8')
    idx = content.find(_BODY_MARKER)
    if idx >= 0:
        newline_idx = content.index('\n', idx)
        body = content[newline_idx + 1:]
    else:
        body = content

    # Hoist `from __future__ import annotations` above _SHARED_HEADER
    future_line = 'from __future__ import annotations\n'
    prefix = ''
    if future_line in body:
        body = body.replace(future_line, '')
        prefix = future_line

    return prefix + _SHARED_HEADER + body
