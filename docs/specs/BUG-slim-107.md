# BUG-slim-107: Custom scan_excludes replaces defaults, leaking .next as modules

## Background
When a project's `pactkit.yaml` defines custom `visualize.scan_excludes`, it completely replaces the built-in `SCAN_EXCLUDES` set. Projects lose critical exclusions like `.next`, causing build artifacts to be detected as modules. Combined with the root module `.` being hidden from the "Available modules" error message, this misleads AI into concluding "visual scan not applicable to Python projects".

## Target
- `src/pactkit/skills/visualize.py:280` — merge custom excludes with defaults instead of replacing
- `src/pactkit/skills/visualize.py:1180` — include root module in available list with descriptive label

## Fix
1. `_detect_modules`: union custom scan_excludes with SCAN_EXCLUDES
2. Available modules list: show root module as `"." (project root)` instead of filtering it out
