"""
LangGraph Send API 全并行工作流 V2

每个任务独立完成: 开发 → 测试 → (返工?) → 等待全部完成 → 合并
使用 LangGraph Send API 实现真正的全并行执行，替代 V1 的批次模型。

符合的核心约束:
- HC-1: LangGraph 状态机驱动
- HC-2: 单向隔离的信息流动 (每个任务独立子图)
- HC-3: Markdown 文件驱动 (整文件传递)
- HC-4: Tester Agent 完备性测试
- HC-5: 时间戳归档
"""

from src.workflow.state import (
    ExecutorState,
    TaskState,
    parse_acceptance_criteria,
    parse_test_requirements,
)
from src.workflow.nodes import WorkflowNodes
from src.workflow.graph_builder import (
    build_parallel_executor_graph,
    build_task_subgraph,
)

__all__ = [
    "ExecutorState",
    "TaskState",
    "parse_acceptance_criteria",
    "parse_test_requirements",
    "WorkflowNodes",
    "build_parallel_executor_graph",
    "build_task_subgraph",
]
