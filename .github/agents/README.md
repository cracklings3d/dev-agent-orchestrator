# Active Agents

This directory contains the active role-specific agent surface for the bounded-context multi-agent system.

## Current Active Agents

### architect.agent.md

Purpose:
- clarify vague requests
- detect blockers
- shape compact task packets
- prepare bounded handoffs for downstream roles

Shared skills used:
- `grill-me-relentlessly`
- `bounded-context-packets`
- `code-quality-principles` when architectural or maintainability judgment is needed

### developer.agent.md

Purpose:
- implement compact task packets with minimal drift
- keep scope tight and change surfaces small
- validate locally when feasible before handoff

Shared skills used:
- `bounded-context-packets`
- `code-quality-principles`
- `grill-me-relentlessly` when the packet is too incomplete to execute safely

### tester.agent.md

Purpose:
- validate implemented work against acceptance criteria
- run focused behavioral checks and local test evidence
- produce pass, fail, or blocked outcomes for deterministic rerouting

Shared skills used:
- `bounded-context-packets`
- `code-quality-principles` when structural quality affects correctness or testability
- `grill-me-relentlessly` when the validation target is too ambiguous

### reviewer.agent.md

Purpose:
- assess maintainability and structural quality beyond test results
- detect weak abstractions, hidden complexity, and scope drift
- produce actionable review findings for rework when needed

Shared skills used:
- `code-quality-principles`
- `bounded-context-packets`
- `grill-me-relentlessly` when the packet is too ambiguous to review fairly

### controller.agent.md

Purpose:
- consume upstream packets or reports and choose the next role deterministically
- keep reroute packets compact when sending work back for rework
- minimize unnecessary human escalation

Shared skills used:
- `bounded-context-packets`
- `grill-me-relentlessly` when deciding whether a blocker truly requires Architect or Human

## Direction

The active role surface now covers the main bounded workflow:

1. Architect
1. Developer
2. Tester
3. Reviewer
4. Controller

Each role prompt stays compact and leans on shared skills rather than duplicating cross-role discipline inside every agent file.

The packet fields and report contracts for these roles live in [TASK_PACKET_CONTRACT.md](../../TASK_PACKET_CONTRACT.md).

The reroute rules for moving work between these roles live in [ROUTING_AND_ESCALATION_POLICY.md](../../ROUTING_AND_ESCALATION_POLICY.md).

## Supporting Agents

### copilot-workflow-runner.agent.md

Purpose:
- run one real repository task through the active role loop inside GitHub Copilot in VS Code
- delegate to Architect, Developer, Tester, Reviewer, and Controller as subagents
- keep handoffs compact while surfacing the final destination cleanly

This is a thin GitHub Copilot adapter layer, not a new domain role.
