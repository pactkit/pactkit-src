"""Frozen legacy engine package (STORY-slim-20260826cb37edfdd4da).

Contains the WorkUnit engine and host-continuation runner that simulate
completion-guarantee semantics on hosts without hooks. The default PDCA
execution path does not traverse this package; entry points are the
explicit `pactkit workflow` / `work-unit` / `continuation` subcommands.

FROZEN: no new features, bugfix-only. Deletion candidate — removal is
gated on one minor release cycle of zero explicit invocations recorded
by the local usage counter (see pactkit.legacy.usage).
"""
