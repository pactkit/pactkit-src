# STORY-004: Project Visibility — GitHub/PyPI/README/Website 曝光度优化

- **Author**: System Architect
- **Status**: Draft
- **Priority**: High
- **Release**: 1.0.0
- **Depends**: None

## Background

PactKit 已发布到 PyPI 和 GitHub，但曝光度几乎为零：
- GitHub repo 无 topics（无法被 Explore/Search 发现）
- Repo description 偏技术化，缺少情感钩子
- README 引用了已删除的 `--mode common` 选项
- PyPI keywords 缺少高搜索量关键词
- PyPI classifier 仍为 Beta（实际已 1.0.0）
- pactkit.dev repo 无 homepage/topics

## Requirements

### R1: GitHub Topics (pactkit/pactkit)
- **MUST** 设置以下 topics: `claude-code`, `ai-agent`, `devops`, `tdd`, `spec-driven`, `multi-agent`, `pdca`, `python`, `cli`, `developer-tools`, `code-quality`, `anthropic`
- **SHOULD** 保持 topics 数量 ≤ 15

### R2: GitHub Description (pactkit/pactkit)
- **MUST** 更新 repo description 为更具吸引力的一句话
- **MUST** 包含核心卖点关键词（spec-driven, agents, Claude Code）
- **SHOULD** 控制在 120 字符以内

### R3: GitHub Metadata (pactkit/pactkit.dev)
- **MUST** 设置 homepage URL 为 `https://pactkit.dev`
- **MUST** 添加 topics: `documentation`, `nextjs`, `fumadocs`

### R4: README 优化
- **MUST** 删除 `--mode common` 相关内容（该功能已移除）
- **MUST** 更新 tagline 使其更具冲击力
- **SHOULD** 增加一个 "What it looks like" 或 demo 引导区域
- **SHOULD** 在 badges 行增加 downloads badge

### R5: PyPI 元数据
- **MUST** 在 keywords 中增加: `claude`, `anthropic`, `multi-agent`, `code-assistant`, `code-quality`, `developer-tools`
- **MUST** 将 classifier 从 `Development Status :: 4 - Beta` 改为 `Development Status :: 5 - Production/Stable`

### R6: Website Hero 文案
- **SHOULD** 优化 sub-headline 使其更简洁有力

## Acceptance Criteria

### Scenario 1: GitHub Topics 可发现
```gherkin
Given the pactkit/pactkit repo on GitHub
When a user searches "claude-code" or "ai-agent" in GitHub Explore
Then the pactkit repo SHOULD appear in search results
```

### Scenario 2: README 无过时内容
```gherkin
Given the README.md file
When a reader follows the Quick Start section
Then there MUST be no reference to --mode common
And the installation steps MUST match current CLI behavior
```

### Scenario 3: PyPI 元数据准确
```gherkin
Given the pyproject.toml file
When the package is built and uploaded
Then the classifier MUST show "Production/Stable"
And keywords MUST include "claude" and "anthropic"
```

### Scenario 4: pactkit.dev repo 有完整元数据
```gherkin
Given the pactkit/pactkit.dev repo on GitHub
When a visitor views the repo page
Then the homepage URL MUST show https://pactkit.dev
And topics MUST include "documentation"
```

## Files to Modify

| File | Change |
|------|--------|
| GitHub API | Set topics + description for both repos |
| `README.md` | Update tagline, remove --mode common, add downloads badge |
| `pyproject.toml` | Update keywords and classifier |
| `pactkit.dev/src/components/hero.tsx` | Optimize sub-headline |
