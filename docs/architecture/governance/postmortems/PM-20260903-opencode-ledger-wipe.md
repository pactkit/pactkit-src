# Postmortem: 部署所有权账本缺口的三种形态（同日第三例）

| Field | Value |
|-------|-------|
| Date | 2026-09-03 |
| Status | resolved |
| Items | HOTFIX-slim-20260903d464746b1909 |

## Timeline

- 上午: codex 形态一（PM-20260903 主文）——账本在写，部署检查不读
- 下午: 根因 story 修复 codex + accept-candidates 上线
- 晚: opencode 形态二——适配器后处理改写后**无人记账**（record_deployed_reference 零调用的 opencode 版）；形态三——**记账也被抹**：write_deploy_manifest 每次部署结尾用 pactkit_owned_files 重建 files 映射，而该函数没有 opencode commands 分支 → 适配器记的 digest 同轮被抹 → 候选跑步机以 0/3/0 交替模式振荡（交替=字节巧合掩蔽）

## Root cause（类级）

三种形态同属一个类：**所有权账本的生命周期没有一个端到端的持有者**——写（record）、读（deploy check）、重建（write_deploy_manifest）三段代码各自为政，每段单独看都"按设计工作"。codex：写在 A 读在 B；opencode：写在 A 重建在 C 且 C 不认识 A 写的键。

## Why defenses missed it

- 每段的单测都过（各自语义正确），缺的是跨段集成测试：record → rebuild → 下次 deploy 所有权可证
- 交替振荡模式被字节巧合掩蔽——单次 E2E 通过 ≠ 稳定，本轮教训：稳定性验证必须连跑 ≥3 轮

## Blast radius

- opencode 用户的 act/plan/done 三个命令每次 update 产候选；若用户 accept 原始内容候选，会得到含 `pactkit clean` 的文本（OpenCode 用户未必装了 CLI）——不只是噪音，是错误内容

## Recurrence-prevention action items

1. [已完成] pactkit_owned_files 增加 opencode commands 分支（含 .pactkit-new 冲突守卫）
2. [已完成] 适配器后处理后 record_deployed_file（双保险）
3. [Board story] 账本生命周期集成测试：对每个 adapter 格式，record → write_deploy_manifest 重建 → 断言 digest 存续且下次 deploy 零候选（三段闭环，防第四种形态）
