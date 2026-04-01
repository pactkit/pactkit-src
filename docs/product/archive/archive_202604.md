
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
