"""Versioned, verifiable continuation checkpoints (STORY-slim-146)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pactkit.utils import atomic_write

SCHEMA_VERSION = 1
STEPS = ("preflight", "red", "green", "regression_lint", "sync_coverage")
STATUSES = ("in_progress", "blocked", "completed")
LOCK_TIMEOUT_SECONDS = 5.0
LOCK_POLL_SECONDS = 0.05
_NEXT_STEP = dict(zip(STEPS, STEPS[1:] + ("completed",)))
_STORY_ID = re.compile(r"^(?:STORY|BUG|HOTFIX)(?:-[a-z]+)?-\d+$")
_SECRET = re.compile(r"(?i)(?:token|password|secret|api[_-]?key)\s*=\s*[^\s,;]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SENSITIVE_KEY = re.compile(
    r"(?i)(?:authorization|credential|password|passwd|secret|token|api[_-]?key|private[_-]?key)"
)
_STORY_BLOCK = re.compile(
    r"^###\s+\[(?P<id>(?:STORY|BUG|HOTFIX)(?:-[\w]+)?-\d+)\].*?(?=^###\s+\[|^##\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)
_MUST_REQUIREMENT = re.compile(r"^###\s+(R\d+):.*?\(MUST\)", re.MULTILINE)
_ACCEPTANCE_CRITERION = re.compile(r"^###\s+(AC\d+):", re.MULTILINE)
_LEGACY_HANDOFF = re.compile(
    r"^Last Command:\s*/project-act\s+(?P<story>(?:STORY|BUG|HOTFIX)(?:-[\w]+)?-\d+)\s*$",
    re.MULTILINE,
)


class ContinuationError(ValueError):
    """Raised when a checkpoint or its completion evidence is invalid."""


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _worktree_fingerprint(root: Path) -> str:
    """Fingerprint actual tracked/untracked content, not only dirty path names."""
    status = subprocess.run(
        [
            "git", "status", "--porcelain=v1", "--untracked-files=all",
            "--", ".", ":(exclude).pactkit",
        ],
        cwd=root, capture_output=True,
    )
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", ".", ":(exclude).pactkit"],
        cwd=root, capture_output=True,
    )
    untracked = subprocess.run(
        [
            "git", "ls-files", "--others", "--exclude-standard", "-z",
            "--", ".", ":(exclude).pactkit",
        ],
        cwd=root, capture_output=True,
    )
    if status.returncode != 0 or diff.returncode != 0 or untracked.returncode != 0:
        return "unavailable"
    digest = hashlib.sha256(status.stdout + b"\0" + diff.stdout)
    for raw_path in sorted(filter(None, untracked.stdout.split(b"\0"))):
        path = root / raw_path.decode(errors="surrogateescape")
        digest.update(b"\0" + raw_path + b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"[unreadable]")
    return digest.hexdigest()


def _sanitize(value: str | None) -> str:
    if not value:
        return ""
    clean = value.splitlines()[0].strip()
    clean = _SECRET.sub("[redacted]", clean)
    clean = _BEARER.sub("[redacted]", clean)
    clean = clean.replace(str(Path.home()), "~")
    return clean[:500]


def _sanitize_evidence(value: Any) -> Any:
    """Recursively remove secret-looking free text before persistence."""
    if isinstance(value, str):
        return _sanitize(value)
    if isinstance(value, list):
        return [_sanitize_evidence(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if _SENSITIVE_KEY.search(str(key)) else _sanitize_evidence(item)
            for key, item in value.items()
        }
    return value


class ContinuationStore:
    """Core-owned continuation store; resume intentionally never writes."""

    def __init__(self, project_root: Path):
        self.root = project_root.resolve()

    def path_for(self, story_id: str) -> Path:
        self._validate_story_id(story_id)
        return self.root / ".pactkit" / "continuations" / f"{story_id}.json"

    def _validate_story_id(self, story_id: str) -> None:
        if not _STORY_ID.fullmatch(story_id):
            raise ContinuationError(f"invalid Story ID: {story_id}")

    def _paths(self, story_id: str) -> tuple[Path, Path]:
        return (
            self.root / "docs" / "specs" / f"{story_id}.md",
            self.root / "docs" / "product" / "sprint_board.md",
        )

    def _fingerprints(self, story_id: str) -> dict[str, str]:
        spec, board = self._paths(story_id)
        return {
            "spec": _fingerprint(spec),
            "board": _fingerprint(board),
            "git_head": _git_head(self.root),
            "worktree": _worktree_fingerprint(self.root),
        }

    def read(self, story_id: str) -> dict[str, Any] | None:
        self._validate_story_id(story_id)
        path = self.path_for(story_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContinuationError(f"corrupt checkpoint: {path.name}: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise ContinuationError(f"unsupported checkpoint schema: {path.name}")
        required = {
            "story_id", "command", "phase", "step_id", "status", "evidence",
            "fingerprints", "blocker", "updated_at",
        }
        if required - set(value):
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        if value["story_id"] != story_id or value["command"] != "$project-act":
            raise ContinuationError(f"checkpoint Story or command mismatch: {path.name}")
        if value["step_id"] not in STEPS or value["status"] not in STATUSES:
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        if not isinstance(value["evidence"], dict) or not isinstance(value["fingerprints"], dict):
            raise ContinuationError(f"invalid checkpoint state: {path.name}")
        return value

    def legacy_handoff(self, story_id: str) -> bool:
        """Whether context.md holds only an unverifiable pre-checkpoint handoff."""
        self._validate_story_id(story_id)
        context = self.root / "docs" / "product" / "context.md"
        if not context.exists():
            return False
        try:
            return any(match.group("story") == story_id for match in _LEGACY_HANDOFF.finditer(
                context.read_text(encoding="utf-8")
            ))
        except OSError:
            return False

    def status(self, story_id: str) -> dict[str, Any]:
        """Read-only state summary, including explicit legacy-handoff detection."""
        state = self.read(story_id)
        if state is not None:
            return state
        reasons = []
        if self.legacy_handoff(story_id):
            reasons.append("unverifiable legacy handoff; create a preflight checkpoint")
        return {
            "decision": "start_fresh", "story_id": story_id,
            "next_step": "preflight", "reasons": reasons,
        }

    @contextmanager
    def _story_lock(self, story_id: str):
        """Serialize a Story's read/validate/write transaction across processes."""
        lock_path = self.path_for(story_id).with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        acquired = False
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        try:
            while not acquired:
                try:
                    if os.name == "nt":  # pragma: no cover - exercised on Windows CI
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
                        raise ContinuationError(
                            f"checkpoint lock timeout: {lock_path.name}"
                        ) from exc
                    time.sleep(LOCK_POLL_SECONDS)
            yield
        finally:
            if acquired:
                if os.name == "nt":  # pragma: no cover - exercised on Windows CI
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def checkpoint(
        self,
        story_id: str,
        *,
        step_id: str,
        evidence: dict[str, Any],
        status: str = "in_progress",
        phase: str = "",
        blocker: str = "",
        fresh: bool = False,
    ) -> dict[str, Any]:
        with self._story_lock(story_id):
            return self._checkpoint_locked(
                story_id, step_id=step_id, evidence=evidence, status=status,
                phase=phase, blocker=blocker, fresh=fresh,
            )

    def _checkpoint_locked(
        self,
        story_id: str,
        *,
        step_id: str,
        evidence: dict[str, Any],
        status: str = "in_progress",
        phase: str = "",
        blocker: str = "",
        fresh: bool = False,
    ) -> dict[str, Any]:
        self._validate_story_id(story_id)
        if step_id not in STEPS:
            raise ContinuationError(f"invalid step_id: {step_id}")
        if status not in STATUSES:
            raise ContinuationError(f"invalid status: {status}")
        if not isinstance(evidence, dict):
            raise ContinuationError("evidence must be a JSON object")
        if status == "blocked" and not blocker.strip():
            raise ContinuationError("blocked checkpoint requires a blocker with a manual next action")
        self._validate_step_evidence(story_id, step_id, evidence, status)
        if fresh and (step_id != "preflight" or status != "in_progress"):
            raise ContinuationError("--fresh requires an in_progress preflight checkpoint")

        previous = self.read(story_id)
        if previous is None and step_id != "preflight":
            raise ContinuationError("checkpoint cycle must start at preflight")
        if previous and previous["status"] == "completed":
            if not fresh:
                raise ContinuationError("completed checkpoint is immutable; use --fresh to start new work")
        elif previous and previous["status"] == "blocked":
            if not fresh and status != "blocked":
                stale = self._stale_reasons(previous, story_id)
                if stale:
                    raise ContinuationError("stale checkpoint: " + "; ".join(stale))
        elif fresh:
            raise ContinuationError("--fresh is only valid after a completed or blocked checkpoint")
        if previous and not fresh and status != "blocked":
            stale = self._stale_reasons(previous, story_id)
            if stale:
                raise ContinuationError("stale checkpoint: " + "; ".join(stale))
        if previous and not fresh and STEPS.index(step_id) < STEPS.index(previous["step_id"]):
            raise ContinuationError("checkpoint step cannot move backward")
        if (
            previous and not fresh
            and STEPS.index(step_id) > STEPS.index(previous["step_id"]) + 1
        ):
            raise ContinuationError("cannot skip checkpoint step")
        if fresh and previous:
            self._archive_completed(story_id, previous)
        if status == "completed":
            self._validate_completion(step_id, evidence, story_id)
        value = {
            "schema_version": SCHEMA_VERSION,
            "story_id": story_id,
            "command": "$project-act",
            "phase": _sanitize(phase),
            "step_id": step_id,
            "status": status,
            "evidence": _sanitize_evidence(evidence),
            # A blocked write is a handoff, not a new verified baseline. Keep
            # the last trusted fingerprints so later progress cannot silently
            # accept inputs that changed while the workflow was blocked.
            "fingerprints": (
                previous["fingerprints"]
                if status == "blocked" and previous and not fresh
                else self._fingerprints(story_id)
            ),
            "blocker": _sanitize(blocker),
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        atomic_write(self.path_for(story_id), json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        return value

    def _validate_step_evidence(
        self, story_id: str, step_id: str, evidence: dict[str, Any], status: str,
    ) -> None:
        """Validate deterministic proof for each safe boundary."""
        if status == "blocked":
            return
        valid = False
        if step_id == "preflight":
            valid = evidence.get("spec_lint") == "pass"
        elif step_id in {"red", "green"}:
            tests = evidence.get("story_tests")
            expected = 1 if step_id == "red" else 0
            valid = isinstance(tests, dict) and tests.get("exit_code") == expected
        elif step_id == "regression_lint":
            valid = evidence.get("regression") == "pass" and evidence.get("lint") == "pass"
        elif step_id == "sync_coverage":
            valid = status == "completed"
        if not valid:
            raise ContinuationError(f"invalid {step_id} evidence")
        if step_id == "preflight":
            self._require_valid_spec(story_id)

    def _require_valid_spec(self, story_id: str) -> None:
        """Run the canonical structural linter; never trust evidence prose alone."""
        from pactkit.skills.spec_linter import validate_spec

        spec_path = self._paths(story_id)[0]
        if not validate_spec(str(spec_path)).passed:
            raise ContinuationError("Spec lint failed")

    def _archive_completed(self, story_id: str, state: dict[str, Any]) -> None:
        """Preserve immutable completion evidence before beginning a new cycle."""
        timestamp = state.get("updated_at", "unknown").replace(":", "-")
        archive = self.root / ".pactkit" / "continuations" / "history" / f"{story_id}-{timestamp}.json"
        content = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        if archive.exists():
            try:
                if archive.read_text(encoding="utf-8") == content:
                    return
            except OSError as exc:
                raise ContinuationError(f"cannot verify checkpoint archive: {archive.name}") from exc
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
            archive = archive.with_name(f"{archive.stem}-{digest}.json")
            if archive.exists():
                try:
                    if archive.read_text(encoding="utf-8") == content:
                        return
                except OSError as exc:
                    raise ContinuationError(f"cannot verify checkpoint archive: {archive.name}") from exc
                raise ContinuationError(f"checkpoint archive collision: {archive.name}")
        atomic_write(archive, content)

    def _validate_completion(self, step_id: str, evidence: dict[str, Any], story_id: str) -> None:
        required = {
            "spec_lint", "story_tests", "regression", "lint", "coverage",
            "acceptance_coverage", "board_tasks",
        }
        if step_id != "sync_coverage" or required - set(evidence):
            raise ContinuationError("missing completion evidence")
        if evidence["spec_lint"] != "pass" or evidence["regression"] != "pass" or evidence["lint"] != "pass":
            raise ContinuationError("missing completion evidence")
        self._require_valid_spec(story_id)
        if not isinstance(evidence["coverage"], dict) or not evidence["coverage"]:
            raise ContinuationError("missing completion evidence")
        if not isinstance(evidence["story_tests"], dict) or evidence["story_tests"].get("exit_code") != 0:
            raise ContinuationError("missing completion evidence")
        board = self._paths(story_id)[1]
        board_text = board.read_text(encoding="utf-8") if board.exists() else ""
        story_block = next(
            (match.group(0) for match in _STORY_BLOCK.finditer(board_text) if match.group("id") == story_id),
            "",
        )
        if not story_block or "- [ ]" in story_block:
            raise ContinuationError("missing completion evidence")
        board_tasks = [
            match.group(1).strip()
            for match in re.finditer(r"^- \[x\] (.+)$", story_block, re.MULTILINE)
        ]
        evidence_tasks = evidence["board_tasks"]
        if (
            not isinstance(evidence_tasks, list)
            or not all(isinstance(task, str) and task.strip() for task in evidence_tasks)
            or set(evidence_tasks) != set(board_tasks)
        ):
            raise ContinuationError("board task evidence mismatch")
        spec = self._paths(story_id)[0]
        spec_text = spec.read_text(encoding="utf-8") if spec.exists() else ""
        required = set(_MUST_REQUIREMENT.findall(spec_text))
        missing_coverage = required - set(evidence["coverage"])
        if missing_coverage:
            raise ContinuationError(
                "missing completion coverage: " + ", ".join(sorted(missing_coverage))
            )
        acceptance_coverage = evidence["acceptance_coverage"]
        if not isinstance(acceptance_coverage, dict):
            raise ContinuationError("missing completion evidence")
        acceptance_criteria = set(_ACCEPTANCE_CRITERION.findall(spec_text))
        missing_acceptance = acceptance_criteria - set(acceptance_coverage)
        if missing_acceptance:
            raise ContinuationError(
                "missing completion acceptance coverage: "
                + ", ".join(sorted(missing_acceptance))
            )
        for mapping in (evidence["coverage"], acceptance_coverage):
            if any(
                not isinstance(items, list)
                or not items
                or not all(isinstance(item, str) and item.strip() for item in items)
                for items in mapping.values()
            ):
                raise ContinuationError("empty completion traceability evidence")

    def resume(self, story_id: str) -> dict[str, Any]:
        state = self.read(story_id)
        if state is None:
            return self.status(story_id)
        reasons: list[str] = []
        # Core contract validation is a deterministic, read-only recovery preflight.
        # It protects newly deployed runtime skills from silently missing a policy.
        from pactkit.prompts.skills import validate_skill_recovery_contracts

        reasons.extend(validate_skill_recovery_contracts())
        if state["status"] == "blocked":
            reasons.append("checkpoint is blocked: " + (state.get("blocker") or "manual action required"))
        if state["status"] == "completed":
            # Completed is terminal. Phase 4 intentionally generates derived
            # context/graph files after the checkpoint; reporting those as
            # stale would misleadingly imply that execution can resume.
            return {
                "decision": "blocked", "story_id": story_id,
                "reasons": reasons + ["checkpoint is completed"],
            }
        peers = self._active_peer_story_ids(story_id)
        if peers:
            reasons.append("competing active checkpoints: " + ", ".join(peers))
        reasons.extend(self._stale_reasons(state, story_id))
        if reasons:
            return {"decision": "blocked", "story_id": story_id, "reasons": reasons}
        return {
            "decision": "resume_at",
            "story_id": story_id,
            "next_step": _NEXT_STEP[state["step_id"]],
            "reasons": [],
        }

    def _stale_reasons(self, state: dict[str, Any], story_id: str) -> list[str]:
        current = self._fingerprints(story_id)
        reasons: list[str] = []
        for key in ("spec", "board"):
            if state.get("fingerprints", {}).get(key) != current[key]:
                reasons.append(f"{key} fingerprint changed")
        if state.get("fingerprints", {}).get("git_head") not in ("unavailable", current["git_head"]):
            reasons.append("git HEAD changed")
        if state.get("fingerprints", {}).get("worktree") not in ("unavailable", current["worktree"]):
            reasons.append("worktree fingerprint changed")
        return reasons

    def _active_peer_story_ids(self, story_id: str) -> list[str]:
        """List other non-terminal checkpoint Stories without trusting their contents."""
        directory = self.root / ".pactkit" / "continuations"
        if not directory.exists():
            return []
        peers: list[str] = []
        for path in sorted(directory.glob("*.json")):
            if not _STORY_ID.fullmatch(path.stem):
                continue
            if path.stem == story_id:
                continue
            try:
                state = self.read(path.stem)
            except ContinuationError:
                peers.append(path.stem)
                continue
            if state and state.get("status") in {"in_progress", "blocked"}:
                peers.append(path.stem)
        return peers

    def diagnostics(self, *, include_completed: bool = False) -> list[str]:
        """Return corrupt/stale state warnings without mutating checkpoints.

        Doctor only needs actionable corruption or inconsistency. Garden also
        requests completed checkpoints so it can flag cleanup candidates.
        """
        directory = self.root / ".pactkit" / "continuations"
        warnings: list[str] = []
        context = self.root / "docs" / "product" / "context.md"
        if context.exists():
            try:
                for match in _LEGACY_HANDOFF.finditer(context.read_text(encoding="utf-8")):
                    story_id = match.group("story")
                    if not self.path_for(story_id).exists():
                        warnings.append(f"Unverifiable legacy handoff: {story_id}")
            except OSError:
                pass
        if not directory.exists():
            return warnings
        for path in sorted(directory.glob("*.json")):
            if not _STORY_ID.fullmatch(path.stem):
                continue
            try:
                state = self.read(path.stem)
                if state and state["status"] == "completed" and include_completed:
                    warnings.append(f"Completed continuation retained: {path.stem}")
                elif state and state["status"] == "completed":
                    continue
                elif state and self.resume(path.stem)["decision"] == "blocked":
                    warnings.append(f"Continuation needs attention: {path.stem}")
            except ContinuationError:
                warnings.append(f"Continuation corrupt: {path.name}")
        return warnings
