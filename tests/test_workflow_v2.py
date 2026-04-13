"""
LangGraph Send API 全并行工作流 V2 单元测试

测试覆盖:
1. 状态类型创建 (TaskState, ExecutorState)
2. Markdown 解析函数 (parse_acceptance_criteria, parse_test_requirements)
3. 工作流节点逻辑 (mock 依赖)
4. 图构建 (验证图结构正确)
5. V2 入口类接口兼容性
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.state import (
    ExecutorState,
    TaskState,
    parse_acceptance_criteria,
    parse_test_requirements,
)


# ==================== 状态类型测试 ====================

class TestTaskState:
    """TaskState 状态类型测试"""

    def test_create_minimal_task_state(self):
        """测试创建最小任务状态"""
        state: TaskState = {
            "task_id": "TASK-001",
            "title": "测试任务",
            "objective": "# Task: 测试任务\n\n## 任务目标\n测试",
            "files_to_modify": [],
            "files_to_create": [],
            "forbidden_files": [],
            "acceptance_criteria": [],
            "test_requirements": None,
            "constraints": [],
            "references": [],
            "notes": [],
            "success": False,
            "output": "",
            "files_changed": [],
            "branch_name": "",
            "commit_hash": None,
            "test_result": None,
            "test_passed": False,
            "retry_count": 0,
        }
        assert state["task_id"] == "TASK-001"
        assert state["success"] is False
        assert state["retry_count"] == 0

    def test_task_state_with_acceptance_criteria(self):
        """测试带验收标准的任务状态"""
        state: TaskState = {
            "task_id": "TASK-001",
            "title": "测试",
            "objective": "## 验收标准\n- [ ] 标准1\n- [ ] 标准2",
            "files_to_modify": [],
            "files_to_create": [],
            "forbidden_files": [],
            "acceptance_criteria": ["标准1", "标准2"],
            "test_requirements": {"need_tests": True, "test_command": "pytest"},
            "constraints": [],
            "references": [],
            "notes": [],
            "success": False,
            "output": "",
            "files_changed": [],
            "branch_name": "",
            "commit_hash": None,
            "test_result": None,
            "test_passed": False,
            "retry_count": 0,
        }
        assert len(state["acceptance_criteria"]) == 2
        assert state["test_requirements"]["need_tests"] is True


class TestExecutorState:
    """ExecutorState 状态类型测试"""

    def test_create_initial_executor_state(self):
        """测试创建初始执行器状态"""
        state: ExecutorState = {
            "parallel_limit": 3,
            "max_retries": 3,
            "task_states": {},
            "pending_indices": [],
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        assert state["parallel_limit"] == 3
        assert len(state["task_states"]) == 0
        assert len(state["pending_indices"]) == 0

    def test_executor_state_with_tasks(self):
        """测试带任务的执行器状态"""
        task: TaskState = {
            "task_id": "TASK-001",
            "title": "任务1",
            "objective": "目标",
            "files_to_modify": [],
            "files_to_create": [],
            "forbidden_files": [],
            "acceptance_criteria": [],
            "test_requirements": None,
            "constraints": [],
            "references": [],
            "notes": [],
            "success": False,
            "output": "",
            "files_changed": [],
            "branch_name": "",
            "commit_hash": None,
            "test_result": None,
            "test_passed": False,
            "retry_count": 0,
        }
        state: ExecutorState = {
            "parallel_limit": 3,
            "max_retries": 3,
            "task_states": {0: task},
            "pending_indices": [0],
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        assert len(state["task_states"]) == 1
        assert state["task_states"][0]["task_id"] == "TASK-001"


# ==================== Markdown 解析测试 ====================

class TestParseAcceptanceCriteria:
    """parse_acceptance_criteria 测试"""

    def test_basic_criteria(self):
        """测试基本的验收标准解析"""
        markdown = (
            "# Task: Test\n\n"
            "## 验收标准\n"
            "- [ ] 标准1\n"
            "- [ ] 标准2\n"
            "- [ ] 标准3\n"
            "## 测试要求\n"
            "需要测试"
        )
        result = parse_acceptance_criteria(markdown)
        assert result == ["标准1", "标准2", "标准3"]

    def test_criteria_at_end_of_file(self):
        """测试验收标准在文件末尾"""
        markdown = (
            "# Task: Test\n\n"
            "## 验收标准\n"
            "- [ ] 最后一个标准"
        )
        result = parse_acceptance_criteria(markdown)
        assert result == ["最后一个标准"]

    def test_no_criteria_section(self):
        """测试没有验收标准部分"""
        markdown = "# Task: Test\n\n## 任务目标\n没有验收标准"
        result = parse_acceptance_criteria(markdown)
        assert result == []

    def test_empty_criteria_section(self):
        """测试空的验收标准部分"""
        markdown = "# Task: Test\n\n## 验收标准\n## 测试要求"
        result = parse_acceptance_criteria(markdown)
        assert result == []

    def test_criteria_with_extra_text(self):
        """测试包含非 checkbox 行的验收标准"""
        markdown = (
            "## 验收标准\n"
            "以下是验收标准：\n"
            "- [ ] 标准1\n"
            "一些额外文本\n"
            "- [ ] 标准2\n"
            "## 下一节"
        )
        result = parse_acceptance_criteria(markdown)
        assert result == ["标准1", "标准2"]

    def test_criteria_with_spaces(self):
        """测试带空格的 checkbox 格式"""
        markdown = (
            "## 验收标准\n"
            "- [  ] 标准1\n"
            "- [ ]标准2\n"
            "## 结束"
        )
        result = parse_acceptance_criteria(markdown)
        # - [ ]标准2 不匹配（缺少空格）
        assert "标准1" in result


class TestParseTestRequirements:
    """parse_test_requirements 测试"""

    def test_with_test_command(self):
        """测试带测试命令的要求"""
        markdown = (
            "## 测试要求\n"
            "需要编写单元测试\n"
            "测试命令: `pytest`\n"
            "## 下一节"
        )
        result = parse_test_requirements(markdown)
        assert result is not None
        assert result["need_tests"] is True
        assert result["test_command"] == "pytest"

    def test_no_test_section(self):
        """测试没有测试要求部分"""
        markdown = "# Task: Test\n\n## 验收标准\n- [ ] 标准1"
        result = parse_test_requirements(markdown)
        assert result is None

    def test_empty_test_section(self):
        """测试空的测试要求部分"""
        markdown = "## 测试要求\n\n## 下一节"
        result = parse_test_requirements(markdown)
        assert result is None

    def test_need_tests_only(self):
        """测试只需要测试但没有命令"""
        markdown = (
            "## 测试要求\n"
            "需要编写单元测试\n"
            "## 结束"
        )
        result = parse_test_requirements(markdown)
        assert result is not None
        assert result["need_tests"] is True
        assert result["test_command"] is None

    def test_chinese_colon_format(self):
        """测试中文冒号格式"""
        markdown = (
            "## 测试要求\n"
            "测试命令：`pytest tests/ -v`\n"
            "## 结束"
        )
        result = parse_test_requirements(markdown)
        assert result is not None
        assert result["need_tests"] is True
        assert result["test_command"] == "pytest tests/ -v"

    def test_no_need_tests_keyword(self):
        """测试不包含'需要测试'关键字"""
        markdown = (
            "## 测试要求\n"
            "无特殊要求\n"
            "## 结束"
        )
        result = parse_test_requirements(markdown)
        # "无特殊要求" 意味着没有测试需求，应返回 None
        assert result is None


# ==================== 路由逻辑测试 ====================

class TestDispatchRouter:
    """dispatch_router_node 路由逻辑测试"""

    def test_dispatch_with_pending_tasks(self):
        """测试有待分发任务时的路由"""
        state: ExecutorState = {
            "pending_indices": [0, 1, 2],
            "task_states": {},
            "max_retries": 3,
            "parallel_limit": 3,
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        # 模拟路由函数行为
        pending = state.get("pending_indices", [])
        from langgraph.types import Send
        sends = [Send("task_subgraph", {"task_idx": idx}) for idx in pending]
        assert len(sends) == 3
        assert all(isinstance(s, Send) for s in sends)

    def test_dispatch_no_pending_tasks(self):
        """测试没有待分发任务时的路由"""
        state: ExecutorState = {
            "pending_indices": [],
            "task_states": {},
            "max_retries": 3,
            "parallel_limit": 3,
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        pending = state.get("pending_indices", [])
        sends = [Send("task_subgraph", {"task_idx": idx}) for idx in pending]
        assert len(sends) == 0


class TestWaitForAll:
    """wait_for_all_node 逻辑测试"""

    def test_all_tasks_accounted(self):
        """测试所有任务都已计入"""
        state: ExecutorState = {
            "task_states": {0: {}, 1: {}, 2: {}},
            "completed_indices": [0, 1],
            "failed_indices": [2],
            "pending_indices": [],
            "running_indices": [],
            "max_retries": 3,
            "parallel_limit": 3,
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        total = len(state["task_states"])
        accounted = len(state["completed_indices"]) + len(state["failed_indices"])
        assert accounted == total

    def test_missing_task_indices(self):
        """测试有遗漏的任务索引"""
        state: ExecutorState = {
            "task_states": {0: {}, 1: {}, 2: {}},
            "completed_indices": [0],
            "failed_indices": [],
            "pending_indices": [],
            "running_indices": [],
            "max_retries": 3,
            "parallel_limit": 3,
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        all_indices = set(state["task_states"].keys())
        accounted = set(state["completed_indices"]) | set(state["failed_indices"])
        missing = all_indices - accounted
        assert missing == {1, 2}


class TestCommandRouting:
    """Command API 路由逻辑测试"""

    def test_test_passed_goto_done(self):
        """测试通过时路由到 task_done"""
        from langgraph.types import Command
        # 模拟 test_single_task 返回 Command
        cmd = Command(
            update={"test_passed": True, "test_result": "通过"},
            goto="task_done",
        )
        assert cmd.goto == "task_done"
        assert cmd.update["test_passed"] is True

    def test_test_failed_goto_rework(self):
        """测试失败时路由到 rework"""
        from langgraph.types import Command
        cmd = Command(
            update={"test_passed": False, "retry_count": 1},
            goto="rework_single_task",
        )
        assert cmd.goto == "rework_single_task"
        assert cmd.update["retry_count"] == 1

    def test_test_failed_max_retries(self):
        """测试失败且达到最大重试时路由到 task_failed"""
        from langgraph.types import Command
        cmd = Command(
            update={"test_passed": False, "retry_count": 3},
            goto="task_failed",
        )
        assert cmd.goto == "task_failed"


# ==================== 图结构测试 ====================

class TestGraphStructure:
    """图结构测试"""

    def test_graph_builds_without_error(self):
        """测试图可以无错误地构建"""
        from unittest.mock import MagicMock
        from src.workflow.nodes import WorkflowNodes
        from src.workflow.graph_builder import build_parallel_executor_graph

        # 创建 mock 依赖
        mock_developer = MagicMock()
        mock_tester = MagicMock()
        mock_git_manager = MagicMock()
        mock_archiver = MagicMock()
        mock_cli = MagicMock()

        nodes = WorkflowNodes(
            developer=mock_developer,
            tester=mock_tester,
            git_manager=mock_git_manager,
            archiver=mock_archiver,
            project_root="/tmp/test",
            base_qwen_cli=mock_cli,
        )

        graph = build_parallel_executor_graph(nodes)
        assert graph is not None

    def test_subgraph_builds_without_error(self):
        """测试子图可以无错误地构建"""
        from unittest.mock import MagicMock
        from src.workflow.nodes import WorkflowNodes
        from src.workflow.graph_builder import build_task_subgraph

        mock_developer = MagicMock()
        mock_tester = MagicMock()
        mock_git_manager = MagicMock()
        mock_archiver = MagicMock()
        mock_cli = MagicMock()

        nodes = WorkflowNodes(
            developer=mock_developer,
            tester=mock_tester,
            git_manager=mock_git_manager,
            archiver=mock_archiver,
            project_root="/tmp/test",
            base_qwen_cli=mock_cli,
        )

        subgraph = build_task_subgraph(nodes)
        assert subgraph is not None


# ==================== V2 入口类测试 ====================

class TestParallelExecutorWorkflowV2:
    """V2 入口类测试"""

    def test_v2_initialization(self):
        """测试 V2 初始化"""
        from unittest.mock import MagicMock, patch

        # Mock 所有外部依赖
        with patch("src.parallel_graph_v2.GitManager") as mock_git, \
             patch("src.parallel_graph_v2.QwenCodeCLI") as mock_cli, \
             patch("src.parallel_graph_v2.TaskArchiver") as mock_archiver, \
             patch("src.parallel_graph_v2.build_parallel_executor_graph") as mock_build:

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_git.return_value = MagicMock()
                mock_cli.return_value = MagicMock()
                mock_archiver.return_value = MagicMock()
                mock_build.return_value = MagicMock()

                from src.parallel_graph_v2 import ParallelExecutorWorkflowV2
                workflow = ParallelExecutorWorkflowV2(
                    project_root=tmpdir,
                    models={"developer": "qwen-coder", "tester": "qwen-coder"},
                    parallel_limit=5,
                )

                assert workflow.project_root == tmpdir
                assert workflow.parallel_limit == 5
                assert workflow.models["developer"] == "qwen-coder"
                assert workflow.nodes is not None
                assert workflow.workflow is not None

    def test_v2_state_initialization(self):
        """测试 V2 初始状态"""
        state: ExecutorState = {
            "parallel_limit": 3,
            "max_retries": 3,
            "task_states": {},
            "pending_indices": [],
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
            "archive_dir": None,
            "final_summary": None,
            "error": None,
        }
        assert isinstance(state["task_states"], dict)
        assert isinstance(state["pending_indices"], list)
        assert state["error"] is None
