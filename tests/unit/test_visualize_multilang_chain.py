"""Tests for STORY-slim-069: dispatch hint + inheritance edges for Go/Java/TS tree-sitter analyzers."""
import pathlib
import pytest

# Skip entire module if tree-sitter is not installed
ts = pytest.importorskip('tree_sitter')

from pactkit.skills.visualize import GoAnalyzer, JavaAnalyzer, TSAnalyzer


# ── Helpers ──────────────────────────────────────────────────────────

def _write_and_extract(analyzer, code: str, tmp_path: pathlib.Path, ext: str):
    """Write code to a temp file and return (func_registry, call_edges)."""
    p = tmp_path / f'test_file{ext}'
    p.write_text(code, encoding='utf-8')
    return analyzer.extract_functions_and_calls(p)


# ── AC1: Go Dispatch Hint ────────────────────────────────────────────

class TestAC1GoDispatchHint:
    def test_dispatch_hint_parsed(self, tmp_path):
        code = '''\
package main

func Deploy() {
    // pactkit-trace: dispatches_to Handler.Run, Logger.Write
    run()
}
'''
        analyzer = GoAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.go')
        assert 'Handler.Run' in edges.get('Deploy', [])
        assert 'Logger.Write' in edges.get('Deploy', [])


# ── AC2: Java Dispatch Hint ──────────────────────────────────────────

class TestAC2JavaDispatchHint:
    def test_dispatch_hint_parsed(self, tmp_path):
        code = '''\
class Server {
    void dispatch() {
        // pactkit-trace: dispatches_to SubService.handle
        run();
    }
}
'''
        analyzer = JavaAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.java')
        assert 'SubService.handle' in edges.get('Server.dispatch', [])


# ── AC3: TS Dispatch Hint ────────────────────────────────────────────

class TestAC3TSDispatchHint:
    def test_dispatch_hint_parsed(self, tmp_path):
        code = '''\
class App {
    navigate() {
        // pactkit-trace: dispatches_to ReactRouter.navigate
        go();
    }
}
'''
        analyzer = TSAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.ts')
        assert 'ReactRouter.navigate' in edges.get('App.navigate', [])


# ── AC4: Go Struct Embedding Inheritance Edges ───────────────────────

class TestAC4GoStructEmbedding:
    def test_override_edge_created(self, tmp_path):
        code = '''\
package main

type Base struct{}
type Sub struct { Base }

func (b *Base) Deploy() { helper() }
func (s *Sub) Deploy() { other() }
'''
        analyzer = GoAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.go')
        assert 'Sub.Deploy' in edges.get('Base.Deploy', [])

    def test_no_false_inheritance_edge(self, tmp_path):
        code = '''\
package main

type Base struct{}
type Sub struct { Base }

func (b *Base) Deploy() { helper() }
func (s *Sub) OnlyInSub() { other() }
'''
        analyzer = GoAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.go')
        # OnlyInSub is not in Base, so no virtual edge
        assert 'Sub.OnlyInSub' not in edges.get('Base.Deploy', [])
        assert 'Base.OnlyInSub' not in edges


# ── AC5: Java extends Inheritance Edges ──────────────────────────────

class TestAC5JavaInheritance:
    def test_extends_edge_created(self, tmp_path):
        code = '''\
class Base {
    void deploy() { helper(); }
}
class Sub extends Base {
    void deploy() { other(); }
}
'''
        analyzer = JavaAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.java')
        assert 'Sub.deploy' in edges.get('Base.deploy', [])

    def test_no_false_inheritance_edge(self, tmp_path):
        code = '''\
class Base {
    void deploy() { helper(); }
}
class Sub extends Base {
    void onlyInSub() { other(); }
}
'''
        analyzer = JavaAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.java')
        assert 'Sub.onlyInSub' not in edges.get('Base.deploy', [])
        assert 'Base.onlyInSub' not in edges


# ── AC6: TS class extends Inheritance Edges ──────────────────────────

class TestAC6TSInheritance:
    def test_extends_edge_created(self, tmp_path):
        code = '''\
class Base {
    deploy() { helper(); }
}
class Sub extends Base {
    deploy() { other(); }
}
'''
        analyzer = TSAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.ts')
        assert 'Sub.deploy' in edges.get('Base.deploy', [])

    def test_no_false_inheritance_edge(self, tmp_path):
        code = '''\
class Base {
    deploy() { helper(); }
}
class Sub extends Base {
    onlyInSub() { other(); }
}
'''
        analyzer = TSAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.ts')
        assert 'Sub.onlyInSub' not in edges.get('Base.deploy', [])
        assert 'Base.onlyInSub' not in edges


# ── AC7: No Hint No Extra Callees ───────────────────────────────────

class TestAC7NoHintNoExtra:
    def test_go_no_hint(self, tmp_path):
        code = '''\
package main

func Deploy() {
    helper()
}
'''
        analyzer = GoAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.go')
        callees = edges.get('Deploy', [])
        assert 'helper' in callees
        # No dispatch hint targets
        assert not any('dispatches_to' in c for c in callees)

    def test_java_no_hint(self, tmp_path):
        code = '''\
class Server {
    void deploy() { helper(); }
}
'''
        analyzer = JavaAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.java')
        callees = edges.get('Server.deploy', [])
        assert 'helper' in callees
        assert not any('dispatches_to' in c for c in callees)

    def test_ts_no_hint(self, tmp_path):
        code = '''\
class App {
    deploy() { helper(); }
}
'''
        analyzer = TSAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.ts')
        callees = edges.get('App.deploy', [])
        assert 'helper' in callees
        assert not any('dispatches_to' in c for c in callees)


# ── AC8: No False Inheritance Edge (covered by AC4/AC5/AC6 negative tests) ──
# Additional edge case: multiple inheritance levels (Go embedding chain)

class TestAC8MultiLevel:
    def test_go_multi_level_embedding(self, tmp_path):
        code = '''\
package main

type A struct{}
type B struct { A }
type C struct { B }

func (a *A) Run() {}
func (b *B) Run() {}
func (c *C) Run() {}
'''
        analyzer = GoAnalyzer()
        _, edges = _write_and_extract(analyzer, code, tmp_path, '.go')
        assert 'B.Run' in edges.get('A.Run', [])
        assert 'C.Run' in edges.get('B.Run', [])
