# Prompts And Instructions Status

## Active Direction

This repository is oriented around a bounded-context multi-agent development system:

`Architect -> Developer -> Tester -> Reviewer -> Controller -> Rework or Complete`

## Active Planning Surface

The current active project-definition documents are:

- [ACTIVE_DIRECTION.md](ACTIVE_DIRECTION.md)
- [DEVELOPMENT_PLAN_BoundedContextMultiAgent.prompt.md](DEVELOPMENT_PLAN_BoundedContextMultiAgent.prompt.md)
- [MULTI_AGENT_PROMPT_ARCHITECTURE.md](MULTI_AGENT_PROMPT_ARCHITECTURE.md)
- [TASK_PACKET_CONTRACT.md](TASK_PACKET_CONTRACT.md)
- [ROUTING_AND_ESCALATION_POLICY.md](ROUTING_AND_ESCALATION_POLICY.md)
- [CONTROLLER_WORKED_EXAMPLES.md](CONTROLLER_WORKED_EXAMPLES.md)

These define the product direction, packet contract, routing policy, worked Controller examples, and implementation roadmap.

## Active Shared Skills

The active shared skills live under `.github/skills/`:

1. `grill-me-relentlessly`
2. `bounded-context-packets`
3. `code-quality-principles`

These support multiple roles rather than being duplicated inside each role prompt.

See [.github/skills/README.md](.github/skills/README.md) for the active shared-skill index.

## Active Role Surface

The active role-specific agents live under `.github/agents/`:

1. `architect.agent.md`
2. `developer.agent.md`
3. `tester.agent.md`
4. `reviewer.agent.md`
5. `controller.agent.md`

See [.github/agents/README.md](.github/agents/README.md) for the active role-agent index.

## Active Platform Integration Layer

The repository includes a multi-platform integration layer:

1. `.github/agents/copilot-workflow-runner.agent.md`
2. `integration_layer/installer.py`
3. `install.py` (interactive + CLI entry point)

This layer renders the active workflow surface into GitHub Copilot, Qwen Code, Claude Code, GLM, and Open Code bundles so live task tests can start before a deeper runtime exists.

## Next Prompt Work

The next prompt and instruction assets should cover:

1. broader packet examples for realistic task shapes across all roles
2. live validation of the Controller against real tasks
3. additional shared skills only where cross-role reuse clearly justifies them
4. prompt-level alignment to keep each role output consistent with the packet contract
