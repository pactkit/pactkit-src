# Test Cases: STORY-slim-202609025bc9246b6a54 — commit-gate 计数解析鲁棒性

> 实现位置:`tests/unit/test_gate_junit_counts.py`(真实 pytest 子进程 + tmp_path
> fixture repos——事故形态在旗标/ini 组合层,monkeypatch 无法复现)。

## TC-1: 事故复现——addopts 叠加 + 真红 (R1, R3, AC1)

**Given** fixture repo:pyproject `addopts = "-q"`,tests/unit 含 3 测试(2 过 1 败)
**When** `run_gate` 触发(gate `-q` 与 addopts 叠加为 `-qq`)
**Then** 拦截(exit 1),计数为真实值 `2 passed, 1 failed`(非全 0)
**And** 文案为 `tests are RED`,输出含 `FAILED tests/unit/...` tail 行
**And** 不出现 `no tests` 断言
**Impl** `TestIncidentRepro::test_ac1_addopts_q_red_reports_real_counts` / `test_ac1_failed_tail_survives_qq`

## TC-2: 绿灯 + addopts 叠加 (R1, AC2)

**Given** 同 TC-1 fixture 但套件全绿
**When** `run_gate` 触发
**Then** 放行(exit 0),计数行显示真实计数(非 "0 passed, 0 failed")
**Impl** `TestGreenWithAddopts::test_ac2_allows_with_real_counts`

## TC-3: junitxml 被禁用的 repo 不自锁 (R2, AC3)

**Given** fixture repo `addopts = "-p no:junitxml"`,套件全绿
**When** `run_gate` 触发(实测:ini 级 `-p` 静默接受旗标但不写 XML,无 exit 4)
**Then** 放行,计数来自终端 fallback;单次 subprocess 调用(无需重试)
**And** 防御分支:合成 exit 4 + `unrecognized arguments: --junitxml` 时,重试命令
不含 `--junitxml` 与 `-o junit_family=xunit2`(插件禁用下后者是未知 ini 键)
**Impl** `TestJunitxmlDisabled::test_ac3_no_selflock_when_plugin_disabled` / `test_ac3_accepted_flag_means_single_run` / `test_exit4_unrecognized_junitxml_retries_without_flags`

## TC-4: exit 5——空收集文案 (R3, AC4)

**Given** fixture repo 测试收集结果为空集(pytest exit 5)
**When** `run_gate` 触发
**Then** 拦截,文案明示 `no tests ran (pytest exit 5)`
**And** 不出现 `no tests collected` 与 `tests are RED`
**Impl** `TestExitFive::test_ac4_says_no_tests_ran`

## TC-5: 双重病态——计数不可解析的诚实文案 (R3, AC5)

**Given** fixture repo `addopts = "-q -p no:junitxml"`(-qq 无 summary 行 + 无 junit 文件)
且套件含失败
**When** `run_gate` 触发
**Then** 拦截,文案报 `pytest exited 1 but counts unparseable` 并含 `addopts` 干扰提示
**And** 不出现 `no tests collected` 断言
**Impl** `TestCountsUnparseable::test_ac5_honest_message_not_no_tests_collected`

## TC-6: junitxml 契约防御 + 临时文件生命周期 (R1, SEC-2)

**Given** parse_junit_counts 收到缺失文件 / 畸形 XML / 正常 XML
**When** 解析执行
**Then** 缺失与畸形返回 None(gate 不崩溃,降级终端解析);正常返回精确计数
(passed = tests − failures − errors − skipped)
**And** mkstemp 生成的 junit 临时文件在 run_gate 结束后被删除,内容不落任何日志
**Impl** `TestParseJunitCounts::test_missing_file_is_none` / `test_garbage_xml_is_none` / `test_real_counts` / `test_junit_file_removed_after_run`

## TC-7: 全量回归与契约兼容 (R4, AC6)

**Given** 实现完成
**When** 全量套件运行(`.venv/bin/pytest tests/unit/`)
**Then** 全绿(4820 passed),含既有 commit-gate 测试与 `run_pytest` 三元组契约的
全部调用方(test_commit_gate / test_push_gate / test_stack_test_command /
test_hotfix_20260901_gate_docsonly)
