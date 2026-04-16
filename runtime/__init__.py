# ruff: noqa: I001
"""Bounded-context multi-agent runtime.

Provides the minimal execution mechanism needed to drive the
Architect -> Developer -> Tester -> Reviewer -> Complete loop
with deterministic routing and persistent task state.
"""

from .agent import AgentError, AgentFn
from .ledger import TaskLedger, TaskRecord
from .models import (
    DifficultyLevel,
    ModelAssignment,
    ModelPool,
    ModelProfile,
    ModelSelector,
    PeakHoursConfig,
    ROLE_MODEL_WEIGHTS,
)
from .packets import Packet, PacketParseError, build_rework_packet, load_agent_prompt, parse_packet
from .router import RouteDecision, Router
from .runner import WorkflowConfig, WorkflowRunner

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
