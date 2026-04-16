"""Bounded-context multi-agent runtime.

Provides the minimal execution mechanism needed to drive the
Architect -> Developer -> Tester -> Reviewer -> Complete loop
with deterministic routing and persistent task state.
"""

from .packets import Packet, PacketParseError, parse_packet, build_rework_packet, load_agent_prompt
from .router import Router, RouteDecision
from .ledger import TaskLedger, TaskRecord
from .agent import AgentFn, AgentError
from .models import (
    DifficultyLevel,
    ModelProfile,
    ModelPool,
    ModelSelector,
    ModelAssignment,
    PeakHoursConfig,
    ROLE_MODEL_WEIGHTS,
)
from .runner import WorkflowRunner, WorkflowConfig

__all__ = [
    "Packet",
    "PacketParseError",
    "parse_packet",
    "build_rework_packet",
    "load_agent_prompt",
    "Router",
    "RouteDecision",
    "TaskLedger",
    "TaskRecord",
    "AgentFn",
    "AgentError",
    "DifficultyLevel",
    "ModelProfile",
    "ModelPool",
    "ModelSelector",
    "ModelAssignment",
    "PeakHoursConfig",
    "ROLE_MODEL_WEIGHTS",
    "WorkflowRunner",
    "WorkflowConfig",
]
