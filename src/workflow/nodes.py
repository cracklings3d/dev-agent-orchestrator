"""
LangGraph Send API 全并行工作流 V2 - 节点实现

包含两类节点:
1. 主图节点: load_tasks, dispatch_tasks, wait_for_all, merge_branches, summarize, archive_finalize
2. 子图节点: execute_single_task, test_single_task, rework_single_task

所有节点作为 WorkflowNodes 类方法实现，通过 self 访问共享依赖。
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Literal, Optional

from langgraph.types import Send, Command

from src.agents.agent_types import DeveloperAgent, TesterAgent
from src.agents.base_agent import AgentContext
from src.qwen_code_adapter import QwenCodeCLI, QwenCodeResult
from src.git_manager import GitManager
from src.task_archiver import TaskArchiver
from src.workflow.state import (
    ExecutorState,
    TaskState,
    parse_acceptance_criteria,
    parse_test_requirements,
)

logger = logging.getLogger(__name__)


class WorkflowNodes:
    """
    工作流节点集合

    所有节点作为类方法实现，通过 self 访问共享依赖 (developer, tester, git_manager 等)。
    这避免了在每个节点中通过 config["configurable"] 传递依赖的复杂性。
    """

    def __init__(
        self,
        developer: DeveloperAgent,
        tester: TesterAgent,
        git_manager: GitManager,
        archiver: TaskArchiver,
        project_root: str,
        base_qwen_cli: QwenCodeCLI,
    ):
        self.developer = developer
        self.tester = tester
        self.git_manager = git_manager
        self.archiver = archiver
        self.project_root = project_root
        self.base_qwen_cli = base_qwen_cli

    # ==================== 主图节点 ====================

    def load_tasks_node(self, state: ExecutorState) -> dict:
        """
        从 .qwen/tasks/ 读取所有 TASK-*.md 文件。
        解析每个文件的元数据，填充 task_states 和 pending_indices。
        """
        tasks_dir = Path(self.project_root) / ".qwen" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[V2] 加载任务文件 from {tasks_dir}...")

        task_files = sorted(tasks_dir.glob("TASK-*.md"))

        if not task_files:
            print("   未找到任务文件，请确保 .qwen/tasks/ 目录下有 TASK-*.md 文件")
            return {
                "error": f"未找到任务文件! 请确保 {tasks_dir} 目录下有 TASK-*.md 文件",
                "task_states": {},
                "pending_indices": [],
                "running_indices": [],
                "completed_indices": [],
                "failed_indices": [],
            }

        print(f"   发现 {len(task_files)} 个任务文件:")

        task_states: dict[int, TaskState] = {}
        for i, task_file in enumerate(task_files):
            print(f"   [{i}] {task_file.name}")

            content = task_file.read_text(encoding="utf-8")
            task_id = task_file.stem  # 如 TASK-001

            # 提取标题
            title = task_id
            for line in content.split("\n")[:5]:
                if line.startswith("# Task:"):
                    title = line.replace("# Task:", "").strip()
                    break

            # HC-3: 解析 Markdown 中的验收标准和测试要求
            acceptance_criteria = parse_acceptance_criteria(content)
            test_requirements = parse_test_requirements(content)

            task_state: TaskState = {
                "task_id": task_id,
                "title": title,
                "objective": content,  # HC-3: 完整 Markdown 内容
                "files_to_modify": [],
                "files_to_create": [],
                "forbidden_files": [],
                "acceptance_criteria": acceptance_criteria,
                "test_requirements": test_requirements,
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
            task_states[i] = task_state

        pending_indices = list(range(len(task_files)))

        print(f"\n   验收标准解析: {sum(1 for ts in task_states.values() if ts.get('acceptance_criteria'))} 个任务包含验收标准")
        print(f"   测试要求解析: {sum(1 for ts in task_states.values() if ts.get('test_requirements'))} 个任务包含测试要求")
        print(f"   待执行任务: {len(pending_indices)} 个")

        return {
            "task_states": task_states,
            "pending_indices": pending_indices,
            "running_indices": [],
            "completed_indices": [],
            "failed_indices": [],
        }

    def dispatch_tasks_node(self, state: ExecutorState) -> dict:
        """
        将所有 pending 任务加入执行队列。
        实际的 Send 扇出由 add_conditional_edges 中的 dispatch_router_node 完成。
        """
        pending = state.get("pending_indices", [])
        if not pending:
            return {}

        print(f"\n[V2] 分发 {len(pending)} 个任务到并行执行队列...")

        return {
            "pending_indices": [],
            "running_indices": pending,
        }

    def dispatch_router_node(self, state: ExecutorState) -> list:
        """
        路由函数: 为每个 pending task 创建 Send 对象。
        用于 add_conditional_edges("dispatch_tasks", dispatch_router_node, ["task_subgraph"])

        LangGraph Send API: 返回 [Send(...), Send(...)] 实现动态扇出。
        每个 Send 创建一个独立的子图实例，真正并行执行。
        """
        pending = state.get("pending_indices", [])
        if not pending:
            return []

        print(f"   扇出 {len(pending)} 个并行任务实例...")
        return [Send("task_subgraph", {"task_idx": idx}) for idx in pending]

    def wait_for_all_node(self, state: ExecutorState) -> dict:
        """
        等待所有任务完成。

        在 Send API 模型中，LangGraph 自动等待所有并行分支完成后才进入下一节点。
        此节点负责将 completed_indices 和 failed_indices 与所有 task_states 对比，
        统计最终结果。
        """
        task_states = state.get("task_states", {})
        completed = state.get("completed_indices", [])
        failed = state.get("failed_indices", [])

        total = len(task_states)
        accounted = len(completed) + len(failed)

        print(f"\n[V2] 所有并行任务执行完毕...")
        print(f"   总任务: {total}, 已完成: {len(completed)}, 已失败: {len(failed)}, 未计入: {total - accounted}")

        # 检查是否有遗漏的任务状态（理论上不应发生）
        all_indices = set(task_states.keys())
        accounted_indices = set(completed) | set(failed)
        missing = all_indices - accounted_indices

        if missing:
            print(f"   警告: 以下任务索引未计入: {sorted(missing)}")
            for idx in sorted(missing):
                ts = task_states[idx]
                # 将未完成的任务归为失败
                failed.append(idx)
                print(f"   标记 {ts.get('task_id', idx)} 为失败")

        return {
            "completed_indices": completed,
            "failed_indices": failed,
        }

    def merge_branches_node(self, state: ExecutorState) -> dict:
        """
        Squash 合并所有 completed_indices 对应的特性分支到主分支。
        只合并 test_passed=True 的任务。
        """
        task_states = state.get("task_states", {})
        completed_indices = state.get("completed_indices", [])

        print(f"\n[V2] Squash 合并 {len(completed_indices)} 个已通过分支到主分支...")

        # 确保在主分支上
        current_branch = self.git_manager.get_status().branch
        if current_branch.startswith("feature/"):
            for branch_name in ["main", "master"]:
                result = subprocess.run(
                    ["git", "-C", str(self.project_root), "branch", "--list", branch_name],
                    capture_output=True, text=True
                )
                if branch_name in result.stdout:
                    self.git_manager.switch_branch(branch_name)
                    current_branch = branch_name
                    break

        merged_count = 0
        deleted_count = 0
        merge_conflicts: list[dict] = []

        for task_idx in completed_indices:
            task_state = task_states[task_idx]
            branch_name = task_state.get("branch_name", "")

            if not branch_name:
                continue

            # 检查测试是否通过
            if not task_state.get("test_passed", False):
                print(f"   跳过 {task_state.get('task_id', task_idx)}: 测试未通过")
                continue

            print(f"   Squash 合并 {branch_name} ({task_state.get('task_id', task_idx)})...")

            merge_result = self.git_manager.squash_merge(
                branch=branch_name,
                into_branch=current_branch,
                commit_message=f"feat({task_state.get('task_id', '')}): {task_state.get('title', '')}"
            )

            if merge_result.success:
                print(f"   合并成功")
                merged_count += 1
                # 删除已合并的分支，减少 .git 体积
                if self.git_manager.delete_branch(branch_name):
                    deleted_count += 1
            else:
                if merge_result.conflicts:
                    print(f"   合并冲突: {merge_result.conflicts}")
                    merge_conflicts.append({
                        "task_idx": task_idx,
                        "branch": branch_name,
                        "conflicts": merge_result.conflicts,
                    })
                    self.git_manager.abort_merge()
                else:
                    print(f"   合并失败: {merge_result.message}")

        print(f"   合并了 {merged_count} 个分支，删除了 {deleted_count} 个旧分支")

        return {
            "final_summary": f"成功 Squash 合并 {merged_count} 个分支，删除 {deleted_count} 个旧分支",
            "_merge_conflicts": merge_conflicts,
        }

    def summarize_node(self, state: ExecutorState) -> dict:
        """生成最终执行总结。"""
        print(f"\n[V2] 生成最终总结...")

        task_states = state.get("task_states", {})
        completed = state.get("completed_indices", [])
        failed = state.get("failed_indices", [])

        summary = f"""
## 任务执行完成 (V2 Send API 全并行)

**总任务数**: {len(task_states)}
**成功完成**: {len(completed)}
**失败任务**: {len(failed)}

### 任务执行情况:
"""

        for idx, task_state in sorted(task_states.items()):
            status = "" if idx in completed else ""
            is_completed = idx in completed
            status_icon = "✅" if is_completed else "❌"
            branch = task_state.get("branch_name", "N/A")
            commit = task_state.get("commit_hash")
            commit_short = commit[:8] if commit else "N/A"
            test_status = "✅" if task_state.get("test_passed") else "❌"

            summary += f"\n{idx + 1}. {status_icon} {task_state.get('title', idx)}"
            summary += f"\n   - 分支: `{branch}`"
            summary += f"\n   - 提交: `{commit_short}`"
            summary += f"\n   - 测试: {test_status}"
            if task_state.get("retry_count", 0) > 0:
                summary += f"\n   - 重试次数: {task_state['retry_count']}"

        conflicts = state.get("_merge_conflicts", [])
        if conflicts:
            summary += f"\n\n## 合并冲突\n"
            for conflict in conflicts:
                summary += f"- {conflict['branch']}: {conflict['conflicts']}\n"

        summary += "\n\n所有任务处理完成！"

        print(summary)

        return {"final_summary": summary}

    def archive_finalize_node(self, state: ExecutorState) -> dict:
        """最终归档（HC-5）。"""
        print(f"\n[V2] 最终归档...")

        # 处理 unfinished/ 中剩余的任务文件（未执行或中断的任务）
        remaining_files = self.archiver.get_all_task_files()
        for rf in remaining_files:
            task_id = rf.stem
            self.archiver.archive_failure(task_id)
            print(f"   未执行: {rf.name} → failure/")

        summary = self.archiver.finalize()

        archive_summary = (
            f"\n\n## 归档统计\n"
            f"- 成功: {summary['success_count']}\n"
            f"- 失败: {summary['failure_count']}\n"
            f"- 未执行: {summary['unfinished_count']}\n"
            f"- 归档目录: {summary['archive_dir']}"
        )

        current_summary = state.get("final_summary", "")
        return {"final_summary": current_summary + archive_summary}

    # ==================== 子图节点 (每个任务独立并行) ====================

    def execute_single_task(self, state: ExecutorState) -> dict:
        """
        执行单个任务（Developer Agent）。

        此节点在子图中被调用，每个 Send 实例有独立的状态副本。
        通过 state 中携带的 task_idx 读取对应的 TaskState。
        """
        task_idx = state.get("task_idx")
        if task_idx is None:
            return {"success": False, "output": "task_idx 未设置"}

        task_state: TaskState = state.get("task_states", {}).get(task_idx, {})
        task_id = task_state.get("task_id", f"TASK-{task_idx}")
        title = task_state.get("title", task_id)

        print(f"\n[V2:子图] 执行任务 [{task_idx}]: {title}")

        # 1. 创建特性分支
        branch_name = f"feature/{task_id.lower()}"
        print(f"   创建分支: {branch_name}")
        created_branch = self.git_manager.create_feature_branch(task_id)
        if not created_branch:
            print(f"   分支创建失败，尝试切换...")
            # 如果分支已存在，切换过去
            self.git_manager.switch_branch(branch_name, create_if_not_exists=False)

        # 2. 构建 AgentContext
        # 注意: 将 notes 中的失败原因注入（返工场景）
        notes = task_state.get("notes", [])

        context = AgentContext(
            task_id=task_id,
            task_title=title,
            task_objective=task_state.get("objective", ""),  # HC-3: 完整 Markdown
            files_to_modify=task_state.get("files_to_modify", []),
            files_to_create=task_state.get("files_to_create", []),
            forbidden_files=task_state.get("forbidden_files", []),
            acceptance_criteria=task_state.get("acceptance_criteria", []),
            test_requirements=task_state.get("test_requirements"),
            constraints=task_state.get("constraints", []),
            references=task_state.get("references", []),
            notes=notes,
        )

        # 3. 调用 Developer Agent
        print(f"   调用 Developer Agent...")
        result = self.developer.execute(context, self.project_root)

        # 4. 提交更改
        commit_hash = None
        if result.success:
            print(f"   提交更改...")
            commit_result = self.git_manager.submit_task_work(
                task_id=task_id,
                task_title=title,
                agent_name="Developer Agent (V2)"
            )

            if commit_result.success:
                commit_hash = commit_result.commit_hash
                print(f"   提交成功: {commit_hash[:8]}")
            else:
                print(f"   提交失败: {commit_result.error}")

        # 5. 更新 TaskState
        task_state["success"] = result.success
        task_state["output"] = result.output
        task_state["files_changed"] = result.files_changed
        task_state["branch_name"] = branch_name
        task_state["commit_hash"] = commit_hash

        # 6. 更新全局 task_states 字典
        all_task_states = state.get("task_states", {})
        all_task_states[task_idx] = task_state

        # 从 running_indices 移除
        running = state.get("running_indices", [])
        if task_idx in running:
            running.remove(task_idx)

        print(f"   执行{'成功' if result.success else '失败'}")

        return {
            "task_states": all_task_states,
            "running_indices": running,
            "success": result.success,
            "output": result.output,
            "files_changed": result.files_changed,
            "branch_name": branch_name,
            "commit_hash": commit_hash,
        }

    def test_single_task(self, state: ExecutorState) -> Command:
        """
        测试单个任务（Tester Agent）。

        使用 Command API 决定下一步:
        - 测试通过 → goto="task_done"
        - 测试失败 + retry < max → goto="rework_single_task"
        - 测试失败 + retry >= max → goto="task_failed"
        """
        task_idx = state.get("task_idx")
        if task_idx is None:
            return Command(
                update={"test_result": "task_idx 未设置", "test_passed": False},
                goto="task_failed",
            )

        task_state: TaskState = state.get("task_states", {}).get(task_idx, {})
        task_id = task_state.get("task_id", f"TASK-{task_idx}")
        title = task_state.get("title", task_id)
        max_retries = state.get("max_retries", 3)

        print(f"\n[V2:子图] 测试任务 [{task_idx}]: {title}")

        # 1. 运行自动化测试 (如果有 test_requirements)
        test_requirements = task_state.get("test_requirements")
        automated_test_passed = True
        auto_test_output = ""

        if test_requirements and test_requirements.get("need_tests"):
            test_command = test_requirements.get("test_command")
            if test_command:
                print(f"   运行自动化测试: {test_command}")
                passed, output = self._run_test_command(test_command)
                automated_test_passed = passed
                auto_test_output = output

                if not passed:
                    print(f"   自动化测试失败")
        else:
            print(f"   跳过自动化测试（无测试要求）")

        # 2. AI 代码审查 (HC-4: Tester Agent)
        context = AgentContext(
            task_id=task_id,
            task_title=f"测试: {title}",
            task_objective=f"验证 {title} 是否符合验收标准",
            files_to_modify=task_state.get("files_changed", []),
            files_to_create=[],
            forbidden_files=[],
            acceptance_criteria=task_state.get("acceptance_criteria", []),
            test_requirements=test_requirements,
            constraints=["客观评估，不要放水", "必须测试边界条件和退化场景"],
            references=[],
            notes=[],
        )

        print(f"   调用 Tester Agent 进行代码审查...")
        result = self.tester.execute(context, self.project_root)

        # 3. 解析 Tester 的 JSON 输出
        test_passed = False
        test_result_summary = ""

        if automated_test_passed:
            try:
                json_start = result.output.find("{")
                json_end = result.output.rfind("}") + 1

                if json_start != -1 and json_end != 0:
                    test_data = json.loads(result.output[json_start:json_end])
                    recommendation = test_data.get("recommendation", "approve")
                    test_result_summary = test_data.get("summary", "")

                    if recommendation == "approve":
                        print(f"   AI 审查通过")
                        test_passed = True
                    else:
                        print(f"   AI 审查未通过: {test_result_summary}")
                        test_passed = False
                        test_result_summary = f"AI 审查未通过: {test_result_summary}"
                else:
                    print(f"   无法解析 Tester 输出，标记为失败")
                    test_result_summary = "无法解析 Tester JSON 输出"
            except Exception as e:
                print(f"   解析测试结果失败: {e}")
                test_result_summary = f"解析失败: {str(e)}"
        else:
            test_result_summary = f"自动化测试失败:\n{auto_test_output}"

        # 4. 更新 TaskState
        retry_count = task_state.get("retry_count", 0)
        task_state["test_result"] = test_result_summary
        task_state["test_passed"] = test_passed

        all_task_states = state.get("task_states", {})
        all_task_states[task_idx] = task_state

        # 5. 使用 Command 决定下一步
        if test_passed:
            # 测试通过 → 标记为完成
            completed = state.get("completed_indices", [])
            if task_idx not in completed:
                completed.append(task_idx)

            print(f"   任务 [{task_idx}] 测试通过")
            return Command(
                update={
                    "task_states": all_task_states,
                    "test_result": test_result_summary,
                    "test_passed": True,
                    "completed_indices": completed,
                },
                goto="task_done",
            )
        else:
            # 测试失败
            new_retry_count = retry_count + 1
            task_state["retry_count"] = new_retry_count

            if new_retry_count < max_retries:
                print(f"   任务 [{task_idx}] 测试失败，第 {new_retry_count} 次返工 (上限 {max_retries})")
                return Command(
                    update={
                        "task_states": all_task_states,
                        "test_result": test_result_summary,
                        "test_passed": False,
                        "retry_count": new_retry_count,
                    },
                    goto="rework_single_task",
                )
            else:
                # 达到最大重试次数 → 标记为失败
                failed = state.get("failed_indices", [])
                if task_idx not in failed:
                    failed.append(task_idx)

                print(f"   任务 [{task_idx}] 测试失败，达到最大重试次数 ({max_retries})")
                return Command(
                    update={
                        "task_states": all_task_states,
                        "test_result": test_result_summary,
                        "test_passed": False,
                        "retry_count": new_retry_count,
                        "failed_indices": failed,
                    },
                    goto="task_failed",
                )

    def rework_single_task(self, state: ExecutorState) -> dict:
        """
        返工单个任务。
        1. 回滚提交
        2. 注入失败原因到 notes
        3. 递增 retry_count
        4. 重置状态
        5. 返回 goto="execute_single_task"
        """
        task_idx = state.get("task_idx")
        if task_idx is None:
            return {}

        task_state: TaskState = state.get("task_states", {}).get(task_idx, {})
        task_id = task_state.get("task_id", f"TASK-{task_idx}")
        title = task_state.get("title", task_id)
        test_result = state.get("test_result", "未知")
        retry_count = task_state.get("retry_count", 0)

        print(f"\n[V2:子图] 返工任务 [{task_idx}]: {title} (第 {retry_count} 次)")

        # 1. 回滚提交
        commit_hash = task_state.get("commit_hash")
        branch_name = task_state.get("branch_name", "")

        if commit_hash and branch_name:
            print(f"   回滚提交: {commit_hash[:8]}")
            try:
                self.git_manager.switch_branch(branch_name)
                self.git_manager.rollback("HEAD~1", "hard")
                print(f"   回滚成功")
            except Exception as e:
                print(f"   回滚失败: {e}")

        # 2. 注入失败原因到 notes
        notes = task_state.get("notes", [])
        notes.append(f"[返工第 {retry_count} 次] 上次失败原因: {test_result}")

        # 3. 重置状态
        task_state["notes"] = notes
        task_state["success"] = False
        task_state["test_passed"] = False
        task_state["test_result"] = None
        task_state["commit_hash"] = None

        # 4. 更新全局 task_states
        all_task_states = state.get("task_states", {})
        all_task_states[task_idx] = task_state

        print(f"   返工准备完成，重新执行...")

        return Command(
            update={
                "task_states": all_task_states,
                "success": False,
                "test_passed": False,
                "test_result": None,
                "commit_hash": None,
            },
            goto="execute_single_task",
        )

    # ==================== 辅助方法 ====================

    def _run_test_command(self, test_command: str, working_dir: Optional[str] = None) -> tuple[bool, str]:
        """
        运行测试命令

        Args:
            test_command: 测试命令
            working_dir: 工作目录

        Returns:
            (是否通过, 输出内容)
        """
        work_dir = Path(working_dir) if working_dir else Path(self.project_root)

        try:
            result = subprocess.run(
                test_command,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=120,  # 120 秒超时
                encoding="utf-8",
                shell=True,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "测试执行超时 (120 秒)"
        except Exception as e:
            return False, f"测试执行异常: {str(e)}"
