"""STORY-slim-142: deploy(format=all, target=...) skips adapters + doctor adapter skew.

Pollution chain (2026-08-17): tests calling `pactkit init -t <tmp>` with the
default format=all triggered adapter deployers with target=None, writing stale
content into the real ~/.config/opencode. R1 skips adapters whenever an
explicit target is given; R3 surfaces adapter/core version skew in doctor.
"""


class _SpyDeployer:
    """Records deploy() invocations."""

    def __init__(self, sink: list):
        self._sink = sink

    def deploy(self, config=None, target=None):
        self._sink.append(target)


def _registry_with_spies(monkeypatch):
    """Replace the deployer registry with classic+adapter spies."""
    # Import first: deployer.py self-registers "classic" at module import;
    # patching the registry before import would collide with that.
    import pactkit.generators.deployer as deployer_mod
    from pactkit.generators import deploy_base

    calls: dict[str, list] = {"classic": [], "opencode": []}
    monkeypatch.setitem(deploy_base._DEPLOYER_REGISTRY, "classic", lambda: _SpyDeployer(calls["classic"]))
    monkeypatch.setitem(deploy_base._DEPLOYER_REGISTRY, "opencode", lambda: _SpyDeployer(calls["opencode"]))
    # Prevent lazy entry-point loading from re-registering real adapters.
    monkeypatch.setattr(deployer_mod, "_ep_loaded", True)
    return calls


# ---------------------------------------------------------------------------
# R1/R2: format=all + explicit target skips adapters
# ---------------------------------------------------------------------------


class TestAllTargetSkipsAdapters:
    def test_adapter_not_called_when_target_given(self, tmp_path, monkeypatch, capsys):
        calls = _registry_with_spies(monkeypatch)

        from pactkit.generators.deployer import deploy

        deploy(config={}, target=tmp_path, format="all", non_interactive=True)

        assert calls["classic"] == [tmp_path]  # classic honors target
        assert calls["opencode"] == []  # adapter skipped entirely
        assert "Skipping adapter" in capsys.readouterr().out

    def test_adapter_called_when_no_target(self, monkeypatch):
        calls = _registry_with_spies(monkeypatch)

        from pactkit.generators.deployer import deploy

        deploy(config={}, target=None, format="all", non_interactive=True)

        assert calls["classic"] == [None]
        assert calls["opencode"] == [None]  # real init: adapters deploy to their homes


# ---------------------------------------------------------------------------
# R3: doctor adapter version skew
# ---------------------------------------------------------------------------


class TestAdapterSkew:
    def test_outdated_adapter_warns(self, monkeypatch):
        import importlib.metadata

        from pactkit import __version__
        from pactkit.doctor import check_adapter_skew

        def fake_version(pkg):
            if pkg == "pactkit-opencode":
                return "2.9.1"
            raise importlib.metadata.PackageNotFoundError(pkg)

        monkeypatch.setattr(importlib.metadata, "version", fake_version)
        monkeypatch.setattr(
            "importlib.metadata.entry_points",
            lambda group: [type("EP", (), {"name": "opencode"})()] if group == "pactkit.deployers" else [],
        )

        warnings = check_adapter_skew()
        assert any("pactkit-opencode" in w and "2.9.1" in w and __version__ in w for w in warnings)

    def test_current_adapter_silent(self, monkeypatch):
        import importlib.metadata

        from pactkit import __version__
        from pactkit.doctor import check_adapter_skew

        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: __version__)
        monkeypatch.setattr(
            "importlib.metadata.entry_points",
            lambda group: [type("EP", (), {"name": "opencode"})()] if group == "pactkit.deployers" else [],
        )

        assert check_adapter_skew() == []

    def test_missing_adapter_silent(self, monkeypatch):
        """SEC-7: adapter entry point present but package metadata gone — no crash."""
        import importlib.metadata

        from pactkit.doctor import check_adapter_skew

        def raise_missing(pkg):
            raise importlib.metadata.PackageNotFoundError(pkg)

        monkeypatch.setattr(importlib.metadata, "version", raise_missing)
        monkeypatch.setattr(
            "importlib.metadata.entry_points",
            lambda group: [type("EP", (), {"name": "opencode"})()] if group == "pactkit.deployers" else [],
        )

        assert check_adapter_skew() == []

    def test_no_entry_points_silent(self, monkeypatch):
        from pactkit.doctor import check_adapter_skew

        monkeypatch.setattr("importlib.metadata.entry_points", lambda group: [])
        assert check_adapter_skew() == []
