"""Structured packet types and markdown parsing for the bounded-context multi-agent workflow.

Provides a single Packet dataclass that covers all six packet families defined in
TASK_PACKET_CONTRACT.md, plus functions for parsing agent output into structured
packets and building rework packets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class PacketParseError(Exception):
    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


def _sections(md: str) -> dict[str, str]:
    result: dict[str, str] = {}
    header = ""
    lines: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if header:
                result[header] = "\n".join(lines).strip()
            header = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    if header:
        result[header] = "\n".join(lines).strip()
    return result


def _kv(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- ") and ":" in s:
            k, v = s[2:].split(":", 1)
            result[k.strip()] = v.strip()
    return result


def _items(text: str) -> tuple[str, ...]:
    found = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- "):
            found.append(s[2:].strip())
    return tuple(found)


def _extract_status(text: str) -> str:
    items = _items(text)
    if items:
        raw = items[0].strip("<> ").lower()
        for known in ("pass", "fail", "blocked", "approve", "rework"):
            if known in raw:
                return known
    return text.strip().lower()


def _format_items(*items: str) -> str:
    if not items or all(not i for i in items):
        return "- none"
    return "\n".join(f"- {item}" for item in items if item)


@dataclass(frozen=True)
class Packet:
    raw: str
    packet_type: str
    source_role: str
    target_role: str
    task_summary: str
    blocker_status: str
    status: str = ""
    required_outcome: str = ""
    in_scope: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    rework_context: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    required_references: tuple[str, ...] = ()
    files_changed: tuple[str, ...] = ()
    implementation_summary: tuple[str, ...] = ()
    validation_result: str = ""
    known_risks: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    scope_drift_concerns: tuple[str, ...] = ()
    difficulty: int = 0


def parse_packet(markdown: str) -> Packet:
    md = markdown.strip()
    if not md:
        raise PacketParseError("Empty markdown input", md)

    secs = _sections(md)
    header_key = ""
    for key in ("Packet", "Report"):
        if key in secs:
            header_key = key
            break

    if not header_key:
        raise PacketParseError("No ## Packet or ## Report header section found", md)

    fields = _kv(secs[header_key])
    packet_type = fields.get("packet_type", "")
    if not packet_type:
        raise PacketParseError(f"Missing packet_type in {header_key} section", md)

    difficulty_raw = fields.get("difficulty", "0").strip()
    try:
        difficulty_val = int(difficulty_raw)
    except ValueError:
        difficulty_val = 0

    return Packet(
        raw=md,
        packet_type=packet_type,
        source_role=fields.get("source_role", ""),
        target_role=fields.get("target_role", ""),
        task_summary=secs.get("Task Summary", ""),
        blocker_status=fields.get("blocker_status", "none"),
        status=_extract_status(secs.get("Overall Status", "")),
        required_outcome="\n".join(_items(secs.get("Required Outcome", ""))),
        in_scope=_items(secs.get("In Scope", "")),
        out_of_scope=_items(secs.get("Out Of Scope", "")),
        rework_context=_items(secs.get("Rework Context", "")),
        acceptance_criteria=_items(secs.get("Acceptance Criteria", "")),
        constraints=_items(secs.get("Constraints", "")),
        required_references=_items(secs.get("Required References", "")),
        files_changed=_items(secs.get("Files Changed", "")),
        implementation_summary=_items(secs.get("Implementation Summary", "")),
        validation_result="\n".join(_items(secs.get("Validation Result", ""))),
        known_risks=_items(secs.get("Known Risks", "")),
        findings=_items(secs.get("Findings Ordered By Severity", secs.get("Failure Findings", ""))),
        scope_drift_concerns=_items(secs.get("Scope Drift Concerns", "")),
        difficulty=difficulty_val,
    )


def build_rework_packet(
    source_role: str,
    task_summary: str,
    required_outcome: str,
    rework_context: tuple[str, ...],
    in_scope: tuple[str, ...],
    out_of_scope: tuple[str, ...],
    required_references: tuple[str, ...] = (),
    difficulty: int = 0,
) -> Packet:
    difficulty_line = f"\n- difficulty: {difficulty}" if difficulty else ""
    md = (
        f"## Packet\n"
        f"- packet_type: rework_packet\n"
        f"- source_role: {source_role}\n"
        f"- target_role: Developer\n"
        f"- blocker_status: none{difficulty_line}\n\n"
        f"## Task Summary\n{task_summary}\n\n"
        f"## Required Outcome\n{_format_items(required_outcome)}\n\n"
        f"## Rework Context\n{_format_items(*rework_context)}\n\n"
        f"## In Scope\n{_format_items(*in_scope)}\n\n"
        f"## Out Of Scope\n{_format_items(*out_of_scope)}\n\n"
        f"## Required References\n{_format_items(*required_references)}"
    )
    return Packet(
        raw=md,
        packet_type="rework_packet",
        source_role=source_role,
        target_role="Developer",
        task_summary=task_summary,
        blocker_status="none",
        required_outcome=required_outcome,
        rework_context=rework_context,
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        difficulty=difficulty,
    )


def load_agent_prompt(role: str, repo_root: Path) -> str:
    candidates = [
        repo_root / ".github" / "agents" / f"{role}.agent.md",
        repo_root / ".github" / "agents" / f"{role.replace('_', '-')}.agent.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""
