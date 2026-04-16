# Multi-Agent Prompt Architecture

## Purpose

This document captures the active prompt-direction architecture for the repository.

The system is not centered on one all-round agent. It is centered on specialized agents working inside an iterative loop while operating under tightly bounded context windows.

## Core Design Principle

Each agent should receive the minimum context necessary to make a high-quality decision, and no more.

This is a reliability rule, not just a prompt-style preference. Compact context reduces drift, unnecessary changes, and pseudo-helpful behavior that broadens scope.

## Target Role Model

The active direction assumes a role-separated loop:

1. Architect
2. Developer
3. Tester
4. Reviewer
5. Controller or routing policy

The Controller does not need to be a creative agent. It can remain a mostly deterministic routing and escalation policy.

The active prompt surface includes a Controller role prompt in `.github/agents/controller.agent.md`, with its decision output defined in [TASK_PACKET_CONTRACT.md](TASK_PACKET_CONTRACT.md).

Worked Controller routing cases live in [CONTROLLER_WORKED_EXAMPLES.md](CONTROLLER_WORKED_EXAMPLES.md).

## Role Intent

### Architect

- clarify vague human intent
- decide whether enough is known to proceed
- shape one or more compact task packets
- escalate only when real information is missing

### Developer

- implement one bounded task packet
- stay inside explicit scope
- avoid task expansion and opportunistic refactors

### Tester

- validate behavior and acceptance criteria
- check failure paths and incomplete test coverage
- surface concrete defects and regression risk

### Reviewer

- judge maintainability and structural quality beyond what tests catch
- detect weak code, wrong code, brittle design, and scope drift

### Controller

- route outcomes between roles
- decide rework, completion, or escalation
- keep the loop disciplined and narrow

## Shared Skill Strategy

Not all knowledge should be embedded separately inside every role prompt.

Cross-role knowledge should live in shared skills when the same discipline is needed in multiple roles.

## Active Shared Skills

### grill-me-relentlessly

Use for requirement clarification, ambiguity reduction, blocker detection, and high-signal questioning before execution begins.

Primary users:
- Architect
- any role deciding whether it has enough information to proceed safely

### bounded-context-packets

Use for designing or validating compact task packets and role handoffs.

Primary users:
- Architect
- Controller
- any role preparing a rework handoff or validating packet scope

### code-quality-principles

Use for maintainability, SOLID-informed reasoning, scope discipline, and structural quality evaluation.

Primary users:
- Developer
- Reviewer
- Tester when quality concerns overlap with behavioral validation

## Context Packet Philosophy

The system should prefer explicit packets over broad ambient context.

A packet should usually include:

- role receiving the packet
- task summary
- expected outcome
- explicit scope boundaries
- allowed references
- constraints
- acceptance criteria relevant to the role
- rework summary, if this is not the first attempt

A packet should usually exclude:

- unrelated tasks
- full backlog context
- whole-repo history by default
- entire previous transcripts
- broad architectural discussion unless required for correctness

The concrete packet fields and report templates live in [TASK_PACKET_CONTRACT.md](TASK_PACKET_CONTRACT.md).

## Workflow Shape

The intended shape is not a rigid straight line. It is a controlled loop with role-specific return paths.

A typical path looks like:

1. Human idea enters
2. Architect clarifies and shapes a task packet
3. Developer implements
4. Tester validates behavior
5. Reviewer evaluates quality
6. Controller decides:
   - complete
   - rework for Developer
   - escalate to Architect
   - escalate to Human

The concrete reroute rules live in [ROUTING_AND_ESCALATION_POLICY.md](ROUTING_AND_ESCALATION_POLICY.md).

## Current Implementation Direction

The current goal is to validate the prompt surface and shared skills before building a runtime.

The next active prompt work should validate the Controller on real packet flows, tighten packet examples, and prove that the role prompts stay aligned to the contracts under realistic iteration.

## Current Limitations And Mitigations

### Controller Still Needs Live Validation

The controller role has worked examples, but it has not yet been validated against a larger set of real packet flows and reroute cases.

Mitigation:
- run a few realistic pass, fail, blocked, and rework scenarios through the Controller

### Soft Boundary Enforcement

Bounded context is defined by prompt contract, not yet enforced by runtime or hooks.

Mitigation:
- keep packet fields explicit
- prefer allowed references and file boundaries in every real packet
- add stronger validation or hooks later if needed

### Example Library Is Still Narrow

The system has Controller examples, but not yet a broader library of realistic packets and reports across the whole role loop.

Mitigation:
- create a few worked examples that show initial shaping, failed validation, rework, and final approval

### No Persistent Loop State Yet

There is no active runtime ledger for packet state, reroute state, or retry history.

Mitigation:
- add the smallest possible persistence layer only after example-driven validation shows the contract is stable
