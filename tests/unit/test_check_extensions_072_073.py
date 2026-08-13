"""
STORY-slim-072 + STORY-slim-073: Check Phase Extensions — Config tests.

072: check.pactguard sub-section (enabled, mode, ruleset, blocking)
073: check.observe sub-section (enabled, sources, max_console, max_network)

Both default to enabled: false (OFF).
"""
import importlib
import warnings


def _config():
    from pactkit import config
    importlib.reload(config)
    return config


# ===========================================================================
# STORY-slim-072: check.pactguard defaults
# ===========================================================================


class TestPactguardConfigDefaults:
    """R2: check.pactguard sub-section exists with correct defaults."""

    def test_check_has_pactguard_section(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert "pactguard" in default["check"], \
            "check.pactguard must exist in default config"

    def test_pactguard_enabled_default_false(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["pactguard"]["enabled"] is False, \
            "check.pactguard.enabled must default to False"

    def test_pactguard_mode_default_all(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["pactguard"]["mode"] == "all"

    def test_pactguard_ruleset_default_empty(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["pactguard"]["ruleset"] == ""

    def test_pactguard_blocking_default_false(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["pactguard"]["blocking"] is False

    def test_existing_check_keys_preserved(self):
        """Adding pactguard must not break existing check keys."""
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["security_checklist"] is True
        assert default["check"]["security_scope_override"] == "none"


# ===========================================================================
# STORY-slim-072: check.pactguard validation
# ===========================================================================


class TestPactguardConfigValidation:
    """R2: validate_config handles check.pactguard correctly."""

    def test_default_pactguard_no_warnings(self):
        cfg = _config()
        config_dict = cfg.get_default_config()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg.validate_config(config_dict)
            pg_warns = [x for x in w if "pactguard" in str(x.message).lower()]
            assert len(pg_warns) == 0

    def test_invalid_pactguard_mode_warns(self):
        cfg = _config()
        config_dict = cfg.get_default_config()
        config_dict["check"]["pactguard"]["mode"] = "invalid"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg.validate_config(config_dict)
            pg_warns = [x for x in w if "pactguard" in str(x.message).lower()]
            assert len(pg_warns) >= 1

    def test_valid_pactguard_mode_pattern_no_warn(self):
        cfg = _config()
        config_dict = cfg.get_default_config()
        config_dict["check"]["pactguard"]["mode"] = "pattern"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg.validate_config(config_dict)
            pg_warns = [x for x in w if "pactguard" in str(x.message).lower()]
            assert len(pg_warns) == 0


# ===========================================================================
# STORY-slim-072: YAML serialization
# ===========================================================================


class TestPactguardYamlSerialization:
    """R2: generate_default_yaml and _rewrite_yaml include pactguard."""

    def test_generate_default_yaml_has_pactguard(self):
        """STORY-slim-135: pactguard defaults asserted on get_default_config()."""
        assert "pactguard" in _config().get_default_config()["check"]

    def test_rewrite_yaml_has_pactguard(self, tmp_path):
        cfg = _config()
        config_path = tmp_path / "pactkit.yaml"
        data = cfg.get_default_config()
        cfg._rewrite_yaml(config_path, data)
        content = config_path.read_text()
        assert "pactguard:" in content

    def test_rewrite_yaml_pactguard_enabled_false(self, tmp_path):
        cfg = _config()
        config_path = tmp_path / "pactkit.yaml"
        data = cfg.get_default_config()
        cfg._rewrite_yaml(config_path, data)
        content = config_path.read_text()
        # Should show enabled: false for pactguard
        # Find pactguard section and check enabled value
        lines = content.split("\n")
        in_pactguard = False
        for line in lines:
            if "pactguard:" in line and "#" not in line.split("pactguard:")[0]:
                in_pactguard = True
                continue
            if in_pactguard and "enabled:" in line:
                assert "false" in line, f"pactguard.enabled should be false, got: {line}"
                break


# ===========================================================================
# STORY-slim-072: deep merge preserves pactguard
# ===========================================================================


class TestPactguardDeepMerge:
    """R2: load_config deep-merges check.pactguard with defaults."""

    def test_partial_check_config_preserves_pactguard_defaults(self, tmp_path):
        """User sets check.security_checklist only → pactguard defaults preserved."""
        cfg = _config()
        import yaml
        config_path = tmp_path / "pactkit.yaml"
        config_path.write_text(yaml.dump({
            "version": "2.9.3",
            "check": {"security_checklist": False},
        }))
        loaded = cfg.load_config(config_path)
        assert loaded["check"]["pactguard"]["enabled"] is False
        assert loaded["check"]["pactguard"]["mode"] == "all"

    def test_user_enables_pactguard(self, tmp_path):
        """User sets check.pactguard.enabled: true → merged correctly."""
        cfg = _config()
        import yaml
        config_path = tmp_path / "pactkit.yaml"
        config_path.write_text(yaml.dump({
            "version": "2.9.3",
            "check": {"pactguard": {"enabled": True, "ruleset": "rules/owasp.yaml"}},
        }))
        loaded = cfg.load_config(config_path)
        assert loaded["check"]["pactguard"]["enabled"] is True
        assert loaded["check"]["pactguard"]["ruleset"] == "rules/owasp.yaml"
        # mode should fall back to default
        assert loaded["check"]["pactguard"]["mode"] == "all"


# ===========================================================================
# STORY-slim-073: check.observe defaults
# ===========================================================================


class TestObserveConfigDefaults:
    """R5: check.observe sub-section exists with correct defaults."""

    def test_check_has_observe_section(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert "observe" in default["check"]

    def test_observe_enabled_default_false(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["observe"]["enabled"] is False

    def test_observe_sources_default_auto(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["observe"]["sources"] == "auto"

    def test_observe_max_console_default_100(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["observe"]["max_console"] == 100

    def test_observe_max_network_default_200(self):
        cfg = _config()
        default = cfg.get_default_config()
        assert default["check"]["observe"]["max_network"] == 200


# ===========================================================================
# STORY-slim-073: check.observe validation
# ===========================================================================


class TestObserveConfigValidation:
    """R5: validate_config handles check.observe correctly."""

    def test_default_observe_no_warnings(self):
        cfg = _config()
        config_dict = cfg.get_default_config()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg.validate_config(config_dict)
            obs_warns = [x for x in w if "observe" in str(x.message).lower()]
            assert len(obs_warns) == 0

    def test_invalid_observe_sources_warns(self):
        cfg = _config()
        config_dict = cfg.get_default_config()
        config_dict["check"]["observe"]["sources"] = "invalid"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg.validate_config(config_dict)
            obs_warns = [x for x in w if "observe" in str(x.message).lower()]
            assert len(obs_warns) >= 1


# ===========================================================================
# STORY-slim-073: YAML serialization
# ===========================================================================


class TestObserveYamlSerialization:
    """R5: generate_default_yaml and _rewrite_yaml include observe."""

    def test_generate_default_yaml_has_observe(self):
        """STORY-slim-135: observe defaults asserted on get_default_config()."""
        assert "observe" in _config().get_default_config()["check"]

    def test_rewrite_yaml_has_observe(self, tmp_path):
        cfg = _config()
        config_path = tmp_path / "pactkit.yaml"
        data = cfg.get_default_config()
        cfg._rewrite_yaml(config_path, data)
        content = config_path.read_text()
        assert "observe:" in content


# ===========================================================================
# STORY-slim-073: deep merge preserves observe
# ===========================================================================


class TestObserveDeepMerge:
    """R5: load_config deep-merges check.observe with defaults."""

    def test_partial_check_config_preserves_observe_defaults(self, tmp_path):
        cfg = _config()
        import yaml
        config_path = tmp_path / "pactkit.yaml"
        config_path.write_text(yaml.dump({
            "version": "2.9.3",
            "check": {"security_checklist": False},
        }))
        loaded = cfg.load_config(config_path)
        assert loaded["check"]["observe"]["enabled"] is False
        assert loaded["check"]["observe"]["sources"] == "auto"

    def test_user_enables_observe(self, tmp_path):
        cfg = _config()
        import yaml
        config_path = tmp_path / "pactkit.yaml"
        config_path.write_text(yaml.dump({
            "version": "2.9.3",
            "check": {"observe": {"enabled": True, "sources": "chrome-devtools"}},
        }))
        loaded = cfg.load_config(config_path)
        assert loaded["check"]["observe"]["enabled"] is True
        assert loaded["check"]["observe"]["sources"] == "chrome-devtools"
        assert loaded["check"]["observe"]["max_console"] == 100
