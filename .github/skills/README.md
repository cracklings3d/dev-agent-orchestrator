# Active Shared Skills

This directory contains the active shared skill layer for the bounded-context multi-agent system.

## Why These Skills Matter

Skills are reusable prompt building blocks. They should carry cross-role discipline that multiple agents need, so that the same guidance does not have to be duplicated inside every agent prompt.

This keeps agent prompts:

- shorter
- more focused
- easier to update
- more consistent across roles

## Current Active Skills

### grill-me-relentlessly

Purpose:
- rigorous clarification
- blocker detection
- ambiguity reduction

Primary users:
- Architect
- any role deciding whether enough is known to proceed safely

### bounded-context-packets

Purpose:
- compact task-packet design
- handoff discipline
- context-window control

Primary users:
- Architect
- Controller
- any role preparing rework or validating packet scope

### code-quality-principles

Purpose:
- shared maintainability standards
- SOLID-informed reasoning
- scope discipline and structural quality

Primary users:
- Developer
- Reviewer
- Tester when quality concerns overlap with validation

## Design Rule

A concept should become a shared skill only when it genuinely belongs to multiple roles.

If a behavior is role-specific, it should live in the role prompt instead.

## Relationship To Other Folders

- `.github/skills/` is the active shared skill surface.
- `archive/langgraph-orchestration/skills/` holds the paused orchestrator-era skills.
- `skills/README.md` is a status pointer for the legacy root folder, not the active skills home.
