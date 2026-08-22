# Lessons Archive (2026-04)

| Date | Lesson | Context |
|------|--------|---------|
| 2026-04-01 | Graduated safety language: retire MANDATORY keyword across prompts/commands.py, workflows.py, skills.py — use CRITICAL for safety gates (T1) and MUST for required steps (T2). Consistency prevents AI from treating all-caps keywords as equally urgent. | prompts/commands.py:MANDATORY→MUST/CRITICAL |
| 2026-04-01 | Multi-stack visualize: _detect_stack() returning single str masks Go/TS/Java files in mixed projects; _build_class_graph hardcoded ast.parse() silently skips non-Python via except. Fix: _detect_stacks() returns list, extract_classes() ABC on all 4 analyzers. | visualize.py:_detect_stacks,_build_class_graph |
