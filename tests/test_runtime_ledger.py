from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.ledger import TaskLedger, TaskRecord, PHASE_COMPLETE, PHASE_BLOCKED, PHASE_FAILED


class TestTaskLedgerCreate:
    def test_create_task_returns_record(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        record = ledger.create_task("Add --dry-run flag")
        assert record.task_id == "TASK-001"
        assert record.description == "Add --dry-run flag"
        assert record.phase == "pending"
        assert record.terminal_state is None

    def test_create_task_with_custom_id(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        record = ledger.create_task("test", task_id="TASK-042")
        assert record.task_id == "TASK-042"

    def test_create_task_persists_meta(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("persisted task")
        meta = (tmp_path / "tasks" / "TASK-001" / "meta.json").read_text()
        assert "persisted task" in meta

    def test_create_sequential_tasks(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("first")
        second = ledger.create_task("second")
        assert second.task_id == "TASK-002"


class TestTaskLedgerGet:
    def test_get_existing_task(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("find me")
        record = ledger.get_task("TASK-001")
        assert record is not None
        assert record.description == "find me"

    def test_get_nonexistent_task(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        assert ledger.get_task("TASK-999") is None


class TestTaskLedgerPackets:
    def test_add_packet(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        path = ledger.add_packet("TASK-001", "## Packet\n- packet_type: test", "architect")
        assert path.exists()
        assert "001_architect.md" in path.name

    def test_add_packet_increments_count(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        ledger.add_packet("TASK-001", "packet1", "a")
        ledger.add_packet("TASK-001", "packet2", "b")
        record = ledger.get_task("TASK-001")
        assert record.packet_count == 2

    def test_add_packet_unknown_task_raises(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        try:
            ledger.add_packet("TASK-999", "data", "x")
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass


class TestTaskLedgerPhase:
    def test_update_phase(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        ledger.update_phase("TASK-001", "developer")
        record = ledger.get_task("TASK-001")
        assert record.phase == "developer"


class TestTaskLedgerRetry:
    def test_increment_retry(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        count = ledger.increment_retry("TASK-001")
        assert count == 1
        count = ledger.increment_retry("TASK-001")
        assert count == 2


class TestTaskLedgerTerminalStates:
    def test_set_complete(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        ledger.set_complete("TASK-001")
        record = ledger.get_task("TASK-001")
        assert record.phase == PHASE_COMPLETE
        assert record.terminal_state == PHASE_COMPLETE

    def test_set_blocked(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        ledger.set_blocked("TASK-001", "needs human input")
        record = ledger.get_task("TASK-001")
        assert record.phase == PHASE_BLOCKED
        assert "human" in record.terminal_reason

    def test_set_failed(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("test")
        ledger.set_failed("TASK-001", "max retries exceeded")
        record = ledger.get_task("TASK-001")
        assert record.phase == PHASE_FAILED
        assert "retries" in record.terminal_reason


class TestTaskLedgerList:
    def test_list_tasks(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        ledger.create_task("first")
        ledger.create_task("second")
        tasks = ledger.list_tasks()
        assert len(tasks) == 2
        assert tasks[0].task_id == "TASK-001"
        assert tasks[1].task_id == "TASK-002"

    def test_list_empty(self, tmp_path):
        ledger = TaskLedger(tmp_path / "tasks")
        assert ledger.list_tasks() == []
