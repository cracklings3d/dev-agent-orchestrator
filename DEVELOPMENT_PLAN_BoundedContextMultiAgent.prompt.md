## Plan: Bounded-Context Multi-Agent Development System

## Big Picture

The active goal is a bounded-context multi-agent development system in which specialized roles collaborate on one iterative job:

`Architect -> Developer -> Tester -> Reviewer -> Rework or Complete`

The core design constraint is compact context per role. Each agent should receive the minimum context necessary to make a high-quality decision, and no more.

The implementation strategy follows that goal directly:

1. Rebuild the active prompt surface around specialized agents rather than one all-round agent.
2. Use shared skills for cross-role disciplines that should not be duplicated in every prompt.
3. Define task packets and reroute rules before building any serious runtime around them.
4. Prove quality and focus at small scale before revisiting parallel execution.

## Guiding Principles

1. Code quality is the primary product requirement because maintainability is the long-term constraint.
2. Bounded context is a first-class reliability mechanism, not just a prompt preference.
3. Shared skills should hold reusable cross-role knowledge when the same discipline is needed in multiple roles.
4. Human checkpoints happen only when requirements are missing or a design decision cannot be resolved from repo context.
5. The controller should remain as deterministic as practical; not every routing decision needs another creative agent.
6. Parallelism remains out of scope until the bounded-context multi-agent loop is reliable.

## Implementation Phases

### Phase 1: Shared Prompt Foundation

**Goal**

Define the reusable prompt-layer disciplines that should be shared across roles instead of duplicated inside every agent definition.

**Why this phase matters**

Prompt systems become brittle when the same critical behavior is copied into multiple roles and drifts over time.

**Work included**

1. Define which knowledge belongs in shared skills versus role prompts.
2. Establish the first shared skills for clarification rigor, bounded task packets, and code-quality discipline.
3. Define the minimum quality standard for any future shared skill: clear purpose, clear triggers, concrete procedure, and role applicability.
4. Decide which additional cross-role capabilities may deserve shared skills later.

**Outcome**

The system has a reusable behavioral foundation that multiple roles can rely on without duplicating the same prompt logic.

### Phase 2: Agent Roster and Responsibility Boundaries

**Goal**

Define the exact responsibilities, boundaries, and stop conditions for each active role.

**Why this phase matters**

If Architect, Developer, Tester, and Reviewer blur together, compact context stops helping because each role starts freelancing outside its lane.

**Work included**

1. Define the Architect role as clarification, scoping, packet shaping, and escalation for missing information.
2. Define the Developer role as bounded implementation inside explicit scope.
3. Define the Tester role as behavioral validation, acceptance checking, and failure detection.
4. Define the Reviewer role as maintainability and structural quality judgment beyond test pass status.
5. Define the Controller as routing and escalation policy rather than a generalist creative role.
6. Define what each role must never do.

**Outcome**

The system has crisp role separation, which is the prerequisite for compact context to work.

### Phase 3: Context Packets and Handoff Artifacts

**Goal**

Make bounded context concrete by defining the task packets and reports that move between roles.

**Why this phase matters**

Role separation is not enough by itself. The system also needs disciplined artifacts so agents do not compensate for vague handoffs by pulling in the whole repo.

**Work included**

1. Define the Architect output packet.
2. Define the Developer implementation output or implementation note format.
3. Define the Tester report format.
4. Define the Reviewer report format.
5. Define the rework packet format so retries carry distilled findings instead of whole transcripts.
6. Define what packet fields are mandatory, optional, and forbidden.

**Outcome**

Every agent handoff can be compact, explicit, and auditable.

### Phase 4: Reroute and Escalation Policy

**Goal**

Specify how the system decides what happens after each role completes its work.

**Why this phase matters**

Without clear reroute rules, the workflow will either become too rigid or devolve into arbitrary bouncing between roles.

**Work included**

1. Define when work returns from Tester to Developer.
2. Define when work returns from Reviewer to Developer.
3. Define when work escalates from Developer, Tester, or Reviewer back to Architect.
4. Define when Architect must ask the human for clarification.
5. Define terminal states such as complete, blocked-for-human, and failed-final.
6. Decide which routing decisions are deterministic and which, if any, require interpretation.

**Outcome**

The multi-agent loop behaves like a controlled system rather than a linear pipeline or a free-form conversation.

### Phase 5: Active Role Prompt Surface

**Goal**

Write the active role prompts or prompt-adjacent assets for Architect, Developer, Tester, and Reviewer around the agreed boundaries and shared skills.

**Why this phase matters**

The shared skills are only the foundation. The actual system still needs role-specific prompts with clear job boundaries.

**Work included**

1. Write the Architect prompt around clarification, packet shaping, and escalation.
2. Write the Developer prompt around bounded execution and scope discipline.
3. Write the Tester prompt around behavioral validation and failure discovery.
4. Write the Reviewer prompt around maintainability and structural quality.
5. Explicitly reference shared skills where cross-role knowledge should be reused.
6. Keep each role prompt compact enough to preserve focus.

**Outcome**

The active prompt surface exists and reflects the multi-agent architecture.

### Phase 6: Execution Policy and Quality Gates

**Goal**

Make testing, review, retry, and escalation part of the system contract rather than relying on prompt goodwill.

**Why this phase matters**

This is where the system becomes trustworthy. Passing code is not enough if it is brittle, weak, or outside scope.

**Work included**

1. Make automated tests mandatory whenever local validation is feasible.
2. Require Tester findings to be explicit and actionable.
3. Require Reviewer findings to focus on maintainability, weak abstractions, scope drift, and structural correctness.
4. Make rework packets compact and evidence-based.
5. Define how much retry context is preserved and how much is intentionally discarded.
6. Define when a task is complete despite imperfections, and when it must continue iterating.

**Outcome**

The system has real quality gates instead of vague role descriptions.

### Phase 7: Multi-Platform Integration Layer

**Goal**

Render the active workflow surface into platform-specific bundles so live task tests can begin before a deeper runtime exists.

**Why this phase matters**

The prompt architecture needs to work across multiple AI coding platforms, not just one.

**Work included**

1. Build a deterministic installer that renders agents and skills for Copilot, Qwen Code, Claude Code, and GLM.
2. Generate per-platform quickstarts.
3. Produce a shared install manifest.
4. Test the installer end-to-end with scratch installs.

**Outcome**

The active workflow can be installed into any target repository for live testing on all four platforms.

### Phase 8: Integrate the Prompt Model Into a Minimal Runtime

**Goal**

Only after the prompt architecture is stable, define the smallest execution mechanism needed to run the multi-agent loop repeatedly and safely.

**Why this phase matters**

The runtime should follow the prompt architecture, not force it. Building the controller too early risks locking in the wrong abstractions.

**Work included**

1. Decide what the minimal controller must do.
2. Define packet persistence and rework persistence requirements.
3. Decide what should be code, what should remain prompt policy, and what should be a shared skill.
4. Add only the smallest runtime needed to exercise the prompt contracts.

**Outcome**

The runtime becomes an implementation of the prompt architecture rather than a substitute for it.

### Phase 9: Validate the System Before Expanding Scope

**Goal**

Prove that the bounded-context multi-agent system works on real tasks and resists drift before any future parallelism discussion resumes.

**Why this phase matters**

If the system is not reliable with compact role packets at small scale, adding more concurrency would only amplify the problem.

**Work included**

1. Validate that Architect packets are clear enough for implementation without broad repo leakage.
2. Validate that Developer stays focused under compact context.
3. Validate that Tester catches failure cases and incomplete behavior.
4. Validate that Reviewer catches weak code that tests may miss.
5. Validate reroute and escalation behavior on ambiguous or partially specified tasks.
6. Defer any return to orchestration work until these checks pass convincingly.

**Outcome**

The project has evidence, not just optimism, that the new prompt architecture is viable.

## Relevant Files by Role

### Active Direction And Planning

- `ACTIVE_DIRECTION.md` — concise statement of the current product direction.
- `README.md` — repository entrypoint for the active direction.
- `PROMPTS_AND_INSTRUCTIONS_STATUS.md` — current prompt-surface status.
- `MULTI_AGENT_PROMPT_ARCHITECTURE.md` — role model, shared skill strategy, and packet philosophy.

### Active Shared Skills

- `.github/skills/grill-me-relentlessly/SKILL.md` — clarification rigor and blocker detection.
- `.github/skills/bounded-context-packets/SKILL.md` — compact packet design and handoff discipline.
- `.github/skills/code-quality-principles/SKILL.md` — shared maintainability and structural quality standards.

### Active Role Agents

- `.github/agents/architect.agent.md`
- `.github/agents/developer.agent.md`
- `.github/agents/tester.agent.md`
- `.github/agents/reviewer.agent.md`
- `.github/agents/controller.agent.md`
- `.github/agents/copilot-workflow-runner.agent.md`

### Active Contracts And Reference Docs

- `TASK_PACKET_CONTRACT.md` — packet and report type definitions.
- `ROUTING_AND_ESCALATION_POLICY.md` — reroute and escalation rules.
- `CONTROLLER_WORKED_EXAMPLES.md` — worked Controller routing cases.

### Active Integration Layer

- `integration_layer/installer.py` — multi-platform asset renderer and installer.
- `install.py` — interactive and CLI entry point.

## Verification Strategy

1. Verify that active docs consistently describe the multi-agent bounded-context model.
2. Verify that shared skills are reusable across roles and not role-locked by wording.
3. Verify that future role prompts can stay compact because shared skills already carry common discipline.
4. Validate the architecture on a few small, ambiguous tasks and inspect whether agents drift outside their packet boundaries.

## Decisions

- Included scope: bounded-context multi-agent development, shared prompt skills, explicit role boundaries, reroute policy, and multi-platform integration.
- Excluded scope: parallel execution, premature runtime elaboration before prompt architecture stabilizes.
- Confirmed user choices: keep each agent context as compact as possible; use specialized agents rather than one all-round agent; allow shared skills to carry cross-role knowledge.
- Recommended default: stabilize the prompt architecture, shared skills, packet formats, and routing policy before building significant runtime machinery around them.

## Further Considerations

1. Task packet granularity: smaller packets reduce drift, but packets that are too thin can starve agents of correctness-critical context.
2. Reviewer placement: Reviewer should remain distinct from Tester so code quality is not reduced to test pass status.
3. Controller implementation: the controller may later be code, prompt policy, or a hybrid, but its routing rules should be defined before its implementation form is chosen.
4. Shared-skill growth: add new shared skills only when the same knowledge genuinely belongs to multiple roles.
