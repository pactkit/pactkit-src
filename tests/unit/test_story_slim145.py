"""Tests for STORY-slim-145: Codex deploy semantic integrity + adapter compat gate.

RED phase — these fail until Core R1/R2/R4/R6 are implemented.

Covers: CLI policy (R1), operation tokens (R2), prompt integrity (R4),
Classic/Codex parity (R5), version gate + editable divergence (R6).
"""

from __future__ import annotations

import importlib.metadata

import pytest

from pactkit.generators.deploy_base import DeployerBase
from pactkit.generators.deployer import _render_prompt
from pactkit.profiles import FORMAT_PROFILES, CLIPolicy, get_profile


# ---------------------------------------------------------------------------
# R1: CLI availability modeled as deploy policy, not fixed format fact
# ---------------------------------------------------------------------------


class TestCLIPolicy:
    """R1 / AC2: CLIPolicy enum + profile assignments + backward-compat property."""

    def test_policy_enum_has_three_values(self):
        assert {p.value for p in CLIPolicy} == {"required", "preferred", "unavailable"}

    def test_classic_is_required(self):
        assert get_profile("classic").cli_policy is CLIPolicy.REQUIRED

    def test_opencode_is_required(self):
        assert get_profile("opencode").cli_policy is CLIPolicy.REQUIRED

    def test_codex_is_preferred(self):
        """R1: codex no longer claims CLI-less; it preserves the CLI (preferred)."""
        assert get_profile("codex").cli_policy is CLIPolicy.PREFERRED

    def test_copilot_is_unavailable(self):
        assert get_profile("copilot").cli_policy is CLIPolicy.UNAVAILABLE

    def test_has_pactkit_cli_derived_from_policy(self):
        """Legacy boolean is now a derived property: required/preferred->True."""
        assert get_profile("classic").has_pactkit_cli is True
        assert get_profile("codex").has_pactkit_cli is True  # R1 change: codex preserves CLI
        assert get_profile("opencode").has_pactkit_cli is True
        assert get_profile("copilot").has_pactkit_cli is False

    def test_every_profile_has_cli_policy(self):
        for name, profile in FORMAT_PROFILES.items():
            assert hasattr(profile, "cli_policy"), f"{name} missing cli_policy"
            assert isinstance(profile.cli_policy, CLIPolicy), f"{name}.cli_policy not CLIPolicy"


# ---------------------------------------------------------------------------
# R2: Structured operation rendering contract (tokens in _render_prompt var_map)
# ---------------------------------------------------------------------------

_OPERATION_TOKENS = [
    "REGRESSION", "LINT", "CONTEXT_CONTINUATION", "CLEANUP",
    "LAZY_VISUALIZE", "INSTALL_UPDATE", "GUARD", "DOCTOR",
]


class TestOperationTokens:
    """R2 / AC1 / AC2 / AC9: {PACTKIT_OP_*} tokens resolve via CLI policy."""

    @pytest.mark.parametrize("token", _OPERATION_TOKENS)
    def test_token_resolved_for_codex(self, token):
        placeholder = "{PACTKIT_OP_" + token + "}"
        out = _render_prompt("Run " + placeholder + " now", get_profile("codex"))
        assert placeholder not in out, f"token {token} left unresolved"

    def test_cli_preserving_profile_keeps_pactkit_regression(self):
        out = _render_prompt("Run {PACTKIT_OP_REGRESSION}", get_profile("classic"))
        assert "`pactkit regression`" in out
        assert "Run run" not in out

    def test_codex_preferred_keeps_pactkit_regression(self):
        """R1/R2: codex=preferred -> regression stays a real pactkit CLI call."""
        out = _render_prompt("Run {PACTKIT_OP_REGRESSION}", get_profile("codex"))
        assert "`pactkit regression`" in out
        assert "Run run" not in out

    def test_unavailable_profile_uses_complete_fallback(self):
        out = _render_prompt("Run {PACTKIT_OP_REGRESSION}", get_profile("copilot"))
        assert "pactkit regression" not in out
        assert "Run run" not in out

    def test_context_continuation_no_stranded_arg(self):
        """Historical corruption: --continuation must not strand into prose."""
        out = _render_prompt("Run {PACTKIT_OP_CONTEXT_CONTINUATION}", get_profile("codex"))
        assert "manually --continuation" not in out
        assert "Run run" not in out
        assert out.count("`") % 2 == 0  # backticks balanced

    def test_unavailable_profile_replaces_hardcoded_cli_span(self):
        """R2 equivalent (Core replace): hardcoded `pactkit regression` code span
        in a CLI-unavailable profile resolves to a complete fallback — no stranded
        args, no double imperative, balanced backticks."""
        out = _render_prompt("Run `pactkit regression` to classify changes.", get_profile("copilot"))
        assert "`pactkit regression`" not in out
        assert "Run run" not in out
        assert out.count("`") % 2 == 0

    def test_unavailable_profile_replaces_context_continuation_span(self):
        """Core replace: `pactkit context --continuation ...` span -> fallback, no stray option."""
        out = _render_prompt("Run `pactkit context --continuation --phase X`", get_profile("copilot"))
        assert "`pactkit context" not in out  # CLI span replaced
        assert "manually --continuation" not in out
        assert "Run run" not in out


# ---------------------------------------------------------------------------
# R4: Prompt integrity (lexical + semantic) validation
# ---------------------------------------------------------------------------


class TestPromptIntegrityLexical:
    """R4 / AC4: lexical corruption signatures detected."""

    def test_detects_double_imperative_run_run(self):
        content = "Run run the full test suite directly"
        v = DeployerBase.validate_deployed_content(content, get_profile("codex"))
        assert v, "double imperative 'Run run' not detected"

    def test_detects_stranded_cli_option(self):
        content = "update `docs/product/context.md` manually --continuation"
        v = DeployerBase.validate_deployed_content(content, get_profile("codex"))
        assert v, "stranded --continuation not detected"

    def test_detects_unbalanced_backticks(self):
        content = "Run `pactkit regression now"
        v = DeployerBase.validate_deployed_content(content, get_profile("codex"))
        assert v, "unbalanced backticks not detected"

    def test_clean_codex_content_passes(self):
        content = "Run `pactkit regression` to classify SKIP/IMPACT/FULL."
        v = DeployerBase.validate_deployed_content(content, get_profile("codex"))
        assert v == []


class TestPromptIntegritySemantic:
    """R4 / AC3 / AC4: required Act workflow operations must be present."""

    def test_missing_required_act_operation_fails(self):
        # project-act playbook missing regression classification + coverage output
        content = (
            "# Command: Act\n"
            "/project-act STORY-XXX. Spec lint. TDD RED/GREEN. lint. context. graph. board."
        )
        v = DeployerBase.validate_deployed_content(content, get_profile("codex"))
        assert v, "missing required Act operation not detected"


# ---------------------------------------------------------------------------
# R5: Classic / Codex behavioral equivalence
# ---------------------------------------------------------------------------


class TestClassicCodexParity:
    """R5 / AC3: normalized required operation sets are equivalent."""

    def test_required_operation_sets_equivalent(self):
        template = (
            "Run {PACTKIT_OP_REGRESSION} ; Run {PACTKIT_OP_LINT} ; "
            "Run {PACTKIT_OP_CONTEXT_CONTINUATION} ; {PACTKIT_OP_LAZY_VISUALIZE}"
        )
        classic = _render_prompt(template, get_profile("classic"))
        codex = _render_prompt(template, get_profile("codex"))
        for op in ["regression", "lint", "context", "visualize"]:
            assert op in classic.lower(), f"missing {op} in classic"
            assert op in codex.lower(), f"missing {op} in codex"


# ---------------------------------------------------------------------------
# R6: Adapter/Core version compat gate + editable metadata divergence
# ---------------------------------------------------------------------------


class TestCoreMetadataDivergence:
    """R6 / AC6: pactkit.__version__ vs importlib.metadata divergence reported."""

    def test_divergence_reported(self, monkeypatch):
        from pactkit.doctor import check_core_metadata_divergence

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "2.19.0")
        warnings = check_core_metadata_divergence()
        assert any("2.20.0" in w and "2.19.0" in w for w in warnings)

    def test_aligned_no_warning(self, monkeypatch):
        from pactkit.doctor import check_core_metadata_divergence

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "2.20.0")
        assert check_core_metadata_divergence() == []

    def test_metadata_lookup_failure_safe(self, monkeypatch):
        """SEC-7: PackageNotFoundError must not crash (degrade to diagnostic)."""
        from pactkit.doctor import check_core_metadata_divergence

        def raise_missing(pkg):
            raise importlib.metadata.PackageNotFoundError(pkg)

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", raise_missing)
        assert check_core_metadata_divergence() == []


class TestDeployTimeCompatGate:
    """R6 / AC5: major/minor mismatch blocks adapter deployment before write."""

    def test_major_minor_mismatch_blocks(self, monkeypatch):
        from pactkit.cli import _check_adapter_compat

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "2.19.0")
        errors = _check_adapter_compat("codex")
        assert errors, "major/minor mismatch did not block"

    def test_allow_adapter_skew_override(self, monkeypatch):
        from pactkit.cli import _check_adapter_compat

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "2.19.0")
        errors = _check_adapter_compat("codex", allow_skew=True)
        assert not errors, "--allow-adapter-skew did not override"

    def test_aligned_adapter_no_block(self, monkeypatch):
        from pactkit.cli import _check_adapter_compat

        monkeypatch.setattr("pactkit.__version__", "2.20.0")
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "2.20.0")
        errors = _check_adapter_compat("codex")
        assert not errors


# ---------------------------------------------------------------------------
# F1: validate must BLOCK (raise), not warn-and-write
# ---------------------------------------------------------------------------


class TestValidateBlocksWrite:
    """F1: DeployIntegrityError raised before atomic_write on corruption."""

    def test_corruption_raises_deploy_integrity_error(self):
        from pactkit.generators.deployer import (
            DeployIntegrityError,
            _enforce_deploy_integrity,
        )

        corrupt = "Run run the full test suite directly"
        with pytest.raises(DeployIntegrityError) as exc_info:
            _enforce_deploy_integrity(corrupt, get_profile("codex"), "test:fixture")
        assert exc_info.value.label == "test:fixture"
        assert exc_info.value.violations  # non-empty

    def test_clean_content_does_not_raise(self):
        from pactkit.generators.deployer import _enforce_deploy_integrity

        clean = "Run `pactkit regression` to classify SKIP/IMPACT/FULL."
        _enforce_deploy_integrity(clean, get_profile("codex"), "test:clean")  # no raise


# ---------------------------------------------------------------------------
# F3: format=all per-adapter gate (skip-only, does not block whole deploy)
# ---------------------------------------------------------------------------


class TestFormatAllPerAdapterGate:
    """F3: format=all skips incompatible adapters, deploys the rest."""

    def test_format_all_skips_incompatible_adapter(self, monkeypatch):
        from pactkit.generators import deployer as dep_mod
        from pactkit.generators.deployer import deploy

        deployed: list[str] = []

        class _Spy:
            def __init__(self, fmt: str) -> None:
                self.fmt = fmt

            def deploy(self, config=None, target=None) -> None:
                deployed.append(self.fmt)

        monkeypatch.setattr(dep_mod, "_DEPLOYER_REGISTRY", {
            "classic": lambda: _Spy("classic"),
            "codex": lambda: _Spy("codex"),
        })
        monkeypatch.setattr(dep_mod, "_DEPLOYMENT_MODES", frozenset())
        monkeypatch.setattr(
            "pactkit.doctor.check_adapter_compat",
            lambda fmt, allow_skew=False: ["incompatible"] if fmt == "codex" else [],
        )

        deploy(config={}, target=None, format="all", non_interactive=True)
        assert "classic" in deployed  # compatible → deployed
        assert "codex" not in deployed  # incompatible → skipped (skip-only)

    def test_format_all_allow_skew_deploys_anyway(self, monkeypatch):
        from pactkit.generators import deployer as dep_mod
        from pactkit.generators.deployer import deploy

        deployed: list[str] = []

        class _Spy:
            def __init__(self, fmt: str) -> None:
                self.fmt = fmt

            def deploy(self, config=None, target=None) -> None:
                deployed.append(self.fmt)

        monkeypatch.setattr(dep_mod, "_DEPLOYER_REGISTRY", {"codex": lambda: _Spy("codex")})
        monkeypatch.setattr(dep_mod, "_DEPLOYMENT_MODES", frozenset())
        monkeypatch.setattr(
            "pactkit.doctor.check_adapter_compat",
            lambda fmt, allow_skew=False: [] if allow_skew else ["incompatible"],
        )

        deploy(config={}, target=None, format="all", non_interactive=True, allow_skew=True)
        assert "codex" in deployed  # override → deployed despite mismatch


# ---------------------------------------------------------------------------
# F5: copilot CONTEXT_CONTINUATION fallback retains continuation params
# ---------------------------------------------------------------------------


class TestCopilotContinuationFallback:
    """F5: copilot fallback mentions last-command/phase (executable, not just 'update')."""

    def test_fallback_mentions_continuation_params(self):
        out = _render_prompt("Run {PACTKIT_OP_CONTEXT_CONTINUATION}", get_profile("copilot"))
        assert "`pactkit context" not in out  # CLI span replaced
        assert "last-command" in out
        assert "phase" in out
        assert "context.md" in out
