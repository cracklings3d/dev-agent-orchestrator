"""
LangGraph Send API 全并行工作流 (V2)

向后兼容 ParallelExecutorWorkflow 接口。
每个任务独立完成: 开发 → 测试 → (返工?) → 等待全部完成 → 合并

与 V1 的区别:
- V1 (parallel_graph.py): 批次模型，execute_tasks 用 for 循环顺序执行一批任务
- V2: Send API 全并行，每个任务独立创建子图实例，真正并行执行

前提: .qwen/tasks/ 目录下必须存在 TASK-*.md 文件
"""

from pathlib import Path
from typing import Optional

from src.agents.agent_types import DeveloperAgent, TesterAgent
from src.qwen_code_adapter import QwenCodeCLI
from src.git_manager import GitManager
from src.task_archiver import TaskArchiver
from src.workflow.nodes import WorkflowNodes
from src.workflow.graph_builder import build_parallel_executor_graph
from src.workflow.state import ExecutorState


class ParallelExecutorWorkflowV2:
    """
    并行任务执行器 V2 (Send API 全并行)

    与 V1 的区别:
    - V1: 批次模型，execute_tasks 用 for 循环顺序执行一批任务
    - V2: Send API 全并行，每个任务独立创建子图实例，真正并行

    前提: .qwen/tasks/ 目录下必须存在 TASK-*.md 文件
    """

    def __init__(self, project_root: str, models: Optional[dict] = None, parallel_limit: int = 3):
        """
        初始化 V2 并行执行器

        Args:
            project_root: 项目根目录路径
            models: 模型配置字典，支持 {"developer": "model-name", "tester": "model-name"}
            parallel_limit: 并行度 (V2 中所有任务天然并行，此参数保留为兼容性)
        """
        self.project_root = project_root
        self.parallel_limit = parallel_limit
        self.models = models or {}

        self.tasks_dir = Path(project_root) / ".qwen" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        self.archiver = TaskArchiver(self.tasks_dir)
        self.git_manager = GitManager(project_root)
        self.base_qwen_cli = QwenCodeCLI(project_root)

        self.developer = DeveloperAgent(
            self.base_qwen_cli, model=self.models.get("developer")
        )
        self.tester = TesterAgent(
            self.base_qwen_cli, model=self.models.get("tester")
        )

        self.nodes = WorkflowNodes(
            developer=self.developer,
            tester=self.tester,
            git_manager=self.git_manager,
            archiver=self.archiver,
            project_root=project_root,
            base_qwen_cli=self.base_qwen_cli,
        )

        self.workflow = build_parallel_executor_graph(self.nodes)

    def execute(self) -> dict:
        """
        执行任务

        Returns:
            最终状态 (ExecutorState)
        """
        print("\n" + "=" * 60)
        print("  LangGraph V2 Send API 全并行工作流启动")
        print("=" * 60)

        initial_state = ExecutorState(
            parallel_limit=self.parallel_limit,
            max_retries=3,
            task_states={},
            pending_indices=[],
            running_indices=[],
            completed_indices=[],
            failed_indices=[],
            archive_dir=None,
            final_summary=None,
            error=None,
        )

        final_state = self.workflow.invoke(initial_state)

        # 清理：切换回主分支 + GC 缩减 .git 体积
        try:
            self.git_manager.switch_branch("main")
        except Exception:
            try:
                self.git_manager.switch_branch("master")
            except Exception:
                pass

        print("\n🧹 Git GC: 清理不可达对象，缩减 .git 体积...")
        self.git_manager.gc_prune()

        print("\n" + "=" * 60)
        print("  LangGraph V2 Send API 全并行工作流完成")
        print("=" * 60)

        return final_state
