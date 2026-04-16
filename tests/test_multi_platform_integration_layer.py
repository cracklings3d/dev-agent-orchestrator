import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402


def test_install_all_platform_bundles(tmp_path):
    from integration_layer.installer import install_platforms

    installed_paths = install_platforms(tmp_path, platforms=["all"], force=False)
    installed_rel_paths = {path.relative_to(tmp_path).as_posix() for path in installed_paths}

    assert ".github/agents/copilot-workflow-runner.agent.md" in installed_rel_paths
    assert ".qwen/agents/workflow-runner.md" in installed_rel_paths
    assert ".claude/agents/workflow-runner.md" in installed_rel_paths
    assert ".glm/agents/workflow-runner.json" in installed_rel_paths
    assert ".opencode/agents/workflow-runner.md" in installed_rel_paths
    assert "COPILOT_VSCODE_MULTI_AGENT_QUICKSTART.md" in installed_rel_paths
    assert "QWEN_CODE_MULTI_AGENT_QUICKSTART.md" in installed_rel_paths
    assert "CLAUDE_CODE_MULTI_AGENT_QUICKSTART.md" in installed_rel_paths
    assert "GLM_MULTI_AGENT_QUICKSTART.md" in installed_rel_paths
    assert "OPENCODE_MULTI_AGENT_QUICKSTART.md" in installed_rel_paths
    assert "MULTI_PLATFORM_INTEGRATION_MANIFEST.json" in installed_rel_paths


def test_manifest_records_requested_platforms(tmp_path):
    from integration_layer.installer import install_platforms

    install_platforms(tmp_path, platforms=["copilot-vscode", "qwen-code"], force=False)

    manifest = json.loads((tmp_path / "MULTI_PLATFORM_INTEGRATION_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["platforms"] == ["copilot-vscode", "qwen-code"]


def test_install_refuses_overwrite_without_force(tmp_path):
    from integration_layer.installer import install_platforms

    install_platforms(tmp_path, platforms=["glm"], force=False)

    try:
        install_platforms(tmp_path, platforms=["glm"], force=False)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Expected FileExistsError when reinstalling without force")


def test_opencode_agent_frontmatter(tmp_path):
    from integration_layer.installer import install_platforms

    install_platforms(tmp_path, platforms=["opencode"], force=False)

    runner_text = (tmp_path / ".opencode" / "agents" / "workflow-runner.md").read_text(encoding="utf-8")
    assert runner_text.startswith("---\n")
    assert "mode: primary" in runner_text

    architect_text = (tmp_path / ".opencode" / "agents" / "architect.md").read_text(encoding="utf-8")
    assert "mode: subagent" in architect_text


def test_opencode_skill_has_frontmatter(tmp_path):
    from integration_layer.installer import install_platforms

    install_platforms(tmp_path, platforms=["opencode"], force=False)

    skill_text = (tmp_path / ".opencode" / "skills" / "grill-me-relentlessly" / "SKILL.md").read_text(encoding="utf-8")
    assert skill_text.startswith("---\n")
    assert "name: grill-me-relentlessly" in skill_text


def test_global_mode_skips_docs_and_manifest(tmp_path):
    from integration_layer.installer import install_platforms

    installed = install_platforms(tmp_path, platforms=["opencode"], force=False, global_mode=True)
    installed_names = {p.name for p in installed}

    assert "OPENCODE_MULTI_AGENT_QUICKSTART.md" not in installed_names
    assert "MULTI_PLATFORM_INTEGRATION_MANIFEST.json" not in installed_names
    assert "TASK_PACKET_CONTRACT.md" not in installed_names
    assert (tmp_path / "agents" / "workflow-runner.md").exists()
    assert (tmp_path / "agents" / "architect.md").exists()
    assert not (tmp_path / ".opencode").exists()


def test_global_mode_copilot_returns_empty(tmp_path):
    from integration_layer.installer import install_platforms

    installed = install_platforms(tmp_path, platforms=["copilot-vscode"], force=False, global_mode=True)
    assert installed == []