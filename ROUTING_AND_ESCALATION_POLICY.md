# Routing And Escalation Policy

## Purpose

This document defines how work moves between Architect, Developer, Tester, Reviewer, and terminal states in the bounded-context multi-agent development system.

The goal is controlled iteration. Routing should be deterministic wherever possible so the system behaves like a disciplined workflow rather than an improvisational conversation.

## Active Role Loop

`Human -> Architect -> Developer -> Tester -> Reviewer -> Controller -> Rework or Complete`

The loop may return to earlier roles when evidence requires rework or clarification.

## Terminal States

### Complete

The task can end when:

- required behavior is implemented
- acceptance criteria are satisfied
- test evidence is adequate for the task
- review does not identify rework-worthy quality issues

### Blocked For Human

The task must return to the human when:

- requirements are genuinely missing
- an unresolved design decision materially affects correctness or acceptance
- the environment prevents required validation and no safe substitute exists

### Failed Final

This state should be rare.

Use it only when:

- the task is intentionally abandoned
- external constraints make completion impossible
- the human explicitly stops the work

## Default Routing Rules

### Human To Architect

Always route new work to Architect first unless an existing packet is already implementation-ready.

### Architect To Developer

Route to Developer when the task is actionable and the packet includes clear scope, constraints, references, and acceptance criteria.

### Architect To Human

Route to Human when the Architect cannot safely resolve missing information from repository context or explicit assumptions.

### Developer To Tester

Route to Tester when implementation is complete enough for behavioral validation.

### Developer To Architect

Route back to Architect when the task packet is missing critical information, contains contradictions, or implies a design decision that cannot be resolved safely during implementation.

### Tester To Reviewer

Route to Reviewer when the implementation passes behavioral validation strongly enough to justify structural review.

### Tester To Developer

Route to Developer when validation fails and the issue appears fixable within the existing task boundary.

### Tester To Architect

Route to Architect when the packet is too ambiguous to validate, the acceptance criteria contradict the implementation target, or the validation failure reveals a task-shaping problem rather than a coding bug.

### Reviewer To Complete

Route to Complete when the change is behaviorally acceptable and maintainable enough to merge or keep.

### Reviewer To Developer

Route to Developer when rework is needed inside the existing task boundary.

### Reviewer To Architect

Route to Architect when the review reveals that the task itself was shaped incorrectly, the scope boundary is wrong, or critical architectural context was missing.

## Deterministic Controller Guidance

The Controller should prefer deterministic routing based on the upstream report status.

The Controller should usually be invoked after Architect, Tester, and Reviewer outputs, and only when a routing decision is actually needed.

### From Tester

- `pass` -> Reviewer
- `fail` -> Developer
- `blocked` -> Architect or Human depending on blocker type

### From Reviewer

- `approve` -> Complete
- `rework` -> Developer
- `blocked` -> Architect or Human depending on blocker type

### From Architect

- `actionable` -> Developer
- `actionable_with_assumptions` -> Developer
- `blocked_for_human_input` -> Human

## Controller Output Contract

When the Controller is used, it should emit a `controller_decision_report` using the field names defined in [TASK_PACKET_CONTRACT.md](TASK_PACKET_CONTRACT.md).

The Controller should:

1. choose the narrowest correct next target
2. explain the routing decision briefly
3. distinguish between forwarding an upstream packet unchanged and synthesizing a new rework packet
4. generate a compact rework packet summary when rerouting to Developer
5. avoid broadening the task while routing

The Controller should not:

1. re-review code quality in place of Reviewer
2. re-test behavior in place of Tester
3. reshape the task in place of Architect unless the only safe move is to route back to Architect
4. ask the human new questions unless the correct target is explicitly Human

## Escalation Rules

### Escalate To Architect

Escalate to Architect when:

- the task packet is underspecified
- scope boundaries need reshaping
- acceptance criteria are missing or contradictory
- the issue is not just a local implementation defect

### Escalate To Human

Escalate to Human only when Architect cannot safely resolve the issue from repository context or clearly stated assumptions.

### Do Not Escalate Prematurely

Do not send work back to the human for ordinary implementation bugs, ordinary test failures, or maintainability defects that are already actionable within the current task boundary.

## Rework Discipline

When routing back to Developer:

1. send a rework packet, not the full history
2. include distilled evidence and the expected corrected outcome
3. preserve the original scope unless reshaped by Architect
4. avoid mixing newly discovered unrelated cleanup into the rework

## Routing Checklist

Before rerouting work, check:

1. Is the next target role the narrowest role that can act on the evidence?
2. Can the issue be fixed within the current task boundary?
3. Is this a task-shaping problem or an implementation-quality problem?
4. Does the next packet contain evidence rather than transcript history?
5. Is human escalation truly required, or has Architect not been given a chance to resolve it yet?
