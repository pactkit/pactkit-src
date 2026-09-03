"""STORY-slim-20260903a4ef6915ed62: rule telemetry + four-class diagnosis.

Boundary tests for the diagnosis decision trees (config/bug/usage/rule_design),
the guide-show choke point, event recording, and the locality red line.
"""

import json
from pathlib import Path

import pytest


def _write_events(root: Path, events: list[dict]) -> Path:
    path = root / ".pactkit" / "events"
    path.mkdir(parents=True, exist_ok=True)
    with (path / "rules.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")
    return root


# ---------------------------------------------------------------------------
# R1: event recording + payload whitelist
# ---------------------------------------------------------------------------


class TestRuleEvents:
    def test_append_event_whitelist_payload(self, tmp_path):
        from pactkit.rule_events import append_rule_event

        append_rule_event(tmp_path, "guide_loaded", {"guide": "caching"})
        append_rule_event(tmp_path, "rule_warning", {"rule": "W012", "spec": "STORY-1"})
        lines = (tmp_path / ".pactkit" / "events" / "rules.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            payload = json.loads(line)
            allowed = {"event", "guide", "rule", "spec", "ts"}
            assert set(payload) <= allowed, f"payload leaks fields: {set(payload) - allowed}"

    def test_unknown_event_rejected(self, tmp_path):
        from pactkit.rule_events import append_rule_event

        with pytest.raises(ValueError):
            append_rule_event(tmp_path, "exfil_attempt", {"anything": "x"})

    def test_recording_failure_never_raises(self, tmp_path, monkeypatch):
        from pactkit.rule_events import append_rule_event

        monkeypatch.setattr(Path, "write_text", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
        append_rule_event(tmp_path, "guide_loaded", {"guide": "caching"})  # MUST NOT raise


# ---------------------------------------------------------------------------
# R2: guide show choke point
# ---------------------------------------------------------------------------


class TestGuideShow:
    def _deployed_root(self, tmp_path: Path) -> Path:
        g = tmp_path / "skills" / "_rules" / "guides" / "caching.md"
        g.parent.mkdir(parents=True)
        g.write_text("# Caching guide body\n", encoding="utf-8")
        return tmp_path

    def test_show_prints_and_records(self, tmp_path, capsys):
        from pactkit.rule_events import read_rule_events
        from pactkit.cli import _run_guide_show  # choke-point helper

        root = self._deployed_root(tmp_path)
        code = _run_guide_show("caching", deploy_roots=[root], project_root=tmp_path)
        out = capsys.readouterr().out
        assert code == 0
        assert "Caching guide body" in out
        events = read_rule_events(tmp_path)
        assert any(e["event"] == "guide_loaded" and e["guide"] == "caching" for e in events)

    def test_unknown_guide_lists_available_exit1(self, tmp_path, capsys):
        from pactkit.cli import _run_guide_show

        root = self._deployed_root(tmp_path)
        code = _run_guide_show("nope", deploy_roots=[root], project_root=tmp_path)
        assert code == 1
        captured = capsys.readouterr()
        assert "caching" in captured.out + captured.err  # available names listed

    def test_guide_name_whitelist_no_traversal(self, tmp_path):
        from pactkit.cli import _run_guide_show

        root = self._deployed_root(tmp_path)
        # a path-traversal-ish name must not resolve outside guides/
        code = _run_guide_show("../rules/pactkit-runtime", deploy_roots=[root], project_root=tmp_path)
        assert code == 1


# ---------------------------------------------------------------------------
# R3: diagnosis engine — four-class boundaries
# ---------------------------------------------------------------------------


def _cfg(excluded=None):
    return {"rules": sorted({"runtime", "pdca-lifecycle", "phase-act"} | (set() if not excluded else set()))}


class TestSignal1GuideZeroLoad:
    def _root(self, tmp_path, *, deployed, excluded, concern_in_specs):
        root = tmp_path / "proj"
        if deployed:
            g = root / "skills" / "_rules" / "guides" / "caching.md"
            g.parent.mkdir(parents=True)
            g.write_text("body", encoding="utf-8")
        specs = root / "docs" / "specs"
        specs.mkdir(parents=True)
        if concern_in_specs:
            (specs / "STORY-1.md").write_text(
                "# S\n\n## Technical Design\n\n加缓存 cache Redis 缓存层\n", encoding="utf-8",
            )
        cfg = (
            {"rules": ["runtime"], "guides": []}
            if excluded
            else {"rules": ["runtime"], "guides": ["caching"]}
        )
        return root, cfg

    def test_undeployed_guide_is_bug(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_guide

        root, cfg = self._root(tmp_path, deployed=False, excluded=False, concern_in_specs=True)
        finding = diagnose_guide("caching", root, cfg, events=[], window_days=30, deploy_roots=[root])
        assert finding["class"] == "bug"

    def test_excluded_guide_is_config_with_yaml_action(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_guide

        root, cfg = self._root(tmp_path, deployed=True, excluded=True, concern_in_specs=True)
        finding = diagnose_guide("caching", root, cfg, events=[], window_days=30, deploy_roots=[root])
        assert finding["class"] == "config"
        assert "guides:" in finding["action"]

    def test_no_concern_scene_is_rule_design(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_guide

        root, cfg = self._root(tmp_path, deployed=True, excluded=False, concern_in_specs=False)
        finding = diagnose_guide("caching", root, cfg, events=[], window_days=30, deploy_roots=[root])
        assert finding["class"] == "rule_design"

    def test_concern_present_zero_load_is_usage_with_confidence(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_guide

        root, cfg = self._root(tmp_path, deployed=True, excluded=False, concern_in_specs=True)
        finding = diagnose_guide("caching", root, cfg, events=[], window_days=30, deploy_roots=[root])
        assert finding["class"] == "usage"
        assert finding["confidence"] == "medium"
        assert "bypass" in finding["action"].lower() or "绕过" in finding["action"]

    def test_finding_carries_class_evidence_action(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_guide

        root, cfg = self._root(tmp_path, deployed=True, excluded=True, concern_in_specs=True)
        finding = diagnose_guide("caching", root, cfg, events=[], window_days=30, deploy_roots=[root])
        for key in ("class", "evidence", "action"):
            assert key in finding


class TestSignal2W012Rate:
    def test_false_positive_is_bug(self, tmp_path):
        from pactkit.rule_diagnostics import diagnose_w012

        finding = diagnose_w012(
            warning_events=[{"rule": "W012", "spec": "S1"}],
            lint_count=1,
            specs_text={"S1": "### Capability Assessment\n| Need |"},
        )
        assert finding["class"] == "bug"

    def test_high_rate_is_usage(self):
        from pactkit.rule_diagnostics import diagnose_w012

        finding = diagnose_w012(
            warning_events=[{"rule": "W012", "spec": f"S{i}"} for i in range(6)],
            lint_count=10,
            specs_text={f"S{i}": "no assessment" for i in range(6)},
        )
        assert finding["class"] == "usage"

    def test_low_rate_no_finding(self):
        from pactkit.rule_diagnostics import diagnose_w012

        assert diagnose_w012(
            warning_events=[{"rule": "W012", "spec": "S1"}],
            lint_count=50,
            specs_text={"S1": "no"},
        ) is None


# ---------------------------------------------------------------------------
# R4/R5: doctor + garden wiring
# ---------------------------------------------------------------------------


class TestConsumers:
    def test_doctor_check_rule_health_emits_config_finding(self, tmp_path, monkeypatch):
        from pactkit import doctor
        from pactkit.rule_events import append_rule_event

        root = tmp_path / "proj"
        g = root / "skills" / "_rules" / "guides" / "caching.md"
        g.parent.mkdir(parents=True)
        g.write_text("x", encoding="utf-8")
        append_rule_event(root, "guide_loaded", {"guide": "other"})

        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude" / "pactkit.yaml").write_text("guides:\n  - other\n", encoding="utf-8")
        result = doctor.check_rule_health(root)
        assert any(f["class"] == "config" for f in result["findings"])
        assert isinstance(result.get("warnings"), list)

    def test_garden_dead_rules_skips_excluded(self, tmp_path):
        from pactkit.garden import check_dead_rules

        root = tmp_path / "proj"
        (root / "docs" / "specs").mkdir(parents=True)
        result = check_dead_rules(root, {"rules": ["runtime"], "guides": ["database"]})  # caching excluded
        # excluded guides are doctor's ①-class, not garden's — no double report
        assert not any(f.get("guide") == "caching" for f in result.get("findings", []))


# ---------------------------------------------------------------------------
# R6: locality red line
# ---------------------------------------------------------------------------


class TestLocality:
    def test_no_network_in_event_path(self, tmp_path, monkeypatch):
        import socket

        from pactkit.rule_events import append_rule_event

        called = []
        monkeypatch.setattr(socket, "create_connection", lambda *a, **k: called.append(a))
        monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
        append_rule_event(tmp_path, "guide_loaded", {"guide": "x"})
        assert not called
