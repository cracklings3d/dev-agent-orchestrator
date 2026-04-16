from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402

from runtime.packets import Packet
from runtime.router import (
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
    Router,
)


def _pkt(**overrides) -> Packet:
    defaults = dict(
        raw="## Packet\n- packet_type: test\n- source_role: X\n- target_role: Y\n- blocker_status: none",
        packet_type="test",
        source_role="X",
        target_role="Y",
        task_summary="test task",
        blocker_status="none",
        status="",
    )
    defaults.update(overrides)
    return Packet(**defaults)


ARCHITECT_PKT = _pkt(
    raw="## Packet\n- packet_type: architect_task_packet\n- source_role: Architect\n- target_role: Developer\n- blocker_status: none",
    packet_type="architect_task_packet",
    source_role="Architect",
    target_role="Developer",
)

ARCHITECT_BLOCKED_PKT = _pkt(
    packet_type="architect_task_packet",
    source_role="Architect",
    target_role="Developer",
    blocker_status="human-required",
)

DEVELOPER_PKT = _pkt(
    raw="## Report\n- packet_type: developer_implementation_report\n- source_role: Developer\n- target_role: Tester\n- blocker_status: none",
    packet_type="developer_implementation_report",
    source_role="Developer",
    target_role="Tester",
)

TESTER_PASS_PKT = _pkt(
    packet_type="tester_validation_report",
    source_role="Tester",
    target_role="Reviewer",
    status="pass",
)

TESTER_FAIL_PKT = _pkt(
    packet_type="tester_validation_report",
    source_role="Tester",
    target_role="Developer",
    status="fail",
    findings=("bug found", "root cause in line 42"),
)

TESTER_BLOCKED_PKT = _pkt(
    packet_type="tester_validation_report",
    source_role="Tester",
    target_role="Architect",
    status="blocked",
    blocker_status="role-blocked",
)

REVIEWER_APPROVE_PKT = _pkt(
    packet_type="reviewer_review_report",
    source_role="Reviewer",
    target_role="Complete",
    status="approve",
)

REVIEWER_REWORK_PKT = _pkt(
    packet_type="reviewer_review_report",
    source_role="Reviewer",
    target_role="Developer",
    status="rework",
    findings=("scattered dry-run checks", "use single dispatcher"),
)

REWORK_PKT = _pkt(
    packet_type="rework_packet",
    source_role="Tester",
    target_role="Developer",
    task_summary="Fix the dry-run bug",
    required_outcome="No files written",
    rework_context=("manifest still written",),
    in_scope=("installer.py",),
    out_of_scope=("quickstart",),
)

ORIGINAL_PKT = _pkt(
    packet_type="architect_task_packet",
    source_role="Architect",
    target_role="Developer",
    task_summary="Add --dry-run flag",
    required_outcome="No files written with --dry-run",
    in_scope=("installer.py",),
    out_of_scope=("quickstart",),
)


class TestRouterArchitect:
    def test_architect_actionable_routes_to_developer(self):
        d = Router().route(ARCHITECT_PKT)
        assert d.target == TARGET_DEVELOPER
        assert d.action == ACTION_FORWARD

    def test_architect_blocked_routes_to_human(self):
        d = Router().route(ARCHITECT_BLOCKED_PKT)
        assert d.target == TARGET_HUMAN
        assert d.action == ACTION_ESCALATE


class TestRouterDeveloper:
    def test_developer_routes_to_tester(self):
        d = Router().route(DEVELOPER_PKT)
        assert d.target == TARGET_TESTER
        assert d.action == ACTION_FORWARD


class TestRouterTester:
    def test_tester_pass_routes_to_reviewer(self):
        d = Router().route(TESTER_PASS_PKT, ORIGINAL_PKT)
        assert d.target == TARGET_REVIEWER
        assert d.action == ACTION_FORWARD

    def test_tester_fail_routes_to_developer_with_rework(self):
        d = Router().route(TESTER_FAIL_PKT, ORIGINAL_PKT)
        assert d.target == TARGET_DEVELOPER
        assert d.action == ACTION_REWORK
        assert d.packet is not None
        assert d.packet.packet_type == "rework_packet"
        assert d.packet.source_role == "Tester"
        assert len(d.packet.rework_context) == 2

    def test_tester_blocked_routes_to_architect(self):
        d = Router().route(TESTER_BLOCKED_PKT, ORIGINAL_PKT)
        assert d.target == TARGET_ARCHITECT
        assert d.action == ACTION_RESHAPE

    def test_tester_blocked_human_routes_to_human(self):
        pkt = _pkt(
            packet_type="tester_validation_report",
            source_role="Tester",
            target_role="Human",
            status="blocked",
            blocker_status="human-required",
        )
        d = Router().route(pkt, ORIGINAL_PKT)
        assert d.target == TARGET_HUMAN
        assert d.action == ACTION_ESCALATE


class TestRouterReviewer:
    def test_reviewer_approve_routes_to_complete(self):
        d = Router().route(REVIEWER_APPROVE_PKT, ORIGINAL_PKT)
        assert d.target == TARGET_COMPLETE
        assert d.action == ACTION_COMPLETE

    def test_reviewer_rework_routes_to_developer(self):
        d = Router().route(REVIEWER_REWORK_PKT, ORIGINAL_PKT)
        assert d.target == TARGET_DEVELOPER
        assert d.action == ACTION_REWORK
        assert d.packet is not None
        assert d.packet.packet_type == "rework_packet"
        assert d.packet.source_role == "Reviewer"
        assert len(d.packet.rework_context) == 2

    def test_reviewer_blocked_routes_to_architect(self):
        pkt = _pkt(
            packet_type="reviewer_review_report",
            source_role="Reviewer",
            target_role="Architect",
            status="blocked",
            blocker_status="role-blocked",
        )
        d = Router().route(pkt, ORIGINAL_PKT)
        assert d.target == TARGET_ARCHITECT
        assert d.action == ACTION_RESHAPE


class TestRouterRework:
    def test_rework_packet_routes_to_developer(self):
        d = Router().route(REWORK_PKT)
        assert d.target == TARGET_DEVELOPER
        assert d.action == ACTION_FORWARD

    def test_rework_preserves_context(self):
        d = Router().route(REWORK_PKT)
        assert d.packet is not None
        assert d.packet.task_summary == "Fix the dry-run bug"
        assert len(d.packet.rework_context) == 1


class TestRouterUnknown:
    def test_unknown_packet_type_routes_to_architect(self):
        pkt = _pkt(packet_type="something_unknown")
        d = Router().route(pkt)
        assert d.target == TARGET_ARCHITECT
        assert d.action == ACTION_RESHAPE
