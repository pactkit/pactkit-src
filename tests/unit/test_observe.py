"""
STORY-slim-073: Agent Observability — observe.py unit tests.

Tests for signal classification, report formatting, and graceful degradation.
"""
from __future__ import annotations


# ===========================================================================
# R3: Signal Severity Classification
# ===========================================================================


class TestSignalClassification:
    """R3: classify_signals assigns correct severity levels."""

    def test_console_error_is_error(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [{"level": "error", "message": "TypeError", "source": "app.js:42"}],
            "network_failures": [],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert classified["errors"]
        assert any("TypeError" in e["message"] for e in classified["errors"])

    def test_http_500_is_error(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [{"url": "/api/users", "status": 500, "method": "POST"}],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert any(e["status"] == 500 for e in classified["errors"])

    def test_http_4xx_except_404_is_warning(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [{"url": "/api/data", "status": 403, "method": "GET"}],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert any(w["status"] == 403 for w in classified["warnings"])

    def test_http_404_is_excluded(self):
        """AC6: HTTP 404 is excluded by default."""
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [{"url": "/missing", "status": 404, "method": "GET"}],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert len(classified["errors"]) == 0
        assert len(classified["warnings"]) == 0

    def test_console_warning_is_warning(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [{"level": "warning", "message": "Deprecation", "source": "lib.js:1"}],
            "network_failures": [],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert any("Deprecation" in w["message"] for w in classified["warnings"])

    def test_slow_lcp_is_warning(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [],
            "performance": {"lcp_ms": 3000, "fcp_ms": 400, "cls": 0.05},
        }
        classified = classify_signals(signals)
        assert any("LCP" in w.get("metric", "") for w in classified["warnings"])

    def test_good_performance_no_issues(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [],
            "performance": {"lcp_ms": 1200, "fcp_ms": 400, "cls": 0.05},
        }
        classified = classify_signals(signals)
        assert len(classified["errors"]) == 0
        assert len(classified["warnings"]) == 0

    def test_null_performance_no_crash(self):
        from pactkit.observe import classify_signals
        signals = {
            "console_errors": [],
            "network_failures": [],
            "performance": None,
        }
        classified = classify_signals(signals)
        assert len(classified["errors"]) == 0


# ===========================================================================
# R4: Report Formatting
# ===========================================================================


class TestReportFormatting:
    """R4: build_report produces structured human-readable output."""

    def test_report_has_console_section(self):
        from pactkit.observe import build_report
        classified = {
            "errors": [{"type": "console", "message": "TypeError", "source": "app.js:42"}],
            "warnings": [],
            "info": [],
        }
        report = build_report(classified)
        assert "### Console" in report
        assert "[E]" in report
        assert "TypeError" in report

    def test_report_has_network_section(self):
        from pactkit.observe import build_report
        classified = {
            "errors": [{"type": "network", "method": "POST", "url": "/api/users", "status": 500}],
            "warnings": [],
            "info": [],
        }
        report = build_report(classified)
        assert "### Network" in report
        assert "POST /api/users" in report
        assert "500" in report

    def test_report_has_performance_section(self):
        from pactkit.observe import build_report
        classified = {
            "errors": [],
            "warnings": [],
            "info": [],
            "performance": {"lcp_ms": 1200, "fcp_ms": 400, "cls": 0.05},
        }
        report = build_report(classified)
        assert "### Performance" in report
        assert "LCP:" in report

    def test_report_verdict_pass_when_clean(self):
        from pactkit.observe import build_report
        classified = {"errors": [], "warnings": [], "info": []}
        report = build_report(classified)
        assert "PASS" in report

    def test_report_verdict_warn_on_errors(self):
        from pactkit.observe import build_report
        classified = {
            "errors": [{"type": "console", "message": "err", "source": "a.js:1"}],
            "warnings": [],
            "info": [],
        }
        report = build_report(classified)
        assert "WARN" in report


# ===========================================================================
# R7: Graceful Degradation
# ===========================================================================


class TestGracefulDegradation:
    """R7: run_observe handles no MCP sources gracefully."""

    def test_no_sources_exits_zero(self):
        from pactkit.observe import run_observe
        output, exit_code = run_observe(detect_fn=lambda: [])
        assert exit_code == 0
        assert "No observability sources available" in output

    def test_empty_signals_produces_clean_report(self):
        from pactkit.observe import classify_signals, build_report
        signals = {
            "console_errors": [],
            "network_failures": [],
            "performance": None,
        }
        classified = classify_signals(signals)
        report = build_report(classified)
        assert "PASS" in report
