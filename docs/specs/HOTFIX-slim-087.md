# HOTFIX-slim-087: pactkit guard 添加 -C 参数支持显式指定项目根目录

## Background
`pactkit guard` 使用 `Path.cwd()` 确定项目根目录。当 subagent 的 CWD 不是项目根时，guard 误报失败。

## Target
- `src/pactkit/cli.py` — guard 子命令定义 (argparse) + 执行逻辑

## Fix
给 `guard` 子命令添加 `-C / --project-root` 可选参数，指定时使用该路径，未指定时保持 `Path.cwd()` 回退。
