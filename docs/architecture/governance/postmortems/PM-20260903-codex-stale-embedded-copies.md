# Postmortem: Codex 嵌入副本陈旧（同日第二次复发）

| Field | Value |
|-------|-------|
| Date | 2026-09-03 |
| Status | resolved |
| Items | STORY-slim-2026090301691dea72e8（首次发现）、STORY-slim-20260903b5ce6be5f7e0（复发） |

## Timeline

- 2026-08-24 前某时: codex adapter 部署链开始把 rules/guides 嵌入到每个 skill 的 references/ 目录，但嵌套副本未登记进 `.pactkit-deployed.json` manifest
- 2026-09-03 上午: STORY-...01691dea72e8 done 阶段 doctor 报 5 处 rule conflict，确认为旧受管内容后手动替换 .pactkit-new 候选；根因（manifest 未登记）记为 backlog 候选，未立 story
- 2026-09-03 下午: 后续 story 修改 capability-design（Knowledge Provenance）与三个 guide（Practice），再次 `pactkit update` 后 8 处副本重新陈旧（含上午已手动替换的 5 处）——手动替换被证明是跑步机而非修复
- 2026-09-03 下午: 用户发现"没看到 rules 更新"，触发第二次人工清点+替换

## Root cause

deployer 的 ownership 安全机制依赖 manifest hash 证明文件归属；codex 嵌入副本（skills/project-*/references/{rules,guides}/*.md）未写入 manifest 的 files 映射 → 每次内容更新时 deployer 无法证明这些文件归 pactkit 所有 → 安全默认 preserve 旧内容 + 写 .pactkit-new 候选。**机制按设计工作，登记缺口使设计自我挫败。**

## Blast radius

- codex adapter 的全部用户：capsule（capability-design 含 Knowledge Provenance 前版本）与 guide（含 Practice 前版本）持续陈旧，直到人工干预
- classic（~/.claude）与 opencode 副本不受影响（它们在 manifest 内，正常更新）
- 上午 5 处手动替换在数小时内再次过时——修复投入被静默作废

## Why existing defenses missed it

- deployer 的 preserve 机制是**正确**的安全默认（它防的是覆写用户内容）——它不是缺陷，是登记缺失让正确机制产出错误结果
- doctor 的 "Rule conflict" 警告确实每次都报了（防线工作）——但输出只提示"review candidate"，无一等接受机制，人工处理依赖维护者记得上午的事
- 首次发现时根因已诊断（"候选接受机制是 backlog 候选"）但未按 defect-class sweep 原则立 story——只修了实例没修类

## 复发记录

- 第 1 次: 2026-09-03 上午, 5 处 capsule/index(手动替换)
- 第 2 次: 2026-09-03 下午, 8 处 capsule + 3 guide(手动替换, 本复盘建立)
- 第 3 次: 2026-09-03 晚, 20 处 guide Practice(按本复盘协议处置)——每 pactkit update 必复发已确认为系统性, 根因 story 未完成前手动替换是标准操作

## Resolution (2026-09-03 晚)

根因修复落地（STORY-slim-20260903a24e1ece0d7f，pactkit 2211e12 + pactkit-codex 5ba9ef2）：
- R1: 部署检查合并 references 账本（ownership_proofs = deploy manifest + command manifest 合并视图，与清理路径同型）
- R2: `pactkit accept-candidates` 一等接受命令（mv + 双账本回写）
- 终态验证：接受 12 个历史候选后再跑 update，零 preserve、零新候选——跑步机闭环
- 遗留：opencode 12 个命令候选已由用户授权收掉（2026-09-03）

## Recurrence-prevention action items

1. [Board story] deployer 将 codex 嵌入副本写入 deploy manifest（.pactkit-deployed.json files 映射），使 ownership 可证明、更新直通——根因修复
2. [Board story] `.pactkit-new` 候选接受机制（`pactkit update --accept-candidates` 或 doctor 提示可执行命令）——在根因修复前的过渡缓解
3. [本复盘] 缺陷类扫除原则的自查：首次发现"同类位点"时应立 story 而非只修实例——2026-09-03 上午的教训已被本复盘捕获
