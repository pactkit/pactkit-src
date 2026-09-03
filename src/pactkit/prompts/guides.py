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
        practice="""

### Concurrency model decision table
| Workload | Model | Reason |
|----------|-------|--------|
| I/O-bound, many waits | asyncio / thread pool | Threads wait, not compute |
| CPU-bound | Process pool | GIL / single-core ceiling |
| Low volume, simple | Sequential | Concurrency is a bug multiplier, not a feature |

### Red lines
- Every queue and buffer is bounded with an explicit max — an unbounded queue is an OOM with a
  delay; when full, apply backpressure (reject/slow), never silently grow.
- Worker counts are configuration, never inline literals.
- Shared mutable state: pick ONE — message passing between tasks, a lock-protected structure,
  or immutable data copies. Ad-hoc mixes are where races live.
""",
    ),
    "async-patterns.md": _guide(
        "Async Patterns", "An async boundary or event loop is changed.",
        ("Which calls can block?", "How are timeout and cancellation propagated?"),
        ("Do not block an event loop.", "Close resources on success, failure, and cancellation."),
        ("Keep a coherent async model and bound external waits.",),
        ("Use synchronous code when concurrency needs are small or dependencies are synchronous.",),
        ("Timeout, cancellation, cleanup, and concurrent-call tests.",),
        ("Pure synchronous code with no async callers or resources.",),
        practice="""

### Blocking-call identification table
| In event loop | Blocks? | Replace with |
|---------------|---------|--------------|
| Sync HTTP / file I/O / sleep / CPU loop / slow regex | YES — everything | Async variant, or executor |

- One blocking call negates the entire async model — there is no "mostly async".

### Cancellation and timeout layering
- Child tasks must observe cancellation: wrap awaits in try/CancelledError and release resources
  in finally — a task that ignores cancel leaks its connection.
- Timeouts are layered and named: connect timeout ≠ read timeout ≠ overall deadline; each has a
  different failure meaning (server down vs slow response vs stuck pipeline).
""",
    ),
    "configuration.md": _guide(
        "Configuration", "Runtime configuration, environment values, or secrets change.",
        ("Which values vary by environment?", "What is required and what has a safe default?"),
        ("Never persist credentials in source or public artifacts.", "Validate untrusted configuration."),
        ("Use existing config layering and fail clearly for missing required values.",),
        ("Use a named code constant for a true invariant.",),
        ("Precedence, invalid-input, missing-value, and redaction tests.",),
        ("A local detail that cannot vary by deployment.",),
        practice="""

### Configuration layering — where a value belongs
| Value type | Home | Example |
|-----------|------|---------|
| True invariant | Named code constant | Buffer sizes of a protocol |
| Varies by environment | Config file / env var | DB URL, feature flags |
| Secret | Env-injected, never in files or VCS | API keys |
| Per-request | Function parameter | Tenant, user context |

### Red lines
- Startup validates configuration and fails fast (fail-fast) with a named field — a missing value detected
  at first use is a production incident with a deploy-time prevention.
- Secrets: env-injected; NEVER written into files, logs, or error messages — and the logging
  entry point redacts them regardless (see observability guide).
""",
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
        practice="""

### Migration safety — expansion/contraction, three reversible steps
- Add column (nullable/defaulted) → backfill in batches → dual-read/dual-write → drop old ONLY
  after a full release cycle verified the new path. Each step independently reversible.
- NEVER combine schema change and data rewrite in one migration — one failing step must be
  rollable-back alone.

### Transaction boundaries
- Keep transactions short; NEVER call external services (HTTP, queues, filesystem) inside a
  transaction — the connection is held, locks pile up, and the external call has no rollback.
- Index discipline: index for the queries you actually run (measure first); composite index
  follows leftmost-prefix — a query not hitting the prefix does not use the index; every index
  taxes every write.
""",
    ),
    "caching.md": _guide(
        "Caching", "A cache is introduced or its lifecycle changes.",
        ("What is the source of truth?", "How are invalidation, bounds, and stale reads handled?"),
        ("A cache cannot be an undeclared source of truth.", "Bound memory growth."),
        ("Prefer cache-aside with explicit invalidation and measured usefulness.",),
        ("Use immutable keys, explicit versions, or no cache when safer than TTL.",),
        ("Hit/miss, invalidation, expiry, stampede, and capacity evidence.",),
        ("No repeated expensive read or measured latency need.",),
        practice="""

### Cache decision table
| Situation | Cache? |
|-----------|--------|
| Read-heavy, stale-tolerant | Yes — TTL slightly beyond consistency tolerance |
| Read-heavy, must-be-fresh | Cache only with active invalidation, not TTL |
| Write-heavy or read-once | No — cache is pure cost (memory + invalidation bugs) |

### Invalidation strategy
- Write-through when the writer owns the truth; cache-aside when readers vary; event-driven
  invalidation when writers and readers are separate services. TTL is the safety net, never the plan.

### Three classic failures (each with mitigation)
- Stampede (hot key expires, all callers hit origin) — lock/single-flight or jittered TTL.
- Penetration (queries for absent keys bypass cache) — cache negative results briefly.
- Avalanche (many keys expire together) — jittered TTL; never identical TTLs across a batch.
""",
    ),
    "api-integration.md": _guide(
        "API Integration", "An external HTTP, RPC, webhook, or service contract changes.",
        ("What are timeout, retry, schema, and ownership boundaries?", "Is the operation idempotent?"),
        ("Validate untrusted responses.", "Do not retry non-idempotent actions without deduplication."),
        ("Reuse the project client with bounded timeout and typed validation.",),
        ("Fail fast, queue, cache, or degrade according to consistency needs.",),
        ("Contract, timeout, partial-response, retry, and duplicate-delivery tests.",),
        ("No call crosses a process or trust boundary.",),
        practice="""

### Server-side API design
| Concern | Rule |
|---------|------|
| Pagination | Cursor (`?after=...&limit=...`) over offset — offset degrades with depth and breaks under inserts |
| Idempotency | Mutating endpoints take a client idempotency key; a retried POST returns the first result |
| Error format | Stable error code + message + trace id — the code is the contract |
| Versioning | Path version (/v1/); a new version coexists through a full deprecation window |

- Offset pagination is acceptable only for small fixed admin lists; error messages are advisory,
  internal class names and stack traces NEVER appear in responses.
""",
    ),
    "event-driven.md": _guide(
        "Event-Driven", "Events, queues, subscribers, or at-least-once delivery are introduced.",
        ("What are delivery and ordering guarantees?", "How are duplicates handled?"),
        ("Make retried handlers safe and failed delivery observable.",),
        ("Use versioned schemas, stable event IDs, and bounded retry or dead-letter handling.",),
        ("Use a synchronous call when the caller requires the result immediately.",),
        ("Duplicate, ordering, schema-version, and dead-letter tests.",),
        ("No asynchronous message boundary or downstream fan-out.",),
        practice="""

### Delivery semantics — the cost table
| Semantics | Cost | Use when |
|-----------|------|----------|
| At-most-once | Fire and forget, may drop | Loss tolerable (metrics, cache invalidation hints) |
| At-least-once | Retry until ack; consumers MUST be idempotent | Default for most business events |
| Exactly-once | Very expensive (txn/dedup infra) | Almost never — build it as at-least-once + idempotent consumer |

### Consumer discipline
- Consumers dedupe by event id (persisted seen-set or idempotent state transition) — the broker
  WILL redeliver; an unguarded consumer double-executes.
- Dead-letter queue: messages that fail N times (poison, schema drift) go to DLQ — never dropped
  silently; DLQ must have an owner, an alert, and a replay path tested end-to-end.
""",
    ),
    "resilience.md": _guide(
        "Resilience", "A remote dependency or overload-sensitive runtime path can fail.",
        ("Which failures are transient?", "What is the resource and latency budget?"),
        ("Bound waits, retries, queues, and resources.", "Do not hide permanent failure as success."),
        ("Use explicit timeout and limited retry for recoverable operations.",),
        ("Choose circuit breaking, bulkheads, backpressure, or immediate failure from evidence.",),
        ("Timeout, overload, dependency outage, and recovery tests.",),
        ("Pure in-process deterministic logic without resource contention.",),
        practice="""

### Circuit breaker state machine
| State | Meaning | Transition |
|-------|---------|-----------|
| Closed | Calls flow normally | N consecutive failures → Open (N from data, not vibes) |
| Open | Calls fail fast without touching the dependency | Cooldown elapses → Half-open |
| Half-open | A few probe calls through | Probes succeed → Closed; any fail → Open |

### Bulkhead and degradation
- Bulkhead: resource pools (connections, workers) are per-dependency — one slow dependency
  exhausts only its own pool, never the shared one.
- Degradation paths (fallbacks, cached answers, feature shutdown) are REAL code paths — they
  carry the same tests as the happy path; an untested fallback is a second outage waiting.
""",
    ),
    "memory-management.md": _guide(
        "Memory Management", "Data volume, lifetime, caching, streaming, or resource ownership changes.",
        ("What bounds allocation?", "Who releases long-lived references?"),
        ("Bound collections fed by untrusted input.", "Release owned resources on every path."),
        ("Stream unknown-size inputs and use context-managed resources.",),
        ("Materialize inputs when a verified small bound improves clarity.",),
        ("Peak-memory, large-input, cleanup, and repeated-operation evidence.",),
        ("Small fixed-size values with no retained resources.",),
        practice="""

### Python-specific practices
- Prefer generators over intermediate lists (`(f(x) for x in items)`); __slots__ for many
  small instances of the same class; weakref to break reference cycles in caches/parents.

### Red lines
- Any in-memory cache/dict/LRU MUST have a max size + eviction — an unbounded collection grows
  until the process dies; the max is a named constant.
- Streaming for large files (chunked read/write) — never read a file of unknown size into memory
  at once; the unknown-size file is exactly the one that will be huge.
""",
    ),
    "code-review-first.md": _guide(
        "Code Review First", "The project contains nearby patterns or abstractions.",
        ("What is the closest maintained exemplar?", "Why does redundant-looking code exist?"),
        ("Do not bypass security or ownership abstractions without evidence.",),
        ("Follow project conventions and inspect history when intent is unclear.",),
        ("Introduce a new pattern when existing ones cannot meet a documented requirement.",),
        ("Exemplar, caller/history inspection, and capability-gap rationale.",),
        ("Greenfield code with no meaningful project precedent.",),
        practice="""

### Layered review checklist
| Layer | Ask |
|-------|-----|
| Correctness | Does it do what the change says? Edge/boundary/error cases covered? |
| Security | Input validated at boundary? Auth on new endpoints? Secrets in logs? |
| Maintainability | Naming says what/why? Duplication vs the existing pattern? |
| Tests | New behavior has a failing-first test? Regression linked? |

### Review conduct
- Every review comment must justify itself — a reason or a concrete suggestion; bare "change
  this" forces the author to guess; disagreements are settled by argument, not authority.
- Self-review before requesting review: re-read your own diff line-by-line first — you catch the
  mechanical issues so reviewers spend attention on design, not typos.
""",
    ),
    "component-reuse.md": _guide(
        "Component Reuse", "A capability may exist in the project, framework, or ecosystem.",
        ("Can an existing public interface meet the need?", "What is the trust and maintenance cost?"),
        ("Do not implement cryptographic or authentication primitives ad hoc.",),
        ("Evaluate standard library, project abstraction, then framework capability.",),
        ("Prefer small local code over a dependency when behavior is well bounded.",),
        ("Capability comparison, reuse decision, and compatibility tests.",),
        ("The requirement is novel and no comparable capability exists.",),
        practice="""

### Lookup decision tree (run BEFORE writing new code)
1. stdlib (standard library)? → use it (no new dependency, always maintained).
2. Project already wraps this? → use the wrapper, NEVER bypass to the underlying library.
3. Mature third-party already in deps? → read its docs, use the documented API.
4. None of the above → write new code (and name why in the Spec).

### Wrapper judgment
- Wrap when: call sites need project conventions (auth, retries, metrics) or the API may swap
  underneath. Do not wrap: thin pass-throughs that only re-name methods — indirection without
  behavior is a maintenance tax.
- Reuse checkpoint: grep twice for the operation name before writing a new implementation —
  once by name, once by what it does; the second grep catches different-named duplicates.
""",
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
        practice="""

### Consistency level decision table
| Level | Cost | Use when |
|-------|------|----------|
| Strong (single txn) | Cheapest where reachable | Data lives in one store — default |
| Causal | Versioning/sequence numbers | Order between related writes matters |
| Eventual | Compensations, reconciliation jobs | Cross-store, cross-service — accept the window |

### Cross-service sagas
- Every compensating action must be designed BEFORE the forward action ships — a step whose
  failure cannot be undone converts a rollback into a manual incident.
- Optimistic lock (version column) for low-contention updates; distributed lock only for
  genuinely exclusive long operations — it trades availability for correctness.
- Reconciliation job as the backstop: scheduled diff-check between stores; every saga can leak.
""",
    ),
    "backwards-compatibility.md": _guide(
        "Backwards Compatibility", "A public API, CLI, config, schema, protocol, or layout changes.",
        ("Which old callers or data must work?", "What are migration and rollback semantics?"),
        ("Do not execute irreversible high-risk migration without exact authorization.",),
        ("Add before remove, preserve declared aliases, and make migration idempotent.",),
        ("Use a versioned break or explicit rejection when compatibility is impossible.",),
        ("Legacy fixture, repeated upgrade, interrupted migration, and rollback evidence.",),
        ("Private implementation with no persisted or externally consumed shape.",),
        practice="""

### Compatibility decision table
| Change | Compatible strategy |
|--------|--------------------|
| Add field | Safe — old readers ignore; never make new fields required |
| Remove field | Deprecate first: dual-write period → deprecation warning → removal (each step a release) |
| Rename field | Never rename — add the new name, dual-write, then deprecate the old |
| Change enum value meaning | Never — add a new value instead; enum values are append-only contracts |

### Serialization red lines
- Enum/constant values are contracts: append-only; reusing a retired value for a new meaning
  corrupts every stored record that ever used it.
- Protobuf/AVRO: field numbers/tags are immutable once released — renumbering is silent data
  corruption for old readers.
- Dual-write period MUST log both old and new paths so migration completeness is measurable.
""",
    ),
    "performance-antipatterns.md": _guide(
        "Performance Antipatterns", "A hot path, large collection, query fan-out, or latency target changes.",
        ("What measured budget is at risk?", "Does work scale with input or caller count?"),
        ("Bound untrusted work and avoid unbounded query or allocation growth.",),
        ("Measure first; batch, paginate, or index the proven bottleneck.",),
        ("Prefer clear simple code when evidence shows no material risk.",),
        ("Representative benchmark, query count, complexity, or profile evidence.",),
        ("Cold or fixed-size path with no performance requirement.",),
        practice="""

### Measure before optimizing
| Rule | Consequence when broken |
|------|------------------------|
| No profile data → no optimization | "Feels slow" is a guess shipped as complexity |
| Optimize the measured hotspot only | Micro-optimizing cold code = cost with zero gain |
| Record baseline / change / delta | Unmeasured "improvements" cannot be verified |

### N+1 identification and fix
- Signature: query count grows with row count (loop body issues one query per item). Fix by
  batching (WHERE id IN (...), select_related/joins, or one aggregate) — query count becomes
  constant regardless of rows.

### Premature optimization discriminator
- Optimizing without a measured hotspot = guessing; complexity added before evidence is debt
  that must still be paid back when the real hotspot turns out to be elsewhere.
""",
    ),
    "graceful-shutdown.md": _guide(
        "Graceful Shutdown", "A service, worker, pool, or background task owns resources.",
        ("How are new and in-flight work sequenced?", "What is the shutdown deadline?"),
        ("Do not abandon durable state or leave owned resources running.",),
        ("Stop intake, drain within a bound, close dependencies, and expose timeout failure.",),
        ("Immediate termination can fit stateless disposable work.",),
        ("Signal, drain, timeout, forced-stop, and cleanup tests.",),
        ("Short-lived commands without background work or persistent resources.",),
        practice="""

### Signal and exit semantics
- SIGTERM means "finish current work, then exit cleanly" (orchestrators send it before SIGKILL);
  the forced-kill timeout (e.g. 30s) is the hard budget — everything below must fit inside it.

### Drain order (each step bounded)
- Stop accepting new work (close listeners/mark unhealthy) → drain in-flight queue items
  (bounded time; log what is abandoned) → close client connections → flush buffers/fsync →
  exit with a meaningful code (0 clean, non-zero partial).
- NEVER skip marking unhealthy first — a "healthy" server being drained keeps receiving work
  that will be killed mid-flight.
""",
    ),
    "testing-strategy.md": _guide(
        "Testing Strategy", "Behavior, regression coverage, or trust boundaries materially change.",
        ("Would the test fail if implementation were removed?", "Which boundary and failure paths matter?"),
        ("Tests cannot expose credentials or mutate uncontrolled external systems.",),
        ("Assert observable behavior and reproduce the defect before relying on mocks.",),
        ("Select unit, integration, contract, property, mutation, or E2E depth from risk.",),
        ("Behavior assertion, defect reproduction, boundary cases, and negative control.",),
        ("Generated or documentation-only change with deterministic structural validation.",),
        practice="""

### Test pyramid ratio
| Layer | Target share | Runtime ceiling | Purpose |
|-------|-------------|----------------|---------|
| Unit | ~70% | seconds total | Logic correctness, fast failure location |
| Integration | ~25% | tens of seconds | Boundaries, contracts, real dependencies (test doubles for externals) |
| E2E | ~5% | minutes | One golden-path per user journey, NOT business logic |

### Test data and flaky policy
- Test factory functions over shared fixtures: each test builds its own data and cleans up; a shared mutable
  fixture makes tests order-dependent — the failure appears only in CI's shuffled order.
- A flaky test is NOT passing: quarantine immediately (skip marker with ticket) → fix or delete
  within a bounded window; a tolerated flaky test trains everyone to rerun-on-red, which hides real regressions.
- Coverage is a floor, not a goal: line coverage never proves assertion quality — an empty
  assert inflates it; review what is asserted, not what is executed.
""",
    ),
    "operational-readiness.md": _guide(
        "Operational Readiness", "A service, scheduled task, worker, or rollout behavior changes.",
        ("How will operators detect failure?", "What rollout, capacity, and rollback signals exist?"),
        ("Do not expose sensitive diagnostics or report false readiness.",),
        ("Define health signals, failure visibility, capacity bounds, and rollback criteria.",),
        ("Use a flag, canary, shadow run, or manual rollback according to deployment risk.",),
        ("Isolated deploy, startup/shutdown, degraded dependency, and rollback evidence.",),
        ("Non-running library, docs, or build-time-only code.",),
        practice="""

### Health check semantics
| Probe | Question | Failing means |
|-------|----------|---------------|
| Liveness | Is the process wedged? | Restart it |
| Readiness | Can this instance serve traffic NOW? | Remove from load balancer, do NOT restart |

- Probes must be cheap and dependency-light: a liveness probe that checks the database restarts
  every instance when the database blips — turning a partial outage into a full one.

### Release checklist
- Rollback trigger conditions and steps are written BEFORE deploy (what metric, what threshold,
  which command) — during the incident is too late to design the rollback.
- Startup logs the effective configuration (redacted) and resource limits — capacity issues are
  diagnosed from the start record, not from memory of what was deployed.
""",
    ),
    "dependency-supply-chain.md": _guide(
        "Dependency Supply Chain", "A dependency, package source, lockfile, or installer changes.",
        ("Is it necessary?", "What source, license, scripts, binaries, and permissions are introduced?"),
        ("Do not execute untrusted scripts or expand privileges without review.",),
        ("Pin reproducibly, retain integrity metadata, and prefer maintained minimal dependencies.",),
        ("Use the standard library, an existing dependency, vendoring, or bounded local code.",),
        ("Dependency diff, provenance, license, advisory, script, and clean-install evidence.",),
        ("No dependency graph, source, binary, installer, or permission change.",),
        practice="""

### Admission criteria — before adding a dependency
| Check | Bar |
|-------|-----|
| Necessity | No stdlib/project-existing option does the job (grep first) |
| Maintenance | Recent releases, issues answered; abandoned = inherited security debt |
| License | Compatible with the project's license obligations |
| Transitive surface | Dependency count is the real cost — 1 dep + 40 transitive deps |

### Lock discipline
- Lockfile committed; application pins exact versions (ranges are for libraries, not apps).
- Minimal replacement order: stdlib → already-present dependency → new dependency — each step
  up adds audit surface forever.
""",
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
        practice="""

### Five-state completeness (check ALL for every async surface)
| State | Every surface has... |
|-------|---------------------|
| Loading | Skeleton/spinner that does not jump on arrival |
| Empty | Guidance ("no results — adjust filters"), not a blank void |
| Error | Retry action + human message, not a raw error dump |
| Disabled | A reason (tooltip/label), never mystery grey |
| Optimistic | Rollback UI on failure — the reverted item must not look stuck |

### Focus and contrast red lines
- Modals trap focus and RETURN it to the trigger on close; keyboard users must complete every
  flow the mouse can (tab order = visual order).
- NEVER hide interactive elements with pointer-events:none alone (invisible to assistive tech);
  text contrast meets WCAG AA (4.5:1 body) — decorative gray-on-gray fails real users.
""",
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
        practice="""

### Pre-write decision table (run before ANY overwrite of an existing file)
| Situation | Action |
|-----------|--------|
| File does not exist | Fresh write is safe |
| I generated 100% of its current content | Full replace allowed |
| Manifest proves ownership | Update flows normally |
| Mixed or unknown ownership | Incremental merge, or `.new` candidate + human accept |
| "Does this file contain content I did not generate?" = not sure | That IS "merge" |

### Failure evidence (why this exists)
- BUG-010 / BUG-slim-089 / 2026-08-13 codex config wipes: full-replace on mixed-ownership files
  destroyed user content — every one was a "the file had things I didn't generate" case.
""",
    ),
}

GUIDES_FILES = {
    filename: definition.render()
    for filename, definition in GUIDE_DEFINITIONS.items()
}

GUIDES_DIR = "guides"
