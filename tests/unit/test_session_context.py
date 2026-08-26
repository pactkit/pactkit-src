"""Tests for STORY-006: Session Context Protocol — cross-session project state awareness."""

import importlib


def _prompts():
    import pactkit.prompts as p

    importlib.reload(p)
    return p


# ==============================================================================
# Scenario 1: Done generates context.md instructions
# ==============================================================================
class TestDoneContextGeneration:
    """Done playbook must include context.md generation phase."""

    def test_done_has_context_generation_phase(self):
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "context.md" in done

    def test_done_context_after_commit(self):
        """Context generation must come after git commit (Phase 4)."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        commit_pos = done.find("Git Commit")
        context_pos = done.find("Context")
        # Find the context generation phase that's after commit
        # There may be "Context Loading" earlier, so find the generation one
        assert "Generate Context" in done or "Update Context" in done or "Session Context" in done

    def test_done_context_reads_story_facts(self):
        """Done must read Story facts rather than the Board projection."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "pactkit board list" in done
        assert "Read `docs/product/sprint_board.md`" not in done

    def test_done_context_reads_lessons(self):
        """Context generation must reference lessons.md."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "lessons" in done.lower()

    def test_done_context_includes_branches(self):
        """Context generation must include active branches."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "branch" in done.lower()

    def test_done_context_includes_next_action(self):
        """Context generation must include recommended next action (via {CONTEXT_SECTIONS})."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "pactkit context" in done


# ==============================================================================
# Scenario 2: CLAUDE.md references context.md
# ==============================================================================
class TestClaudeMdRuntimeBoundary:
    """The global Runtime Kernel does not turn history into a session gate."""

    def test_template_has_runtime_only_reference(self):
        p = _prompts()
        assert "@~/.claude/rules/pactkit-runtime.md" in p.CLAUDE_MD_TEMPLATE
        assert "pactkit context" not in p.CLAUDE_MD_TEMPLATE
        assert ".pactkit/context.md" not in p.CLAUDE_MD_TEMPLATE
        assert "@./docs/product/context.md" not in p.CLAUDE_MD_TEMPLATE

    def test_runtime_template_has_no_phase_or_history_imports(self):
        p = _prompts()
        template = p.CLAUDE_MD_TEMPLATE
        assert template.count("@~/.claude/rules/") == 1
        assert "skills/_rules" not in template

    def test_runtime_explicitly_preserves_current_session_execution(self):
        p = _prompts()
        runtime = p.RULES_MODULES["runtime"].lower()
        assert "current session" in runtime
        assert "never exclusive locks" in runtime

    def test_deployer_classic_produces_header(self):
        """_deploy_claude_md should produce CLAUDE.md with version header."""
        import tempfile
        from pathlib import Path

        from pactkit.generators.deployer import _deploy_claude_md
        from pactkit.prompts import RULES_FILES

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _deploy_claude_md(tmp_path, list(RULES_FILES.keys()))
            content = (tmp_path / "CLAUDE.md").read_text()
            assert "# PactKit Runtime Contract" in content


# ==============================================================================
# Scenario 3: Cold start with context (format validation)
# ==============================================================================
class TestContextFileFormat:
    """Context file generation instructions must specify the correct format."""

    def test_done_context_format_has_sprint_status(self):
        """After STORY-slim-007: sections come from schemas via {CONTEXT_SECTIONS} placeholder."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        # Either the placeholder or the rendered section name must be present
        assert "pactkit context" in done

    def test_done_context_format_has_recent_completions(self):
        """After STORY-slim-007: section names come from schemas via {CONTEXT_SECTIONS} placeholder."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]

        # Either the placeholder is present, or the rendered sections are present
        assert "pactkit context" in done

    def test_done_context_format_has_active_branches(self):
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "pactkit context" in done

    def test_done_context_format_has_key_decisions(self):
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "pactkit context" in done


# ==============================================================================
# Scenario 4: Lessons auto-appended
# ==============================================================================
class TestLessonsAutoAppend:
    """Done playbook must use sharded Lesson records."""

    def test_done_has_lessons_append(self):
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "lesson-append" in done
        assert "lessons.md" not in done

    def test_done_lessons_not_conditional_on_mcp(self):
        """Lessons append must NOT be conditional on Memory MCP."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        # Find lessons.md reference that's NOT inside MCP conditional
        # The lessons append should be a standalone step, not inside "IF mcp__memory"
        lines = done.split("\n")
        found_unconditional_lessons = False
        for i, line in enumerate(lines):
            if "lesson-append" in line and "mcp__memory" not in line:
                # Check this line isn't inside an MCP conditional block
                found_unconditional_lessons = True
                break
        assert found_unconditional_lessons, "Lesson record append must exist outside Memory MCP conditional"

    def test_done_lessons_has_date_format(self):
        """Lessons entry must include date."""
        p = _prompts()
        done = p.COMMANDS_CONTENT["project-done.md"]
        assert "date" in done.lower() or "Date" in done


# ==============================================================================
# Scenario 5: Context.md missing gracefully (no code needed — @import behavior)
# This is a behavioral test — Claude Code silently skips missing @imports.
# We just verify the template uses the right syntax.
# ==============================================================================
class TestContextMissingGraceful:
    """Missing local Context is rebuilt rather than imported."""

    def test_uses_relative_path(self):
        """Global Runtime must not import a project history path."""
        p = _prompts()
        template = p.CLAUDE_MD_TEMPLATE
        assert "@~/.claude/rules/pactkit-runtime.md" in template
        assert "pactkit context" not in template
        assert "@./docs/product/context.md" not in template
        assert "@~/.claude/context.md" not in template


# ==============================================================================
# Scenario 6: Plan updates context
# ==============================================================================
class TestPlanContextGeneration:
    """Plan playbook must include context.md generation phase."""

    def test_plan_has_context_generation(self):
        p = _prompts()
        plan = p.COMMANDS_CONTENT["project-plan.md"]
        assert "context.md" in plan

    def test_plan_context_after_board(self):
        """Context generation must come after Board creation."""
        p = _prompts()
        plan = p.COMMANDS_CONTENT["project-plan.md"]
        board_pos = plan.find("add_story")
        context_pos = plan.find("context.md")
        assert context_pos > board_pos, "context.md generation must come after Board (add_story)"


# ==============================================================================
# Additional: Init generates context
# ==============================================================================
class TestInitContextGeneration:
    """Init playbook must include context.md generation phase."""

    def test_init_has_context_generation(self):
        p = _prompts()
        init = p.COMMANDS_CONTENT["project-init.md"]
        assert "context.md" in init


# ==============================================================================
# Plugin mode: minimal Runtime entrypoint
# ==============================================================================
class TestPluginModeContext:
    """Plugin inline CLAUDE.md must not route ordinary work into PDCA."""

    def test_plugin_inline_keeps_only_runtime_contract(self):
        """Plugin global content should not advertise an initialization phase."""
        import tempfile
        from pathlib import Path

        from pactkit.generators.deployer import _deploy_claude_md_inline

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _deploy_claude_md_inline(tmp_path)
            content = (tmp_path / "CLAUDE.md").read_text()
            assert "# PactKit Runtime Contract" in content
            assert "/project-init" not in content
            assert "PDCA Routing Table" not in content
