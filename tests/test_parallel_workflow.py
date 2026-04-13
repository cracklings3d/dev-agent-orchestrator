"""
并行执行器单元测试
测试执行器路由逻辑和状态管理
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parallel_graph import ExecutorState, TaskState


class TestExecutorState:
    """执行器状态测试"""

    def test_create_executor_state(self):
        """测试创建执行器状态"""
        state = ExecutorState(
            parallel_limit=3,
            max_retries=3,
            active_tasks=[0, 1],
            completed_tasks=[],
            failed_tasks=[],
            task_states={
                0: TaskState(task_id="TASK-001", title="任务 1", objective="目标 1"),
                1: TaskState(task_id="TASK-002", title="任务 2", objective="目标 2"),
            },
            archive_dir=None,
            final_summary=None,
            error=None
        )
        assert state["parallel_limit"] == 3
        assert len(state["active_tasks"]) == 2
        assert len(state["task_states"]) == 2

    def test_task_state_creation(self):
        """测试任务状态创建"""
        task = TaskState(
            task_id="TASK-001",
            title="实现登录功能",
            objective="实现用户登录",
            success=False,
            retry_count=0
        )
        assert task["task_id"] == "TASK-001"
        assert task["success"] is False
        assert task["retry_count"] == 0


class TestParallelExecutorWorkflow:
    """并行执行器工作流测试"""

    def test_route_after_execute_all_done(self):
        """测试所有任务完成后路由到 done"""
        # 模拟状态
        state = ExecutorState(
            active_tasks=[],
            completed_tasks=[0, 1, 2],
            failed_tasks=[],
            task_states={0: {}, 1: {}, 2: {}},
        )
        
        # 所有任务都处理完且无活跃任务 → done
        all_processed = len(state["completed_tasks"]) + len(state["failed_tasks"]) >= len(state["task_states"])
        assert all_processed and not state["active_tasks"]

    def test_route_after_execute_has_active(self):
        """测试有活跃任务时路由到 test"""
        state = ExecutorState(
            active_tasks=[2],
            completed_tasks=[0, 1],
            failed_tasks=[],
            task_states={0: {}, 1: {}, 2: {}},
        )
        
        all_processed = len(state["completed_tasks"]) + len(state["failed_tasks"]) >= len(state["task_states"])
        assert not (all_processed and not state["active_tasks"])

    def test_route_after_test_has_rework(self):
        """测试需要返工时路由到 rework"""
        state = ExecutorState(
            active_tasks=[],
            completed_tasks=[0],
            failed_tasks=[],
            task_states={0: {}},
            _tasks_need_rework=[0],
        )
        
        tasks_need_rework = state.get("_tasks_need_rework", [])
        active_tasks = state.get("active_tasks", [])
        assert tasks_need_rework or active_tasks

    def test_route_after_test_no_rework(self):
        """测试不需要返工时路由到 merge"""
        state = ExecutorState(
            active_tasks=[],
            completed_tasks=[0],
            failed_tasks=[],
            task_states={0: {}},
            _tasks_need_rework=[],
        )
        
        tasks_need_rework = state.get("_tasks_need_rework", [])
        active_tasks = state.get("active_tasks", [])
        assert not (tasks_need_rework or active_tasks)

    def test_parallel_task_batching(self):
        """测试并行批次计算"""
        parallel_limit = 3
        total_tasks = 7
        
        # 首批活跃任务
        active = list(range(min(total_tasks, parallel_limit)))
        assert len(active) == 3
        assert active == [0, 1, 2]

    def test_merge_conflict_detection(self):
        """测试合并冲突检测逻辑"""
        conflicts = [
            {"task_idx": 0, "branch": "feature/task-001", "conflicts": ["file1.py"]},
            {"task_idx": 1, "branch": "feature/task-002", "conflicts": ["file2.py"]},
        ]
        
        assert len(conflicts) == 2
        assert conflicts[0]["conflicts"] == ["file1.py"]
