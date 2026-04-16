"""Render and install the active workflow assets for multiple target platforms.

This module converts the active bounded-context multi-agent workflow into platform-
specific bundles for:

- GitHub Copilot in VS Code
- Qwen Code
- Claude Code
- GLM
- Open Code

The integrations are intentionally pragmatic. Copilot gets the most native output.
The other platforms receive deterministic local bundles and quickstarts that can be
used for live validation even where native orchestration features differ.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

SUPPORTED_PLATFORMS = (
    "copilot-vscode",
    "qwen-code",
    "claude-code",
    "glm",
    "opencode",
)

PLATFORM_DISPLAY_NAMES: dict[str, str] = {
    "copilot-vscode": "GitHub Copilot (VS Code)",
    "qwen-code": "Qwen Code",
    "claude-code": "Claude Code",
    "glm": "GLM",
    "opencode": "Open Code",
}

PLATFORM_GLOBAL_ROOTS: dict[str, Path | None] = {
    "copilot-vscode": None,
    "qwen-code": None,
    "claude-code": None,
    "glm": None,
    "opencode": Path.home() / ".config" / "opencode",
}

AGENT_SOURCE_FILES = [
    Path(".github/agents/architect.agent.md"),
    Path(".github/agents/developer.agent.md"),
    Path(".github/agents/tester.agent.md"),
    Path(".github/agents/reviewer.agent.md"),
    Path(".github/agents/controller.agent.md"),
    Path(".github/agents/copilot-workflow-runner.agent.md"),
]

SKILL_SOURCE_FILES = [
    Path(".github/skills/grill-me-relentlessly/SKILL.md"),
    Path(".github/skills/bounded-context-packets/SKILL.md"),
    Path(".github/skills/code-quality-principles/SKILL.md"),
]

SHARED_DOC_FILES = [
    Path("TASK_PACKET_CONTRACT.md"),
    Path("ROUTING_AND_ESCALATION_POLICY.md"),
    Path("CONTROLLER_WORKED_EXAMPLES.md"),
]


@dataclass(frozen=True)
class MarkdownAsset:
    slug: str
    name: str
    description: str
    body: str
    source_path: Path


def _validate_source_paths(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not (REPO_ROOT / path).exists()]
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"Missing integration source assets:\n{joined}")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    end_marker = text.find("\n---\n", 4)
    if end_marker == -1:
        return {}, text

    frontmatter_text = text[4:end_marker]
    body = text[end_marker + 5 :].lstrip("\n")

    data: dict[str, str] = {}
    for raw_line in frontmatter_text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data, body


def _slug_from_source_path(source_path: Path) -> str:
    name = source_path.name
    if name.endswith(".agent.md"):
        return name[: -len(".agent.md")]
    if name == "SKILL.md":
        return source_path.parent.name
    return source_path.stem


def _load_markdown_asset(source_path: Path) -> MarkdownAsset:
    text = (REPO_ROOT / source_path).read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    slug = _slug_from_source_path(source_path)
    name = frontmatter.get("name", slug.replace("-", " ").title())
    description = frontmatter.get("description", "")
    return MarkdownAsset(
        slug=slug,
        name=name,
        description=description,
        body=body.strip() + "\n",
        source_path=source_path,
    )


def _load_agents() -> list[MarkdownAsset]:
    _validate_source_paths(AGENT_SOURCE_FILES)
    return [_load_markdown_asset(path) for path in AGENT_SOURCE_FILES]


def _load_skills() -> list[MarkdownAsset]:
    _validate_source_paths(SKILL_SOURCE_FILES)
    return [_load_markdown_asset(path) for path in SKILL_SOURCE_FILES]


def _copy_file(rel_path: Path, target_root: Path, force: bool) -> Path:
    source_path = REPO_ROOT / rel_path
    target_path = target_root / rel_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file without --force: {target_path}")
    shutil.copy2(source_path, target_path)
    return target_path


def _write_text(target_path: Path, text: str, force: bool) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file without --force: {target_path}")
    target_path.write_text(text, encoding="utf-8")
    return target_path


def _resolve_base(target_root: Path, platform_dir_name: str, global_mode: bool) -> Path:
    if global_mode:
        return target_root
    return target_root / platform_dir_name


def _plain_markdown_agent_text(asset: MarkdownAsset, platform_label: str) -> str:
    return (
        f"# Agent: {asset.name}\n\n"
        f"Description: {asset.description}\n\n"
        f"Platform Bundle: {platform_label}\n\n"
        f"{asset.body}"
    )


def _plain_markdown_skill_text(asset: MarkdownAsset, platform_label: str) -> str:
    return (
        f"# Skill: {asset.name}\n\n"
        f"Description: {asset.description}\n\n"
        f"Platform Bundle: {platform_label}\n\n"
        f"{asset.body}"
    )


def _glm_agent_json(asset: MarkdownAsset) -> str:
    payload = {
        "name": asset.name,
        "slug": asset.slug,
        "description": asset.description,
        "system_message": asset.body.strip(),
        "model": "glm-4-plus",
        "temperature": 0.2,
        "metadata": {
            "integration_layer": "bounded-context-multi-agent",
            "source_path": str(asset.source_path).replace("\\", "/"),
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _copilot_quickstart() -> str:
    return """# GitHub Copilot VS Code Multi-Agent Quickstart

This repository has been prepared with the bounded-context multi-agent integration layer for GitHub Copilot in VS Code.

## How To Run

1. Open this repository in VS Code.
2. Open Copilot Chat.
3. Select `Copilot Workflow Runner` from the agent picker.
4. Give it one real task in this repository.

Suggested prompt:

```md
Run this task through the bounded-context workflow in this workspace.

Objective:
- <what should change>

Known constraints:
- <constraint>

Relevant references:
- <file or directory>

Acceptance criteria:
- <criterion>
```
"""


def _qwen_quickstart() -> str:
    return """# Qwen Code Multi-Agent Quickstart

This repository has been prepared with a Qwen Code integration bundle for the bounded-context multi-agent workflow.

## Installed Layout

- `.qwen/agents/*.md`
- `.qwen/skills/<name>/SKILL.md`

## Intended Use

Use the installed agent markdown files as role prompts or system prompt files when running Qwen Code.

Start with `.qwen/agents/workflow-runner.md` if you want one high-level coordinator prompt.
If you want stricter role separation, invoke the role prompts individually in this order:

1. `architect.md`
2. `developer.md`
3. `tester.md`
4. `reviewer.md`
5. `controller.md`

## Important Note

This bundle assumes Qwen Code can consume plain markdown prompts reliably, but it does not assume native workspace-level subagent orchestration.
"""


def _claude_quickstart() -> str:
    return """# Claude Code Multi-Agent Quickstart

This repository has been prepared with a Claude Code integration bundle for the bounded-context multi-agent workflow.

## Installed Layout

- `.claude/agents/*.md`
- `.claude/skills/<name>/SKILL.md`

## Intended Use

Use the installed agent markdown files as role prompts or reusable prompt assets.

Start with `.claude/agents/workflow-runner.md` if you want one coordinator prompt.
If you want stricter manual role separation, use the role prompts individually.

## Important Note

This bundle is pragmatic. It gives Claude Code a deterministic local asset layout even if your current Claude environment does not natively mirror GitHub Copilot's custom-agent behavior.
"""


def _glm_quickstart() -> str:
    return """# GLM Multi-Agent Quickstart

This repository has been prepared with a GLM integration bundle for the bounded-context multi-agent workflow.

## Installed Layout

- `.glm/agents/*.json`
- `.glm/skills/<name>/SKILL.md`

## Intended Use

The JSON files under `.glm/agents/` contain structured system-message payloads for the workflow roles.

Use them as character or system prompt definitions when calling GLM tooling.

## Important Note

This bundle provides deterministic rendered assets for GLM, but not a native orchestration runtime. It is meant for platform adaptation and live prompt testing.
"""


def _opencode_agent_text(asset: MarkdownAsset) -> str:
    is_workflow_runner = asset.slug == "copilot-workflow-runner"
    mode = "primary" if is_workflow_runner else "subagent"
    desc = asset.description.replace("\\", "\\\\").replace('"', '\\"')
    return f'---\ndescription: "{desc}"\nmode: {mode}\n---\n\n{asset.body}'


def _opencode_skill_text(asset: MarkdownAsset) -> str:
    desc = asset.description.replace("\\", "\\\\").replace("'", "\\'")
    return f"---\nname: {asset.slug}\ndescription: '{desc}'\n---\n\n{asset.body}"


def _opencode_quickstart() -> str:
    return """# Open Code Multi-Agent Quickstart

This repository has been prepared with an Open Code (opencode) integration bundle for the bounded-context multi-agent workflow.

## Installed Layout

- `.opencode/agents/*.md` — Agent definitions with OpenCode-compatible YAML frontmatter
- `.opencode/skills/<name>/SKILL.md` — Shared skills

## How To Use

1. Run `opencode` in this repository.
2. The `workflow-runner` agent should appear as a primary agent you can invoke directly via Tab or @ mention.
3. Give it a real task:

```md
Run this task through the bounded-context workflow.

Objective:
- <what should change>

Known constraints:
- <constraint>

Acceptance criteria:
- <criterion>
```

The workflow runner will delegate to the Architect, Developer, Tester, Reviewer, and Controller subagents using compact task packets.

## Agent Roles

| Agent | Mode | Purpose |
|-------|------|---------|
| workflow-runner | primary | Coordinates the full workflow |
| architect | subagent | Scopes and shapes tasks |
| developer | subagent | Implements the code |
| tester | subagent | Tests the implementation |
| reviewer | subagent | Reviews for quality |
| controller | subagent | Validates acceptance criteria |
"""


def _manifest_text(platforms: list[str], installed_paths: list[Path], target_root: Path) -> str:
    relative_paths = [path.relative_to(target_root).as_posix() for path in installed_paths]
    manifest = {
        "integration_layer": "bounded-context-multi-agent",
        "platforms": platforms,
        "installed_files": relative_paths,
    }
    return json.dumps(manifest, indent=2)


def _install_shared_docs(target_root: Path, force: bool) -> list[Path]:
    _validate_source_paths(SHARED_DOC_FILES)
    return [_copy_file(path, target_root, force) for path in SHARED_DOC_FILES]


def _install_copilot_vscode(target_root: Path, force: bool, global_mode: bool = False) -> list[Path]:
    if global_mode:
        return []
    installed: list[Path] = []
    for rel_path in AGENT_SOURCE_FILES:
        installed.append(_copy_file(rel_path, target_root, force))

    installed.append(_copy_file(Path(".github/agents/README.md"), target_root, force))

    for rel_path in SKILL_SOURCE_FILES:
        installed.append(_copy_file(rel_path, target_root, force))

    installed.append(_copy_file(Path(".github/skills/README.md"), target_root, force))
    installed.append(_write_text(target_root / "COPILOT_VSCODE_MULTI_AGENT_QUICKSTART.md", _copilot_quickstart(), force))
    return installed


def _install_plain_markdown_platform(target_root: Path, force: bool, platform_id: str, platform_dir_name: str, quickstart_name: str, quickstart_text: str, global_mode: bool = False) -> list[Path]:
    agents = _load_agents()
    skills = _load_skills()
    installed: list[Path] = []
    base = _resolve_base(target_root, platform_dir_name, global_mode)
    agent_dir = base / "agents"
    skill_dir = base / "skills"

    for asset in agents:
        file_name = "workflow-runner.md" if asset.slug == "copilot-workflow-runner" else f"{asset.slug}.md"
        installed.append(_write_text(agent_dir / file_name, _plain_markdown_agent_text(asset, platform_id), force))

    for asset in skills:
        installed.append(_write_text(skill_dir / asset.slug / "SKILL.md", _plain_markdown_skill_text(asset, platform_id), force))

    if not global_mode:
        installed.append(_write_text(target_root / quickstart_name, quickstart_text, force))
    return installed


def _install_glm(target_root: Path, force: bool, global_mode: bool = False) -> list[Path]:
    agents = _load_agents()
    skills = _load_skills()
    installed: list[Path] = []
    base = _resolve_base(target_root, ".glm", global_mode)
    agent_dir = base / "agents"
    skill_dir = base / "skills"

    for asset in agents:
        file_name = "workflow-runner.json" if asset.slug == "copilot-workflow-runner" else f"{asset.slug}.json"
        installed.append(_write_text(agent_dir / file_name, _glm_agent_json(asset), force))

    for asset in skills:
        installed.append(_write_text(skill_dir / asset.slug / "SKILL.md", _plain_markdown_skill_text(asset, "glm"), force))

    if not global_mode:
        installed.append(_write_text(target_root / "GLM_MULTI_AGENT_QUICKSTART.md", _glm_quickstart(), force))
    return installed


def _install_opencode(target_root: Path, force: bool, global_mode: bool = False) -> list[Path]:
    agents = _load_agents()
    skills = _load_skills()
    installed: list[Path] = []
    base = _resolve_base(target_root, ".opencode", global_mode)
    agent_dir = base / "agents"
    skill_dir = base / "skills"

    for asset in agents:
        file_name = "workflow-runner.md" if asset.slug == "copilot-workflow-runner" else f"{asset.slug}.md"
        installed.append(_write_text(agent_dir / file_name, _opencode_agent_text(asset), force))

    for asset in skills:
        installed.append(_write_text(skill_dir / asset.slug / "SKILL.md", _opencode_skill_text(asset), force))

    if not global_mode:
        installed.append(_write_text(target_root / "OPENCODE_MULTI_AGENT_QUICKSTART.md", _opencode_quickstart(), force))
    return installed


def install_platforms(target_root: Path, platforms: Iterable[str], force: bool = False, *, global_mode: bool = False) -> list[Path]:
    requested = list(platforms)
    if not requested:
        raise ValueError("At least one platform must be requested")

    normalized = []
    for platform in requested:
        if platform == "all":
            normalized = list(SUPPORTED_PLATFORMS)
            break
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        normalized.append(platform)

    target_root.mkdir(parents=True, exist_ok=True)

    installed: list[Path] = []
    if not global_mode:
        installed.extend(_install_shared_docs(target_root, force))

    if "copilot-vscode" in normalized:
        installed.extend(_install_copilot_vscode(target_root, force, global_mode=global_mode))
    if "qwen-code" in normalized:
        installed.extend(
            _install_plain_markdown_platform(
                target_root,
                force,
                platform_id="qwen-code",
                platform_dir_name=".qwen",
                quickstart_name="QWEN_CODE_MULTI_AGENT_QUICKSTART.md",
                quickstart_text=_qwen_quickstart(),
                global_mode=global_mode,
            )
        )
    if "claude-code" in normalized:
        installed.extend(
            _install_plain_markdown_platform(
                target_root,
                force,
                platform_id="claude-code",
                platform_dir_name=".claude",
                quickstart_name="CLAUDE_CODE_MULTI_AGENT_QUICKSTART.md",
                quickstart_text=_claude_quickstart(),
                global_mode=global_mode,
            )
        )
    if "glm" in normalized:
        installed.extend(_install_glm(target_root, force, global_mode=global_mode))
    if "opencode" in normalized:
        installed.extend(_install_opencode(target_root, force, global_mode=global_mode))

    if not global_mode:
        installed.append(
            _write_text(
                target_root / "MULTI_PLATFORM_INTEGRATION_MANIFEST.json",
                _manifest_text(normalized, installed, target_root),
                force,
            )
        )
    return installed
