"""
LangGraph 并行任务执行器 (纯执行模式)

职责:
1. 从 .qwen/tasks/ 读取已有 TASK-*.md 任务文件
2. 并行执行每个任务 (fan-out/fan-in)
3. Tester Agent 验证 + 返工循环
4. 时间戳归档 (HC-5)

注意: 本模块不包含 Architect，任务文件必须已存在。

符合的核心约束:
- HC-1: LangGraph 状态机驱动
- HC-2: 单向隔离的信息流动
- HC-3: Markdown 文件驱动 (整文件传递)
- HC-4: Tester Agent 完备性测试
- HC-5: 时间戳归档
- HC-6: 模式化架构 (dev 模式)

工作流:
    load_tasks → archive_start → execute_tasks (fan-out)
                                      ↓
                                   test_task (fan-in)
                                      ↓
                                 rework_task? → execute_tasks (重试)
                                      ↓
                                 merge_branches → summarize → archive_finalize → END
"""

from typing import TypedDict, Optional, Literal
import json
import subprocess
from pathlib import Path
from datetime import datetime

from langgraph.graph import StateGraph, END

from src.agents.agent_types import DeveloperAgent, TesterAgent
from src.agents.base_agent import AgentContext
from src.qwen_code_adapter import QwenCodeCLI
from src.git_manager import GitManager
from src.task_archiver import TaskArchiver


# ==================== 状态定义 ====================

class TaskState(TypedDict, total=False):
    """单个任务的状态"""
    task_id: str
    title: str
    objective: str
    files_to_modify: list[str]
    files_to_create: list[str]
    forbidden_files: list[str]
    acceptance_criteria: list[str]
    test_requirements: Optional[dict]
    constraints: list[str]
    references: list[str]
    notes: list[str]

    # 执行结果
    success: bool
    output: str
    files_changed: list[str]
    branch_name: str
    commit_hash: Optional[str]
    test_result: Optional[str]
    test_passed: bool
    retry_count: int


class ExecutorState(TypedDict, total=False):
    """执行器总体状态"""
    # 控制参数
    parallel_limit: int
    max_retries: int

    # 任务索引和状态
    active_tasks: list[int]
    completed_tasks: list[int]
    failed_tasks: list[int]
    task_states: dict  # dict[int, TaskState]

    # 归档 (HC-5)
    archive_dir: Optional[str]

    # 最终结果
    final_summary: Optional[str]
    error: Optional[str]


# ==================== 并行执行器 ====================

class ParallelExecutorWorkflow:
    """
    并行任务执行器 (纯执行模式)
    
    前提: .qwen/tasks/ 目录下必须存在 TASK-*.md 文件
    """

    def __init__(self, project_root: str, models: Optional[dict] = None, parallel_limit: int = 3):
        self.project_root = project_root
        self.parallel_limit = parallel_limit
        self.models = models or {}

        # 任务目录
        self.tasks_dir = Path(project_root) / ".qwen" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # 归档管理器 (HC-5)
        self.archiver = TaskArchiver(self.tasks_dir)

        # Git Manager
        self.git_manager = GitManager(project_root)

        # 基础 CLI
        self.base_qwen_cli = QwenCodeCLI(project_root)

        # 初始化 Agent (只需要 Developer 和 Tester)
        self.developer = DeveloperAgent(self.base_qwen_cli, model=self.models.get("developer"))
        self.tester = TesterAgent(self.base_qwen_cli, model=self.models.get("tester"))

        # 构建图
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(ExecutorState)

        # 添加节点
        workflow.add_node("load_tasks", self.load_tasks_node)
        workflow.add_node("archive_start", self.archive_start_node)
        workflow.add_node("execute_tasks", self.execute_tasks_node)
        workflow.add_node("test_task", self.test_task_node)
        workflow.add_node("rework_task", self.rework_task_node)
        workflow.add_node("merge_branches", self.merge_branches_node)
        workflow.add_node("summarize", self.summarize_node)
        workflow.add_node("archive_finalize", self.archive_finalize_node)

        # 设置入口点
        workflow.set_entry_point("load_tasks")

        # load_tasks -> archive_start
        workflow.add_edge("load_tasks", "archive_start")

        # archive_start -> execute_tasks
        workflow.add_edge("archive_start", "execute_tasks")

        # execute_tasks -> test_task 或 merge_branches
        workflow.add_conditional_edges(
            "execute_tasks",
            self.route_after_execute,
            {"test": "test_task", "done": "merge_branches"}
        )

        # test_task -> rework_task 或 merge_branches
        workflow.add_conditional_edges(
            "test_task",
            self.route_after_test,
            {"rework": "rework_task", "merge": "merge_branches"}
        )

        # rework_task -> execute_tasks (重新开发)
        workflow.add_edge("rework_task", "execute_tasks")

        # merge_branches -> summarize -> archive_finalize -> END
        workflow.add_edge("merge_branches", "summarize")
        workflow.add_edge("summarize", "archive_finalize")
        workflow.add_edge("archive_finalize", END)

        return workflow.compile()

    # ==================== 节点实现 ====================

    def load_tasks_node(self, state: ExecutorState) -> dict:
        """
        加载任务节点
        从 .qwen/tasks/ 读取所有 TASK-*.md 文件
        """
        print(f"\n📂 加载任务文件 from {self.tasks_dir}...")

        # 查找所有 TASK-*.md 文件
        task_files = sorted(self.tasks_dir.glob("TASK-*.md"))
        
        if not task_files:
            return {
                "error": f"未找到任务文件! 请确保 {self.tasks_dir} 目录下有 TASK-*.md 文件",
                "active_tasks": [],
                "completed_tasks": [],
                "failed_tasks": [],
                "task_states": {}
            }

        print(f"   发现 {len(task_files)} 个任务文件:")

        task_states = {}
        for i, task_file in enumerate(task_files):
            print(f"   📄 {task_file.name}")
            
            # HC-3: 读取整份文件内容
            content = task_file.read_text(encoding="utf-8")
            
            # 提取 Task ID (从文件名)
            task_id = task_file.stem  # 如 TASK-001
            
            # 提取标题 (从第一行 # Task: ...)
            title = task_id
            for line in content.split("\n")[:5]:
                if line.startswith("# Task:"):
                    title = line.replace("# Task:", "").strip()
                    break

            task_states[i] = TaskState(
                task_id=task_id,
                title=title,
                objective=content,  # HC-3: 整份 Markdown 内容
                files_to_modify=[],
                files_to_create=[],
                forbidden_files=[],
                acceptance_criteria=[],
                test_requirements=None,
                constraints=[],
                references=[],
                notes=[],
                success=False,
                output="",
                files_changed=[],
                branch_name="",
                commit_hash=None,
                test_result=None,
                test_passed=False,
                retry_count=0
            )

        # 前 N 个任务标记为活跃
        active_count = min(len(task_files), self.parallel_limit)
        active_tasks = list(range(active_count))

        print(f"\n✅ 加载 {len(task_files)} 个任务，首批执行 {active_count} 个")

        return {
            "active_tasks": active_tasks,
            "completed_tasks": [],
            "failed_tasks": [],
            "task_states": task_states,
            "max_retries": 3,
            "parallel_limit": self.parallel_limit
        }

    def archive_start_node(self, state: ExecutorState) -> dict:
        """归档开始节点 (HC-5)"""
        task_states = state.get("task_states", {})
        if not task_states:
            return {}
            
        print(f"\n📁 归档开始: 创建时间戳归档目录...")
        archive_dir = self.archiver.start_execution()
        return {"archive_dir": str(archive_dir)}

    def execute_tasks_node(self, state: ExecutorState) -> dict:
        """
        执行任务节点 (fan-out)
        HC-3: 使用整份 Markdown 文件内容作为上下文
        """
        active_tasks = state.get("active_tasks", [])
        task_states = state.get("task_states", {})

        if not active_tasks:
            return {"active_tasks": []}

        print(f"\n⚙️  并行执行 {len(active_tasks)} 个任务...")

        updated_task_states = {}
        newly_completed = []
        newly_failed = []

        for task_idx in active_tasks:
            task_state = task_states[task_idx]
            task_id = task_state["task_id"]

            print(f"\n  📋 任务 [{task_idx + 1}]: {task_state['title']}")

            # HC-3: 使用整份文件内容 (已在 load_tasks_node 中读取)
            context = AgentContext(
                task_id=task_id,
                task_title=task_state["title"],
                task_objective=task_state["objective"],  # 整份 Markdown 内容
                files_to_modify=task_state.get("files_to_modify", []),
                files_to_create=task_state.get("files_to_create", []),
                forbidden_files=task_state.get("forbidden_files", []),
                acceptance_criteria=task_state.get("acceptance_criteria", []),
                test_requirements=task_state.get("test_requirements"),
                constraints=task_state.get("constraints", []),
                references=task_state.get("references", []),
                notes=task_state.get("notes", [])
            )

            # 创建特性分支
            branch_name = f"feature/{task_id.lower()}"
            print(f"   🔀 分支: {branch_name}")
            self.git_manager.create_feature_branch(task_id)

            # 执行任务
            result = self.developer.execute(context, self.project_root)

            # 提交更改
            commit_hash = None
            if result.success:
                print(f"   💾 提交更改...")
                commit_result = self.git_manager.submit_task_work(
                    task_id=task_id,
                    task_title=task_state["title"],
                    agent_name="Developer Agent"
                )

                if commit_result.success:
                    commit_hash = commit_result.commit_hash
                    print(f"   ✅ 提交成功: {commit_hash[:8]}")
                else:
                    print(f"   ⚠️  提交失败: {commit_result.error}")

            # 更新任务状态
            task_state["success"] = result.success
            task_state["output"] = result.output
            task_state["files_changed"] = result.files_changed
            task_state["branch_name"] = branch_name
            task_state["commit_hash"] = commit_hash

            updated_task_states[task_idx] = task_state

            if result.success:
                newly_completed.append(task_idx)
            else:
                newly_failed.append(task_idx)

        # 更新总体状态
        completed_tasks = state.get("completed_tasks", []) + newly_completed
        failed_tasks = state.get("failed_tasks", []) + newly_failed

        # 计算下一批活跃任务
        all_indices = set(range(len(task_states)))
        processed = set(completed_tasks + failed_tasks)
        remaining = list(all_indices - processed)

        next_active = remaining[:self.parallel_limit] if remaining else []

        return {
            "task_states": {**task_states, **updated_task_states},
            "active_tasks": next_active,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks
        }

    def test_task_node(self, state: ExecutorState) -> dict:
        """测试节点 (fan-in) - HC-4: Tester 完备性测试"""
        completed_tasks = state.get("completed_tasks", [])
        task_states = state.get("task_states", {})

        if not completed_tasks:
            return {}

        tasks_to_test = [
            idx for idx in completed_tasks
            if not task_states.get(idx, {}).get("test_passed", True)
        ]

        if not tasks_to_test:
            return {}

        print(f"\n🧪 测试 {len(tasks_to_test)} 个任务...")

        all_passed = True
        tasks_need_rework = []

        for task_idx in tasks_to_test:
            task_state = task_states[task_idx]

            print(f"\n  🔍 测试任务: {task_state['title']}")

            # 1. 运行自动化测试
            test_requirements = task_state.get("test_requirements")
            automated_test_passed = True

            if test_requirements and test_requirements.get("need_tests"):
                test_command = test_requirements.get("test_command")
                if test_command:
                    print(f"  🏃 运行测试: {test_command}")
                    passed, output = self._run_test_command(test_command)
                    automated_test_passed = passed

                    if not passed:
                        print(f"  ❌ 自动化测试失败")
                        task_state["test_result"] = f"自动化测试失败:\n{output}"
                        task_state["test_passed"] = False
                        task_state["retry_count"] = task_state.get("retry_count", 0) + 1
                        tasks_need_rework.append(task_idx)
                        all_passed = False
                        continue

            # 2. AI 代码审查 (HC-4)
            context = AgentContext(
                task_id=task_state["task_id"],
                task_title=f"测试: {task_state['title']}",
                task_objective=f"验证 {task_state['title']} 是否符合验收标准",
                files_to_modify=task_state.get("files_changed", []),
                files_to_create=[],
                forbidden_files=[],
                acceptance_criteria=task_state.get("acceptance_criteria", []),
                test_requirements=test_requirements,
                constraints=["客观评估，不要放水", "必须测试边界条件和退化场景"],
                references=[],
                notes=[]
            )

            result = self.tester.execute(context, self.project_root)

            # 解析结果
            try:
                json_start = result.output.find("{")
                json_end = result.output.rfind("}") + 1

                if json_start != -1 and json_end != 0:
                    test_data = json.loads(result.output[json_start:json_end])
                    recommendation = test_data.get("recommendation", "approve")

                    if recommendation == "approve" and automated_test_passed:
                        print(f"  ✅ AI 审查通过")
                        task_state["test_passed"] = True
                        task_state["test_result"] = test_data.get("summary", "审查通过")
                    else:
                        print(f"  ❌ AI 审查未通过")
                        task_state["test_passed"] = False
                        task_state["test_result"] = test_data.get("summary", "审查失败")
                        task_state["retry_count"] = task_state.get("retry_count", 0) + 1
                        tasks_need_rework.append(task_idx)
                        all_passed = False
                else:
                    print(f"  ❌ 无法解析 Tester 输出，标记为失败")
                    task_state["test_passed"] = False
                    tasks_need_rework.append(task_idx)
                    all_passed = False
            except Exception as e:
                print(f"  ❌ 解析测试结果失败: {e}")
                task_state["test_passed"] = False
                tasks_need_rework.append(task_idx)
                all_passed = False

        return {
            "task_states": task_states,
            "_test_passed": all_passed,
            "_tasks_need_rework": tasks_need_rework
        }

    def rework_task_node(self, state: ExecutorState) -> dict:
        """返工节点"""
        task_states = state.get("task_states", {})
        tasks_to_rework = state.get("_tasks_need_rework", [])

        if not tasks_to_rework:
            return {}

        print(f"\n🔧 返工 {len(tasks_to_rework)} 个任务...")

        reworked_tasks = []
        failed_tasks = state.get("failed_tasks", [])

        for task_idx in tasks_to_rework:
            task_state = task_states[task_idx]
            retry_count = task_state.get("retry_count", 0)
            max_retries = state.get("max_retries", 3)

            if retry_count >= max_retries:
                print(f"  ❌ 任务 {task_state['task_id']} 达到最大重试次数 ({max_retries})")
                failed_tasks.append(task_idx)

                if task_state.get("commit_hash"):
                    print(f"  🔙 回滚提交: {task_state['commit_hash'][:8]}")
                    self.git_manager.switch_branch(task_state["branch_name"])
                    self.git_manager.rollback("HEAD~1", "hard")
            else:
                print(f"  🔄 任务 {task_state['task_id']} 第 {retry_count} 次返工")
                reworked_tasks.append(task_idx)

                if task_state.get("commit_hash"):
                    print(f"  🔙 回滚提交: {task_state['commit_hash'][:8]}")
                    self.git_manager.switch_branch(task_state["branch_name"])
                    self.git_manager.rollback("HEAD~1", "hard")

        return {
            "task_states": task_states,
            "active_tasks": reworked_tasks,
            "failed_tasks": failed_tasks,
            "_tasks_need_rework": []
        }

    def merge_branches_node(self, state: ExecutorState) -> dict:
        """合并所有成功的特性分支到主分支"""
        task_states = state.get("task_states", {})
        completed_tasks = state.get("completed_tasks", [])

        print(f"\n🔀 合并 {len(completed_tasks)} 个分支到主分支...")

        main_branch = self.git_manager.get_status().branch
        if main_branch.startswith("feature/"):
            for branch_name in ["main", "master"]:
                check = subprocess.run(
                    ["git", "-C", str(self.project_root), "branch", "--list", branch_name],
                    capture_output=True, text=True
                )
                if branch_name in check.stdout:
                    self.git_manager.switch_branch(branch_name)
                    main_branch = branch_name
                    break

        merged_successfully = []
        merge_conflicts = []

        for task_idx in completed_tasks:
            task_state = task_states[task_idx]
            branch_name = task_state.get("branch_name", "")

            if not branch_name:
                continue

            print(f"  🔀 合并 {branch_name}...")

            merge_result = self.git_manager.merge_branch(
                branch=branch_name,
                into_branch=main_branch,
                no_ff=True,
                commit_message=f"feat({task_state['task_id']}): Merge {task_state['title']}"
            )

            if merge_result.success:
                print(f"  ✅ 合并成功")
                merged_successfully.append(task_idx)
            else:
                if merge_result.conflicts:
                    print(f"  ❌ 合并冲突: {merge_result.conflicts}")
                    merge_conflicts.append({
                        "task_idx": task_idx,
                        "branch": branch_name,
                        "conflicts": merge_result.conflicts
                    })
                    self.git_manager.abort_merge()
                else:
                    print(f"  ❌ 合并失败: {merge_result.message}")

        return {
            "final_summary": f"成功合并 {len(merged_successfully)} 个分支",
            "_merge_conflicts": merge_conflicts
        }

    def summarize_node(self, state: ExecutorState) -> dict:
        """总结节点"""
        print(f"\n📊 生成最终总结...")

        task_states = state.get("task_states", {})
        completed_tasks = state.get("completed_tasks", [])
        failed_tasks = state.get("failed_tasks", [])

        summary = f"""
## 🎉 任务执行完成

**总任务数**: {len(task_states)}
**成功完成**: {len(completed_tasks)}
**失败任务**: {len(failed_tasks)}
**并行度**: {state.get('parallel_limit', 3)}

### 任务执行情况:
"""

        for i, (idx, task_state) in enumerate(sorted(task_states.items()), 1):
            status = "✅" if idx in completed_tasks else "❌"
            branch = task_state.get("branch_name", "N/A")
            commit = task_state.get("commit_hash", "N/A")
            commit_short = commit[:8] if commit and commit != "N/A" else "N/A"
            test_status = "✅" if task_state.get("test_passed") else "❌"

            summary += f"\n{i}. {status} {task_state.get('title', idx)}"
            summary += f"\n   - 分支: `{branch}`"
            summary += f"\n   - 提交: `{commit_short}`"
            summary += f"\n   - 测试: {test_status}"
            if task_state.get("retry_count", 0) > 0:
                summary += f"\n   - 重试次数: {task_state['retry_count']}"

        conflicts = state.get("_merge_conflicts", [])
        if conflicts:
            summary += f"\n\n## ⚠️  合并冲突\n"
            for conflict in conflicts:
                summary += f"- {conflict['branch']}: {conflict['conflicts']}\n"

        summary += "\n\n所有任务处理完成！"

        print(summary)

        return {"final_summary": summary}

    def archive_finalize_node(self, state: ExecutorState) -> dict:
        """归档最终化节点 (HC-5)"""
        print(f"\n📁 归档最终化: 统计归档结果...")

        remaining_files = self.archiver.get_all_task_files()
        for rf in remaining_files:
            task_id = rf.stem
            self.archiver.archive_failure(task_id)
            print(f"   ⚠️  未执行: {rf.name} → failure/")

        summary = self.archiver.finalize()

        archive_summary = (
            f"\n\n## 📁 归档统计\n"
            f"- 成功: {summary['success_count']}\n"
            f"- 失败: {summary['failure_count']}\n"
            f"- 未执行: {summary['unfinished_count']}\n"
            f"- 归档目录: {summary['archive_dir']}"
        )

        return {"final_summary": state.get("final_summary", "") + archive_summary}

    # ==================== 路由函数 ====================

    def route_after_execute(self, state: ExecutorState) -> Literal["test", "done"]:
        """执行后路由"""
        active_tasks = state.get("active_tasks", [])
        completed_tasks = state.get("completed_tasks", [])
        failed_tasks = state.get("failed_tasks", [])
        task_states = state.get("task_states", {})

        all_processed = len(completed_tasks) + len(failed_tasks) >= len(task_states)

        if all_processed and not active_tasks:
            return "done"
        return "test"

    def route_after_test(self, state: ExecutorState) -> Literal["rework", "merge"]:
        """测试后路由"""
        tasks_need_rework = state.get("_tasks_need_rework", [])
        active_tasks = state.get("active_tasks", [])

        if tasks_need_rework or active_tasks:
            return "rework"
        return "merge"

    # ==================== 辅助方法 ====================

    def _run_test_command(self, test_command: str, working_dir: Optional[str] = None) -> tuple[bool, str]:
        """运行测试命令"""
        work_dir = Path(working_dir) if working_dir else Path(self.project_root)

        try:
            result = subprocess.run(
                test_command,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                shell=True
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "测试执行超时 (120 秒)"
        except Exception as e:
            return False, f"测试执行异常: {str(e)}"

    # ==================== 执行入口 ====================

    def execute(self) -> dict:
        """
        执行任务

        Returns:
            最终状态
        """
        initial_state = ExecutorState(
            parallel_limit=self.parallel_limit,
            max_retries=3,
            active_tasks=[],
            completed_tasks=[],
            failed_tasks=[],
            task_states={},
            archive_dir=None,
            final_summary=None,
            error=None
        )

        final_state = self.workflow.invoke(initial_state)

        # 清理：切换回主分支
        try:
            self.git_manager.switch_branch("main")
        except:
            try:
                self.git_manager.switch_branch("master")
            except:
                pass

        return final_state
