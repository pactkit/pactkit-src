
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
