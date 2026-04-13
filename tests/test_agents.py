"""
Agent 模块单元测试
测试 AgentContext 和 BaseAgent 的核心功能
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.base_agent import AgentContext


class TestAgentContext:
    """AgentContext 测试类"""

    def test_create_context(self):
        """测试创建 AgentContext"""
        context = AgentContext(
            task_id="TEST-001",
            task_title="测试任务",
            task_objective="测试 AgentContext 功能",
            files_to_modify=["file1.ts"],
            files_to_create=["new.ts"],
            forbidden_files=["protected.ts"],
            acceptance_criteria=["标准 1"],
            test_requirements=None,
            constraints=[],
            references=[],
            notes=[]
        )

        assert context.task_id == "TEST-001"
        assert context.task_title == "测试任务"
        assert len(context.files_to_modify) == 1
        assert "file1.ts" in context.files_to_modify

    def test_markdown_generation(self):
        """测试 Markdown 生成"""
        context = AgentContext(
            task_id="TEST-002",
            task_title="Markdown 测试",
            task_objective="生成 Markdown",
            files_to_modify=["a.ts", "b.ts"],
            files_to_create=["c.ts"],
            forbidden_files=[],
            acceptance_criteria=["完成功能", "通过测试"],
            test_requirements={"need_tests": True, "test_command": "npm test"},
            constraints=["约束 1"],
            references=["docs/ref.md"],
            notes=["注意项"]
        )

        md = context.to_markdown()

        # 验证关键字段出现在 Markdown 中
        assert "Markdown 测试" in md
        assert "生成 Markdown" in md
        assert "a.ts" in md
        assert "b.ts" in md
        assert "c.ts" in md
        assert "完成功能" in md
        assert "通过测试" in md
        assert "npm test" in md
        assert "约束 1" in md

    def test_empty_context(self):
        """测试空上下文"""
        context = AgentContext(
            task_id="EMPTY-001",
            task_title="空任务",
            task_objective="",
            files_to_modify=[],
            files_to_create=[],
            forbidden_files=[],
            acceptance_criteria=[],
            test_requirements=None,
            constraints=[],
            references=[],
            notes=[]
        )

        md = context.to_markdown()
        assert "空任务" in md


class TestQwenCodeResult:
    """QwenCodeResult 测试类"""

    def test_create_result(self):
        """测试创建 QwenCodeResult"""
        from src.qwen_code_adapter import QwenCodeResult

        result = QwenCodeResult(
            success=True,
            output="测试输出",
            error="",
            exit_code=0,
            files_changed=["file1.ts", "file2.ts"]
        )

        assert result.success is True
        assert result.output == "测试输出"
        assert result.exit_code == 0
        assert len(result.files_changed) == 2
        assert "file1.ts" in result.files_changed

    def test_failed_result(self):
        """测试失败的结果"""
        from src.qwen_code_adapter import QwenCodeResult

        result = QwenCodeResult(
            success=False,
            output="",
            error="测试错误",
            exit_code=1,
            files_changed=[]
        )

        assert result.success is False
        assert result.error == "测试错误"
        assert result.exit_code == 1
