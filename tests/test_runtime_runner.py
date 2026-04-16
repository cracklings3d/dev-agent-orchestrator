from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402

from runtime.ledger import PHASE_BLOCKED, PHASE_COMPLETE, PHASE_FAILED, TaskLedger
from runtime.models import (
    DifficultyLevel,
    ModelPool,
    ModelProfile,
    ModelSelector,
)
from runtime.runner import WorkflowRunner, WorkflowConfig


GLM_51 = ModelProfile(name="glm-5.1", provider="zhipu", reasoning=9.5, coding=9.0, speed=3.0, cost=1.1, rate_limit_risk=1.0)
GLM_5 = ModelProfile(name="glm-5", provider="zhipu", reasoning=9.0, coding=8.5, speed=4.0, cost=2.0, rate_limit_risk=0.7)
GLM_47 = ModelProfile(name="glm-4.7", provider="zhipu", reasoning=8.0, coding=8.5, speed=5.0, cost=5.0, rate_limit_risk=0.3)
GLM_5T = ModelProfile(name="glm-5-turbo", provider="zhipu", reasoning=7.5, coding=7.0, speed=8.0, cost=6.0, rate_limit_risk=0.1)
GLM_47F = ModelProfile(name="glm-4.7-flash", provider="zhipu", reasoning=5.5, coding=5.5, speed=9.5, cost=10.0, rate_limit_risk=0.0)

TEST_POOL = ModelPool.from_profiles(
    [GLM_51, GLM_5, GLM_47, GLM_5T, GLM_47F],
    {"architect": "glm-5.1", "developer": "glm-4.7", "tester": "glm-5-turbo", "reviewer": "glm-4.7", "controller": "glm-5-turbo"},
)


ARCHITECT_OUTPUT = """## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: none

## Task Summary
Add --dry-run flag to installer

## Required Outcome
- --dry-run prints paths without writing

## In Scope
- integration_layer/installer.py

## Out Of Scope
- quickstart changes

## Acceptance Criteria
- no files created with --dry-run
- exit code 0

## Constraints
- minimal change surface

## Required References
- integration_layer/installer.py
"""

DEVELOPER_OUTPUT = """## Report
- packet_type: developer_implementation_report
- source_role: Developer
- target_role: Tester
- blocker_status: none

## Task Summary
Added --dry-run flag

## Implementation Summary
- added dry_run parameter
- skip writes when True

## Files Changed
- integration_layer/installer.py

## Validation Result
- tests pass

## Known Risks
- none
"""

TESTER_PASS_OUTPUT = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Reviewer
- blocker_status: none

## Task Summary
Validate --dry-run

## Overall Status
- pass

## Acceptance Criteria Results
- no files created: pass
- exit code 0: pass

## Failure Findings
- none
"""

TESTER_FAIL_OUTPUT = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Developer
- blocker_status: none

## Task Summary
Validate --dry-run

## Overall Status
- fail

## Failure Findings
- manifest still written
- root cause in install_platforms
"""

REVIEWER_APPROVE_OUTPUT = """## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Complete
- blocker_status: none

## Task Summary
Review --dry-run

## Overall Status
- approve

## Findings Ordered By Severity
- none

## Scope Drift Concerns
- none
"""

REVIEWER_REWORK_OUTPUT = """## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Developer
- blocker_status: none

## Task Summary
Review --dry-run

## Overall Status
- rework

## Findings Ordered By Severity
- dry-run checks scattered
- use single dispatcher

## Scope Drift Concerns
- none
"""

ARCHITECT_BLOCKED_OUTPUT = """## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: human-required

## Task Summary
Cannot resolve UX

## Required Outcome
- unclear

## In Scope
- installer

## Out Of Scope
- none

## Acceptance Criteria
- needs human input

## Constraints
- blocked

## Required References
- installer.py
"""


def _make_agent_fn(responses: dict[str, list[str]]) -> callable:
    call_log: list[tuple[str, str]] = []
    model_log: list[tuple[str, str | None]] = []

    def agent_fn(role: str, context: str, *, model_assignment=None) -> str:
        call_log.append((role, context))
        model_log.append((role, model_assignment.model if model_assignment else None))
        role_calls = [r for c, r in call_log if c == role]
        idx = len(role_calls) - 1
        available = responses.get(role, [])
        if idx < len(available):
            return available[idx]
        return available[-1] if available else ""

    agent_fn.call_log = call_log
    agent_fn.model_log = model_log
    return agent_fn


class TestRunnerHappyPath:
    def test_full_loop_completes(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger, config=WorkflowConfig(max_retries=3))
        record = runner.run("Add --dry-run flag to the installer")

        assert record.terminal_state == PHASE_COMPLETE
        assert record.packet_count == 4
        assert record.retry_count == 0

    def test_ledger_has_all_packets(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger)
        runner.run("Test task")

        packets_dir = tmp_path / "tasks" / "TASK-001" / "packets"
        files = sorted(packets_dir.iterdir())
        assert len(files) == 4
        assert "001_architect.md" in files[0].name
        assert "002_developer.md" in files[1].name
        assert "003_tester.md" in files[2].name
        assert "004_reviewer.md" in files[3].name


class TestRunnerRework:
    def test_tester_fail_triggers_rework_then_success(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT, DEVELOPER_OUTPUT],
            "tester": [TESTER_FAIL_OUTPUT, TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger, config=WorkflowConfig(max_retries=3))
        record = runner.run("Test rework loop")

        assert record.terminal_state == PHASE_COMPLETE
        assert record.retry_count == 1
        assert record.packet_count == 7

    def test_reviewer_rework_triggers_rework_then_success(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT, DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT, TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_REWORK_OUTPUT, REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger, config=WorkflowConfig(max_retries=3))
        record = runner.run("Test rework loop")

        assert record.terminal_state == PHASE_COMPLETE
        assert record.retry_count == 1

    def test_max_retries_exceeded(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT] * 5,
            "tester": [TESTER_FAIL_OUTPUT] * 5,
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger, config=WorkflowConfig(max_retries=2))
        record = runner.run("Test max retries")

        assert record.terminal_state == PHASE_FAILED
        assert "retries" in record.terminal_reason.lower()


class TestRunnerBlocked:
    def test_architect_blocked_escalates_to_human(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_BLOCKED_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger)
        record = runner.run("Ambiguous task")

        assert record.terminal_state == PHASE_BLOCKED
        assert "human" in record.terminal_reason.lower()

    def test_tester_blocked_routes_to_architect(self, tmp_path):
        blocked_tester = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Architect
- blocker_status: role-blocked

## Task Summary
Cannot validate

## Overall Status
- blocked

## Failure Findings
- acceptance criteria too vague
"""
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT, ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT, DEVELOPER_OUTPUT],
            "tester": [blocked_tester, TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger, config=WorkflowConfig(max_retries=3))
        record = runner.run("Test blocked")

        assert record.terminal_state == PHASE_COMPLETE


class TestRunnerAgentError:
    def test_empty_agent_output_fails_task(self, tmp_path):
        def agent_fn(role, context, *, model_assignment=None):
            return ""

        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger)
        record = runner.run("Test empty output")

        assert record.terminal_state == PHASE_FAILED

    def test_unparseable_output_fails_task(self, tmp_path):
        def agent_fn(role, context, *, model_assignment=None):
            return "This is not a valid packet at all\nno headers no nothing"

        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger)
        record = runner.run("Test unparseable")

        assert record.terminal_state == PHASE_FAILED


class TestRunnerModelSelection:
    def test_model_selector_assigns_models(self, tmp_path):
        selector = ModelSelector(TEST_POOL)
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        config = WorkflowConfig(model_selector=selector, initial_difficulty=DifficultyLevel.COMPLEX)
        runner = WorkflowRunner(agent_fn, ledger, config=config)
        record = runner.run("Test model selection")

        assert record.terminal_state == PHASE_COMPLETE
        assert len(agent_fn.model_log) == 4
        assert agent_fn.model_log[0] == ("architect", "glm-5.1")
        assert agent_fn.model_log[1] == ("developer", "glm-4.7")

    def test_no_model_selector_passes_none(self, tmp_path):
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        runner = WorkflowRunner(agent_fn, ledger)
        runner.run("No model selector")

        for role, model in agent_fn.model_log:
            assert model is None

    def test_retry_escalates_model(self, tmp_path):
        selector = ModelSelector(TEST_POOL)
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT, DEVELOPER_OUTPUT],
            "tester": [TESTER_FAIL_OUTPUT, TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        config = WorkflowConfig(model_selector=selector, initial_difficulty=DifficultyLevel.SIMPLE, max_retries=3)
        runner = WorkflowRunner(agent_fn, ledger, config=config)
        record = runner.run("Test model escalation")

        assert record.terminal_state == PHASE_COMPLETE
        assert record.retry_count == 1
        first_dev_model = agent_fn.model_log[1][1]
        retry_dev_model = agent_fn.model_log[4][1]
        assert retry_dev_model is not None
        assert first_dev_model is not None

    def test_difficulty_persisted_in_ledger(self, tmp_path):
        selector = ModelSelector(TEST_POOL)
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        config = WorkflowConfig(model_selector=selector, initial_difficulty=DifficultyLevel.COMPLEX)
        runner = WorkflowRunner(agent_fn, ledger, config=config)
        record = runner.run("Test difficulty persist")

        assert record.difficulty == 4

    def test_packet_difficulty_overrides_initial(self, tmp_path):
        architect_diff4 = ARCHITECT_OUTPUT.replace("- blocker_status: none", "- blocker_status: none\n- difficulty: 5")
        selector = ModelSelector(TEST_POOL)
        agent_fn = _make_agent_fn({
            "architect": [architect_diff4],
            "developer": [DEVELOPER_OUTPUT],
            "tester": [TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        config = WorkflowConfig(model_selector=selector, initial_difficulty=DifficultyLevel.SIMPLE)
        runner = WorkflowRunner(agent_fn, ledger, config=config)
        record = runner.run("Test packet difficulty override")

        assert record.difficulty == 5

    def test_reshape_uses_complex_model(self, tmp_path):
        blocked_tester = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Architect
- blocker_status: role-blocked

## Task Summary
Cannot validate

## Overall Status
- blocked

## Failure Findings
- criteria too vague
"""
        selector = ModelSelector(TEST_POOL)
        agent_fn = _make_agent_fn({
            "architect": [ARCHITECT_OUTPUT, ARCHITECT_OUTPUT],
            "developer": [DEVELOPER_OUTPUT, DEVELOPER_OUTPUT],
            "tester": [blocked_tester, TESTER_PASS_OUTPUT],
            "reviewer": [REVIEWER_APPROVE_OUTPUT],
        })
        ledger = TaskLedger(tmp_path / "tasks")
        config = WorkflowConfig(model_selector=selector, initial_difficulty=DifficultyLevel.MODERATE)
        runner = WorkflowRunner(agent_fn, ledger, config=config)
        record = runner.run("Test reshape model")

        assert record.terminal_state == PHASE_COMPLETE
        reshape_model = agent_fn.model_log[3][1]
        assert reshape_model is not None
