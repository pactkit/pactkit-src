
### [STORY-slim-075] Prompt engineering quality: graduated safety language, tool call guidance, routing disambiguation, lessons rotation
> Spec: docs/specs/STORY-slim-075.md

- [x] Audit safety language,Add parallel/serial tool guidance,Add routing When NOT to use,Implement lessons rotation,Add prompt quality tests

### [STORY-slim-076] Multi-stack visualize: class mode + multi-language file scanning
> Spec: docs/specs/STORY-slim-076.md

- [x] R1: _detect_stacks multi-stack detection
- [x] R2: Multi-stack file scanning
- [x] R3: extract_classes ABC
- [x] R4: _build_class_graph refactor
- [x] R5: _select_analyzers
- [x] R6: Backward compat tests

### [STORY-slim-077] Monorepo stack detection + redetect-stack CLI
> Spec: docs/specs/STORY-slim-077.md

- [x] Extend detect_stacks depth-1,Add redetect-stack CLI,Update init flow,Tests

### [STORY-slim-078] Multi-language module resolution for file-mode dependency graph
> Spec: docs/specs/STORY-slim-078.md

- [x] Per-lang module keys,Per-lang import normalization,Multi-analyzer file graph,Fix src-strip,Go module prefix,Tests

### [STORY-slim-079] TS/JS path alias resolution for file-mode dependency graph
> Spec: docs/specs/STORY-slim-079.md

- [x] Read tsconfig paths,Resolve alias imports,Wildcard patterns,Tests

### [STORY-slim-082] Sync prompt templates for --mode module and --focus scoping
> Spec: docs/specs/STORY-slim-082.md

- [x] Update SKILL_VISUALIZE_MD
- [x] Update Visual First rule
- [x] Update release snapshot
- [x] Update init Phase 3
- [x] Deploy and verify

### [STORY-slim-081] Two-tier module graph with scoped focus for large codebases
> Spec: docs/specs/STORY-slim-081.md

- [x] R1: _detect_modules boundary detection,R2: _build_module_graph with weighted edges,R3: Auto-degradation when files > MAX_SCAN_FILES,R4: Scoped focus scan (resolve module → directory),R5: .tsx/.jsx regression test,R6: Backward compat for small projects

### [STORY-slim-080] Deep monorepo scanning: nearest-ancestor config discovery for all analyzers
> Spec: docs/specs/STORY-slim-080.md

- [x] Extend _detect_stacks depth,TS nearest-ancestor tsconfig,Go nearest-ancestor go.mod,Plumb consumer_path,Tests

### [STORY-slim-083] Copilot deployer adapter package (pactkit-copilot)
> Spec: docs/specs/STORY-slim-083.md

- [x] CopilotDeployer class + entry_point registration + deploy to .github/ + OCP fix for rules_import_style dispatch

### [STORY-slim-084] Adapter deploy-output validation guard
> Spec: docs/specs/STORY-slim-084.md

- [x] R2: has_pactkit_cli field,R1: validate_deployed_content(),R3: Core deploy integration,R6: Core unit tests,R4: Copilot integration test,R5: Codex integration test

### [STORY-slim-086] Prompt Writing Quality — Signal Strength, Consequence Language, NO_TOOLS Mode
> Spec: docs/specs/STORY-slim-086.md

- [x] R1: Signal Strength Convention 追加到 01-core-protocol.md
- [x] R2: 校准现有规则文件信号词 (01, 02, 10)
- [x] R3: 7 条关键禁止规则添加后果语言
- [x] R4: project-check.md 添加 NO_TOOLS restriction

## ✅ Done

- **STORY-slim-059**: Remove dead codex profile and slim down core package
- **STORY-slim-058**: Extract pactkit-opencode as independent adapter package
- **STORY-slim-057**: Refactor deployer.py: extract DeployerProtocol and DeployerBase

### [HOTFIX-slim-085] Add Duplication Audit to Plan phase
> Spec: docs/specs/HOTFIX-slim-085.md

- [x] system-architect agent + Plan playbook

### [STORY-slim-088] Slim dependencies and robust CLI fallback
> Spec: docs/specs/STORY-slim-088.md

- [x] Move adapters+tree-sitter to optional-dependencies
- [x] Add python3 -m fallback for spec-lint in playbooks
- [x] Fix add_story call signature in Plan playbook

### [HOTFIX-slim-087] guard 添加 -C 参数
> Spec: docs/specs/HOTFIX-slim-087.md

- [x] Fix guard CWD false alarm in subagent

### [BUG-slim-089] Global CLAUDE.md overwritten on every deploy
> Spec: docs/specs/BUG-slim-089.md

- [x] Add _is_pactkit_managed_global_md helper
- [x] Refactor _deploy_claude_md with read-before-write guard
- [x] Add unit tests for AC1-AC5

### [STORY-slim-090] Interactive HTML Report Skill (D3 Force Graph)
> Spec: docs/specs/STORY-slim-090.md

- [x] Implement MMD parser (graph TD + classDiagram)
- [x] Create D3 HTML template with force simulation
- [x] Implement render_html with zoom/pan/drag/hover/search/theme
- [x] Add overlay support (blast radius, complexity, layers)
- [x] Create skill entry point + CLI
- [x] Write unit tests

### [STORY-slim-089] Enterprise Code Analysis: Blast Radius, Cyclomatic Complexity, Layer Violations
> Spec: docs/specs/STORY-slim-089.md

- [x] Add complexity counting to LanguageAnalyzer interface
- [x] Implement Python complexity in PythonAnalyzer
- [x] Implement TS/Go/Java complexity in TreeSitterAnalyzer subclasses
- [x] Add blast_radius() with bidirectional BFS
- [x] Add complexity() report function
- [x] Add layers() with configurable layer model
- [x] Add CLI subcommands (blast_radius, complexity, layers)
- [x] Write unit tests for all 3 features
