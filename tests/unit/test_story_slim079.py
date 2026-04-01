"""Tests for STORY-slim-079: TS/JS path alias resolution for file-mode dependency graph."""
import json


def _make():
    from pactkit.skills.analyzers.ts_analyzer import TSAnalyzer
    return TSAnalyzer.__new__(TSAnalyzer)


# --- R1: _load_tsconfig_paths ---

class TestLoadTsconfigPaths:
    def test_reads_paths_from_tsconfig(self, tmp_path):
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make()._load_tsconfig_paths(tmp_path)
        assert len(result) >= 1
        # Should have ("@/", "src/") or similar
        assert any(alias.startswith('@/') for alias, _ in result)

    def test_jsconfig_fallback(self, tmp_path):
        jsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'jsconfig.json').write_text(json.dumps(jsconfig))
        result = _make()._load_tsconfig_paths(tmp_path)
        assert len(result) >= 1

    def test_no_tsconfig_returns_empty(self, tmp_path):
        result = _make()._load_tsconfig_paths(tmp_path)
        assert result == []

    def test_no_paths_returns_empty(self, tmp_path):
        tsconfig = {"compilerOptions": {"target": "ES2017"}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make()._load_tsconfig_paths(tmp_path)
        assert result == []

    def test_cached_per_root(self, tmp_path):
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        analyzer = _make()
        r1 = analyzer._load_tsconfig_paths(tmp_path)
        r2 = analyzer._load_tsconfig_paths(tmp_path)
        assert r1 is r2  # Same object = cached

    def test_baseurl_respected(self, tmp_path):
        """AC4: baseUrl changes resolution root."""
        tsconfig = {"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["./*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make()._load_tsconfig_paths(tmp_path)
        # With baseUrl='.', '@/*' -> './*' means no 'src/' prefix
        assert any(alias.startswith('@/') for alias, _ in result)
        # replacement should NOT have src/ prefix
        for alias, repl in result:
            if alias.startswith('@/'):
                assert not repl.startswith('src/')

    def test_monorepo_subdir_tsconfig(self, tmp_path):
        """AC7: tsconfig in frontend/ subdir."""
        frontend = tmp_path / 'frontend'
        frontend.mkdir()
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (frontend / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make()._load_tsconfig_paths(frontend)
        assert len(result) >= 1

    def test_monorepo_root_discovers_subdir_tsconfig(self, tmp_path):
        """AC7 real-world: root is monorepo root, tsconfig in frontend/ subdir."""
        frontend = tmp_path / 'frontend'
        frontend.mkdir()
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (frontend / 'tsconfig.json').write_text(json.dumps(tsconfig))
        # Pass monorepo root, not frontend subdir
        result = _make()._load_tsconfig_paths(tmp_path)
        assert len(result) >= 1
        assert any(alias.startswith('@/') for alias, _ in result)


# --- R2: normalize_import with aliases ---

class TestNormalizeImportAlias:
    def test_at_alias_resolves(self, tmp_path):
        """AC1: @/lib/supabase/server → src/lib/supabase/server."""
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@/lib/supabase/server',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result == 'src/lib/supabase/server'

    def test_multi_segment_prefix(self, tmp_path):
        """AC2: @components/Button → src/components/Button."""
        tsconfig = {"compilerOptions": {"paths": {"@components/*": ["./src/components/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@components/Button',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result == 'src/components/Button'

    def test_exact_match(self, tmp_path):
        """AC3: @config → src/config."""
        tsconfig = {"compilerOptions": {"paths": {"@config": ["./src/config"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@config',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result == 'src/config'

    def test_bare_module_still_none(self, tmp_path):
        """AC8: react is not an alias."""
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            'react',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result is None

    def test_scoped_package_still_none(self, tmp_path):
        """AC8: @supabase/ssr is not an alias."""
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@supabase/ssr',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result is None


# --- R4: Backward compatibility ---

class TestBackwardCompat:
    def test_relative_import_unchanged(self, tmp_path):
        """AC6: ../lib/utils still resolves via relative logic."""
        consumer = tmp_path / 'src/app/page.ts'
        result = _make().normalize_import('../lib/utils', consumer, tmp_path)
        assert result == 'src/lib/utils'

    def test_no_tsconfig_relative_works(self, tmp_path):
        """AC5 + AC6: no tsconfig, relative still works."""
        consumer = tmp_path / 'src/app/page.ts'
        result = _make().normalize_import('../lib/utils', consumer, tmp_path)
        assert result == 'src/lib/utils'

    def test_no_tsconfig_alias_returns_none(self, tmp_path):
        """AC5: no tsconfig, @/ returns None."""
        result = _make().normalize_import(
            '@/lib/utils',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result is None


# --- R1+R2: Monorepo subdir resolve ---

class TestMonorepoResolve:
    def test_monorepo_root_alias_resolves(self, tmp_path):
        """AC7 e2e: root=monorepo, tsconfig in frontend/, alias resolves with subdir prefix."""
        frontend = tmp_path / 'frontend'
        (frontend / 'src/app').mkdir(parents=True)
        tsconfig = {"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}
        (frontend / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@/lib/supabase/server',
            tmp_path / 'frontend/src/app/page.ts',
            tmp_path,
        )
        assert result == 'frontend/src/lib/supabase/server'


# --- R1+R2: baseUrl ---

class TestBaseUrl:
    def test_baseurl_no_src(self, tmp_path):
        """AC4: baseUrl='.' with paths '@/*' -> './*' → lib/utils (no src/)."""
        tsconfig = {"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["./*"]}}}
        (tmp_path / 'tsconfig.json').write_text(json.dumps(tsconfig))
        result = _make().normalize_import(
            '@/lib/utils',
            tmp_path / 'src/app/page.ts',
            tmp_path,
        )
        assert result == 'lib/utils'
