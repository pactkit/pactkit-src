"""Four-class rule diagnosis engine (STORY-slim-20260903a4ef6915ed62).

Pure functions: events + config + specs in, findings out. Every finding
carries the class/evidence/action triple; non-high confidence is always
labeled (ADR-0003: consumption must tell the user WHAT to adjust and
WHETHER it is a config issue, a PactKit bug, a usage habit, or a rule
design problem).
"""

from __future__ import annotations

from pathlib import Path

# Class taxonomy (mirrors shared-execution's failure classification):
# config  — PactKit parameter problem -> exact yaml fix
# bug     — PactKit defect -> report issue + workaround
# usage   — habit/process gap -> workflow advice (bypass-aware confidence)
# rule_design — the rule itself -> prune/merge/escalate feedback to PactKit

_GUIDE_CONCERN_KEYWORDS = {
    "caching": ("缓存", "cache", "Redis", "Memcached"),
    "database": ("数据库", "DB", "SQL", "ORM", "事务"),
    "observability": ("日志", "log", "监控", "metrics", "trace"),
    "concurrency": ("并发", "concurrent", "多线程", "多进程"),
    "api-integration": ("API", "HTTP", "webhook", "REST", "gRPC"),
    "resilience": ("重试", "timeout", "超时", "熔断", "circuit"),
    "write-safety": ("覆盖", "overwrite", "配置文件", "merge"),
    "testing-strategy": ("测试策略", "mock", "stub", "测试"),
}
_DEFAULT_WINDOW_DAYS = 30
_ASSESSMENT_HEADING = "### Capability Assessment"


def _finding(cls: str, evidence: dict, action: str, confidence: str = "high") -> dict:
    return {"class": cls, "evidence": evidence, "action": action, "confidence": confidence}


def _specs_root(project_root: Path) -> Path:
    return Path(project_root) / "docs" / "specs"


def _concern_in_specs(guide: str, project_root: Path) -> bool:
    keywords = _GUIDE_CONCERN_KEYWORDS.get(guide, (guide,))
    specs = _specs_root(project_root)
    if not specs.is_dir():
        return False
    for spec in specs.glob("*.md"):
        try:
            text = spec.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(kw.lower() in text.lower() for kw in keywords):
            return True
    return False


def _loaded_since(events: list[dict], guide: str, window_days: int) -> bool:
    cutoff = f"-{window_days}d"
    # ts is "YYYY-MM-DDTHH:MM:SS"; a day-level comparison is sufficient here.
    import datetime as _dt

    limit = _dt.date.today() - _dt.timedelta(days=window_days)
    for ev in events:
        if ev.get("event") == "guide_loaded" and ev.get("guide") == guide:
            try:
                day = _dt.date.fromisoformat(str(ev.get("ts", ""))[:10])
            except ValueError:
                continue
            if day >= limit:
                return True
    del cutoff
    return False


def default_deploy_roots(project_root: Path) -> list[Path]:
    from pactkit.doctor import DEPLOY_PROBE_PATHS

    return [Path(t.format(home=Path.home(), root=project_root)) for t in DEPLOY_PROBE_PATHS]


def diagnose_guide(
    guide: str,
    project_root: Path,
    config: dict,
    events: list[dict],
    window_days: int = _DEFAULT_WINDOW_DAYS,
    deploy_roots: list[Path] | None = None,
) -> dict | None:
    """Signal 1: guide zero-load decision tree (ordered, short-circuit).

    1. deployed?        no  -> bug (registered but not on this host)
    2. config excludes? yes -> config (exact yaml fix)
    3. concern in specs? no  -> rule_design (not applicable here — prune/merge)
    4. loaded recently? no  -> usage (medium confidence — choke point bypassable)
    """
    project_root = Path(project_root)
    deployed = False
    for base in (deploy_roots if deploy_roots is not None else default_deploy_roots(project_root)):
        candidates = [
            base / "skills" / "_rules" / "guides" / f"{guide}.md",
            base / "skills" / "project-act" / "references" / "guides" / f"{guide}.md",
        ]
        if any(c.is_file() for c in candidates):
            deployed = True
            break
    if not deployed:
        return _finding(
            "bug",
            {"guide": guide, "deployed": False},
            f"guide '{guide}' is registered but not deployed to this host — "
            f"run `pactkit update`; if it persists, report an issue with this output",
        )

    # Guides deploy unconditionally in the current architecture; a guide can
    # only be config-excluded via an explicit `guides:` list (E2E 2026-09-03:
    # checking `rules:` misfired — that key governs capsules, not guides —
    # producing false class-① findings telling users to change a no-op key).
    guides_config = config.get("guides")
    if isinstance(guides_config, list) and guide not in guides_config:
        return _finding(
            "config",
            {"guide": guide, "guides_config": sorted(guides_config)},
            f"guide '{guide}' is excluded by pactkit.yaml — add it under `guides:` "
            f"to enable:\n  guides:\n    - {guide}",
        )

    if not _concern_in_specs(guide, project_root):
        return _finding(
            "rule_design",
            {"guide": guide, "concern_in_specs": False},
            f"no '{guide}' concern scenes in this project's specs — the guide is not "
            f"applicable here; consider excluding it, or merging with a neighbor "
            f"(feedback to PactKit maintainers)",
        )

    if not _loaded_since(events, guide, window_days):
        return _finding(
            "usage",
            {"guide": guide, "window_days": window_days, "loads": 0},
            f"concern scenes exist but '{guide}' has zero loads in {window_days} days — "
            f"Act Phase 1.5 is being skipped or bypassed by raw file reads; verify the "
            f"phase-1.5 guide checklist at Act exit. Confidence: medium (the "
            f"`pactkit guide show` choke point can be bypassed)",
            confidence="medium",
        )
    return None


def diagnose_w012(
    warning_events: list[dict],
    lint_count: int,
    specs_text: dict[str, str],
    rate_threshold: float = 0.5,
) -> dict | None:
    """Signal 2: W012 trigger-rate decision tree."""
    if not warning_events or lint_count <= 0:
        return None
    # 1. false-positive sample: warned spec that actually carries the table
    for ev in warning_events[-3:]:
        spec = str(ev.get("spec", ""))
        text = specs_text.get(spec, "")
        if _ASSESSMENT_HEADING.lower() in text.lower():
            return _finding(
                "bug",
                {"spec": spec, "rule": "W012", "false_positive": True},
                f"W012 fired on '{spec}' but it contains a Capability Assessment — "
                f"detector false positive; report an issue with the spec path",
            )
    rate = len(warning_events) / max(lint_count, 1)
    if rate > rate_threshold:
        return _finding(
            "usage",
            {"rate": round(rate, 2), "threshold": rate_threshold, "count": len(warning_events)},
            f"{len(warning_events)} of {lint_count} lint runs warned W012 — the plan-phase "
            f"capability-assessment habit is missing; adopt a plan-exit self-check for the "
            f"Need|Source|Decision table",
        )
    return None


def assess_spec_texts(project_root: Path) -> dict[str, str]:
    """Read all specs as {story_id: text} (doctor scan input)."""
    specs = _specs_root(project_root)
    out: dict[str, str] = {}
    if not specs.is_dir():
        return out
    for spec in sorted(specs.glob("*.md")):
        try:
            out[spec.stem] = spec.read_text(encoding="utf-8")
        except OSError:
            continue
    return out


def assessment_presence_rate(specs_text: dict[str, str]) -> float:
    if not specs_text:
        return 0.0
    with_table = sum(
        1 for text in specs_text.values() if _ASSESSMENT_HEADING.lower() in text.lower()
    )
    return with_table / len(specs_text)


def run_diagnosis(
    project_root: Path,
    config: dict,
    events: list[dict],
    guides: list[str] | None = None,
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    w012_rate_threshold: float = 0.5,
    lint_count: int | None = None,
) -> list[dict]:
    """Full pass: signals 1/2/4 (signal 3 cross-checks via signal 2 output)."""
    project_root = Path(project_root)
    findings: list[dict] = []
    if guides is None:
        from pactkit.prompts.guides import GUIDE_DEFINITIONS

        guides = [name.removesuffix(".md") for name in GUIDE_DEFINITIONS]
    for guide in guides:
        finding = diagnose_guide(guide, project_root, config, events, window_days)
        if finding:
            findings.append(finding)
    warning_events = [e for e in events if e.get("event") == "rule_warning"]
    specs_text = assess_spec_texts(project_root)
    if lint_count is None:
        lint_count = len({e.get("spec") for e in warning_events}) or len(specs_text) or 1
    finding = diagnose_w012(warning_events, lint_count, specs_text, w012_rate_threshold)
    if finding:
        findings.append(finding)

    # Merge same-class guide findings into one (spec: 三类及以上同类合并为一条).
    by_class: dict[str, list[dict]] = {}
    for f in findings:
        by_class.setdefault(f["class"], []).append(f)
    merged: list[dict] = []
    for cls, group in by_class.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        guides = [g["evidence"].get("guide") for g in group if g["evidence"].get("guide")]
        action = group[0]["action"]
        note = ""
        if _telemetry_age_days(events) < window_days:
            note = (
                f" (telemetry recording started {_telemetry_age_days(events)} day(s) ago — "
                f"window incomplete; re-check after {window_days} days)"
            )
        merged.append({
            "class": cls,
            "evidence": {"guides": guides, "count": len(group)},
            "action": f"{len(group)} guides share this diagnosis ({', '.join(map(str, guides))}): "
                      f"{action}{note}",
            "confidence": group[0]["confidence"],
        })
    return merged


def _telemetry_age_days(events: list[dict]) -> int:
    import datetime as _dt

    stamps = []
    for ev in events:
        try:
            stamps.append(_dt.date.fromisoformat(str(ev.get("ts", ""))[:10]))
        except ValueError:
            continue
    if not stamps:
        return 0
    return (_dt.date.today() - min(stamps)).days
