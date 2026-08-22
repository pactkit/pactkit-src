"""Codegraph-first static-analysis provider routing."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

QUERY_KINDS = frozenset({"callers", "callees", "chain", "explore", "impact"})
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_TARGET = re.compile(r"^[^\x00\r\n]{1,500}$")
_SYNC_LOCK_POLL_SECONDS = 0.05


class GraphProviderError(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class GraphQueryRequest:
    kind: str
    target: str
    direction: str = "up"
    limit: int = 200

    def __post_init__(self) -> None:
        if self.kind not in QUERY_KINDS:
            raise ValueError(f"unsupported graph query kind: {self.kind}")
        if not _TARGET.fullmatch(self.target):
            raise ValueError("invalid graph query target")
        if self.direction not in {"up", "down"}:
            raise ValueError("query direction must be up or down")
        if not 1 <= self.limit <= 1000:
            raise ValueError("query limit must be between 1 and 1000")


@dataclass
class ProviderDecision:
    requested_provider: str | None
    selected_provider: str
    availability: bool
    freshness: bool
    query_kind: str
    query_target: str
    result_count: int = 0
    fallback: bool = False
    fallback_reason: str | None = None
    fallback_chain: list[str] = field(default_factory=list)
    reason_code: str = "ok"
    warnings: list[str] = field(default_factory=list)


@dataclass
class GraphQueryResult:
    results: list[dict[str, Any]]
    decision: ProviderDecision
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "results": self.results, "decision": asdict(self.decision)}


class GraphProvider(Protocol):
    name: str

    def health(self) -> dict[str, Any]: ...
    def sync(self) -> dict[str, Any]: ...
    def query(self, request: GraphQueryRequest) -> list[dict[str, Any]]: ...


def _clean(text: str) -> str:
    return _ANSI.sub("", text).replace(str(Path.home()), "~")[:4000]


class CodegraphProvider:
    name = "codegraph"

    def __init__(self, root: Path, *, db_path: Path | None = None, timeout: float = 30.0):
        self.root = root.resolve()
        index_root = (self.root / ".codegraph").resolve()
        self.db_path = (db_path or index_root / "codegraph.db").resolve()
        if not self.db_path.is_relative_to(index_root):
            raise ValueError("Codegraph database must stay inside the project .codegraph directory")
        self.timeout = timeout

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["codegraph", *args], cwd=self.root, capture_output=True, text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GraphProviderError("codegraph_timeout", "Codegraph command timed out") from exc
        except OSError as exc:
            raise GraphProviderError("binary_missing", "Codegraph executable is unavailable") from exc

    def health(self) -> dict[str, Any]:
        if shutil.which("codegraph") is None:
            return {"available": False, "fresh": False, "reason": "binary_missing", "warnings": []}
        version = self._run("--version")
        if version.returncode != 0:
            return {"available": False, "fresh": False, "reason": "version_failed", "warnings": []}
        if not self.db_path.is_file():
            return {
                "available": False, "fresh": False, "reason": "db_missing",
                "version": _clean(version.stdout or version.stderr).strip(), "warnings": [],
            }
        status = self._run("status", str(self.root))
        output = _clean((status.stdout or "") + "\n" + (status.stderr or ""))
        if status.returncode != 0:
            return {
                "available": False, "fresh": False, "reason": "status_failed",
                "version": _clean(version.stdout or version.stderr).strip(), "warnings": [],
                "detail": output,
            }
        warnings = []
        if "earlier version" in output.lower():
            warnings.append("index_old_engine")
        stale = bool(re.search(r"Pending Changes:.*?(?:Added|Modified|Deleted):\s*[1-9]\d*", output, re.S))
        if "index is up to date" in output.lower():
            stale = False
        return {
            "available": True, "fresh": not stale, "reason": "ok" if not stale else "index_stale",
            "version": _clean(version.stdout or version.stderr).strip(), "warnings": warnings,
        }

    @contextmanager
    def _sync_lock(self):
        lock_path = self.root / ".pactkit" / "locks" / "codegraph-sync.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        acquired = False
        deadline = time.monotonic() + self.timeout
        try:
            while not acquired:
                try:
                    if os.name == "nt":  # pragma: no cover - Windows CI
                        import msvcrt

                        handle.seek(0, os.SEEK_END)
                        if handle.tell() == 0:
                            handle.write(b"0")
                            handle.flush()
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except (BlockingIOError, PermissionError, OSError) as exc:
                    if time.monotonic() >= deadline:
                        raise GraphProviderError(
                            "sync_lock_timeout", "Timed out waiting for Codegraph sync lock"
                        ) from exc
                    time.sleep(_SYNC_LOCK_POLL_SECONDS)
            yield
        finally:
            if acquired:
                if os.name == "nt":  # pragma: no cover - Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def sync(self) -> dict[str, Any]:
        with self._sync_lock():
            current = self.health()
            if current.get("available") and current.get("fresh"):
                return current
            result = self._run("sync", str(self.root))
            if result.returncode != 0:
                return {
                    "available": True, "fresh": False, "reason": "sync_failed",
                    "warnings": [], "detail": _clean(result.stderr or result.stdout),
                }
            health = self.health()
            if not health.get("fresh"):
                health["reason"] = "sync_incomplete"
            return health

    def query(self, request: GraphQueryRequest) -> list[dict[str, Any]]:
        if request.kind == "chain":
            return self._query_sqlite(request)
        command = request.kind
        args = [command, request.target, "--path", str(self.root)]
        if request.kind in {"callers", "callees"}:
            args += ["--limit", str(request.limit), "--json"]
        elif request.kind == "impact":
            args += ["--json"]
        result = self._run(*args)
        if result.returncode != 0:
            raise GraphProviderError("query_failed", _clean(result.stderr or result.stdout))
        if request.kind == "explore":
            output = _clean(result.stdout).strip()
            return [] if not output else [{"text": output}]
        try:
            value = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise GraphProviderError("query_output_invalid", "Codegraph returned invalid JSON") from exc
        if isinstance(value, list):
            return [item if isinstance(item, dict) else {"value": item} for item in value]
        if isinstance(value, dict):
            for key in ("results", "callers", "callees", "nodes", "affected"):
                if isinstance(value.get(key), list):
                    return [item if isinstance(item, dict) else {"value": item} for item in value[key]]
            return [value] if value else []
        raise GraphProviderError("query_output_invalid", "Codegraph returned an unsupported payload")

    def _query_sqlite(self, request: GraphQueryRequest) -> list[dict[str, Any]]:
        """Compatibility adapter for transitive chain until CLI exposes it."""
        if not self.db_path.is_file():
            raise GraphProviderError("db_missing", f"Codegraph database missing: {self.db_path.name}")
        direction = ("source", "target") if request.direction == "down" else ("target", "source")
        start_col, next_col = direction
        sql = f"""
            WITH RECURSIVE chain(id) AS (
                SELECT DISTINCT e.{next_col} FROM edges e JOIN nodes n ON e.{start_col} = n.id
                WHERE e.kind = 'calls' AND n.name LIKE ?
                UNION
                SELECT e.{next_col} FROM edges e JOIN chain c ON e.{start_col} = c.id
                WHERE e.kind = 'calls'
            )
            SELECT DISTINCT n.name, n.file_path, n.start_line
            FROM chain c JOIN nodes n ON c.id = n.id LIMIT ?
        """
        try:
            connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            try:
                rows = connection.execute(sql, (f"%{request.target}%", request.limit)).fetchall()
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise GraphProviderError("schema_incompatible", "Codegraph SQLite schema is incompatible") from exc
        return [{"name": name, "file_path": path, "start_line": line} for name, path, line in rows]


class BuiltinGraphProvider:
    name = "builtin_graph"

    def __init__(self, root: Path):
        self.root = root.resolve()

    def health(self) -> dict[str, Any]:
        return {"available": True, "fresh": True, "warnings": []}

    def sync(self) -> dict[str, Any]:
        return self.health()

    def query(self, request: GraphQueryRequest) -> list[dict[str, Any]]:
        graph = self.root / "docs" / "architecture" / "graphs" / "call_graph.mmd"
        if not graph.is_file():
            return []
        matches = []
        for line in graph.read_text(encoding="utf-8", errors="replace").splitlines():
            if request.target.lower() in line.lower():
                matches.append({"text": line.strip()})
                if len(matches) >= request.limit:
                    break
        return matches


class TextSearchProvider:
    """Last-resort literal source search used only after explicit fallback."""

    name = "text_search"

    def __init__(self, root: Path, *, timeout: float = 30.0):
        self.root = root.resolve()
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        available = shutil.which("rg") is not None
        return {
            "available": available,
            "fresh": available,
            "reason": "ok" if available else "text_search_missing",
            "warnings": [],
        }

    def sync(self) -> dict[str, Any]:
        return self.health()

    def query(self, request: GraphQueryRequest) -> list[dict[str, Any]]:
        command = [
            "rg", "--line-number", "--no-heading", "--color", "never",
            "--fixed-strings", "--max-count", str(request.limit), "--", request.target,
        ]
        try:
            result = subprocess.run(
                command, cwd=self.root, capture_output=True, text=True, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GraphProviderError("text_search_timeout", "Text search timed out") from exc
        except OSError as exc:
            raise GraphProviderError("text_search_missing", "rg executable is unavailable") from exc
        if result.returncode not in {0, 1}:
            raise GraphProviderError("text_search_failed", _clean(result.stderr or result.stdout))
        rows = []
        for line in result.stdout.splitlines():
            match = re.match(r"^(.*?):(\d+):(.*)$", line)
            if not match:
                continue
            rows.append({
                "path": _clean(match.group(1)),
                "line": int(match.group(2)),
                "text": _clean(match.group(3)),
            })
            if len(rows) >= request.limit:
                break
        return rows


class GraphProviderRouter:
    def __init__(self, providers: dict[str, GraphProvider]):
        self.providers = providers

    def query(
        self, request: GraphQueryRequest, *, configured_provider: str | None, allow_fallback: bool = False,
    ) -> GraphQueryResult:
        requested = configured_provider
        primary = configured_provider or "builtin_graph"
        failure: GraphProviderError | None = None
        chain = [primary]
        try:
            return self._query_one(primary, request, requested)
        except GraphProviderError as exc:
            failure = exc
        if not allow_fallback or primary != "codegraph":
            raise failure
        for name in ("builtin_graph", "text_search"):
            provider = self.providers.get(name)
            if provider is None:
                continue
            chain.append(name)
            try:
                result = self._query_one(name, request, requested)
            except GraphProviderError:
                continue
            result.decision.fallback = True
            result.decision.fallback_reason = failure.reason_code
            result.decision.fallback_chain = chain
            result.decision.reason_code = "fallback"
            return result
        raise failure

    def _query_one(
        self, name: str, request: GraphQueryRequest, requested: str | None,
    ) -> GraphQueryResult:
        provider = self.providers.get(name)
        if provider is None:
            raise GraphProviderError("provider_missing", f"Graph provider is not registered: {name}")
        health = provider.health()
        warnings = list(health.get("warnings", []))
        if not health.get("available"):
            raise GraphProviderError(health.get("reason", "provider_unavailable"), f"{name} unavailable")
        if not health.get("fresh", False):
            synced = provider.sync()
            warnings.extend(item for item in synced.get("warnings", []) if item not in warnings)
            if not synced.get("fresh", False):
                reason = synced.get("reason")
                if reason not in {"sync_failed", "codegraph_timeout"}:
                    reason = "sync_incomplete"
                raise GraphProviderError(reason, f"{name} index is stale")
        results = provider.query(request)
        decision = ProviderDecision(
            requested_provider=requested, selected_provider=name, availability=True, freshness=True,
            query_kind=request.kind, query_target=request.target, result_count=len(results), warnings=warnings,
        )
        return GraphQueryResult(results, decision, "valid_empty" if not results else "ok")


def project_router(root: Path, *, db_path: Path | None = None) -> GraphProviderRouter:
    return GraphProviderRouter({
        "codegraph": CodegraphProvider(root, db_path=db_path),
        "builtin_graph": BuiltinGraphProvider(root),
        "text_search": TextSearchProvider(root),
    })
