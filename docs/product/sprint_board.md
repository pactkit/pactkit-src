# Sprint Board

## 📋 Backlog

### [STORY-slim-118] codegraph MCP Integration for Semantic Code Queries
> Spec: docs/specs/STORY-slim-118.md

- [ ] Document replacement vs augmentation decision
- [ ] Add codegraph MCP conditional note to SKILL_VISUALIZE_MD Graph Query Protocol
- [ ] Run pactkit update to redeploy

### [STORY-slim-119] Improve Python Call Graph Coverage
> Spec: docs/specs/STORY-slim-119.md

- [ ] Extend _extract_calls to capture non-self attribute method calls (R1)
- [ ] Capture function references in list/assignment contexts (R2)
- [ ] Use ast.walk to scan nested functions (R3)
- [ ] Write TDD tests for AC1-AC4
- [ ] Run pactkit update to redeploy


### [HOTFIX-slim-123] Fix: call_graph.db duplicate edges and orphan nodes
> Spec: docs/specs/HOTFIX-slim-123.md

- [ ] Dedup rel_edges before insert
- [ ] Filter edges to only reference existing nodes

## 🔄 In Progress

## ✅ Done

### [HOTFIX-slim-122] Fix: focus/entry overwrites call_graph.db
> Spec: docs/specs/HOTFIX-slim-122.md

- [x] Guard sqlite write against focus/entry mode
