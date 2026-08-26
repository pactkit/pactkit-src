"""Evidence-driven change-risk classification for PDCA guide routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

RISK_LEVELS = ("none", "low", "medium", "high")


@dataclass(frozen=True)
class RiskDecision:
    concern: str
    level: str
    reason: str
    evidence: tuple[str, ...]
    guide: str | None = None


@dataclass(frozen=True)
class ChangeRiskProfile:
    decisions: dict[str, RiskDecision]
    selected_guides: tuple[str, ...]


_RISK_RULES = {
    "data-migration": {
        "terms": ("migration", "migrate", "schema", "backfill", "数据库迁移"),
        "paths": ("migrations",),
        "guide": "backwards-compatibility.md",
        "evidence": ("old-data fixture", "idempotent migration", "interrupted-run recovery"),
    },
    "public-api-schema": {
        "terms": ("public api", "manifest", "schema", "cli", "协议", "配置"),
        "paths": ("schemas.py", "deploy_manifest.py", "pyproject.toml"),
        "guide": "backwards-compatibility.md",
        "evidence": ("legacy caller fixture", "compatibility declaration"),
    },
    "authentication-authorization": {
        "terms": ("auth", "permission", "credential", "权限", "凭据"),
        "paths": ("auth", "permission",),
        "guide": "configuration.md",
        "evidence": ("deny-path test", "actor/action/resource review"),
    },
    "concurrency-state": {
        "terms": ("concurrent", "parallel", "race", "lock", "并发", "状态"),
        "paths": ("workflow_engine.py",),
        "guide": "concurrency.md",
        "evidence": ("ordering test", "contention or recovery test"),
    },
    "external-side-effect": {
        "terms": ("publish", "release", "push", "external", "外部副作用"),
        "paths": ("release", "issue_sync.py"),
        "guide": "error-recovery.md",
        "evidence": ("authorization evidence", "duplicate/partial-failure test"),
    },
    "deployment-runtime": {
        "terms": ("deploy", "runtime", "rollout", "部署", "运行"),
        "paths": ("deployer.py", "profiles.py"),
        "guide": "operational-readiness.md",
        "evidence": ("isolated deployment", "rollback signal"),
    },
    "ui-accessibility": {
        "terms": (" ui ", "accessibility", "keyboard", "focus", "可访问", "界面"),
        "paths": (".tsx", ".jsx", ".vue", ".svelte"),
        "guide": "ui-state-accessibility.md",
        "evidence": ("interaction-state test", "keyboard/focus review"),
    },
    "dependency-supply-chain": {
        "terms": ("dependency", "package", "library", "依赖", "供应链"),
        "paths": ("requirements", "package.json", "pyproject.toml", "lock"),
        "guide": "dependency-supply-chain.md",
        "evidence": ("dependency diff", "source/license/install review"),
    },
}


def _is_docs_only(paths: tuple[str, ...]) -> bool:
    return bool(paths) and all(PurePosixPath(path).parts[0] in {"docs", "tests"} for path in paths)


def build_change_risk_profile(
    description: str, *, changed_paths: tuple[str, ...] = (), max_guides: int = 3,
) -> ChangeRiskProfile:
    """Classify evidence-backed risks and select at most ``max_guides``.

    Words are candidate signals only. A non-document implementation path is
    required before prose matches can select a guide, preventing a document
    that merely mentions "database" from activating database policy.
    """
    text = f" {description.lower()} "
    docs_only = _is_docs_only(changed_paths)
    decisions: dict[str, RiskDecision] = {}
    candidates: list[tuple[int, str]] = []
    for concern, rule in _RISK_RULES.items():
        term_hit = any(term in text for term in rule["terms"])
        path_hit = any(token in path.lower() for path in changed_paths for token in rule["paths"])
        score = (2 if path_hit else 0) + (1 if term_hit and not docs_only else 0)
        level = ("none", "low", "medium", "high")[min(score, 3)]
        reason = (
            "implementation path and requirement evidence match" if score == 3
            else "implementation path matches" if path_hit
            else "requirement signal requires implementation confirmation" if term_hit
            else "no supporting evidence"
        )
        decision = RiskDecision(
            concern=concern, level=level, reason=reason,
            evidence=rule["evidence"] if score else (), guide=rule["guide"],
        )
        decisions[concern] = decision
        if score >= 2 and rule["guide"]:
            candidates.append((score, rule["guide"]))
    selected = tuple(guide for _, guide in sorted(candidates, key=lambda item: (-item[0], item[1]))[:max_guides])
    return ChangeRiskProfile(decisions=decisions, selected_guides=selected)
