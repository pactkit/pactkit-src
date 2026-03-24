# Sprint Board

## 📋 Backlog

### [STORY-slim-029] Multi-language file discovery via LANG_PROFILES
> Spec: docs/specs/STORY-slim-029.md

- [ ] _scan_files accepts file_ext param,visualize reads stack and passes file_ext,Fallback to *.py for unknown stacks,Unit tests for Python Go Java detection

### [STORY-slim-030] LanguageAnalyzer interface + Python adapter
> Spec: docs/specs/STORY-slim-030.md

- [ ] Define LanguageAnalyzer base class,Implement PythonAnalyzer wrapping ast logic,Refactor _build_call_graph to use analyzer,Refactor _build_file_graph to use analyzer,Snapshot test for identical output

### [STORY-slim-031] Unified impact test mapping via LANG_PROFILES
> Spec: docs/specs/STORY-slim-031.md

- [ ] impact reads test_map_pattern from LANG_PROFILES,Pattern resolver for module and package,Fallback to current hardcoded logic,Unit tests for Python Go Java mapping

### [STORY-slim-032] Go LanguageAnalyzer adapter
> Spec: docs/specs/STORY-slim-032.md

- [ ] Implement GoAnalyzer with regex,Import extraction for Go,Function and method extraction,Register in analyzer selection,Unit tests with Go source samples

### [STORY-slim-033] Java LanguageAnalyzer adapter
> Spec: docs/specs/STORY-slim-033.md

- [ ] Implement JavaAnalyzer with regex,Import extraction for Java,Method and call extraction,Register in analyzer selection,Unit tests with Java source samples

### [STORY-slim-034] TS/JS LanguageAnalyzer adapter
> Spec: docs/specs/STORY-slim-034.md

- [ ] Implement TSAnalyzer with regex,ES module and CommonJS import extraction,Function and arrow function extraction,Multi-extension support,Unit tests with TS/JS source samples

## 🔄 In Progress

## ✅ Done
