---
name: bounded-context-packets
description: 'Design or consume compact task packets for specialized agents. Use when shaping Architect, Developer, Tester, or Reviewer handoffs, minimizing context windows, defining allowed references, limiting file scope, and preventing cross-task or whole-repo contamination.'
argument-hint: 'Describe the role and task packet you need to design or validate'
---

# Bounded Context Packets

## Purpose

Use this skill to keep each agent focused by giving it only the minimum context required to do its job well.

This skill is about context discipline, not starvation. The packet should be small enough to prevent drift and large enough to preserve correctness.

## When To Use

Use this skill when:

- an Architect is preparing a task for another role
- a Developer, Tester, or Reviewer needs a tightly scoped handoff
- the system is deciding which references to include
- you want to prevent whole-repo context leakage into a local task
- you want to validate whether a packet is too broad or too thin

## Core Principle

Each agent should receive the minimum context necessary to make a high-quality decision, and no more.

## Packet Design Rules

1. Include the task objective.
2. Include explicit scope boundaries.
3. Include the acceptance criteria relevant to the receiving role.
4. Include only the references needed for correctness.
5. Include allowed and forbidden files when file-touch boundaries matter.
6. Include failure summaries, not entire historical transcripts, on rework.
7. Exclude unrelated backlog, broad repo history, and other tasks unless they are directly relevant.

## Recommended Packet Structure

A compact packet should usually contain:

- role receiving the packet
- task summary
- required outcome
- in-scope files or components
- out-of-scope files or components
- acceptance criteria
- constraints
- required references
- current blocker or rework notes, if any

## Validation Checklist

Before passing a packet onward, check:

- Is any included context unrelated to the immediate task?
- Is any critical architectural or behavioral constraint missing?
- Would the receiving role be tempted to broaden scope?
- Is the packet specific enough to avoid guesswork?
- Is retry context summarized rather than dumped wholesale?

## Failure Modes To Avoid

- giving the whole repo by default
- hiding critical constraints in omitted references
- mixing multiple tasks into one packet
- passing complete conversations instead of distilled summaries
- letting agents pull in broad context without justification
