"""Agent Observability — structured runtime signal collection and reporting.

STORY-slim-073: Collects console errors, network failures, and performance
metrics from MCP sources, classifies them by severity, and produces
human-readable or JSON reports.

All functions are pure (no side effects) except run_observe() which
orchestrates the pipeline.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# R3: Signal Severity Classification
# ---------------------------------------------------------------------------

# Thresholds
_LCP_WARN_MS = 2500


def classify_signals(signals: dict) -> dict:
    """Classify raw signals into errors, warnings, and info.

    Args:
        signals: dict with keys console_errors, network_failures, performance.

    Returns:
        dict with keys errors, warnings, info (lists of dicts),
        plus optional performance dict.
    """
    errors: list[dict] = []
    warn: list[dict] = []
    info: list[dict] = []

    # Console messages
    for msg in signals.get("console_errors") or []:
        level = msg.get("level", "error")
        entry = {"type": "console", "message": msg.get("message", ""), "source": msg.get("source", "")}
        if level == "error":
            errors.append(entry)
        elif level == "warning":
            warn.append(entry)
        else:
            info.append(entry)

    # Network failures
    for req in signals.get("network_failures") or []:
        status = req.get("status", 0)
        entry = {
            "type": "network",
            "method": req.get("method", ""),
            "url": req.get("url", ""),
            "status": status,
        }
        if status >= 500:
            errors.append(entry)
        elif 400 <= status < 500 and status != 404:
            warn.append(entry)
        # 404 and 3xx/2xx are excluded from issues

    # Performance metrics
    perf = signals.get("performance")
    result: dict = {"errors": errors, "warnings": warn, "info": info}
    if perf and isinstance(perf, dict):
        result["performance"] = perf
        lcp = perf.get("lcp_ms", 0)
        if lcp > _LCP_WARN_MS:
            warn.append({"type": "performance", "metric": "LCP", "value_ms": lcp, "threshold_ms": _LCP_WARN_MS})

    return result


# ---------------------------------------------------------------------------
# R4: Report Formatting
# ---------------------------------------------------------------------------


def build_report(classified: dict) -> str:
    """Build a human-readable observability report.

    Args:
        classified: output from classify_signals().

    Returns:
        Markdown-formatted report string.
    """
    lines: list[str] = []
    errors = classified.get("errors", [])
    warnings_list = classified.get("warnings", [])

    # Console section
    console_errors = [e for e in errors if e.get("type") == "console"]
    console_warns = [w for w in warnings_list if w.get("type") == "console"]
    if console_errors or console_warns:
        lines.append(f"### Console ({len(console_errors)} errors, {len(console_warns)} warnings)")
        for e in console_errors:
            lines.append(f"[E] {e.get('source', '?')} — {e.get('message', '')}")
        for w in console_warns:
            lines.append(f"[W] {w.get('source', '?')} — {w.get('message', '')}")
        lines.append("")

    # Network section
    net_errors = [e for e in errors if e.get("type") == "network"]
    net_warns = [w for w in warnings_list if w.get("type") == "network"]
    if net_errors or net_warns:
        lines.append(f"### Network ({len(net_errors) + len(net_warns)} failures)")
        for e in net_errors:
            lines.append(f"[E] {e.get('method', '')} {e.get('url', '')} → {e.get('status', '')} Internal Server Error")
        for w in net_warns:
            lines.append(f"[W] {w.get('method', '')} {w.get('url', '')} → {w.get('status', '')}")
        lines.append("")

    # Performance section
    perf = classified.get("performance")
    if perf and isinstance(perf, dict):
        lcp = perf.get("lcp_ms", 0)
        fcp = perf.get("fcp_ms", 0)
        cls_val = perf.get("cls", 0)
        lcp_mark = "✓" if lcp <= _LCP_WARN_MS else "⚠"
        lines.append("### Performance")
        lines.append(f"LCP: {lcp}ms {lcp_mark} | FCP: {fcp}ms ✓ | CLS: {cls_val} ✓")
        lines.append("")

    # Verdict
    if errors:
        lines.append(f"### Verdict: WARN ({len(errors)} errors)")
    else:
        lines.append("### Verdict: PASS")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R1 + R7: Run observe pipeline
# ---------------------------------------------------------------------------


def run_observe(
    *,
    report: bool = False,
    json_output: bool = False,
    detect_fn=None,
) -> tuple[str, int]:
    """Run the observability pipeline.

    Args:
        report: If True, produce human-readable report.
        json_output: If True, produce JSON output.
        detect_fn: Callable returning list of available source names.
                   Defaults to _detect_sources().

    Returns:
        (output_string, exit_code) tuple.
    """
    if detect_fn is None:
        detect_fn = _detect_sources

    sources = detect_fn()
    if not sources:
        return "No observability sources available — skipping", 0

    # Collect signals from available sources
    signals = _collect_signals(sources)
    classified = classify_signals(signals)

    if json_output:
        import json
        return json.dumps(classified, indent=2), 0

    output = build_report(classified)
    return output, 0


def _detect_sources() -> list[str]:
    """Detect available MCP observability sources.

    Returns list of source names (e.g., ['chrome-devtools', 'playwright']).
    In CLI context, MCP tools are not directly callable — this returns
    an empty list. The actual detection happens in the agent runtime.
    """
    return []


def _collect_signals(sources: list[str]) -> dict:
    """Collect signals from available sources.

    In CLI context, returns empty signal structure.
    Actual collection happens via MCP tools in agent runtime.
    """
    return {
        "console_errors": [],
        "network_failures": [],
        "performance": None,
    }
