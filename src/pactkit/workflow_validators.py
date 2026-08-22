"""Workflow-specific evidence policies for the generic continuation engine."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

_PLACEHOLDER = re.compile(
    r"(?i)(?:\bTBD\b|\bTODO\b|\(description|\(requirement|\(scenario|\{[^}]+\})"
)
_MUST = re.compile(r"^###\s+(R\d+):(?P<body>.*?)(?=^###\s+R\d+:|^##\s+|\Z)", re.M | re.S)
_AC = re.compile(r"^###\s+(AC\d+):(?P<body>.*?)(?=^###\s+AC\d+:|^##\s+|\Z)", re.M | re.S)
_STORY_HEADING = re.compile(r"^#{3,4}\s+\[(?P<id>[^]]+)\]\s+(?P<title>.+)$", re.M)


class WorkflowEvidenceError(ValueError):
    """Workflow evidence does not prove the requested transition."""


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


class NoopValidator:
    def __init__(self, root: Path):
        self.root = root

    def validate(self, state: dict[str, Any], step: str, evidence: dict[str, Any], status: str) -> None:
        if status == "blocked":
            return
        if not isinstance(evidence, dict):
            raise WorkflowEvidenceError(f"invalid {step} evidence")

    def fingerprints(self, state: dict[str, Any]) -> dict[str, str]:
        return {}

    def _require_graph_evidence(self, evidence: dict[str, Any]) -> None:
        from pactkit.config import find_pactkit_yaml, load_config

        config_path = find_pactkit_yaml(self.root)
        config = load_config(config_path) if config_path else {}
        configured = config.get("visualize", {}).get("graph_provider")
        if configured != "codegraph":
            return
        graph = evidence.get("graph_provider")
        if not isinstance(graph, dict):
            raise WorkflowEvidenceError("configured Codegraph provider evidence is required")
        required = {
            "requested_provider", "selected_provider", "availability", "freshness",
            "query_kind", "query_target", "result_count", "fallback", "reason_code",
        }
        if not required <= graph.keys():
            message = "invalid fallback evidence" if graph.get("fallback") else "incomplete graph provider evidence"
            raise WorkflowEvidenceError(message)
        if graph.get("requested_provider") != "codegraph":
            raise WorkflowEvidenceError("graph provider evidence does not match configuration")
        if graph.get("query_kind") not in {"callers", "callees", "chain", "explore", "impact"}:
            raise WorkflowEvidenceError("invalid graph query kind evidence")
        if not isinstance(graph.get("query_target"), str) or not graph["query_target"].strip():
            raise WorkflowEvidenceError("invalid graph query target evidence")
        if not isinstance(graph.get("result_count"), int) or graph["result_count"] < 0:
            raise WorkflowEvidenceError("invalid graph result count evidence")
        selected = graph.get("selected_provider")
        fallback = graph.get("fallback")
        if not isinstance(fallback, bool):
            raise WorkflowEvidenceError("invalid fallback evidence")
        if not fallback:
            if selected != "codegraph":
                raise WorkflowEvidenceError("configured Codegraph was not used and fallback was not authorized")
            if graph.get("availability") is not True or graph.get("freshness") is not True:
                raise WorkflowEvidenceError("Codegraph evidence is unavailable or stale")
            if graph.get("reason_code") not in {"ok", "valid_empty"}:
                raise WorkflowEvidenceError("invalid Codegraph success evidence")
            return
        chain = graph.get("fallback_chain")
        reason = graph.get("fallback_reason")
        if (
            not isinstance(chain, list)
            or len(chain) < 2
            or chain[0] != "codegraph"
            or chain[-1] != selected
            or selected not in {"builtin_graph", "text_search"}
            or chain not in (["codegraph", "builtin_graph"],
                             ["codegraph", "builtin_graph", "text_search"])
            or not isinstance(reason, str)
            or not reason.strip()
            or graph.get("reason_code") != "fallback"
            or graph.get("availability") is not True
            or graph.get("freshness") is not True
        ):
            raise WorkflowEvidenceError("invalid fallback evidence")


class PlanEvidenceValidator(NoopValidator):
    """Deterministic evidence checks for project-plan."""

    def _spec(self, state: dict[str, Any]) -> Path:
        return self.root / "docs" / "specs" / f"{state['story_id']}.md"

    def _board(self) -> Path:
        return self.root / "docs" / "product" / "sprint_board.md"

    def validate(self, state: dict[str, Any], step: str, evidence: dict[str, Any], status: str) -> None:
        super().validate(state, step, evidence, status)
        if status == "blocked":
            return
        if step == "preflight":
            if evidence.get("guard") != "pass" or not evidence.get("input_fingerprint"):
                raise WorkflowEvidenceError("invalid Plan preflight evidence")
            return
        if step == "intent_clarified" and not evidence.get("input_fingerprint"):
            raise WorkflowEvidenceError("invalid intent_clarified evidence")
        elif step == "archaeology":
            trace = evidence.get("trace")
            if not isinstance(trace, list) or not trace:
                raise WorkflowEvidenceError("invalid archaeology evidence")
            self._require_graph_evidence(evidence)
        elif step == "story_identified":
            if evidence.get("story_id") != state.get("story_id"):
                raise WorkflowEvidenceError("Story identity evidence mismatch")
            if self._spec(state).exists():
                raise WorkflowEvidenceError("Story ID is no longer unique")
        elif step == "spec_scaffolded":
            expected = f"docs/specs/{state['story_id']}.md"
            if evidence.get("spec_path") != expected or not self._spec(state).is_file():
                raise WorkflowEvidenceError("Spec scaffold is missing or mismatched")
        elif step == "requirements_written":
            self._require_requirements(state)
        elif step == "acceptance_written":
            self._require_acceptance(state)
        elif step == "security_scoped":
            self._require_security(state)
        elif step == "spec_linted":
            self._require_lint(state)
        elif step == "board_synced":
            self._require_board(state, evidence)
            if status == "completed":
                self._require_complete(state, evidence)

    def _text(self, state: dict[str, Any]) -> str:
        path = self._spec(state)
        if not path.is_file():
            raise WorkflowEvidenceError("Spec scaffold is missing or mismatched")
        return path.read_text(encoding="utf-8")

    def _require_requirements(self, state: dict[str, Any]) -> None:
        must = [m for m in _MUST.finditer(self._text(state)) if "(MUST)" in m.group(0)]
        if not must or any(_PLACEHOLDER.search(m.group("body")) for m in must):
            raise WorkflowEvidenceError("Spec MUST requirements are missing or contain placeholders")

    def _require_acceptance(self, state: dict[str, Any]) -> None:
        criteria = list(_AC.finditer(self._text(state)))
        if not criteria or any(
            _PLACEHOLDER.search(m.group("body"))
            or not all(f"**{word}**" in m.group("body") for word in ("Given", "When", "Then"))
            for m in criteria
        ):
            raise WorkflowEvidenceError("Spec acceptance criteria are incomplete")

    def _require_security(self, state: dict[str, Any]) -> None:
        text = self._text(state)
        match = re.search(r"^## Security Scope\s*$([\s\S]*?)(?=^##\s+|\Z)", text, re.M)
        if not match or "SEC-" not in match.group(1) or _PLACEHOLDER.search(match.group(1)):
            raise WorkflowEvidenceError("Security Scope is incomplete")

    def _require_lint(self, state: dict[str, Any]) -> None:
        from pactkit.skills.spec_linter import validate_spec

        result = validate_spec(str(self._spec(state)))
        if result.errors or result.warnings:
            raise WorkflowEvidenceError(
                f"Spec lint failed: {len(result.errors)} errors, {len(result.warnings)} warnings"
            )

    def _require_board(self, state: dict[str, Any], evidence: dict[str, Any]) -> None:
        records = self.root / "docs" / "product" / "stories"
        if records.is_dir():
            from pactkit.governance import GovernanceError, StoryRepository

            try:
                record = StoryRepository(self.root).load(state["story_id"])
            except GovernanceError as exc:
                raise WorkflowEvidenceError(str(exc)) from exc
            if evidence.get("title") and record["title"] != evidence["title"].strip():
                raise WorkflowEvidenceError("Story title mismatch")
            if evidence.get("tasks") is not None and [task["title"] for task in record["tasks"]] != evidence["tasks"]:
                raise WorkflowEvidenceError("Story task list mismatch")
            return
        board = self._board().read_text(encoding="utf-8") if self._board().exists() else ""
        matches = [m for m in _STORY_HEADING.finditer(board) if m.group("id") == state["story_id"]]
        if len(matches) != 1:
            raise WorkflowEvidenceError("Board must contain the Story exactly once")
        title = evidence.get("title")
        if title and matches[0].group("title").strip() != title.strip():
            raise WorkflowEvidenceError("Board Story title mismatch")
        tasks = evidence.get("tasks")
        if tasks is not None:
            start = matches[0].end()
            next_heading = re.search(r"^#{2,4}\s+", board[start:], re.M)
            block = board[start:start + next_heading.start()] if next_heading else board[start:]
            actual = re.findall(r"^- \[[ x]\] (.+)$", block, re.M)
            if actual != tasks:
                raise WorkflowEvidenceError("Board task list mismatch")

    def _require_complete(self, state: dict[str, Any], evidence: dict[str, Any]) -> None:
        self._require_requirements(state)
        self._require_acceptance(state)
        self._require_security(state)
        self._require_lint(state)
        if not evidence.get("title") or not isinstance(evidence.get("tasks"), list) or not evidence["tasks"]:
            raise WorkflowEvidenceError("missing Plan completion evidence")

    def fingerprints(self, state: dict[str, Any]) -> dict[str, str]:
        if not state.get("story_id"):
            return {}
        fingerprints = {
            "spec": _hash(self._spec(state)),
            "hld": _hash(self.root / "docs" / "architecture" / "graphs" / "system_design.mmd"),
        }
        story_directory = self.root / "docs" / "product" / "stories"
        if story_directory.is_dir():
            fingerprints["story_fact"] = _hash(
                story_directory / f"{state['story_id']}.yaml"
            )
        else:
            fingerprints["board"] = _hash(self._board())
        return fingerprints


def plan_validator(root: Path) -> PlanEvidenceValidator:
    return PlanEvidenceValidator(root)


def noop_validator(root: Path) -> NoopValidator:
    return NoopValidator(root)


class ActEvidenceValidator(NoopValidator):
    def validate(self, state: dict[str, Any], step: str, evidence: dict[str, Any], status: str) -> None:
        super().validate(state, step, evidence, status)
        if status != "blocked" and step == "preflight":
            self._require_graph_evidence(evidence)


def act_validator(root: Path) -> ActEvidenceValidator:
    return ActEvidenceValidator(root)
