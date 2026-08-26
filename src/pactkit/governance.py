"""Sharded governance facts and deterministic projections."""

from __future__ import annotations

import re
import secrets
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pactkit.id_generator import ITEM_ID_RE
from pactkit.utils import atomic_write

STORY_SCHEMA_VERSION = 1
LESSON_SCHEMA_VERSION = 1
STATUSES = ("backlog", "in_progress", "done", "archived")
_ITEM_BODY = ITEM_ID_RE.pattern.removeprefix("^").removesuffix("$")
_STORY_HEADING = re.compile(
    rf"^#{{3,4}}\s+\[?(?P<id>{_ITEM_BODY})\]?:?\s*(?P<title>.*)$", re.MULTILINE
)
_SECTION = re.compile(r"^##\s+(?P<title>.+)$", re.MULTILINE)
_TASK = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<title>.+)$", re.MULTILINE)
_LESSON_ROW = re.compile(
    r"^\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*(?P<text>[^|]+?)\s*\|\s*(?P<context>[^|]*?)\s*\|\s*$"
)


class GovernanceError(ValueError):
    """A governance record is invalid or unsafe to update."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _validate_item_id(item_id: str) -> None:
    if not ITEM_ID_RE.fullmatch(item_id):
        raise GovernanceError(f"invalid item ID: {item_id}")


def _task_id(title: str, position: int) -> str:
    import hashlib

    digest = hashlib.sha256(f"{position}\0{title}".encode()).hexdigest()[:10]
    return f"task-{digest}"


class StoryRepository:
    def __init__(
        self, root: Path, *, run_id: str | None = None,
        workflow_id: str | None = None, standalone: bool = True,
    ):
        self.root = root.resolve()
        self.directory = self.root / "docs" / "product" / "stories"
        self.run_id = run_id
        self.workflow_id = workflow_id
        self.standalone = standalone

    def _authorize(self, operation: str, item_id: str) -> dict[str, Any]:
        if self.run_id:
            from pactkit.continuation import ContinuationEngine

            if not self.workflow_id:
                raise GovernanceError("managed Story write requires workflow identity")
            try:
                return ContinuationEngine(self.root).validate_managed_operation(
                    self.run_id, workflow_id=self.workflow_id, operation=operation,
                    story_id=item_id,
                )
            except ValueError as exc:
                raise GovernanceError(str(exc)) from exc
        if not self.standalone:
            raise GovernanceError("Story write requires managed run or explicit standalone mode")
        return {"managed": False}

    def path_for(self, item_id: str) -> Path:
        _validate_item_id(item_id)
        return self.directory / f"{item_id}.yaml"

    def _validate(self, record: Any) -> dict[str, Any]:
        if not isinstance(record, dict) or record.get("schema_version") != STORY_SCHEMA_VERSION:
            raise GovernanceError("invalid Story record schema")
        _validate_item_id(str(record.get("id", "")))
        if not isinstance(record.get("title"), str) or not record["title"].strip():
            raise GovernanceError("Story title is required")
        if record.get("status") not in STATUSES:
            raise GovernanceError(f"unknown Story status: {record.get('status')}")
        tasks = record.get("tasks")
        if not isinstance(tasks, list):
            raise GovernanceError("Story tasks must be a list")
        ids = set()
        for task in tasks:
            if (
                not isinstance(task, dict)
                or not isinstance(task.get("id"), str)
                or not isinstance(task.get("title"), str)
                or not isinstance(task.get("completed"), bool)
            ):
                raise GovernanceError("invalid Story task")
            if task["id"] in ids:
                raise GovernanceError("duplicate task ID")
            ids.add(task["id"])
        return record

    def load(self, item_id: str) -> dict[str, Any]:
        path = self.path_for(item_id)
        if not path.is_file():
            raise GovernanceError(f"Story record not found: {item_id}")
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise GovernanceError(f"invalid Story YAML: {item_id}") from exc
        record = self._validate(record)
        if record["id"] != item_id:
            raise GovernanceError(f"Story path/identity mismatch: {item_id}")
        return record

    def list(self) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        return [self.load(path.stem) for path in sorted(self.directory.glob("*.yaml"))]

    def _write(self, record: dict[str, Any], *, create_only: bool = False) -> None:
        self._validate(record)
        path = self.path_for(record["id"])
        if create_only and path.exists():
            raise GovernanceError(f"Story record already exists: {record['id']}")
        content = yaml.safe_dump(record, sort_keys=False, allow_unicode=True)
        atomic_write(path, content)

    def add(self, item_id: str, title: str, tasks: list[str], *, status: str = "backlog") -> dict[str, Any]:
        _validate_item_id(item_id)
        ownership = self._authorize("create_story", item_id)
        normalized_title = title.strip()
        normalized_tasks = [task.strip() for task in tasks if task.strip()]
        path = self.path_for(item_id)
        if path.exists() and ownership["managed"]:
            existing = self.load(item_id)
            actual_tasks = [task["title"] for task in existing["tasks"]]
            if (
                existing["title"] == normalized_title
                and existing["status"] == status
                and actual_tasks == normalized_tasks
            ):
                return {**existing, "managed": True}
            raise GovernanceError(f"existing Story mismatch: {item_id}")
        timestamp = _now()
        record = {
            "schema_version": STORY_SCHEMA_VERSION,
            "id": item_id,
            "title": normalized_title,
            "spec_path": f"docs/specs/{item_id}.md",
            "status": status,
            "tasks": [
                {"id": _task_id(task.strip(), index), "title": task.strip(), "completed": False}
                for index, task in enumerate(normalized_tasks)
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        self._write(record, create_only=True)
        return {**record, "managed": ownership["managed"]}

    def add_task(self, item_id: str, task: str) -> dict[str, Any]:
        """Append a task to an existing Story (mid-story additions).

        Adding open work to a done Story reopens it (in_progress), keeping
        the all-completed status invariant honest.
        """
        ownership = self._authorize("update_story", item_id)
        record = self.load(item_id)
        normalized = task.strip()
        if not normalized:
            raise GovernanceError("task title must not be empty")
        if any(entry["title"] == normalized for entry in record["tasks"]):
            raise GovernanceError(f"task already exists: {normalized}")
        record["tasks"].append({
            "id": _task_id(normalized, len(record["tasks"])),
            "title": normalized,
            "completed": False,
        })
        if record["status"] == "done":
            record["status"] = "in_progress"
            record.pop("completed_at", None)
        record["updated_at"] = _now()
        self._write(record)
        return {**record, "managed": ownership["managed"]}

    def complete_task(self, item_id: str, task: str) -> dict[str, Any]:
        ownership = self._authorize("update_story", item_id)
        record = self.load(item_id)
        matches = [entry for entry in record["tasks"] if entry["id"] == task or entry["title"] == task]
        if len(matches) != 1:
            raise GovernanceError(f"task must match exactly once: {task}")
        matches[0]["completed"] = True
        if record["tasks"] and all(entry["completed"] for entry in record["tasks"]):
            record["status"] = "done"
            record["completed_at"] = _now()
        elif record["status"] == "backlog":
            record["status"] = "in_progress"
        record["updated_at"] = _now()
        self._write(record)
        return {**record, "managed": ownership["managed"]}

    def move(self, item_id: str, status: str) -> dict[str, Any]:
        if status not in STATUSES:
            raise GovernanceError(f"unknown Story status: {status}")
        ownership = self._authorize("update_story", item_id)
        record = self.load(item_id)
        record["status"] = status
        record["updated_at"] = _now()
        if status in {"done", "archived"}:
            record.setdefault("completed_at", _now())
        if status == "archived":
            record["archived_at"] = _now()
        self._write(record)
        return {**record, "managed": ownership["managed"]}


class BoardRenderer:
    def __init__(self, repository: StoryRepository):
        self.repository = repository

    def render(self) -> str:
        buckets = {"backlog": [], "in_progress": [], "done": []}
        for record in self.repository.list():
            bucket = "done" if record["status"] in {"done", "archived"} else record["status"]
            buckets[bucket].append(record)
        lines = ["# Sprint Board", ""]
        sections = (
            ("## 📋 Backlog", "backlog"),
            ("## 🔄 In Progress", "in_progress"),
            ("## ✅ Done", "done"),
        )
        for heading, status in sections:
            lines.extend([heading, ""])
            for record in sorted(buckets[status], key=lambda item: item["id"]):
                lines.append(f"### [{record['id']}] {record['title']}")
                lines.extend([f"> Spec: {record['spec_path']}", ""])
                lines.extend(
                    f"- [{'x' if task['completed'] else ' '}] {task['title']}"
                    for task in record["tasks"]
                )
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def check(self, path: Path) -> bool:
        return path.is_file() and path.read_text(encoding="utf-8") == self.render()


class LessonRepository:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.directory = self.root / "docs" / "architecture" / "governance" / "lessons"

    def add(self, story_id: str, text: str, context: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        _validate_item_id(story_id)
        lesson_id = f"LESSON-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(5)}"
        path = self.directory / f"{lesson_id}.md"
        if path.exists():
            raise GovernanceError(f"Lesson record already exists: {lesson_id}")
        metadata = {
            "schema_version": LESSON_SCHEMA_VERSION, "id": lesson_id,
            "date": date.today().isoformat(), "story_id": story_id,
            "context": context or story_id, "tags": tags or [],
        }
        content = (
            "---\n"
            + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
            + "---\n\n"
            + text.strip()
            + "\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.open("x", encoding="utf-8").write(content)
        return {**metadata, "text": text.strip(), "path": str(path.relative_to(self.root))}

    def import_legacy(
        self, lesson_id: str, lesson_date: str, text: str, context: str, *, source: str
    ) -> dict[str, Any]:
        """Create one immutable record from a legacy table row."""
        if not re.fullmatch(r"LESSON-\d{8}-[0-9a-f]{10}", lesson_id):
            raise GovernanceError(f"invalid Lesson ID: {lesson_id}")
        try:
            date.fromisoformat(lesson_date)
        except ValueError as exc:
            raise GovernanceError(f"invalid Lesson date: {lesson_date}") from exc
        if not text.strip():
            raise GovernanceError("Lesson text is required")
        path = self.directory / f"{lesson_id}.md"
        if path.exists():
            raise GovernanceError(f"Lesson record already exists: {lesson_id}")
        metadata = {
            "schema_version": LESSON_SCHEMA_VERSION,
            "id": lesson_id,
            "date": lesson_date,
            "story_id": context if ITEM_ID_RE.fullmatch(context) else None,
            "context": context,
            "tags": ["legacy-import"],
            "legacy_source": source,
        }
        content = (
            "---\n"
            + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
            + "---\n\n"
            + text.strip()
            + "\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.open("x", encoding="utf-8").write(content)
        return {**metadata, "text": text.strip(), "path": str(path.relative_to(self.root))}

    def _load(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n") or "\n---\n" not in content[4:]:
            raise GovernanceError(f"invalid Lesson record: {path.name}")
        raw, text = content[4:].split("\n---\n", 1)
        metadata = yaml.safe_load(raw)
        if not isinstance(metadata, dict) or metadata.get("schema_version") != LESSON_SCHEMA_VERSION:
            raise GovernanceError(f"invalid Lesson schema: {path.name}")
        return {**metadata, "text": text.strip(), "path": str(path.relative_to(self.root))}

    def recent(self, limit: int = 5) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        records = [self._load(path) for path in self.directory.glob("*.md")]
        return sorted(records, key=lambda item: item["id"], reverse=True)[:limit]


class GovernanceMigrator:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _legacy_stories(self) -> list[dict[str, Any]]:
        path = self.root / "docs" / "product" / "sprint_board.md"
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8")
        sections = list(_SECTION.finditer(text))
        status_at: list[tuple[int, str]] = []
        for section in sections:
            label = section.group("title").lower()
            status = "in_progress" if "progress" in label else "done" if "done" in label else "backlog"
            status_at.append((section.start(), status))
        headings = list(_STORY_HEADING.finditer(text))
        records = []
        seen = set()
        for index, heading in enumerate(headings):
            item_id = heading.group("id")
            if item_id in seen:
                raise GovernanceError(f"duplicate Story in legacy board: {item_id}")
            seen.add(item_id)
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            next_section = next((pos for pos, _ in status_at if heading.end() < pos < end), end)
            block = text[heading.end():next_section]
            status = next((value for pos, value in reversed(status_at) if pos < heading.start()), "backlog")
            records.append({
                "id": item_id, "title": heading.group("title").strip(), "status": status,
                "tasks": [(m.group("title").strip(), m.group("mark").lower() == "x") for m in _TASK.finditer(block)],
            })
        return records

    def _legacy_lessons(self) -> list[dict[str, str]]:
        governance = self.root / "docs" / "architecture" / "governance"
        sources = [governance / "lessons.md"]
        sources.extend(sorted((governance / "archive").glob("lessons_archive_*.md")))
        records: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for source in sources:
            if not source.is_file():
                continue
            relative_source = str(source.relative_to(self.root))
            for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if not stripped.startswith("|") or not re.search(r"\d{4}-\d{2}-\d{2}", stripped):
                    continue
                match = _LESSON_ROW.fullmatch(stripped)
                if not match:
                    raise GovernanceError(
                        f"ambiguous legacy Lesson row: {relative_source}:{line_number}"
                    )
                values = {name: value.strip() for name, value in match.groupdict().items()}
                try:
                    date.fromisoformat(values["date"])
                except ValueError as exc:
                    raise GovernanceError(
                        f"invalid legacy Lesson date: {relative_source}:{line_number}"
                    ) from exc
                import hashlib

                identity = f"{relative_source}\0{line_number}\0{values['date']}\0{values['text']}\0{values['context']}"
                digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
                lesson_id = f"LESSON-{values['date'].replace('-', '')}-{digest}"
                if lesson_id in seen_ids:
                    raise GovernanceError(f"duplicate generated Lesson ID: {lesson_id}")
                seen_ids.add(lesson_id)
                records.append({**values, "id": lesson_id, "source": relative_source})
        return records

    @staticmethod
    def _remove_installed(paths: list[Path]) -> None:
        for path in reversed(paths):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def migrate(self, *, dry_run: bool = True) -> dict[str, Any]:
        stories = self._legacy_stories()
        lessons = self._legacy_lessons()
        report = {
            "stories": len(stories), "lessons": len(lessons), "dry_run": dry_run,
            "legacy_preserved": True,
            "git_actions": ["review generated records", "stop tracking legacy projections after confirmation"],
        }
        if dry_run or (not stories and not lessons):
            return report
        story_target = self.root / "docs" / "product" / "stories"
        lesson_target = self.root / "docs" / "architecture" / "governance" / "lessons"
        for label, target in (("Story", story_target), ("Lesson", lesson_target)):
            if target.exists() and (not target.is_dir() or any(target.iterdir())):
                raise GovernanceError(
                    f"{label} records already exist; refusing legacy dual-write migration"
                )
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            stage_root = Path(temp)
            story_repo = StoryRepository(stage_root)
            for item in stories:
                record = story_repo.add(
                    item["id"], item["title"],
                    [title for title, _ in item["tasks"]], status=item["status"],
                )
                for task, completed in zip(record["tasks"], item["tasks"]):
                    task["completed"] = completed[1]
                story_repo._write(record)
            lesson_repo = LessonRepository(stage_root)
            for item in lessons:
                lesson_repo.import_legacy(
                    item["id"], item["date"], item["text"], item["context"],
                    source=item["source"],
                )
            staged_stories = story_repo.list()
            staged_lessons = lesson_repo.recent(limit=len(lessons) + 1)
            story_facts = sorted(
                (record["id"], record["title"], record["status"],
                 [(task["title"], task["completed"]) for task in record["tasks"]])
                for record in staged_stories
            )
            expected_story_facts = sorted(
                (item["id"], item["title"], item["status"], item["tasks"])
                for item in stories
            )
            lesson_facts = sorted(
                (record["id"], str(record["date"]), record["text"], record["context"])
                for record in staged_lessons
            )
            expected_lesson_facts = sorted(
                (item["id"], item["date"], item["text"], item["context"])
                for item in lessons
            )
            if story_facts != expected_story_facts or lesson_facts != expected_lesson_facts:
                raise GovernanceError("migration reconciliation failed")

            installs = []
            try:
                for source, target in (
                    (story_repo.directory, story_target),
                    (lesson_repo.directory, lesson_target),
                ):
                    if not source.exists():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        target.rmdir()
                    source.replace(target)
                    installs.append(target)
            except OSError as exc:
                self._remove_installed(installs)
                raise GovernanceError(f"migration install failed and rolled back: {exc}") from exc
        return report
