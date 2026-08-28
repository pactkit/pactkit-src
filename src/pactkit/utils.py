import json
import os
import sys


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    try:
        tmp.write_text(content, encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    print(f'   -> Wrote {path.name}', file=sys.stderr)


def pytest_command(root) -> list[str]:
    """Venv-aware [python, "-m", "pytest"] for this project root.

    Single source shared by commit_gate and coverage_gate
    (STORY-slim-20260826ce35b77ce005 R4). Prefers the project venv's
    interpreter, else the current interpreter.
    """
    import sys
    from pathlib import Path

    from pactkit.config import detect_venv

    root = Path(root)
    found = detect_venv(root)
    if found:
        venv_dir, layout = found
        candidate = root / venv_dir / (
            "Scripts/python.exe" if layout == "windows" else "bin/python3"
        )
        if candidate.exists():
            return [str(candidate), "-m", "pytest"]
    return [sys.executable, "-m", "pytest"]


def stack_test_command(root) -> tuple[str, list[str]] | None:
    """Stack-aware test command for this project root.

    STORY-slim-20260828d43fae4edbb6: the commit-gate must run the project's
    real suite, not force pytest onto a Node/Go/Java repo.  Returns
    ``(stack, argv)`` or ``None`` when the detected stack has no runnable
    test command — callers degrade to WARN + allow (self-lock protection),
    never run a wrong-suite command.

    Resolution order: python markers (or no markers at all) keep the
    venv-aware pytest command — existing behavior, monorepos included.
    """
    from pathlib import Path

    from pactkit.cleaners import detect_stacks

    root = Path(root)
    try:
        stacks = detect_stacks(root)
    except OSError:
        stacks = ["python"]

    if "python" in stacks:
        return ("python", pytest_command(root))

    if "node" in stacks:
        package = root / "package.json"
        if package.is_file():
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            scripts = data.get("scripts")
            if isinstance(scripts, dict) and scripts.get("test"):
                return ("node", ["npm", "test", "--silent"])
        return None

    if "go" in stacks:
        return ("go", ["go", "test", "./..."])

    if "java" in stacks:
        if (root / "mvnw").exists() or (root / "pom.xml").exists():
            if (root / "mvnw").exists():
                return ("java", ["./mvnw", "-q", "test"])
            return ("java", ["mvn", "-q", "test"])
        if (root / "gradlew").exists():
            return ("java", ["./gradlew", "-q", "test"])
        return ("java", ["gradle", "-q", "test"])

    return ("python", pytest_command(root))
