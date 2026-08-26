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
