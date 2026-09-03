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
    # STORY-slim-20260903b5ce6be5f7e0 / ADR-0002: optional operational
    # reference block — verbatim markdown (tables allowed), rendered between
    # Defaults and Alternatives. Empty for un-enriched guides.
    practice: str = ""

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
        )
        blocks = [f"# {self.title} — Engineering Guide"]
        for heading, values in sections:
            blocks.append(
                f"## {heading}\n" + "\n".join(f"- {value}" for value in values)
            )
        if self.practice:
            blocks.append(f"## Practice\n{self.practice.strip()}")
        tail = (
            ("Alternatives", self.alternatives),
            ("Evidence", self.evidence),
            ("Non-applicable", self.non_applicable),
        )
        for heading, values in tail:
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
    *,
    practice: str = "",
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
        practice=practice,
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
        practice="""
### Log level criteria — decide before writing the call
| Level | Use for | NEVER for |
|-------|---------|-----------|
| ERROR | Failures needing human intervention (data loss, dependency down) | Transient errors that auto-retry |
| WARN  | Auto-recovered but worth a trace (retry succeeded, fallback engaged) | Normal-path branches |
| INFO  | State transitions (service start/stop, job begin/end, config loaded) | Per-item output inside loops |
| DEBUG | Local diagnostic detail, off by default | Anything production-on |

### Structured field conventions
- Every log line carries a correlation field (request_id / trace_id / run_id — whichever the
  project already uses) so one user action can be followed across processes and tasks.
- Events start with `event=<verb_past>` (`event=deploy_started`, `event=retry_exhausted`);
  field names are snake_case; data goes into fields, not into the message string.

### Volume red lines
- No per-item INFO-or-above inside loops — batch operations log one summary line
  ("processed 800 files, 3 failed"), not 800 lines.
- Sensitive-field redaction (password/token/authorization/cookie/api-key) happens once at the
  logging entry point, not self-checked at every call site — a missed call site is a leak.

### Anti-patterns (each with its consequence)
- log-and-rethrow — logged, re-raised, logged again upstream: one error, 3 records, polluted counts.
- Log level as flow control (`grep ERROR` decides success) — breaks the day a level is corrected.
- Logging full request/response bodies — PII and credentials enter logs; aggregation becomes a breach surface.
""",
    ),
    "module-design.md": _guide(
        "Module Design", "Responsibilities, boundaries, or public interfaces are added or moved.",
        ("Who owns this responsibility?", "Can callers use a smaller stable interface?"),
        ("Avoid circular ownership and parallel sources of truth.",),
        ("Follow an existing boundary and extract cohesive, independently testable behavior.",),
        ("Local duplication can be clearer than premature abstraction.",),
        ("Caller map, public-interface tests, and ownership rationale.",),
        ("A contained change inside an established boundary.",),
        practice="""
### Splitting criteria — when a module must be split
- Single-sentence responsibility test: if you cannot state the module's job in one sentence
  without "and", it is doing two jobs — split it.
- Public interface surface: a module callers must import 10+ names from to do one task is a
  boundary in name only; the real boundary is elsewhere.
- Line reference: 500 lines = evaluate for splitting; 1000 = split before the next feature.
  Reference lines, not hard walls — cohesion beats size.
- File ownership: if two halves of a file change in disjoint stories, they want to be two files.

### Layering rules
- Dependency direction is one-way: domain/core imports nothing from infrastructure;
  infrastructure imports from domain. A domain module importing an infra module is a
  layering violation even if it "works".
- Circular imports are always a layering violation — fix the structure (extract the shared
  concept downward), never the symptom (deferred import inside a function).

### Extract vs premature abstraction
- Extract when 2+ real callers need the same behavior AND agree on the shape; duplication
  observed once is cheaper than a wrong abstraction.
- Do NOT extract same-looking code with different change-velocity — they must stay separate.

### Naming
- Name modules by responsibility (user_access, not user_utils); the word "utils" means the
  boundary was not found yet.
""",
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
        practice="""
### Error taxonomy — classify before handling
| Class | Definition | Handling |
|-------|-----------|----------|
| Transient | May succeed on retry (network blip, throttle, lock timeout) | Bounded retry with backoff |
| Permanent | Fails identically forever (404, invalid input, quota out) | Fail fast — retry burns quota |
| Programming | Bug in our code (TypeError, broken invariant) | Fix the code, not the symptom |

Decision: succeeds 1 min later? → transient. No input helps? → permanent. Impossible for correct code? → programming.

### User-facing vs log-facing — same error, two faces
- User-facing: what happened in their terms + what to do next ("Upload failed — file exceeds
  10MB, compress it"). Never a stack trace or internal class name.
- Log record: full diagnostic detail (exception type, correlation id, input fingerprint).
- One message for both fails both — users cannot act on stack traces, operators cannot diagnose vagueness.

### Retry boundaries
- Bounded backoff, parameterized (named constants/config, never inline literals); jitter under contention.
- Every retried operation MUST be idempotent or carry an idempotency key — a double-charging
  retry turns a transient failure into permanent data corruption.
- Retry at ONE layer only (the external boundary); nested retries multiply (3×3 = 27).

### Error type hierarchy
- Subclass by RECOVERY STRATEGY (RetryableError / TerminalError), not by origin (HttpError /
  DbError) — callers branch on "what to do", not "where from".
""",
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
    # STORY-slim-2026090333d6b72f7645: restored (condensed) from the
    # architecture-principles layer deleted in the 2.24 capsule rewrite —
    # the direct countermeasure for BUG-010 / BUG-slim-089 / the
    # 2026-08-13 codex config wipe.
    "write-safety.md": _guide(
        "Write Safety — Merge over Replace",
        "Writing to a file that already exists and may contain content the writer did not"
        " generate (configs, user tool files, managed sections).",
        (
            "Who owns each section of this file — the writer, the user, or another tool?",
            "Litmus test: does this file contain content I did not generate?",
        ),
        (
            "MUST NOT fully replace a file with mixed ownership — full replacement silently"
            " destroys content the writer did not generate.",
            "One authoritative location per truth; every duplicate drifts (no dual-write)",
        ),
        (
            "Generator owns 100% of the file → full replace is safe; mixed ownership →"
            " incremental merge (Edit/patch/append, or only the writer-owned section);"
            " unsure → merge",
        ),
        (
            "Write a candidate (.new) and let the human accept — the deployer's"
            " ownership-manifest pattern",
        ),
        (
            "A merge-or-replace decision recorded for each pre-existing file written, and"
            " zero full replaces on mixed-ownership files",
        ),
        ("Files created fresh by this change — no prior content to destroy.",),
    ),
}

GUIDES_FILES = {
    filename: definition.render()
    for filename, definition in GUIDE_DEFINITIONS.items()
}

GUIDES_DIR = "guides"
