"""Tests for STORY-slim-2026090333d6b72f7645: SDLC T1 alignment.

R1 ADR institution (schema + scaffold + lint-adr + context aggregation),
R2 validation semantics, R3 postmortem discipline, R4 write-safety guide,
R5 adapter parity, R6 knowledge provenance (anti-fabrication).

The spec-preflight inline-range revival (the regex never matched its own
documented L1-L2 format — silent dead code since introduction) is covered
in test_spec_preflight.py::TestTableInlineRange.
"""



# ---------------------------------------------------------------------------
# R1: ADR institution
# ---------------------------------------------------------------------------


class TestADRSchema:
    def test_schema_registry_has_adr_entry(self):
        from pactkit.schemas import SCHEMA_REGISTRY

        adr = SCHEMA_REGISTRY["adr"]
        assert adr["description"]
        for section in (
            "## Context",
            "## Options Considered",
            "## Decision",
            "## Consequences",
        ):
            assert section in adr["required_sections"], section

    def test_adr_status_lifecycle_defined(self):
        from pactkit.schemas import ADR_STATUSES

        assert set(ADR_STATUSES) == {"proposed", "accepted", "superseded"}


class TestADRSCaffold:
    def _root(self, tmp_path):
        (tmp_path / "docs" / "architecture" / "governance" / "adr").mkdir(parents=True)
        return tmp_path

    def test_create_adr_writes_required_structure(self, tmp_path):
        from pactkit.skills.scaffold import create_adr

        create_adr(1, "Use junitxml as authoritative gate counts", project_root=tmp_path)
        files = list((tmp_path / "docs" / "architecture" / "governance" / "adr").glob("ADR-0001-*.md"))
        assert len(files) == 1
        text = files[0].read_text(encoding="utf-8")
        for field in ("| ID |", "| Status |", "| Date |", "| Supersedes |", "| Superseded-by |"):
            assert field in text, field
        for section in ("## Context", "## Options Considered", "## Decision", "## Consequences"):
            assert section in text, section
        assert "| Status | proposed |" in text

    def test_create_adr_supersedes_backwrites_target(self, tmp_path):
        from pactkit.skills.scaffold import create_adr

        create_adr(1, "First decision", project_root=tmp_path)
        target = next(
            (tmp_path / "docs" / "architecture" / "governance" / "adr").glob("ADR-0001-*.md")
        )
        target_id = target.stem

        create_adr(2, "Second decision", supersedes=target_id, project_root=tmp_path)
        new_file = next(
            (tmp_path / "docs" / "architecture" / "governance" / "adr").glob("ADR-0002-*.md")
        )
        # 新 ADR 声明 Supersedes
        assert f"| Supersedes | {target_id} |" in new_file.read_text(encoding="utf-8")
        # 旧 ADR 被回写 Superseded-by（增量 merge，非全量替换）
        target_text = target.read_text(encoding="utf-8")
        assert f"| Superseded-by | {new_file.stem} |" in target_text
        assert "# ADR-0001" in target_text  # 其余内容未被破坏


class TestADRLint:
    def _write(self, tmp_path, text, name="ADR-0001-test.md"):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    VALID = """# ADR-0001: Test

| Field | Value |
|-------|-------|
| ID | ADR-0001-test |
| Status | accepted |
| Date | 2026-09-03 |
| Supersedes | None |
| Superseded-by | None |

## Context

Forces at play.

## Options Considered

- **A**: tradeoff.

## Decision

B wins.

## Consequences

- Accepted risk.
"""

    def test_valid_adr_passes(self, tmp_path):
        from pactkit.validators import lint_adr

        p = self._write(tmp_path, self.VALID)
        assert lint_adr(p) == []

    def test_missing_section_fails(self, tmp_path):
        from pactkit.validators import lint_adr

        text = self.VALID.replace("## Options Considered\n\n- **A**: tradeoff.\n\n", "")
        p = self._write(tmp_path, text)
        errors = lint_adr(p)
        assert any("Options Considered" in e for e in errors)

    def test_invalid_status_fails(self, tmp_path):
        from pactkit.validators import lint_adr

        p = self._write(tmp_path, self.VALID.replace("accepted", "final"))
        errors = lint_adr(p)
        assert any("Status" in e for e in errors)

    def test_supersession_requires_back_reference(self, tmp_path):
        from pactkit.validators import lint_adr

        # ADR-0002 声明 Supersedes 一个存在但未被回写的目标
        self._write(tmp_path, self.VALID)
        two_text = self.VALID.replace("ADR-0001-test", "ADR-0002-test").replace(
            "| Supersedes | None |", "| Supersedes | ADR-0001-test |"
        )
        two = self._write(tmp_path, two_text, name="ADR-0002-test.md")
        errors = lint_adr(two)
        assert any("back-reference" in e or "Superseded-by" in e for e in errors)


class TestADRContextAggregation:
    def test_key_decisions_aggregates_accepted_excludes_superseded(self, tmp_path):
        from pactkit.context_gen import _parse_last_adrs

        adr_dir = tmp_path / "docs" / "architecture" / "governance" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-0001-old.md").write_text(
            "# ADR-0001: Old\n\n| Status | superseded |\n", encoding="utf-8"
        )
        (adr_dir / "ADR-0002-new.md").write_text(
            "# ADR-0002: New\n\n| Status | accepted |\n", encoding="utf-8"
        )
        rows = _parse_last_adrs(tmp_path)
        assert any("ADR-0002" in r for r in rows)
        assert not any("ADR-0001" in r for r in rows)


# ---------------------------------------------------------------------------
# R2: validation semantics / R3: postmortem / R4: write-safety / R6: provenance
# ---------------------------------------------------------------------------


class TestCheckValidationSemantics:
    def test_check_contract_has_user_path_validation_invariant(self):
        from pactkit.prompts.rules import PHASE_CONTRACTS

        joined = " ".join(PHASE_CONTRACTS["project-check"].invariants).lower()
        assert "user-path validation" in joined
        assert "verification" in joined

    def test_check_playbook_phase5_has_validation_row(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check = COMMANDS_CONTENT["project-check.md"]
        assert "Validation" in check
        assert "real end-user path" in check.lower()


class TestPostmortemDiscipline:
    def test_hotfix_playbook_has_phase_37_with_triggers(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        hotfix = COMMANDS_CONTENT["project-hotfix.md"]
        assert "Phase 3.7" in hotfix
        assert "postmortem" in hotfix.lower()
        # 三个触发条件
        assert "user-visible" in hotfix.lower() or "用户可见" in hotfix
        assert "recurrence" in hotfix.lower() or "复发" in hotfix or "same-pattern" in hotfix.lower()
        # 产物路径 + 回流
        assert "postmortems" in hotfix
        assert "board" in hotfix.lower()

    def test_hotfix_skip_reason_required(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        hotfix = COMMANDS_CONTENT["project-hotfix.md"].lower()
        assert "skip" in hotfix


class TestWriteSafetyGuide:
    def test_guide_registered_with_matrix_and_litmus(self):
        from pactkit.prompts.guides import GUIDE_DEFINITIONS

        assert "write-safety.md" in GUIDE_DEFINITIONS
        rendered = GUIDE_DEFINITIONS["write-safety.md"].render()
        lowered = rendered.lower()
        assert "merge" in lowered and "replace" in lowered
        assert "litmus" in lowered or "did not generate" in lowered
        # no-dual-write
        assert "one authoritative location" in lowered or "dual-write" in lowered

    def test_engineering_index_routes_write_safety(self):
        from pactkit.prompts.rules import RULES_MODULES

        index = RULES_MODULES["engineering"]
        assert "write-safety" in index
        plan_table = index.split("## Act Phase")[0]
        assert "write-safety" in plan_table  # keyword 行存在（防孤儿）


class TestKnowledgeProvenance:
    def test_capability_design_has_provenance_hierarchy(self):
        from pactkit.prompts.rules import SHARED_RULES

        capsule = SHARED_RULES["capability-design"]
        lowered = capsule.lower()
        # 来源优先级 + unverified 标注 + 编造=缺陷
        assert "context7" in lowered or "docs" in lowered
        assert "unverified" in lowered
        assert "project" in lowered and ("own code" in lowered or "自身代码" in capsule)
        assert "defect" in lowered or "缺陷" in capsule

    def test_act_playbook_phase3_verifies_before_writing(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        act = COMMANDS_CONTENT["project-act.md"].lower()
        assert "verify" in act and ("context7" in act or "signature" in act)

    def test_check_playbook_flags_fabrication(self):
        from pactkit.prompts.commands import COMMANDS_CONTENT

        check = COMMANDS_CONTENT["project-check.md"]
        lowered = check.lower()
        assert "fabricat" in lowered
        assert "undefined" in lowered or "F821" in check


# ---------------------------------------------------------------------------
# R5: adapter parity
# ---------------------------------------------------------------------------


class TestAdapterParityT1:
    def test_new_semantics_render_across_formats(self):
        from pactkit.generators.deployer import _render_prompt
        from pactkit.profiles import FORMAT_PROFILES
        from pactkit.prompts.commands import COMMANDS_CONTENT

        checks = {
            "project-check.md": ["Validation", "fabricat"],
            "project-hotfix.md": ["Phase 3.7"],
            "project-act.md": ["erif"],  # verify 的宽松锚点
        }
        for name, needles in checks.items():
            template = COMMANDS_CONTENT[name]
            for fmt, profile in FORMAT_PROFILES.items():
                rendered = _render_prompt(template, profile)
                for needle in needles:
                    assert needle.lower() in rendered.lower(), f"{fmt}:{name}:{needle}"
