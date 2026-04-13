"""
LangGraph Send API 全并行工作流 V2 - 图构建器

构建两个图:
1. 任务子图: 每个任务独立的 execute → test → (rework?) 循环
2. 主图: load → dispatch → (Send 扇出到子图 × N) → wait → merge → summarize → archive

Send API 扇出机制:
- dispatch_router_node 返回 [Send("task_subgraph", {"task_idx": idx}), ...]
- LangGraph 为每个 Send 创建独立子图实例，真正并行执行
- 每个子图独立完成 execute → test → (rework loop) → done/failed
- 所有子图完成后自动进入 wait_for_all 节点
"""

from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command

from src.workflow.state import ExecutorState
from src.workflow.nodes import WorkflowNodes


def build_task_subgraph(nodes: WorkflowNodes) -> StateGraph:
    """
    构建单个任务的执行子图。

    每个任务独立完成:
    execute_single_task → test_single_task
                              ↓ (Command 路由)
                    ┌─────────┼──────────┐
                    ↓         ↓          ↓
              rework    task_done    task_failed
                ↓
        execute_single_task (重新排队)

    注意:
    - test_single_task 使用 Command(goto=...) 动态路由
    - rework_single_task 使用 Command(goto="execute_single_task") 重新排队
    - task_done 和 task_failed 是终点（子图结束）
    """
    subgraph = StateGraph(ExecutorState)

    # 添加节点
    subgraph.add_node("execute_single_task", nodes.execute_single_task)
    subgraph.add_node("test_single_task", nodes.test_single_task)
    subgraph.add_node("rework_single_task", nodes.rework_single_task)

    # 入口
    subgraph.add_edge(START, "execute_single_task")

    # execute → test
    subgraph.add_edge("execute_single_task", "test_single_task")

    # test → 通过 Command API 动态路由到:
    # - "rework_single_task" (测试失败，需要返工)
    # - "task_done" (测试通过，子图正常结束)
    # - "task_failed" (测试失败，达到最大重试，子图异常结束)
    # 注意: 路由由 test_single_task 节点内部的 Command(goto=...) 决定

    # task_done 和 task_failed 作为终点（不需要显式添加为节点）
    # 当 Command goto 到一个不存在的节点名时，子图会结束
    # 为了清晰，添加为 passthrough 节点
    subgraph.add_node("task_done", _passthrough_node)
    subgraph.add_node("task_failed", _passthrough_node)

    # 终点
    subgraph.add_edge("task_done", END)
    subgraph.add_edge("task_failed", END)

    # rework → execute (通过 Command goto="execute_single_task" 实现)
    # 不需要显式边，因为 rework_single_task 返回 Command(goto="execute_single_task")

    return subgraph


def _passthrough_node(state: ExecutorState) -> dict:
    """简单传递节点，不做任何操作。"""
    return {}


def build_parallel_executor_graph(nodes: WorkflowNodes) -> StateGraph:
    """
    构建 Send API 全并行工作流。

    图结构:
    load_tasks → dispatch_tasks → task_subgraph (Send 扇出 × N，真正并行)
                                       ↓
                                (所有子图完成后)
                                       ↓
                                wait_for_all → merge_branches → summarize → archive_finalize → END

    每个 task_subgraph 内部:
    execute_single_task → test_single_task → (Command 路由)
      ↖ rework_single_task ↗
    """
    # 先构建子图
    task_subgraph = build_task_subgraph(nodes)
    compiled_subgraph = task_subgraph.compile()

    # 构建主图
    workflow = StateGraph(ExecutorState)

    # 添加子图作为一个复合节点
    workflow.add_node("task_subgraph", compiled_subgraph)

    # 添加主图节点
    workflow.add_node("load_tasks", nodes.load_tasks_node)
    workflow.add_node("dispatch_tasks", nodes.dispatch_tasks_node)
    workflow.add_node("wait_for_all", nodes.wait_for_all_node)
    workflow.add_node("merge_branches", nodes.merge_branches_node)
    workflow.add_node("summarize", nodes.summarize_node)
    workflow.add_node("archive_finalize", nodes.archive_finalize_node)

    # === 边和路由 ===

    # 入口
    workflow.set_entry_point("load_tasks")

    # load_tasks → dispatch_tasks
    workflow.add_edge("load_tasks", "dispatch_tasks")

    # dispatch_tasks → task_subgraph (Send 扇出)
    # 使用 add_conditional_edges + dispatch_router_node 返回 Send 列表
    # 这是 LangGraph Send API 的标准用法
    workflow.add_conditional_edges(
        "dispatch_tasks",
        nodes.dispatch_router_node,
        ["task_subgraph"],
    )

    # task_subgraph → wait_for_all
    # 当所有 Send 实例（子图）完成后，自动进入下一节点
    workflow.add_edge("task_subgraph", "wait_for_all")

    # wait_for_all → merge_branches
    workflow.add_edge("wait_for_all", "merge_branches")

    # merge_branches → summarize
    workflow.add_edge("merge_branches", "summarize")

    # summarize → archive_finalize
    workflow.add_edge("summarize", "archive_finalize")

    # archive_finalize → END
    workflow.add_edge("archive_finalize", END)

    return workflow.compile()
