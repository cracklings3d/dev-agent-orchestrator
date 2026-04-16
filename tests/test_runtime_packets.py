from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.packets import Packet, PacketParseError, parse_packet, build_rework_packet


ARCHITECT_PACKET_MD = """## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: none

## Task Summary
Add a --dry-run flag to the installer

## Required Outcome
- --dry-run prints target paths without writing files

## In Scope
- integration_layer/installer.py

## Out Of Scope
- quickstart content changes

## Acceptance Criteria
- no files created with --dry-run
- exit code is 0

## Constraints
- minimal change surface

## Required References
- integration_layer/installer.py
"""

DEVELOPER_REPORT_MD = """## Report
- packet_type: developer_implementation_report
- source_role: Developer
- target_role: Tester
- blocker_status: none

## Task Summary
Added --dry-run flag to installer

## Implementation Summary
- added dry_run parameter to install_platforms
- skip all write calls when dry_run is True

## Files Changed
- integration_layer/installer.py

## Validation Result
- local tests pass

## Known Risks
- none
"""

TESTER_PASS_MD = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Reviewer
- blocker_status: none

## Task Summary
Validate --dry-run flag

## Overall Status
- pass

## Acceptance Criteria Results
- no files created: pass
- exit code is 0: pass

## Validation Commands
- python -m pytest tests/ -v

## Failure Findings
- none
"""

TESTER_FAIL_MD = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Developer
- blocker_status: none

## Task Summary
Validate --dry-run flag

## Overall Status
- fail

## Acceptance Criteria Results
- no files created: fail

## Validation Commands
- python -m pytest tests/ -v

## Failure Findings
- manifest file still written despite --dry-run
- root cause: manifest write bypasses dry-run guard
"""

TESTER_BLOCKED_MD = """## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Architect
- blocker_status: role-blocked

## Task Summary
Validate installer behavior

## Overall Status
- blocked

## Acceptance Criteria Results
- acceptance criteria too vague to validate

## Failure Findings
- none
"""

REVIEWER_APPROVE_MD = """## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Complete
- blocker_status: none

## Task Summary
Review --dry-run implementation

## Overall Status
- approve

## Findings Ordered By Severity
- none

## Scope Drift Concerns
- none
"""

REVIEWER_REWORK_MD = """## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Developer
- blocker_status: none

## Task Summary
Review --dry-run implementation

## Overall Status
- rework

## Findings Ordered By Severity
- dry-run checks scattered across multiple functions
- should use a single write dispatcher

## Scope Drift Concerns
- none
"""

ARCHITECT_BLOCKED_MD = """## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: human-required

## Task Summary
Cannot resolve UX decision

## Required Outcome
- unclear

## In Scope
- install.py

## Out Of Scope
- everything else

## Acceptance Criteria
- needs human input on error message format

## Constraints
- blocked

## Required References
- install.py
"""


class TestParsePacket:
    def test_parse_architect_task_packet(self):
        packet = parse_packet(ARCHITECT_PACKET_MD)
        assert packet.packet_type == "architect_task_packet"
        assert packet.source_role == "Architect"
        assert packet.target_role == "Developer"
        assert packet.blocker_status == "none"
        assert "--dry-run" in packet.task_summary
        assert len(packet.in_scope) == 1
        assert len(packet.out_of_scope) == 1
        assert len(packet.acceptance_criteria) == 2
        assert len(packet.constraints) == 1
        assert len(packet.required_references) == 1

    def test_parse_developer_implementation_report(self):
        packet = parse_packet(DEVELOPER_REPORT_MD)
        assert packet.packet_type == "developer_implementation_report"
        assert packet.source_role == "Developer"
        assert packet.target_role == "Tester"
        assert len(packet.implementation_summary) == 2
        assert len(packet.files_changed) == 1
        assert len(packet.known_risks) == 1
        assert packet.validation_result

    def test_parse_tester_pass(self):
        packet = parse_packet(TESTER_PASS_MD)
        assert packet.packet_type == "tester_validation_report"
        assert packet.status == "pass"
        assert packet.target_role == "Reviewer"

    def test_parse_tester_fail(self):
        packet = parse_packet(TESTER_FAIL_MD)
        assert packet.packet_type == "tester_validation_report"
        assert packet.status == "fail"
        assert packet.target_role == "Developer"
        assert len(packet.findings) == 2

    def test_parse_tester_blocked(self):
        packet = parse_packet(TESTER_BLOCKED_MD)
        assert packet.status == "blocked"
        assert packet.blocker_status == "role-blocked"

    def test_parse_reviewer_approve(self):
        packet = parse_packet(REVIEWER_APPROVE_MD)
        assert packet.packet_type == "reviewer_review_report"
        assert packet.status == "approve"
        assert packet.target_role == "Complete"

    def test_parse_reviewer_rework(self):
        packet = parse_packet(REVIEWER_REWORK_MD)
        assert packet.status == "rework"
        assert len(packet.findings) == 2

    def test_parse_architect_blocked(self):
        packet = parse_packet(ARCHITECT_BLOCKED_MD)
        assert packet.blocker_status == "human-required"

    def test_parse_empty_raises(self):
        with pytest.raises(PacketParseError):
            parse_packet("")

    def test_parse_no_header_raises(self):
        with pytest.raises(PacketParseError):
            parse_packet("Some random text\nwithout headers")

    def test_parse_missing_packet_type_raises(self):
        with pytest.raises(PacketParseError):
            parse_packet("## Packet\n- source_role: Architect\n")

    def test_raw_preserved(self):
        packet = parse_packet(ARCHITECT_PACKET_MD)
        assert packet.raw == ARCHITECT_PACKET_MD.strip()


class TestBuildReworkPacket:
    def test_build_rework_packet_structure(self):
        packet = build_rework_packet(
            source_role="Tester",
            task_summary="Fix --dry-run bug",
            required_outcome="No files written with --dry-run",
            rework_context=("manifest still written", "root cause in install_platforms"),
            in_scope=("integration_layer/installer.py",),
            out_of_scope=("quickstart content",),
        )
        assert packet.packet_type == "rework_packet"
        assert packet.source_role == "Tester"
        assert packet.target_role == "Developer"
        assert "manifest still written" in packet.raw
        assert len(packet.rework_context) == 2
        assert len(packet.in_scope) == 1

    def test_build_rework_packet_parseable(self):
        packet = build_rework_packet(
            source_role="Reviewer",
            task_summary="Refactor dry-run",
            required_outcome="Single write dispatcher",
            rework_context=("scattered dry-run checks",),
            in_scope=("installer.py",),
            out_of_scope=(),
        )
        reparsed = parse_packet(packet.raw)
        assert reparsed.packet_type == "rework_packet"
        assert reparsed.source_role == "Reviewer"
