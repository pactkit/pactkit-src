"""Canonical, stateless methods shared by every PactKit host package."""

from __future__ import annotations

from dataclasses import dataclass

METHOD_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PortableMethod:
    name: str
    version: int
    description: str
    instructions: str


PORTABLE_METHODS = (
    PortableMethod(
        "pactkit-method-clarify", 1, "Clarify requirements without owning workflow state.",
        "Identify material ambiguities, ask bounded questions, and return confirmed decisions. "
        "Do not own persistent run state or decide that the overall process is complete.",
    ),
    PortableMethod(
        "pactkit-method-architecture-trace", 1, "Trace architecture and affected interfaces.",
        "Use the available static-analysis capability, report its provenance and fallback, and "
        "return a bounded call-chain summary. Do not select the next process step.",
    ),
    PortableMethod(
        "pactkit-method-spec-writing", 1, "Write one structurally valid Spec section.",
        "Write only the files authorized by the current request. Preserve requirements, use "
        "Given/When/Then acceptance criteria, and report the resulting file references.",
    ),
    PortableMethod(
        "pactkit-method-tdd", 1, "Apply a local red-green-refactor loop.",
        "Create a failing test before source changes, run only the scoped test until green, and "
        "return command/result references. Do not infer workflow completion from test output.",
    ),
    PortableMethod(
        "pactkit-method-verification", 1, "Verify deterministic acceptance evidence.",
        "Run the acceptance commands applicable to the current task, report exact exit codes "
        "and artifact references, "
        "and treat all natural-language success claims as untrusted.",
    ),
    PortableMethod(
        "pactkit-method-release-preparation", 1, "Prepare a release without publishing it.",
        "Collect version, changelog, regression and authorization evidence. Never tag, push, or "
        "publish without fresh authorization in the current conversation.",
    ),
)


def get_portable_methods() -> list[dict]:
    """Return the single canonical content source consumed by thin adapters."""
    return [
        {
            "name": method.name,
            "method_schema_version": METHOD_SCHEMA_VERSION,
            "version": method.version,
            "description": method.description,
            "skill_md": (
                "---\n"
                f"name: {method.name}\n"
                f'description: "{method.description}"\n'
                "---\n\n"
                f"# {method.name}\n\n{method.instructions}\n"
            ),
            "script_name": None,
        }
        for method in PORTABLE_METHODS
    ]
