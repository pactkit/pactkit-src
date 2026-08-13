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

### [HOTFIX-slim-127] Add codegraph sync to PDCA command source templates
> Spec: docs/specs/HOTFIX-slim-127.md

- [ ] Fix project-plan
- [ ] Fix project-act
- [ ] Fix project-done
- [ ] Fix project-hotfix

### [HOTFIX-slim-131] Fix deployer @ refs before frontmatter
> Spec: docs/specs/HOTFIX-slim-131.md

- [ ] Fix _deploy_commands prepend order

### [HOTFIX-slim-132] Add explicit board.py move_story command to project-act
> Spec: docs/specs/HOTFIX-slim-132.md

- [ ] Add move_story command template to Phase 0.6


### [STORY-slim-139] Skill manifest single source + adapter parity check
> Spec: docs/specs/STORY-slim-139.md

- [ ] SKILL_MANIFEST 注册表+get_skill_manifest()
- [ ] _deploy_skills 迭代化+.pactkit-deployed.json 落盘
- [ ] doctor parity 检查(能力矩阵感知)
- [ ] 跨仓: pactkit-codex 消费契约+版本 bump
- [ ] 单测


### [STORY-slim-140] commit-gate git-hook fallback for non-Claude environments
> Spec: docs/specs/STORY-slim-140.md

- [ ] cli post-deploy 格式分派(无 classic→自动 git hook)
- [ ] 门禁通道状态输出
- [ ] 幂等/链式/no_git 单测

## 🔄 In Progress

## ✅ Done

