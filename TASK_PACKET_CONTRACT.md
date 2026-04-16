# Task Packet Contract

## Purpose

This document defines the compact handoff artifacts used by the bounded-context multi-agent development system.

The goal is not documentation for its own sake. The goal is to give each role enough context to act correctly without pulling in broad repo context, full transcripts, or adjacent tasks.

## Core Rule

Every packet must be small enough to preserve focus and complete enough to avoid guesswork.

## Packet Families

The active system uses six packet or report families:

1. Architect task packet
2. Developer implementation report
3. Tester validation report
4. Reviewer review report
5. Rework packet
6. Controller decision report

## Global Fields

These fields are shared across most packet types.

### Mandatory

- `packet_type`
- `source_role`
- `target_role`
- `task_summary`
- `required_outcome`
- `in_scope`
- `out_of_scope`
- `constraints`
- `required_references`
- `blocker_status`

### Optional

- `assumptions`
- `allowed_files`
- `forbidden_files`
- `validation_commands`
- `rework_context`
- `risks`
- `notes`

### Forbidden

- full chat transcript dumps
- unrelated backlog items
- whole-repo history by default
- vague references such as "look around the codebase"
- mixed tasks with different completion criteria

## Architect Task Packet

Use when the Architect sends implementation-ready work to the Developer.

### Required Fields

- `packet_type: architect_task_packet`
- `source_role: Architect`
- `target_role: Developer`
- `task_summary`
- `required_outcome`
- `in_scope`
- `out_of_scope`
- `acceptance_criteria`
- `constraints`
- `required_references`
- `blocker_status`

### Optional Fields

- `assumptions`
- `allowed_files`
- `forbidden_files`
- `notes`

### Template

```md
## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: none

## Task Summary
<one compact paragraph>

## Required Outcome
- <expected result>

## In Scope
- <file, component, or behavior>

## Out Of Scope
- <explicit exclusions>

## Acceptance Criteria
- <criterion>

## Constraints
- <constraint>

## Required References
- <specific file or document>

## Assumptions
- <only if needed>

## Allowed Files
- <only if file-touch boundaries matter>

## Forbidden Files
- <only if file-touch boundaries matter>

## Notes
- <only if needed>
```

## Developer Implementation Report

Use when the Developer finishes an implementation pass and hands evidence forward.

### Required Fields

- `packet_type: developer_implementation_report`
- `source_role: Developer`
- `target_role: Tester`
- `task_summary`
- `implementation_summary`
- `files_changed`
- `validation_result`
- `known_risks`
- `blocker_status`

### Optional Fields

- `design_choices`
- `validation_commands`
- `assumptions`
- `rework_context`

### Template

```md
## Report
- packet_type: developer_implementation_report
- source_role: Developer
- target_role: Tester
- blocker_status: none

## Task Summary
<what was implemented>

## Implementation Summary
- <main change>

## Files Changed
- <file>

## Important Design Choices
- <choice and rationale>

## Validation Commands
- <command>

## Validation Result
- <pass, partial, or not run with evidence>

## Known Risks
- <risk or none>

## Assumptions
- <only if needed>

## Rework Context
- <only if this was a retry>
```

## Tester Validation Report

Use when the Tester validates implemented work.

### Required Fields

- `packet_type: tester_validation_report`
- `source_role: Tester`
- `target_role`
- `task_summary`
- `overall_status`
- `acceptance_criteria_results`
- `validation_commands`
- `failure_findings`
- `blocker_status`

### Target Role Rules

- use `target_role: Reviewer` when status is `pass`
- use `target_role: Developer` when status is `fail`
- use `target_role: Architect` when status is `blocked` because the packet is insufficient or contradictory

### Template

```md
## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: <Reviewer | Developer | Architect>
- blocker_status: <none | role-blocked | human-required>

## Task Summary
<behavior that was validated>

## Overall Status
- <pass | fail | blocked>

## Acceptance Criteria Results
- <criterion>: <result>

## Validation Commands
- <command and outcome>

## Failure Findings
- <finding or none>

## Regression Concerns
- <concern or none>

## Rework Context
- <only if failing or retrying>
```

## Reviewer Review Report

Use when the Reviewer decides whether the implemented change is maintainable enough to survive.

### Required Fields

- `packet_type: reviewer_review_report`
- `source_role: Reviewer`
- `target_role`
- `task_summary`
- `overall_status`
- `findings`
- `scope_drift_concerns`
- `blocker_status`

### Target Role Rules

- use `target_role: Complete` when status is `approve`
- use `target_role: Developer` when status is `rework`
- use `target_role: Architect` when status is `blocked`

### Template

```md
## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: <Complete | Developer | Architect>
- blocker_status: <none | role-blocked | human-required>

## Task Summary
<reviewed change>

## Overall Status
- <approve | rework | blocked>

## Findings Ordered By Severity
- <finding>

## Maintainability And Structural Concerns
- <concern or none>

## Scope Drift Concerns
- <concern or none>

## Rework Context
- <only if rework is needed>
```

## Rework Packet

Use when work returns to Developer after Tester or Reviewer finds problems.

### Required Fields

- `packet_type: rework_packet`
- `source_role`
- `target_role: Developer`
- `task_summary`
- `required_outcome`
- `rework_context`
- `in_scope`
- `out_of_scope`
- `required_references`
- `blocker_status`

### Rules

- summarize findings instead of forwarding full reports plus full history
- preserve only the evidence needed to fix the issue safely
- keep the original task boundary unless the Architect explicitly reshapes the task

### Template

```md
## Packet
- packet_type: rework_packet
- source_role: <Tester | Reviewer | Architect>
- target_role: Developer
- blocker_status: none

## Task Summary
<original task plus rework focus>

## Required Outcome
- <what must now be true>

## Rework Context
- <distilled findings and evidence>

## In Scope
- <bounded rework scope>

## Out Of Scope
- <explicit exclusions>

## Required References
- <specific files or docs>
```

## Packet Validation Checklist

Before sending a packet or report onward, check:

1. Does it define one task rather than several mixed tasks?
2. Does it include the minimum references needed for correctness?
3. Does it make scope boundaries explicit?
4. Does it avoid transcript dumping?
5. Does it give the receiving role enough evidence to act without broad repo exploration?
6. Does it preserve the original task boundary unless reshaping is intentional?

## Controller Decision Report

Use when the Controller receives an upstream packet or report and determines the next role or terminal state.

### Required Fields

- `packet_type: controller_decision_report`
- `source_role: Controller`
- `upstream_source_role`
- `upstream_packet_type`
- `target_role`
- `task_summary`
- `decision`
- `decision_reason`
- `packet_action`
- `blocker_status`

### Optional Fields

- `next_packet_type`
- `next_packet_summary`
- `required_outcome`
- `in_scope`
- `out_of_scope`
- `constraints`
- `rework_context`
- `required_references`
- `notes`

### Packet Action Rules

- use `forward_existing_packet` when the upstream packet is already the correct next packet and should move forward unchanged
- use `synthesize_rework_packet` when the Controller must distill failure or review findings into a compact `rework_packet`
- use `return_for_reshaping` when the next role must be Architect because the issue is about task shape or ambiguity
- use `escalate_to_human` when the correct next destination is Human
- use `terminate_complete` when the task can end successfully

### Target Role Rules

- use `target_role: Developer` when a bounded rework packet should be sent
- use `target_role: Reviewer` when a Tester pass should advance to structural review
- use `target_role: Architect` when the issue is a shaping or ambiguity problem
- use `target_role: Human` when the task is truly blocked for human input
- use `target_role: Complete` when the task can terminate successfully

When `packet_action` is `forward_existing_packet`:

- `next_packet_type` should match the upstream packet type
- `next_packet_summary` should say that the upstream packet is being forwarded without reshaping

When `packet_action` is `synthesize_rework_packet`:

- `next_packet_type` must be `rework_packet`
- include `required_outcome`, `in_scope`, `out_of_scope`, and `rework_context`
- include only the references needed for the retry

### Template

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: <Architect | Tester | Reviewer>
- upstream_packet_type: <architect_task_packet | tester_validation_report | reviewer_review_report | blocked_for_human_input>
- target_role: <Developer | Reviewer | Architect | Human | Complete>
- blocker_status: <none | role-blocked | human-required>

## Task Summary
<the task being routed>

## Decision
- <route_to_developer | route_to_reviewer | route_to_architect | route_to_human | complete>

## Decision Reason
- <why this is the narrowest correct next step>

## Packet Action
- <forward_existing_packet | synthesize_rework_packet | return_for_reshaping | escalate_to_human | terminate_complete>

## Next Packet Type
- <architect_task_packet | rework_packet | none>

## Next Packet Summary
- <distilled next-step packet summary or none>

## Required Outcome
- <only when the next step needs a synthesized rework packet>

## In Scope
- <only when the next step needs a synthesized rework packet>

## Out Of Scope
- <only when the next step needs a synthesized rework packet>

## Constraints
- <only when the next step needs a synthesized rework packet>

## Rework Context
- <only if sending work back>

## Required References
- <only what the next role needs>

## Notes
- <only if needed>
```
