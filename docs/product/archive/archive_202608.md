
### [STORY-slim-137] pactkit deps: external dependency check and guided install
> Spec: docs/specs/STORY-slim-137.md

- [x] deps.py 注册表+check/install
- [x] CLI 子命令+init 只读摘要+doctor 健康项
- [x] project-init Phase 1.5 接线+plugin 同步
- [x] mock 单测

### [STORY-slim-138] pactkit commit-gate: pre-commit test gate with skip transparency
> Spec: docs/specs/STORY-slim-138.md

- [x] commit_gate.py 判定逻辑(regression+test-map+pytest -rs)
- [x] --hook PreToolUse 模式+自锁防护
- [x] settings.json hook 幂等部署+--git-hook
- [x] mock/fixture 单测

### [STORY-slim-136] pactkit done-verify: mechanical archive honesty gate
> Spec: docs/specs/STORY-slim-136.md

- [x] done_verify 模块: R项证据链+勾选诚实性+状态机核验
- [x] 接线验证(零生产调用方 WARN)
- [x] CLI 子命令注册
- [x] project-done playbook 强制接线+plugin 同步
- [x] 单测覆盖 AC2-AC5 场景

### [STORY-slim-135] Schema-driven pactkit.yaml governance: minimal init, single renderer, drift detection
> Spec: docs/specs/STORY-slim-135.md

- [x] 引入 CONFIG_SCHEMA registry
- [x] 渲染器收敛+init 极简输出
- [x] pactkit schema config 可发现性
- [x] 多副本同步写入+doctor 漂移检测
- [x] golden 等价性测试+全量回归

### [STORY-slim-140] commit-gate git-hook fallback for non-Claude environments
> Spec: docs/specs/STORY-slim-140.md

- [x] cli post-deploy 格式分派(无 classic→自动 git hook)
- [x] 门禁通道状态输出
- [x] 幂等/链式/no_git 单测

### [STORY-slim-139] Skill manifest single source + adapter parity check
> Spec: docs/specs/STORY-slim-139.md

- [x] SKILL_MANIFEST 注册表+get_skill_manifest()
- [x] _deploy_skills 迭代化+.pactkit-deployed.json 落盘
- [x] doctor parity 检查(能力矩阵感知)
- [x] 跨仓: pactkit-codex 消费契约+版本 bump
- [x] 单测

### [STORY-slim-141] Deployment manifest content hash verification
> Spec: docs/specs/STORY-slim-141.md

- [x] TDD 测试 AC1-AC6 (RED)
- [x] deploy_manifest.py: _hash_deployed_files + files 字段
- [x] doctor.py: 内容级 parity 比对 + 旧 manifest 降级
- [x] 回归 test_story_slim139

### [STORY-slim-142] deploy format=all with target must skip adapters + adapter skew guard
> Spec: docs/specs/STORY-slim-142.md

- [x] TDD spy 测试 AC1-AC4 (RED)
- [x] deployer.py: format=all+target 跳过 adapter
- [x] doctor.py: adapter 版本偏斜 warning
- [x] 运维: 本机 adapter 升级 2.17.0
- [x] AC3 双跑全量套件验证

### [STORY-slim-143] Spec Dependency Surface & Story DAG (spec-graph)
> Spec: docs/specs/STORY-slim-143.md

- [x] schemas.py Dependency Surface constants+template
- [x] spec_linter dangling-ref/missing-section rules
- [x] spec_graph.py DAG+waves+conflict matrix
- [x] cli.py spec-graph subcommand
- [x] TDD tests AC1-AC7
- [x] plan playbook Phase 3.2 step

### [STORY-slim-144] Sprint Wave Mode: conflict-aware parallel orchestration
> Spec: docs/specs/STORY-slim-144.md

- [x] spec-graph --json serializer
- [x] TDD json tests AC1-AC2
- [x] SPRINT_PROMPT wave mode section R2-R5
- [x] regenerate deployed sprint playbook
- [x] prompt content tests AC3-AC6
