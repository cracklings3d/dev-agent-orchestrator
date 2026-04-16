"""Deterministic routing logic for the bounded-context multi-agent workflow.

Implements the routing policy defined in ROUTING_AND_ESCALATION_POLICY.md as
pure code rather than relying on a Controller prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from .packets import Packet, build_rework_packet


TARGET_DEVELOPER = "Developer"
TARGET_TESTER = "Tester"
TARGET_REVIEWER = "Reviewer"
TARGET_ARCHITECT = "Architect"
TARGET_HUMAN = "Human"
TARGET_COMPLETE = "Complete"

ACTION_FORWARD = "forward"
ACTION_REWORK = "rework"
ACTION_RESHAPE = "reshape"
ACTION_ESCALATE = "escalate"
ACTION_COMPLETE = "complete"


@dataclass(frozen=True)
class RouteDecision:
    target: str
    action: str
    packet: Packet | None = None


class Router:
    def route(self, packet: Packet, original_packet: Packet | None = None) -> RouteDecision:
        pt = packet.packet_type
        if pt == "architect_task_packet":
            return self._from_architect(packet)
        if pt == "developer_implementation_report":
            return self._from_developer(packet)
        if pt == "tester_validation_report":
            return self._from_tester(packet, original_packet)
        if pt == "reviewer_review_report":
            return self._from_reviewer(packet, original_packet)
        if pt == "rework_packet":
            return RouteDecision(target=TARGET_DEVELOPER, action=ACTION_FORWARD, packet=packet)
        if pt == "controller_decision_report":
            return self._from_controller(packet, original_packet)
        return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE)

    def _from_architect(self, packet: Packet) -> RouteDecision:
        if packet.blocker_status == "human-required":
            return RouteDecision(target=TARGET_HUMAN, action=ACTION_ESCALATE)
        return RouteDecision(target=TARGET_DEVELOPER, action=ACTION_FORWARD, packet=packet)

    def _from_developer(self, packet: Packet) -> RouteDecision:
        if packet.blocker_status == "role-blocked":
            return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE)
        if packet.blocker_status == "human-required":
            return RouteDecision(target=TARGET_HUMAN, action=ACTION_ESCALATE)
        return RouteDecision(target=TARGET_TESTER, action=ACTION_FORWARD, packet=packet)

    def _from_tester(self, packet: Packet, original_packet: Packet | None) -> RouteDecision:
        status = packet.status
        if status == "pass":
            return RouteDecision(target=TARGET_REVIEWER, action=ACTION_FORWARD, packet=packet)
        if status == "fail":
            rework = self._build_rework_from_tester(packet, original_packet)
            return RouteDecision(target=TARGET_DEVELOPER, action=ACTION_REWORK, packet=rework)
        if status == "blocked":
            if packet.blocker_status == "human-required":
                return RouteDecision(target=TARGET_HUMAN, action=ACTION_ESCALATE)
            return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE, packet=packet)
        return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE)

    def _from_reviewer(self, packet: Packet, original_packet: Packet | None) -> RouteDecision:
        status = packet.status
        if status == "approve":
            return RouteDecision(target=TARGET_COMPLETE, action=ACTION_COMPLETE)
        if status == "rework":
            rework = self._build_rework_from_reviewer(packet, original_packet)
            return RouteDecision(target=TARGET_DEVELOPER, action=ACTION_REWORK, packet=rework)
        if status == "blocked":
            if packet.blocker_status == "human-required":
                return RouteDecision(target=TARGET_HUMAN, action=ACTION_ESCALATE)
            return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE, packet=packet)
        return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE)

    def _from_controller(self, packet: Packet, original_packet: Packet | None) -> RouteDecision:
        target = packet.target_role
        action = packet.raw.split("Packet Action")[1].split("-")[1].strip() if "Packet Action" in packet.raw else ""
        if target == TARGET_COMPLETE or "terminate_complete" in action:
            return RouteDecision(target=TARGET_COMPLETE, action=ACTION_COMPLETE)
        if target == TARGET_HUMAN or "escalate_to_human" in action:
            return RouteDecision(target=TARGET_HUMAN, action=ACTION_ESCALATE)
        if target == TARGET_DEVELOPER:
            return RouteDecision(target=TARGET_DEVELOPER, action=ACTION_REWORK)
        if target == TARGET_REVIEWER:
            return RouteDecision(target=TARGET_REVIEWER, action=ACTION_FORWARD, packet=packet)
        if target == TARGET_ARCHITECT:
            return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE, packet=packet)
        return RouteDecision(target=TARGET_ARCHITECT, action=ACTION_RESHAPE)

    def _build_rework_from_tester(self, tester: Packet, original: Packet | None) -> Packet:
        ref = original or tester
        return build_rework_packet(
            source_role="Tester",
            task_summary=ref.task_summary,
            required_outcome=ref.required_outcome,
            rework_context=tester.findings,
            in_scope=ref.in_scope,
            out_of_scope=ref.out_of_scope,
        )

    def _build_rework_from_reviewer(self, reviewer: Packet, original: Packet | None) -> Packet:
        ref = original or reviewer
        return build_rework_packet(
            source_role="Reviewer",
            task_summary=ref.task_summary,
            required_outcome=ref.required_outcome,
            rework_context=reviewer.findings,
            in_scope=ref.in_scope,
            out_of_scope=ref.out_of_scope,
        )
