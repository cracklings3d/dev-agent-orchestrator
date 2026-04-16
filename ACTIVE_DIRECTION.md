# Active Direction

## Current Product Goal

The active goal of this repository is to build a bounded-context multi-agent development system with the following execution shape:

`Architect -> Developer -> Tester -> Reviewer -> Rework or Complete`

The primary success criterion is code quality, with maintainability treated as the main long-term constraint and compact context windows treated as a first-class reliability mechanism.

## What Is In Scope

- Multi-agent iterative development
- Compact task-local context packets per role
- Strong automated test gates
- Structured review gates
- Safe retry, rollback, and resume behavior
- Human escalation only when requirements are missing or a design decision cannot be resolved from repository context
- Shared skills for cross-role knowledge that should not be duplicated inside every agent prompt
- Multi-platform integration layer for Copilot, Qwen Code, Claude Code, and GLM

## What Is Out Of Scope For Now

- Parallel task execution
- Broad shared context across all agents by default

## Immediate Focus

1. Validate the Controller on real packet flows and reroute cases.
2. Tighten packet examples and prove that role prompts stay aligned to the contracts under realistic iteration.
3. Create a few worked examples that show initial shaping, failed validation, rework, and final approval.
4. Add the smallest possible persistence layer only after example-driven validation shows the contract is stable.
