"""Agent invocation interface for the runtime.

Defines the callback signature that platform-specific implementations must
provide, plus a helper for loading agent prompts from the .github/agents/ directory.
"""

from __future__ import annotations

from typing import Protocol

from .models import ModelAssignment
from .packets import Packet, PacketParseError, parse_packet


class AgentFn(Protocol):
    def __call__(
        self,
        role: str,
        context: str,
        *,
        model_assignment: ModelAssignment | None = None,
    ) -> str: ...


class AgentError(Exception):
    pass


def invoke_agent(
    fn: AgentFn,
    role: str,
    context: str,
    *,
    model_assignment: ModelAssignment | None = None,
) -> Packet:
    raw = fn(role, context, model_assignment=model_assignment)
    if not raw or not raw.strip():
        raise AgentError(f"Agent {role} returned empty output")
    return parse_packet(raw)
