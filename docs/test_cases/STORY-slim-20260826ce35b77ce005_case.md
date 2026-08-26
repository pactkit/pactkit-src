# Test Case: STORY-slim-20260826ce35b77ce005

Gate subsystem fails closed: inverted and fail-open gates fixed.

## TC-01: pip-audit exit 1 reports vulnerabilities (R1, AC1)

- **Given** a mocked pip-audit subprocess exiting 1 with a JSON body of two vulnerabilities
- **When** the dependency-health check runs
- **Then** vulns == 2 and fixable == 1

## TC-02: pip-audit probe error is explicit (R1, AC1)

- **Given** a mocked pip-audit subprocess exiting 2
- **When** the dependency-health check runs
- **Then** vulns == -1 with an error reason

## TC-03: R12 does not satisfy R1-R11 (R2, AC2)

- **Given** a spec with MUST items R1-R12 and a case file referencing only R12
- **When** done-verify runs
- **Then** exactly R12 passes and R1-R11 fail

## TC-04: story IDs match on boundary (R2, AC2)

- **Given** an archive mentioning STORY-slim-100
- **When** _archived searches for STORY-slim-10
- **Then** no match (and hyphen-suffixed IDs also do not prefix-match)

## TC-05: doctor receives a config file path (R3, AC3)

- **Given** monkeypatched pactkit.config.load_config recording its argument
- **When** check_stale_graphs runs
- **Then** load_config never receives a directory

## TC-06: coverage block verdict exits 1 (R4, AC4)

- **Given** a coverage result with overall "block"
- **When** the CLI coverage-gate handler runs
- **Then** the process exits with code 1

## TC-07: dropped source file surfaces as failure (R4, AC5)

- **Given** two changed sources where one produces no coverage data
- **When** check_coverage runs
- **Then** the unresolved file appears as a block entry

## TC-08: git collection failure blocks, not skip (R5, AC6)

- **Given** a git probe returning nonzero during changed-file collection
- **When** commit-gate runs
- **Then** the outcome is COLLECTION-FAILED with exit code 1

## TC-09: test-only changes are not doc-only (R5, AC6)

- **Given** a change set of only tests/**
- **When** classify_changes runs
- **Then** the strategy is not skip

## TC-10: fresh-repo initial commit is not blocked (R5, QA fix)

- **Given** a repo with zero commits where rev-parse HEAD fails
- **When** collect_changed_files runs
- **Then** staged and untracked files are collected without GitCollectionError

## TC-11: crashed analyzer is visible (R6, AC7)

- **Given** a layer check raising an exception
- **When** audit runs
- **Then** the layer shows an error entry and checks_failed names it

## TC-12: single-layer probe preserves the scorecard (R8, AC8)

- **Given** a persisted passing harness_audit.json
- **When** audit --layer H2 runs
- **Then** the persisted record is unchanged

## TC-13: secret pathspec covers key material (R7, AC9)

- **Given** git ls-files returning id_rsa and server.pem
- **When** the H5 no_secrets check runs
- **Then** no_secrets is False

## TC-14: coverage probe failure blocks (R4, QA fix)

- **Given** a pytest-cov run raising TimeoutExpired
- **When** check_coverage runs
- **Then** overall is block with a probe-failed reason
