"""Native, risk-driven engineering guides.

Each guide separates correctness boundaries from overridable defaults and
states when it does not apply. Guides are loaded only from concrete risk
evidence; they are never global workflow gates.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuideDefinition:
    title: str
    trigger: str
    questions: tuple[str, ...]
    safe_invariants: tuple[str, ...]
    defaults: tuple[str, ...]
    alternatives: tuple[str, ...]
    evidence: tuple[str, ...]
    non_applicable: tuple[str, ...]

    @property
    def hard_safety(self) -> tuple[str, ...]:
        """Compatibility alias for consumers of the 2.23 metadata API."""
        return self.safe_invariants

    def render(self) -> str:
        sections = (
            ("Trigger", (self.trigger,)),
            ("Questions", self.questions),
            ("Safe Invariants", self.safe_invariants),
            ("Defaults", self.defaults),
            ("Alternatives", self.alternatives),
            ("Evidence", self.evidence),
            ("Non-applicable", self.non_applicable),
        )
        blocks = [f"# {self.title} — Engineering Guide"]
        for heading, values in sections:
            blocks.append(
                f"## {heading}\n" + "\n".join(f"- {value}" for value in values)
            )
        return "\n\n".join(blocks) + "\n"


def _guide(
    title: str,
    trigger: str,
    questions: tuple[str, ...],
    safe_invariants: tuple[str, ...],
    defaults: tuple[str, ...],
    alternatives: tuple[str, ...],
    evidence: tuple[str, ...],
    non_applicable: tuple[str, ...],
) -> GuideDefinition:
    return GuideDefinition(
        title=title,
        trigger=trigger,
        questions=questions,
        safe_invariants=safe_invariants,
        defaults=defaults,
        alternatives=alternatives,
        evidence=evidence,
        non_applicable=non_applicable,
    )


GUIDE_DEFINITIONS = {
    "concurrency.md": _guide(
        "Concurrency", "Concurrent execution or shared mutable state is in scope.",
        ("Is work I/O-bound or CPU-bound?", "Who owns ordering and cancellation?"),
        ("Bound workers and queues.", "Synchronize shared mutable state and expose failures."),
        ("Reuse the project executor with configurable limits.",),
        ("Use sequential execution when load does not justify concurrency.",),
        ("Contention, ordering, cancellation, and shutdown tests.",),
        ("Single-threaded work with no shared state or parallel execution.",),
    ),
    "async-patterns.md": _guide(
        "Async Patterns", "An async boundary or event loop is changed.",
        ("Which calls can block?", "How are timeout and cancellation propagated?"),
        ("Do not block an event loop.", "Close resources on success, failure, and cancellation."),
        ("Keep a coherent async model and bound external waits.",),
        ("Use synchronous code when concurrency needs are small or dependencies are synchronous.",),
        ("Timeout, cancellation, cleanup, and concurrent-call tests.",),
        ("Pure synchronous code with no async callers or resources.",),
    ),
    "configuration.md": _guide(
        "Configuration", "Runtime configuration, environment values, or secrets change.",
        ("Which values vary by environment?", "What is required and what has a safe default?"),
        ("Never persist credentials in source or public artifacts.", "Validate untrusted configuration."),
        ("Use existing config layering and fail clearly for missing required values.",),
        ("Use a named code constant for a true invariant.",),
        ("Precedence, invalid-input, missing-value, and redaction tests.",),
        ("A local detail that cannot vary by deployment.",),
    ),
    "observability.md": _guide(
        "Observability", "A runtime path needs operational diagnosis or service-level signals.",
        ("Which failures must operators distinguish?", "Which identifiers safely correlate events?"),
        ("Do not log credentials or sensitive payloads.", "Telemetry must not fail the primary operation."),
        ("Reuse project logging and record structured outcomes and correlation fields.",),
        ("Metrics or traces may answer the operational question better than logs.",),
        ("Captured failure signals and sensitive-field redaction evidence.",),
        ("Pure library logic already observable through its caller.",),
    ),
    "module-design.md": _guide(
        "Module Design", "Responsibilities, boundaries, or public interfaces are added or moved.",
        ("Who owns this responsibility?", "Can callers use a smaller stable interface?"),
        ("Avoid circular ownership and parallel sources of truth.",),
        ("Follow an existing boundary and extract cohesive, independently testable behavior.",),
        ("Local duplication can be clearer than premature abstraction.",),
        ("Caller map, public-interface tests, and ownership rationale.",),
        ("A contained change inside an established boundary.",),
    ),
    "database.md": _guide(
        "Database", "Persistent database reads, writes, schema, or transactions change.",
        ("What consistency and isolation are required?", "What is the query and transaction cost?"),
        ("Parameterize untrusted values.", "Release connections and preserve atomicity on failure."),
        ("Reuse the project pool and keep transactions scoped to database work.",),
        ("Choose optimistic locking, atomic updates, or serialization from contention evidence.",),
        ("Query-plan or index evidence plus rollback, conflict, and failure tests.",),
        ("No persistent database interaction or schema impact.",),
    ),
    "caching.md": _guide(
        "Caching", "A cache is introduced or its lifecycle changes.",
        ("What is the source of truth?", "How are invalidation, bounds, and stale reads handled?"),
        ("A cache cannot be an undeclared source of truth.", "Bound memory growth."),
        ("Prefer cache-aside with explicit invalidation and measured usefulness.",),
        ("Use immutable keys, explicit versions, or no cache when safer than TTL.",),
        ("Hit/miss, invalidation, expiry, stampede, and capacity evidence.",),
        ("No repeated expensive read or measured latency need.",),
    ),
    "api-integration.md": _guide(
        "API Integration", "An external HTTP, RPC, webhook, or service contract changes.",
        ("What are timeout, retry, schema, and ownership boundaries?", "Is the operation idempotent?"),
        ("Validate untrusted responses.", "Do not retry non-idempotent actions without deduplication."),
        ("Reuse the project client with bounded timeout and typed validation.",),
        ("Fail fast, queue, cache, or degrade according to consistency needs.",),
        ("Contract, timeout, partial-response, retry, and duplicate-delivery tests.",),
        ("No call crosses a process or trust boundary.",),
    ),
    "event-driven.md": _guide(
        "Event-Driven", "Events, queues, subscribers, or at-least-once delivery are introduced.",
        ("What are delivery and ordering guarantees?", "How are duplicates handled?"),
        ("Make retried handlers safe and failed delivery observable.",),
        ("Use versioned schemas, stable event IDs, and bounded retry or dead-letter handling.",),
        ("Use a synchronous call when the caller requires the result immediately.",),
        ("Duplicate, ordering, schema-version, and dead-letter tests.",),
        ("No asynchronous message boundary or downstream fan-out.",),
    ),
    "resilience.md": _guide(
        "Resilience", "A remote dependency or overload-sensitive runtime path can fail.",
        ("Which failures are transient?", "What is the resource and latency budget?"),
        ("Bound waits, retries, queues, and resources.", "Do not hide permanent failure as success."),
        ("Use explicit timeout and limited retry for recoverable operations.",),
        ("Choose circuit breaking, bulkheads, backpressure, or immediate failure from evidence.",),
        ("Timeout, overload, dependency outage, and recovery tests.",),
        ("Pure in-process deterministic logic without resource contention.",),
    ),
    "memory-management.md": _guide(
        "Memory Management", "Data volume, lifetime, caching, streaming, or resource ownership changes.",
        ("What bounds allocation?", "Who releases long-lived references?"),
        ("Bound collections fed by untrusted input.", "Release owned resources on every path."),
        ("Stream unknown-size inputs and use context-managed resources.",),
        ("Materialize inputs when a verified small bound improves clarity.",),
        ("Peak-memory, large-input, cleanup, and repeated-operation evidence.",),
        ("Small fixed-size values with no retained resources.",),
    ),
    "code-review-first.md": _guide(
        "Code Review First", "The project contains nearby patterns or abstractions.",
        ("What is the closest maintained exemplar?", "Why does redundant-looking code exist?"),
        ("Do not bypass security or ownership abstractions without evidence.",),
        ("Follow project conventions and inspect history when intent is unclear.",),
        ("Introduce a new pattern when existing ones cannot meet a documented requirement.",),
        ("Exemplar, caller/history inspection, and capability-gap rationale.",),
        ("Greenfield code with no meaningful project precedent.",),
    ),
    "component-reuse.md": _guide(
        "Component Reuse", "A capability may exist in the project, framework, or ecosystem.",
        ("Can an existing public interface meet the need?", "What is the trust and maintenance cost?"),
        ("Do not implement cryptographic or authentication primitives ad hoc.",),
        ("Evaluate standard library, project abstraction, then framework capability.",),
        ("Prefer small local code over a dependency when behavior is well bounded.",),
        ("Capability comparison, reuse decision, and compatibility tests.",),
        ("The requirement is novel and no comparable capability exists.",),
    ),
    "error-recovery.md": _guide(
        "Error Recovery", "Partial failure, retry, resumability, or interrupted writes are possible.",
        ("Is failure transient?", "Can retry duplicate or corrupt the operation?"),
        ("Bound retries and preserve failure context.", "Do not silently discard partial failure."),
        ("Fail fast for permanent errors; retry idempotent transient errors with bounded backoff.",),
        ("Resume, compensate, quarantine, or manual recovery may fit better than retry.",),
        ("Interrupted-run, duplicate-attempt, terminal-error, and recovery tests.",),
        ("Atomic deterministic work with no recoverable intermediate state.",),
    ),
    "data-consistency.md": _guide(
        "Data Consistency", "One logical change spans records, stores, services, or concurrent writers.",
        ("What consistency level is required?", "What compensation or conflict policy applies?"),
        ("Do not claim unavailable atomicity.", "Protect against lost updates."),
        ("Use the smallest transaction boundary satisfying the invariant.",),
        ("Saga, outbox, optimistic concurrency, or eventual consistency require explicit trade-offs.",),
        ("Conflict, duplicate, compensation, and partial-commit tests.",),
        ("A single atomic write with no concurrent or distributed boundary.",),
    ),
    "backwards-compatibility.md": _guide(
        "Backwards Compatibility", "A public API, CLI, config, schema, protocol, or layout changes.",
        ("Which old callers or data must work?", "What are migration and rollback semantics?"),
        ("Do not execute irreversible high-risk migration without exact authorization.",),
        ("Add before remove, preserve declared aliases, and make migration idempotent.",),
        ("Use a versioned break or explicit rejection when compatibility is impossible.",),
        ("Legacy fixture, repeated upgrade, interrupted migration, and rollback evidence.",),
        ("Private implementation with no persisted or externally consumed shape.",),
    ),
    "performance-antipatterns.md": _guide(
        "Performance Antipatterns", "A hot path, large collection, query fan-out, or latency target changes.",
        ("What measured budget is at risk?", "Does work scale with input or caller count?"),
        ("Bound untrusted work and avoid unbounded query or allocation growth.",),
        ("Measure first; batch, paginate, or index the proven bottleneck.",),
        ("Prefer clear simple code when evidence shows no material risk.",),
        ("Representative benchmark, query count, complexity, or profile evidence.",),
        ("Cold or fixed-size path with no performance requirement.",),
    ),
    "graceful-shutdown.md": _guide(
        "Graceful Shutdown", "A service, worker, pool, or background task owns resources.",
        ("How are new and in-flight work sequenced?", "What is the shutdown deadline?"),
        ("Do not abandon durable state or leave owned resources running.",),
        ("Stop intake, drain within a bound, close dependencies, and expose timeout failure.",),
        ("Immediate termination can fit stateless disposable work.",),
        ("Signal, drain, timeout, forced-stop, and cleanup tests.",),
        ("Short-lived commands without background work or persistent resources.",),
    ),
    "testing-strategy.md": _guide(
        "Testing Strategy", "Behavior, regression coverage, or trust boundaries materially change.",
        ("Would the test fail if implementation were removed?", "Which boundary and failure paths matter?"),
        ("Tests cannot expose credentials or mutate uncontrolled external systems.",),
        ("Assert observable behavior and reproduce the defect before relying on mocks.",),
        ("Select unit, integration, contract, property, mutation, or E2E depth from risk.",),
        ("Behavior assertion, defect reproduction, boundary cases, and negative control.",),
        ("Generated or documentation-only change with deterministic structural validation.",),
    ),
    "operational-readiness.md": _guide(
        "Operational Readiness", "A service, scheduled task, worker, or rollout behavior changes.",
        ("How will operators detect failure?", "What rollout, capacity, and rollback signals exist?"),
        ("Do not expose sensitive diagnostics or report false readiness.",),
        ("Define health signals, failure visibility, capacity bounds, and rollback criteria.",),
        ("Use a flag, canary, shadow run, or manual rollback according to deployment risk.",),
        ("Isolated deploy, startup/shutdown, degraded dependency, and rollback evidence.",),
        ("Non-running library, docs, or build-time-only code.",),
    ),
    "dependency-supply-chain.md": _guide(
        "Dependency Supply Chain", "A dependency, package source, lockfile, or installer changes.",
        ("Is it necessary?", "What source, license, scripts, binaries, and permissions are introduced?"),
        ("Do not execute untrusted scripts or expand privileges without review.",),
        ("Pin reproducibly, retain integrity metadata, and prefer maintained minimal dependencies.",),
        ("Use the standard library, an existing dependency, vendoring, or bounded local code.",),
        ("Dependency diff, provenance, license, advisory, script, and clean-install evidence.",),
        ("No dependency graph, source, binary, installer, or permission change.",),
    ),
    "ui-state-accessibility.md": _guide(
        "UI State and Accessibility", "Interactive UI structure, state, or navigation changes.",
        (
            "What are loading, empty, error, disabled, and optimistic states?",
            "Can keyboard and assistive users complete the task?",
        ),
        ("Preserve keyboard access, visible focus, semantic labels, and error recovery.",),
        ("Use semantic controls, managed focus, labelled states, responsive overflow, and rollback.",),
        ("Use platform-native interactions instead of custom behavior when suitable.",),
        ("Keyboard, focus, label, contrast, state, and responsive tests.",),
        ("No user interface, rendered state, or interaction behavior changes.",),
    ),
}

GUIDES_FILES = {
    filename: definition.render()
    for filename, definition in GUIDE_DEFINITIONS.items()
}

GUIDES_DIR = "guides"
