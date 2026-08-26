"""Compatibility alias: the runner lives in pactkit.legacy (FROZEN).

The sys.modules alias keeps existing imports and mock.patch targets
working unchanged (STORY-slim-20260826cb37edfdd4da R1).
"""

import sys

from pactkit.legacy import host_continuation as _implementation

sys.modules[__name__] = _implementation
