# Orchestrator

A multi-agent system that breaks software tasks into focused roles, each doing one job well.

Instead of one AI assistant trying to do everything, Orchestrator sends your task through a disciplined loop:

```
Architect → Developer → Tester → Reviewer → Controller → Done or Rework
```

Each role receives only the context it needs, nothing more. Humans are only pulled in when real information is missing.

## Why This Exists

A single general-purpose agent tends to drift, over-reach, or lose track of what it was asked to do. Orchestrator avoids that by giving each step to a specialist:

| Role | Job |
|------|-----|
| **Architect** | Clarify what needs to happen, shape it into a scoped task |
| **Developer** | Implement exactly what was asked, nothing extra |
| **Tester** | Validate the work against acceptance criteria |
| **Reviewer** | Judge code quality and maintainability |
| **Controller** | Route to the right next step, or escalate if stuck |

The system's top priority is **code quality**. The main constraint is **bounded context** — each role gets the minimum information necessary to make a good decision.

## Supported Platforms

Orchestrator can install its workflow prompts into five AI coding platforms:

| Platform | Output Location |
|----------|----------------|
| GitHub Copilot (VS Code) | `.github/` |
| Open Code | `.opencode/` |
| Claude Code | `.claude/` |
| Qwen Code | `.qwen/` |
| GLM | `.glm/` |

## Quick Start

### Install into a target repository

```bash
# Interactive — the installer will ask you what you need
python install.py

# Non-interactive, all platforms
python install.py /path/to/target-repo

# Non-interactive, specific platforms
python install.py /path/to/target-repo -p copilot-vscode -p opencode
```

Each platform gets its own quickstart guide and a manifest of installed files.

Global install (user-level config) is available for Open Code and can be selected interactively.

### Give it a task

Once installed, invoke the workflow runner in your chosen platform and describe what you want:

```
Run this task through the bounded-context workflow.

Objective:
- what should change

Known constraints:
- any hard limits

Acceptance criteria:
- how you know it's done
```

The runner will coordinate the roles for you.

## How The Handoff Works

Roles communicate through structured task packets rather than free-form conversation. This keeps context compact and the workflow deterministic:

- **Architect** produces a task packet → **Developer** implements it
- **Developer** produces an implementation report → **Tester** validates it
- **Tester** produces a pass/fail report → **Reviewer** reviews it
- **Reviewer** approves or sends it back for rework
- **Controller** decides the next step at every junction

For the exact packet format, see [TASK_PACKET_CONTRACT.md](TASK_PACKET_CONTRACT.md).
For the routing rules, see [ROUTING_AND_ESCALATION_POLICY.md](ROUTING_AND_ESCALATION_POLICY.md).
For worked examples, see [CONTROLLER_WORKED_EXAMPLES.md](CONTROLLER_WORKED_EXAMPLES.md).

## Shared Skills

Three cross-role skills are embedded into the agents:

1. **Grill Me Relentlessly** — aggressive clarification before work begins
2. **Bounded Context Packets** — disciplined task shaping and handoff
3. **Code Quality Principles** — maintainability awareness across all roles

## Current Status

The workflow contracts, role prompts, shared skills, and multi-platform installer are all functional. The system has been validated through worked examples and automated tests.

What's still in progress:

- Live validation against real tasks in production repositories
- A broader example library across all role flows
- Mechanical enforcement of packet structure (currently prompt-based)

For technical details, see:
- [ACTIVE_DIRECTION.md](ACTIVE_DIRECTION.md) — current priorities
- [MULTI_AGENT_PROMPT_ARCHITECTURE.md](MULTI_AGENT_PROMPT_ARCHITECTURE.md) — role and skill model
- [PROMPTS_AND_INSTRUCTIONS_STATUS.md](PROMPTS_AND_INSTRUCTIONS_STATUS.md) — prompt surface status
- [DEVELOPMENT_PLAN_BoundedContextMultiAgent.prompt.md](DEVELOPMENT_PLAN_BoundedContextMultiAgent.prompt.md) — implementation roadmap
- [CHECKPOINT_2026-04-16.md](CHECKPOINT_2026-04-16.md) — latest checkpoint

## Testing

```bash
pytest tests/ -v
```

## License

Internal project
