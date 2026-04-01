"""Tests for STORY-slim-080: Deep monorepo scanning — nearest-ancestor config discovery."""
import json


def _make_ts():
    from pactkit.skills.analyzers.ts_analyzer import TSAnalyzer
    return TSAnalyzer.__new__(TSAnalyzer)


def _make_go():
    from pactkit.skills.analyzers.go_analyzer import GoAnalyzer
    return GoAnalyzer.__new__(GoAnalyzer)


# --- R1: _detect_stacks deep scanning ---

class TestDetectStacksDeep:
    def test_depth2_package_json(self, tmp_path):
        """AC1: packages/web/package.json detected at depth-2."""
        (tmp_path / 'packages/web').mkdir(parents=True)
        (tmp_path / 'packages/web/package.json').write_text('{}')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'node' in result

    def test_depth2_go_mod(self, tmp_path):
        """AC1: packages/api/go.mod detected at depth-2."""
        (tmp_path / 'packages/api').mkdir(parents=True)
        (tmp_path / 'packages/api/go.mod').write_text('module api')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'go' in result

    def test_depth3_go_mod(self, tmp_path):
        """AC9: services/billing/api/go.mod detected at depth-3."""
        (tmp_path / 'services/billing/api').mkdir(parents=True)
        (tmp_path / 'services/billing/api/go.mod').write_text('module api')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'go' in result

    def test_scan_excludes_respected(self, tmp_path):
        """AC8: node_modules/some-pkg/go.mod NOT detected."""
        (tmp_path / 'node_modules/some-pkg').mkdir(parents=True)
        (tmp_path / 'node_modules/some-pkg/go.mod').write_text('module fake')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'go' not in result

    def test_depth1_still_works(self, tmp_path):
        """AC6 backward compat: depth-1 detection unchanged."""
        (tmp_path / 'frontend').mkdir()
        (tmp_path / 'frontend/package.json').write_text('{}')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'node' in result

    def test_root_level_still_works(self, tmp_path):
        """AC6 backward compat: root-level detection unchanged."""
        (tmp_path / 'package.json').write_text('{}')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert 'node' in result

    def test_no_duplicates(self, tmp_path):
        """Multiple go.mod at different depths → single 'go' entry."""
        (tmp_path / 'backend').mkdir()
        (tmp_path / 'backend/go.mod').write_text('module backend')
        (tmp_path / 'services/api').mkdir(parents=True)
        (tmp_path / 'services/api/go.mod').write_text('module api')
        from pactkit.skills.visualize import _detect_stacks
        result = _detect_stacks(tmp_path)
        assert result.count('go') == 1


# --- R2: TS nearest-ancestor tsconfig ---

class TestTSNearestAncestor:
    def test_depth2_tsconfig(self, tmp_path):
        """AC2: apps/frontend/tsconfig.json found for apps/frontend/src/app/page.ts."""
        (tmp_path / 'apps/frontend/src/app').mkdir(parents=True)
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'apps/frontend/tsconfig.json').write_text(json.dumps(tsconfig))
        consumer = tmp_path / 'apps/frontend/src/app/page.ts'
        result = _make_ts().normalize_import('@/lib/utils', consumer, tmp_path)
        assert result == 'apps/frontend/src/lib/utils'

    def test_multiple_tsconfigs(self, tmp_path):
        """AC4: frontend/ and packages/ui/ each use own tsconfig."""
        # frontend tsconfig
        (tmp_path / 'frontend/src').mkdir(parents=True)
        ts1 = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'frontend/tsconfig.json').write_text(json.dumps(ts1))
        # packages/ui tsconfig
        (tmp_path / 'packages/ui/src').mkdir(parents=True)
        ts2 = {"compilerOptions": {"paths": {"@ui/*": ["./components/*"]}}}
        (tmp_path / 'packages/ui/tsconfig.json').write_text(json.dumps(ts2))

        analyzer = _make_ts()
        r1 = analyzer.normalize_import(
            '@/lib/utils', tmp_path / 'frontend/src/page.ts', tmp_path)
        r2 = analyzer.normalize_import(
            '@ui/Button', tmp_path / 'packages/ui/src/page.ts', tmp_path)
        assert r1 == 'frontend/src/lib/utils'
        assert r2 == 'packages/ui/components/Button'

    def test_flat_project_unchanged(self, tmp_path):
        """AC6: tsconfig at root still works."""
        (tmp_path / 'src/app').mkdir(parents=True)
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make_ts().normalize_import(
            '@/lib/utils', tmp_path / 'src/app/page.ts', tmp_path)
        assert result == 'src/lib/utils'

    def test_no_tsconfig_returns_none(self, tmp_path):
        """AC7: no tsconfig at any level → None."""
        result = _make_ts().normalize_import(
            '@/lib/utils', tmp_path / 'src/app/page.ts', tmp_path)
        assert result is None

    def test_cache_per_tsconfig_path(self, tmp_path):
        """R2.4: Cache keyed by tsconfig path, not root."""
        (tmp_path / 'a/src').mkdir(parents=True)
        (tmp_path / 'b/src').mkdir(parents=True)
        ts_a = {"compilerOptions": {"paths": {"@a/*": ["./src/*"]}}}
        ts_b = {"compilerOptions": {"paths": {"@b/*": ["./src/*"]}}}
        (tmp_path / 'a/tsconfig.json').write_text(json.dumps(ts_a))
        (tmp_path / 'b/tsconfig.json').write_text(json.dumps(ts_b))

        analyzer = _make_ts()
        r_a = analyzer.normalize_import('@a/foo', tmp_path / 'a/src/x.ts', tmp_path)
        r_b = analyzer.normalize_import('@b/bar', tmp_path / 'b/src/x.ts', tmp_path)
        assert r_a == 'a/src/foo'
        assert r_b == 'b/src/bar'


# --- R3: Go nearest-ancestor go.mod ---

class TestGoNearestAncestor:
    def test_depth2_go_mod(self, tmp_path):
        """AC3: services/api/go.mod found for services/api/internal/handler.go."""
        (tmp_path / 'services/api/internal').mkdir(parents=True)
        (tmp_path / 'services/api/go.mod').write_text('module github.com/org/api\n')
        go = _make_go()
        go._go_mod_cache = {}
        result = go.normalize_import(
            'github.com/org/api/internal/db',
            tmp_path / 'services/api/internal/handler.go',
            tmp_path,
        )
        assert result == 'services/api/internal/db'

    def test_multiple_go_mods(self, tmp_path):
        """AC5: backend/ and gateway/ each use own go.mod."""
        (tmp_path / 'backend/cmd').mkdir(parents=True)
        (tmp_path / 'backend/internal').mkdir(parents=True)
        (tmp_path / 'backend/go.mod').write_text('module backend\n')
        (tmp_path / 'gateway/cmd').mkdir(parents=True)
        (tmp_path / 'gateway/go.mod').write_text('module gateway\n')

        go = _make_go()
        go._go_mod_cache = {}
        r1 = go.normalize_import(
            'backend/internal/db',
            tmp_path / 'backend/cmd/main.go',
            tmp_path,
        )
        r2 = go.normalize_import(
            'gateway/routes',
            tmp_path / 'gateway/cmd/main.go',
            tmp_path,
        )
        # Module prefix stripped, then go.mod dir prepended to match build_module_keys
        assert r1 == 'backend/internal/db'
        assert r2 == 'gateway/routes'

    def test_flat_project_unchanged(self, tmp_path):
        """AC6: go.mod at root still works."""
        (tmp_path / 'internal').mkdir()
        (tmp_path / 'go.mod').write_text('module github.com/org/myapp\n')
        go = _make_go()
        go._go_mod_cache = {}
        result = go.normalize_import(
            'github.com/org/myapp/internal/db',
            tmp_path / 'cmd/main.go',
            tmp_path,
        )
        assert result == 'internal/db'

    def test_no_go_mod_returns_none(self, tmp_path):
        """AC7: no go.mod → external import returns None."""
        go = _make_go()
        go._go_mod_cache = {}
        result = go.normalize_import(
            'github.com/org/api/pkg',
            tmp_path / 'main.go',
            tmp_path,
        )
        assert result is None

    def test_stdlib_still_none(self, tmp_path):
        """Backward compat: stdlib imports still return None."""
        go = _make_go()
        go._go_mod_cache = {}
        assert go.normalize_import('fmt', tmp_path / 'main.go', tmp_path) is None
        assert go.normalize_import('net/http', tmp_path / 'main.go', tmp_path) is None
