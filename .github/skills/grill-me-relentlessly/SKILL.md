---
name: grill-me-relentlessly
description: 'Relentlessly clarify vague requirements before task shaping or execution. Use for ambiguous feature requests, missing constraints, blocker detection, hidden assumptions, and requirement gaps. Useful for architect-style intake, task definition, and any role deciding whether enough is known to proceed safely.'
argument-hint: 'Describe the idea, requirement, or ambiguity that needs aggressive clarification'
---

# Grill Me Relentlessly

## Purpose

Use this skill to force disciplined clarification before planning or implementation begins.

The goal is not to ask endless questions. The goal is to remove the specific ambiguities that would cause unsafe assumptions, scope drift, or low-quality execution later.

## When To Use

Use this skill when:

- the user request is vague or underspecified
- scope boundaries are unclear
- acceptance criteria are missing
- architectural consequences are unclear
- constraints may exist but are not yet explicit
- a role is deciding whether to proceed or escalate

Do not use this skill when the task is already concrete, bounded, and actionable.

## Core Principle

Proceed only when the task is clear enough to execute responsibly.

If uncertainty remains, distinguish between:

1. uncertainty that can be resolved from repo context
2. uncertainty that can be handled with explicit assumptions
3. uncertainty that requires human clarification

Only the third category is a true blocker.

## Procedure

1. Restate the task in one compact paragraph.
2. Identify what is already known.
3. Identify what is missing and why it matters.
4. Ask the smallest set of highest-signal questions.
5. Avoid speculative implementation ideas while clarifying.
6. Stop once the task is actionable; do not keep asking low-value questions.
7. Produce a compact clarification result containing:
   - clarified objective
   - scope boundaries
   - constraints
   - assumptions
   - blocker status
   - questions for the human, if blocked

## Quality Bar

A good clarification result:

- removes ambiguity that changes implementation behavior
- defines what success looks like
- narrows scope instead of widening it
- does not invent requirements
- does not start implementation prematurely

## Escalation Rule

Escalate only when missing information would materially affect correctness, architecture, user-visible behavior, or acceptance criteria.
