"""Main workflow runner that drives the bounded-context multi-agent loop.

Orchestrates Architect -> Developer -> Tester -> Reviewer -> Complete using
a deterministic Router and a caller-provided agent function.

When a ModelSelector is configured, the runner selects the most appropriate
model for each role based on task difficulty. On retry, difficulty bumps up,
causing the system to escalate to a stronger model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent import AgentFn, AgentError, invoke_agent
from .ledger import (
    PHASE_ARCHITECT,
    PHASE_BLOCKED,
    PHASE_COMPLETE,
    PHASE_DEVELOPER,
    PHASE_FAILED,
    PHASE_REVIEWER,
    PHASE_TESTER,
    TaskLedger,
    TaskRecord,
)
from .models import (
    DifficultyLevel,
    ModelAssignment,
    ModelSelector,
)
from .packets import Packet, PacketParseError
from .router import (
    ACTION_COMPLETE,
    ACTION_ESCALATE,
    ACTION_FORWARD,
    ACTION_RESHAPE,
    ACTION_REWORK,
    TARGET_ARCHITECT,
    TARGET_COMPLETE,
    TARGET_DEVELOPER,
    TARGET_HUMAN,
    TARGET_REVIEWER,
    TARGET_TESTER,
    RouteDecision,
    Router,
)


ROLE_ARCHITECT = "architect"
ROLE_DEVELOPER = "developer"
ROLE_TESTER = "tester"
ROLE_REVIEWER = "reviewer"

PHASE_ROLE_MAP = {
    PHASE_ARCHITECT: ROLE_ARCHITECT,
    PHASE_DEVELOPER: ROLE_DEVELOPER,
    PHASE_TESTER: ROLE_TESTER,
    PHASE_REVIEWER: ROLE_REVIEWER,
}

TARGET_ROLE_MAP = {
    TARGET_DEVELOPER: ROLE_DEVELOPER,
    TARGET_TESTER: ROLE_TESTER,
    TARGET_REVIEWER: ROLE_REVIEWER,
    TARGET_ARCHITECT: ROLE_ARCHITECT,
}


@dataclass
class WorkflowConfig:
    max_retries: int = 3
    agent_prompts_dir: Path | None = None
    model_selector: ModelSelector | None = None
    initial_difficulty: DifficultyLevel = DifficultyLevel.MODERATE


class WorkflowRunner:
    def __init__(
        self,
        agent_fn: AgentFn,
        ledger: TaskLedger,
        router: Router | None = None,
        config: WorkflowConfig | None = None,
    ):
        self._agent_fn = agent_fn
        self._ledger = ledger
        self._router = router or Router()
        self._config = config or WorkflowConfig()

    @property
    def ledger(self) -> TaskLedger:
        return self._ledger

    def _refresh(self, record: TaskRecord) -> TaskRecord:
        updated = self._ledger.get_task(record.task_id)
        return updated if updated is not None else record

    def _resolve_difficulty(self, packet: Packet, record: TaskRecord) -> DifficultyLevel:
        if packet.difficulty in (1, 2, 3, 4, 5):
            return DifficultyLevel(packet.difficulty)
        if record.packet_count > 0 and record.difficulty in (1, 2, 3, 4, 5):
            return DifficultyLevel(record.difficulty)
        return self._config.initial_difficulty

    def _select_model(self, role: str, difficulty: DifficultyLevel) -> ModelAssignment | None:
        selector = self._config.model_selector
        if selector is None:
            return None
        profile = selector.select(role, difficulty)
        return ModelAssignment.from_profile(profile)

    def run(self, task_description: str, task_id: str | None = None) -> TaskRecord:
        record = self._ledger.create_task(task_description, task_id)
        original_packet: Packet | None = None

        try:
            original_packet = self._run_architect(record, task_description)
            if original_packet is None:
                return self._refresh(record)

            packet_difficulty = self._resolve_difficulty(original_packet, record)
            self._ledger.update_difficulty(record.task_id, int(packet_difficulty))

            retries = 0
            current_packet = original_packet
            current_difficulty = packet_difficulty

            while retries <= self._config.max_retries:
                dev_report = self._run_developer(record, current_packet, current_difficulty)
                if dev_report is None:
                    return self._refresh(record)

                tester_report = self._run_tester(record, dev_report, current_difficulty)
                if tester_report is None:
                    return self._refresh(record)

                tester_decision = self._router.route(tester_report, original_packet)

                if tester_decision.action == ACTION_FORWARD and tester_decision.target == TARGET_REVIEWER:
                    reviewer_report = self._run_reviewer(record, dev_report, tester_report, current_difficulty)
                    if reviewer_report is None:
                        return self._refresh(record)

                    reviewer_decision = self._router.route(reviewer_report, original_packet)

                    if reviewer_decision.action == ACTION_COMPLETE:
                        self._ledger.set_complete(record.task_id)
                        return self._refresh(record)

                    if reviewer_decision.action == ACTION_REWORK:
                        retries += 1
                        if retries > self._config.max_retries:
                            self._ledger.set_failed(record.task_id, "Max retries exceeded after reviewer rework")
                            return self._refresh(record)
                        self._ledger.increment_retry(record.task_id)
                        current_difficulty = self._bump_difficulty(current_difficulty)
                        self._ledger.update_difficulty(record.task_id, int(current_difficulty))
                        rework = reviewer_decision.packet or self._router._build_rework_from_reviewer(reviewer_report, original_packet)
                        self._ledger.add_packet(record.task_id, rework.raw, "rework")
                        current_packet = rework
                        continue

                    if reviewer_decision.action == ACTION_RESHAPE:
                        reshape_result = self._run_reshape(record, reviewer_decision, original_packet)
                        if reshape_result is None:
                            return self._refresh(record)
                        original_packet = reshape_result
                        current_packet = original_packet
                        continue

                    if reviewer_decision.action == ACTION_ESCALATE:
                        self._ledger.set_blocked(record.task_id, "Reviewer escalation requires human input")
                        return self._refresh(record)

                elif tester_decision.action == ACTION_REWORK:
                    retries += 1
                    if retries > self._config.max_retries:
                        self._ledger.set_failed(record.task_id, "Max retries exceeded after tester failure")
                        return self._refresh(record)
                    self._ledger.increment_retry(record.task_id)
                    current_difficulty = self._bump_difficulty(current_difficulty)
                    self._ledger.update_difficulty(record.task_id, int(current_difficulty))
                    rework = tester_decision.packet or self._router._build_rework_from_tester(tester_report, original_packet)
                    self._ledger.add_packet(record.task_id, rework.raw, "rework")
                    current_packet = rework
                    continue

                elif tester_decision.action == ACTION_RESHAPE:
                    reshape_result = self._run_reshape(record, tester_decision, original_packet)
                    if reshape_result is None:
                        return self._refresh(record)
                    original_packet = reshape_result
                    current_packet = original_packet
                    continue

                elif tester_decision.action == ACTION_ESCALATE:
                    self._ledger.set_blocked(record.task_id, "Tester escalation requires human input")
                    return self._refresh(record)

            self._ledger.set_failed(record.task_id, "Max retries exceeded")
            return self._refresh(record)

        except AgentError as e:
            self._ledger.set_failed(record.task_id, f"Agent error: {e}")
            return self._ledger.get_task(record.task_id) or record

    def _bump_difficulty(self, current: DifficultyLevel) -> DifficultyLevel:
        bumped = min(int(current) + 1, DifficultyLevel.CRITICAL)
        return DifficultyLevel(bumped)

    def _run_architect(self, record: TaskRecord, description: str) -> Packet | None:
        self._ledger.update_phase(record.task_id, PHASE_ARCHITECT)
        context = f"Shape this into one compact architect_task_packet for Developer.\n\nObjective:\n{description}"
        difficulty = self._config.initial_difficulty
        model = self._select_model(ROLE_ARCHITECT, difficulty)
        packet = self._invoke(ROLE_ARCHITECT, context, record, "architect", model)

        if packet.blocker_status == "human-required":
            self._ledger.set_blocked(record.task_id, "Architect requires human input")
            return None

        return packet

    def _run_developer(self, record: TaskRecord, task_packet: Packet, difficulty: DifficultyLevel) -> Packet | None:
        self._ledger.update_phase(record.task_id, PHASE_DEVELOPER)
        context = task_packet.raw
        model = self._select_model(ROLE_DEVELOPER, difficulty)
        return self._invoke(ROLE_DEVELOPER, context, record, "developer", model)

    def _run_tester(self, record: TaskRecord, dev_report: Packet, difficulty: DifficultyLevel) -> Packet | None:
        self._ledger.update_phase(record.task_id, PHASE_TESTER)
        context = dev_report.raw
        model = self._select_model(ROLE_TESTER, difficulty)
        return self._invoke(ROLE_TESTER, context, record, "tester", model)

    def _run_reviewer(self, record: TaskRecord, dev_report: Packet, tester_report: Packet, difficulty: DifficultyLevel) -> Packet | None:
        self._ledger.update_phase(record.task_id, PHASE_REVIEWER)
        context = f"{dev_report.raw}\n\n---\n\nTester validation result:\n\n{tester_report.raw}"
        model = self._select_model(ROLE_REVIEWER, difficulty)
        return self._invoke(ROLE_REVIEWER, context, record, "reviewer", model)

    def _run_reshape(self, record: TaskRecord, decision: RouteDecision, original: Packet) -> Packet | None:
        self._ledger.update_phase(record.task_id, PHASE_ARCHITECT)
        context = f"Reshape this task based on downstream feedback.\n\nOriginal task:\n{original.raw}\n\nReshaping trigger:\n{decision.packet.raw if decision.packet else 'No upstream packet provided'}"
        model = self._select_model(ROLE_ARCHITECT, DifficultyLevel.COMPLEX)
        return self._invoke(ROLE_ARCHITECT, context, record, "architect_reshape", model)

    def _invoke(
        self,
        role: str,
        context: str,
        record: TaskRecord,
        label: str,
        model: ModelAssignment | None = None,
    ) -> Packet:
        try:
            packet = invoke_agent(self._agent_fn, role, context, model_assignment=model)
        except PacketParseError as e:
            self._ledger.add_packet(record.task_id, e.raw or context, f"{label}_unparseable")
            raise AgentError(f"Could not parse {role} output: {e}") from e
        except Exception as e:
            raise AgentError(f"{role} invocation failed: {e}") from e

        self._ledger.add_packet(record.task_id, packet.raw, label)
        return packet
