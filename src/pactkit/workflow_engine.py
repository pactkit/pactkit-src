"""Compatibility alias: the engine lives in pactkit.legacy (FROZEN).

The sys.modules alias makes this path and pactkit.legacy.workflow_engine
the SAME module object, so existing imports and mock.patch targets keep
working unchanged (STORY-slim-20260826cb37edfdd4da R1).
"""

import sys

from pactkit.legacy import workflow_engine as _implementation

sys.modules[__name__] = _implementation
