"""Engineering Concern Guides — on-demand loaded by Act Phase 1.5.

Each guide is < 50 lines, format: Decision Table + MUST + NEVER + Template.
Deployed to ~/.claude/skills/_rules/guides/ by deployer._deploy_guides().
"""

GUIDES_FILES = {
    "concurrency.md": """\
# Concurrency — Implementation Guide

## Decision Table
| Scenario | Choice | Reason |
|----------|--------|--------|
| I/O-bound batch (network, file) | asyncio / ThreadPoolExecutor | Release CPU while waiting |
| CPU-bound (image, crypto, ML) | ProcessPoolExecutor / multiprocessing | Bypass GIL |
| Mixed I/O + CPU | async + ProcessPoolExecutor | async for I/O, process for compute |
| Shared mutable state required | threading + Lock | IPC overhead too high |
| Crash isolation needed | multiprocessing | Child crash won't kill parent |

## MUST
- Pool size MUST be configurable (not hardcoded)
- Shared mutable state MUST have explicit synchronization (Lock/Queue)
- All pools MUST support graceful shutdown (signal handling + join with timeout)
- Thread/process count MUST have an upper bound

## NEVER
- NEVER create unbounded threads/processes in a loop
- NEVER use threading for CPU-bound work in Python (GIL)
- NEVER share mutable state without synchronization

## Template
```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=config.POOL_SIZE) as pool:
    results = list(pool.map(process_item, items))
```
""",

    "async-patterns.md": """\
# Async Patterns — Implementation Guide

## Decision Table
| Scenario | Choice |
|----------|--------|
| Web server (FastAPI, aiohttp) | async mandatory |
| Many concurrent I/O (100+ parallel requests) | async preferred |
| Simple script, few I/O calls | sync — simpler |
| All dependencies are sync-only | sync — avoid run_in_executor everywhere |

## MUST
- Blocking calls in async context MUST use `loop.run_in_executor()`
- All async resources MUST use `async with` (connections, files, locks)
- Every awaitable MUST have timeout (`asyncio.wait_for(coro, timeout=)`)
- Choose sync or async at project start — MUST NOT mix architectures

## NEVER
- NEVER call `requests.*`, `time.sleep()`, sync file I/O inside async functions
- NEVER forget to `await` a coroutine (silent no-op)
- NEVER use `asyncio.run()` inside an already-running event loop

## Template
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await asyncio.wait_for(
        client.get(url), timeout=15.0
    )
```
""",

    "configuration.md": """\
# Configuration — Implementation Guide

## Layering (highest priority first)
1. Environment variables (12-factor)
2. Command-line arguments
3. Environment-specific config file (config.prod.yaml)
4. Default config file (config.default.yaml)
5. Code constants (named, with semantic meaning)

## MUST
- Values that differ across environments MUST be config, not code
- Every magic number MUST have a named constant with semantic name
- Secrets (API keys, passwords) MUST use env vars or secret manager, NEVER in config files
- Config loading MUST fail fast on missing required values (not silently use None)

## NEVER
- NEVER hardcode IP addresses, ports, or URLs in source code
- NEVER commit secrets to version control
- NEVER use bare literals (30, 8080, "localhost") without naming

## Classification
| Type | Where | Example |
|------|-------|---------|
| Secret | env var / Vault | API_KEY, DB_PASSWORD |
| Environment-specific | config file | DB_HOST, LOG_LEVEL |
| Tuning parameter | config with default | POOL_SIZE, TIMEOUT_SEC |
| True constant | code constant | HTTP_OK = 200, PI = 3.14159 |
""",

    "observability.md": """\
# Observability — Implementation Guide

## Three Pillars
| Pillar | Tool | Purpose |
|--------|------|---------|
| Logs | structlog / loguru | Discrete events ("what happened") |
| Metrics | prometheus / statsd | Aggregates ("how many, how fast") |
| Traces | OpenTelemetry | Request flow ("which path, where slow") |

## MUST
- Use structured logging library (NOT print)
- Each module: `logger = structlog.get_logger(__name__)`
- ERROR logs MUST include: context to reproduce (inputs, state, traceback)
- All logs MUST include request_id / trace_id for correlation
- Log rotation MUST be configured (prevent disk exhaustion)

## NEVER
- NEVER use `print()` for production logging
- NEVER log secrets (passwords, tokens, PII)
- NEVER log inside hot loops without sampling or DEBUG guard
- NEVER use wrong level (login=INFO not ERROR; connection failure=ERROR not DEBUG)

## Level Guide
| Level | Meaning | Example |
|-------|---------|---------|
| DEBUG | Dev only | SQL queries, variable values |
| INFO | Normal business events | User login, order created |
| WARN | Abnormal but recovered | Retry succeeded, fallback triggered |
| ERROR | Failed, needs attention | Request failed, data inconsistency |
""",

    "module-design.md": """\
# Module Design — Implementation Guide

## Boundary Criteria (when to extract a module)
1. Change direction is consistent — one requirement change affects only this module
2. Independently testable — no full system needed
3. Interface is stable — internal refactoring doesn't break callers
4. Single responsibility — describable in one sentence

## MUST
- Single file SHOULD NOT exceed 300 lines
- Single function SHOULD NOT exceed 50 lines
- Inter-module communication MUST use public interface only
- New feature MUST check: does an existing module own this responsibility?
- Circular dependencies MUST be resolved (indicates layering violation)

## NEVER
- NEVER access `_private` members from outside the module
- NEVER create "util" or "helper" modules (dumping ground anti-pattern)
- NEVER abstract prematurely — wait for 3 occurrences (Rule of Three)

## Abstraction Decision
| Signal | Action |
|--------|--------|
| Same pattern 1-2 times | Tolerate duplication |
| Same pattern 3+ times | Extract shared abstraction |
| Extraction makes caller harder to read | Don't extract |
| Module needs god-object disclaimer | Split by responsibility |
""",

    "database.md": """\
# Database — Implementation Guide

## Decision Table
| Scenario | Strategy |
|----------|----------|
| Single-row concurrent update | Optimistic lock: `WHERE version = ?` + retry |
| Counter / balance | Atomic: `SET x = x + ?` |
| Batch update | Chunk < 1000 rows, independent transactions |
| Read-heavy, low conflict | No lock, rely on MVCC |

## MUST
- Use connection pool (project's existing engine/pool)
- All connections via `async with` / `with` context manager
- Transactions MUST be minimal scope (no network calls inside txn)
- Connection acquire MUST have timeout
- Pool size MUST be configurable (default: `(cores * 2) + disk_count`)

## NEVER
- NEVER raw `connect()` — use pool
- NEVER call external APIs inside a transaction
- NEVER `SELECT FOR UPDATE` without WHERE clause or LIMIT
- NEVER hold transactions > 1 second
- NEVER ignore deadlock — implement retry with backoff

## Template
```python
async with db_pool.acquire(timeout=5.0) as conn:
    async with conn.transaction():
        await conn.execute(query, *params)
```
""",

    "caching.md": """\
# Caching — Implementation Guide

## Strategy Selection
| Strategy | Read | Write | Consistency | Use When |
|----------|------|-------|-------------|----------|
| Cache Aside | miss→DB→fill cache | update DB→delete cache | Eventual | Most cases |
| Write Through | miss→DB→fill cache | write cache+DB together | Strong | Write-rare |
| Write Behind | same | write cache only, async flush | Weak | Counters, analytics |

## MUST
- All caches MUST have TTL (no infinite cache)
- TTL SHOULD include random jitter (prevent stampede)
- Cache miss for non-existent keys MUST cache null (short TTL) — prevent penetration
- Hot keys MUST use singleflight/mutex — prevent thundering herd
- In-memory caches MUST have maxsize and eviction policy (LRU/LFU)

## NEVER
- NEVER cache without TTL
- NEVER treat cache as source of truth
- NEVER let all keys expire at the same time (add random offset)
- NEVER skip cache invalidation after write operations

## Template
```python
from functools import lru_cache
from cachetools import TTLCache

cache = TTLCache(maxsize=10000, ttl=300)  # 5min, max 10k entries
```
""",

    "api-integration.md": """\
# API Integration — Implementation Guide

## Defense Layers (all external calls)
| Layer | Purpose | Implementation |
|-------|---------|---------------|
| Timeout | Don't wait forever | connect=5s, read=30s |
| Retry | Transient failure recovery | 3 attempts, exponential backoff |
| Circuit Breaker | Stop hammering dead service | Open after 5 failures, half-open after 30s |
| Fallback | Graceful degradation | Return cached/default value |

## MUST
- All external HTTP calls MUST have explicit timeout (connect + read)
- Retries MUST use exponential backoff with jitter
- Retries MUST have max attempt limit (default: 3)
- Request and response MUST have schema validation
- API clients SHOULD be reusable (connection pooling via shared client)

## NEVER
- NEVER make external calls without timeout
- NEVER retry infinitely (`while True`)
- NEVER retry non-idempotent operations (POST) without confirmation
- NEVER trust external API response without validation

## Template
```python
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def call_api(url, payload):
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30)) as c:
        resp = await c.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
```
""",

    "event-driven.md": """\
# Event-Driven — Implementation Guide

## When to Use Events
| Signal | Use Events |
|--------|-----------|
| One action triggers 3+ downstream effects | Yes — decouple |
| Effects are independent of each other | Yes — parallel |
| Caller must wait for all effects | No — direct call |
| Effects need transactional guarantee | No — saga pattern |

## MUST
- Events MUST have a defined schema (dataclass / Pydantic)
- Event handlers MUST be idempotent (same event twice = same result)
- Critical events MUST be processed async (not blocking the main flow)
- Failed events MUST have retry + dead letter queue (DLQ)
- Each event MUST carry a unique event_id for dedup

## NEVER
- NEVER hardcode a chain of 3+ downstream calls in one function
- NEVER process events without idempotency check
- NEVER fire-and-forget without error visibility
- NEVER emit events without schema definition

## Template
```python
@dataclass
class OrderCreated:
    event_id: str
    order_id: str
    user_id: str
    timestamp: datetime

@event_bus.subscribe(OrderCreated)
def handle(event: OrderCreated):
    if already_processed(event.event_id): return
    mark_processed(event.event_id)
    # ... handle logic
```
""",

    "resilience.md": """\
# Resilience — Implementation Guide

## Four Defense Lines
| Line | Pattern | Purpose |
|------|---------|---------|
| 1 | Timeout | Don't wait forever |
| 2 | Circuit Breaker | Stop calling dead dependencies |
| 3 | Bulkhead | Isolate failure domains |
| 4 | Backpressure | Reject when overloaded |

## MUST
- All external calls MUST have timeout (connect + read + total)
- Retries MUST have max count + exponential backoff
- Independent dependencies SHOULD use separate resource pools (bulkhead)
- Queues/pools MUST have size limits — reject on full, never unlimited queue
- System MUST have health check endpoint (liveness + readiness)

## NEVER
- NEVER wait indefinitely for external resource
- NEVER retry in `while True` without max attempts
- NEVER let one slow dependency block all other functionality
- NEVER queue unlimited work (leads to OOM then crash)

## Template
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
def call_service(payload):
    return httpx.post(url, json=payload, timeout=10)
```
""",

    "memory-management.md": """\
# Memory Management — Implementation Guide

## Common Leak Patterns
| Pattern | Cause | Fix |
|---------|-------|-----|
| Unbounded collection | Global list/dict only grows | maxsize + eviction |
| Closure capture | Lambda holds reference to large object | Capture only needed fields |
| Event listener leak | Subscribe without unsubscribe | WeakRef or explicit cleanup |
| Resource leak | Connection/file not closed | Context manager |
| Full file read | `.read()` on large file | Streaming / chunked read |

## MUST
- All caches/collections MUST have size limit (maxsize)
- Large file processing MUST use streaming (line-by-line or chunked)
- Event listeners MUST have corresponding unsubscribe mechanism
- Long-lived objects referencing short-lived SHOULD use WeakRef
- Closures MUST capture minimal data (not entire large objects)

## NEVER
- NEVER append to global list/dict without eviction
- NEVER `.read()` entire file of unknown/unbounded size into memory
- NEVER subscribe to events without corresponding cleanup path
- NEVER hold large objects in closure when only a field is needed

## Template
```python
# Streaming read
with open(path) as f:
    for line in f:  # O(1) memory
        process(line)

# Bounded cache
from functools import lru_cache
@lru_cache(maxsize=1000)
def get_item(key): ...
```
""",

    "code-review-first.md": """\
# Code Review First — Implementation Guide

## Before Writing New Code (MUST)
1. Find the "exemplar file" — an existing implementation most similar to your task
2. Check shared/common/utils — what's already built?
3. `git blame` on related files — understand WHY code is the way it is
4. Search GitHub for existing open-source solutions

## MUST
- New feature MUST find an existing similar implementation as template
- New code MUST use same patterns as existing code (logger, ORM, error handling)
- "Redundant-looking" code MUST be investigated via git blame before removing
- MUST NOT introduce a second way of doing something the project already does

## NEVER
- NEVER write new code without reviewing existing patterns first
- NEVER introduce a new library when project already uses one for the same purpose
- NEVER delete code that "looks useless" without checking git history
- NEVER bypass project's abstraction layers to use framework directly

## Checklist
- [ ] Found exemplar file for this task?
- [ ] Using same logging library as rest of project?
- [ ] Using same ORM/DB access pattern?
- [ ] Using same error handling approach?
- [ ] No new lib when existing one covers the need?
""",

    "component-reuse.md": """\
# Component Reuse — Implementation Guide

## Reuse Priority (check in order)
1. Standard library provides it? → Use native API
2. Project already has it? → Use existing wrapper (do NOT bypass)
3. Framework provides it? → Enable native capability
4. Mature third-party exists? → Evaluate and adopt
5. None of above → Implement new (only valid case)

## MUST
- Before implementing, MUST search: stdlib → project → framework → ecosystem
- Third-party evaluation MUST check: maintenance (6mo commits), license, CVEs
- Project abstractions MUST be used — never bypass wrapper to call underlying lib
- MUST NOT self-implement: crypto, auth protocols, date parsing, retry logic

## NEVER
- NEVER reimplement what stdlib provides (lru_cache, dataclass, pathlib, etc.)
- NEVER bypass project's existing wrapper to use framework directly
- NEVER self-implement cryptography or security primitives
- NEVER add a dependency for trivial functionality (< 20 lines to implement)

## Evaluation Criteria (for third-party)
| Dimension | Threshold |
|-----------|-----------|
| Last commit | < 6 months |
| GitHub stars | > 500 |
| License | MIT/Apache/BSD compatible |
| Known CVEs | Zero unpatched |
| Dependency count | Fewer is better |
""",
}

GUIDES_DIR = "guides"
