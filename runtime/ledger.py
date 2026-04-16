"""File-based task ledger for persisting workflow state.

Each task gets a directory with a meta.json for structured state and numbered
markdown files for the raw packets and reports that move between agents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


PHASE_PENDING = "pending"
PHASE_ARCHITECT = "architect"
PHASE_DEVELOPER = "developer"
PHASE_TESTER = "tester"
PHASE_REVIEWER = "reviewer"
PHASE_COMPLETE = "complete"
PHASE_BLOCKED = "blocked"
PHASE_FAILED = "failed"


@dataclass
class TaskRecord:
    task_id: str
    description: str
    phase: str = PHASE_PENDING
    packet_count: int = 0
    retry_count: int = 0
    difficulty: int = 3
    terminal_state: str | None = None
    terminal_reason: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now()
        if not self.updated_at:
            self.updated_at = self.created_at


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


class TaskLedger:
    def __init__(self, workdir: Path):
        self._workdir = workdir

    @property
    def workdir(self) -> Path:
        return self._workdir

    def create_task(self, description: str, task_id: str | None = None) -> TaskRecord:
        if task_id is None:
            existing = list(self._workdir.glob("TASK-*")) if self._workdir.exists() else []
            nums = (int(p.name.split("-")[1]) for p in existing if p.name.split("-")[1].isdigit())
            next_num = max(nums, default=0) + 1
            task_id = f"TASK-{next_num:03d}"

        record = TaskRecord(task_id=task_id, description=description)
        task_dir = self._workdir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "packets").mkdir(exist_ok=True)
        self._write_meta(record)
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        meta_path = self._workdir / task_id / "meta.json"
        if not meta_path.exists():
            return None
        return self._load_meta(meta_path)

    def add_packet(self, task_id: str, packet_markdown: str, label: str = "") -> Path:
        record = self.get_task(task_id)
        if record is None:
            raise ValueError(f"Task {task_id} not found")
        seq = record.packet_count + 1
        record.packet_count = seq
        record.updated_at = _now()

        filename = f"{seq:03d}_{label}.md" if label else f"{seq:03d}.md"
        packet_path = self._workdir / task_id / "packets" / filename
        packet_path.write_text(packet_markdown, encoding="utf-8")
        self._write_meta(record)
        return packet_path

    def update_phase(self, task_id: str, phase: str) -> None:
        record = self.get_task(task_id)
        if record is None:
            raise ValueError(f"Task {task_id} not found")
        record.phase = phase
        record.updated_at = _now()
        self._write_meta(record)

    def increment_retry(self, task_id: str) -> int:
        record = self.get_task(task_id)
        if record is None:
            raise ValueError(f"Task {task_id} not found")
        record.retry_count += 1
        record.updated_at = _now()
        self._write_meta(record)
        return record.retry_count

    def update_difficulty(self, task_id: str, difficulty: int) -> None:
        record = self.get_task(task_id)
        if record is None:
            raise ValueError(f"Task {task_id} not found")
        record.difficulty = max(1, min(5, difficulty))
        record.updated_at = _now()
        self._write_meta(record)

    def set_complete(self, task_id: str) -> None:
        self._set_terminal(task_id, PHASE_COMPLETE, "Task completed successfully")

    def set_blocked(self, task_id: str, reason: str = "") -> None:
        self._set_terminal(task_id, PHASE_BLOCKED, reason or "Blocked")

    def set_failed(self, task_id: str, reason: str = "") -> None:
        self._set_terminal(task_id, PHASE_FAILED, reason or "Failed")

    def list_tasks(self) -> list[TaskRecord]:
        if not self._workdir.exists():
            return []
        results = []
        for task_dir in sorted(self._workdir.iterdir()):
            meta_path = task_dir / "meta.json"
            if meta_path.exists():
                results.append(self._load_meta(meta_path))
        return results

    def _set_terminal(self, task_id: str, state: str, reason: str) -> None:
        record = self.get_task(task_id)
        if record is None:
            raise ValueError(f"Task {task_id} not found")
        record.phase = state
        record.terminal_state = state
        record.terminal_reason = reason
        record.updated_at = _now()
        self._write_meta(record)

    def _write_meta(self, record: TaskRecord) -> None:
        meta_path = self._workdir / record.task_id / "meta.json"
        data = {
            "task_id": record.task_id,
            "description": record.description,
            "phase": record.phase,
            "packet_count": record.packet_count,
            "retry_count": record.retry_count,
            "difficulty": record.difficulty,
            "terminal_state": record.terminal_state,
            "terminal_reason": record.terminal_reason,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        meta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_meta(self, meta_path: Path) -> TaskRecord:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return TaskRecord(
            task_id=data["task_id"],
            description=data["description"],
            phase=data.get("phase", PHASE_PENDING),
            packet_count=data.get("packet_count", 0),
            retry_count=data.get("retry_count", 0),
            difficulty=data.get("difficulty", 3),
            terminal_state=data.get("terminal_state"),
            terminal_reason=data.get("terminal_reason", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
