---
name: code-quality-principles
description: 'Apply shared code-quality standards across implementation and review. Use for SOLID thinking, cohesion and coupling checks, maintainability review, testability, complexity control, naming, scope discipline, and avoiding brittle or weak code. Useful for both Developer and Reviewer roles.'
argument-hint: 'Describe the change, code path, or review target that needs quality evaluation'
---

# Code Quality Principles

## Purpose

Use this skill to enforce a shared quality standard across implementation and review roles.

This skill should help multiple roles reason from the same principles so quality expectations do not diverge between the Developer and Reviewer.

## When To Use

Use this skill when:

- implementing a new feature or refactor
- reviewing whether a change is maintainable
- deciding between a quick fix and a cleaner design
- checking whether a passing implementation is still structurally weak
- evaluating whether a change widened scope unnecessarily

## Core Principles

1. Prefer high cohesion and low coupling.
2. Keep responsibilities clear and localized.
3. Avoid speculative abstraction.
4. Design for testability and observability.
5. Minimize the change surface needed to solve the task.
6. Preserve existing style unless there is a strong reason to improve it.
7. Reject technically passing solutions that create long-term maintenance drag.

## Practical Review Lens

Evaluate changes by asking:

- Does each changed unit have one clear responsibility?
- Did the change introduce unnecessary coupling?
- Is the abstraction level appropriate, or is it overbuilt?
- Are naming and boundaries clear?
- Is failure handling explicit enough?
- Are tests aligned with the true behavioral risks?
- Did the change solve only the assigned task, or did it drift outward?

## SOLID Guidance

Use SOLID as a heuristic, not as ceremony:

- Single Responsibility: avoid mixing unrelated concerns
- Open/Closed: extend with care, but do not over-abstract early
- Liskov Substitution: preserve behavior contracts where polymorphism matters
- Interface Segregation: prefer narrow interfaces over broad multipurpose ones
- Dependency Inversion: depend on stable abstractions when it actually reduces coupling

## Anti-Patterns

Reject or question changes that rely on:

- broad refactors unrelated to the task
- hidden side effects
- vague naming
- duplicated logic introduced for speed
- test gaps around risky paths
- architecture justifications that are not reflected in the code

## Output Expectation

When using this skill in review, produce findings that are specific, actionable, and tied to maintainability or correctness rather than general taste.
