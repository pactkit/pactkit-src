# Contributing to PactKit

Thank you for your interest in contributing to PactKit!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/pactkit.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Install in development mode: `pip install -e ".[dev]"`
5. Run tests: `pytest`

## Development Workflow

PactKit follows its own PDCA workflow:

1. **Plan** — Open an issue describing what you want to change and why
2. **Act** — Write tests first (TDD), then implement
3. **Check** — Ensure all tests pass: `pytest`
4. **Done** — Submit a PR with conventional commit messages

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix a bug
docs(scope): update documentation
test(scope): add or update tests
chore(scope): build/tooling changes
refactor(scope): code refactoring
```

## Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if behavior changes
- All CI checks must pass before merge

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior through [GitHub Security Advisories](https://github.com/pactkit/pactkit/security/advisories/new) or by opening a [GitHub Issue](https://github.com/pactkit/pactkit/issues).
