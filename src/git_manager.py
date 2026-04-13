"""
Git 自动化管理器
负责分支管理、提交、回滚、合并等操作
用于 Orchestrator 的自动化开发流程
"""

import subprocess
import logging
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git 状态快照"""
    branch: str
    is_clean: bool
    modified_files: list[str]
    staged_files: list[str]
    untracked_files: list[str]


@dataclass
class CommitResult:
    """提交结果"""
    success: bool
    commit_hash: Optional[str]
    message: str
    files_committed: list[str]
    error: Optional[str] = None


@dataclass
class MergeResult:
    """合并结果"""
    success: bool
    branch: str
    conflicts: list[str]
    message: str


class GitManager:
    """
    Git 自动化管理器
    
    提供分支创建、提交、回滚、合并等操作的自动化封装
    用于 Orchestrator 控制多个开发 Agent 的工作流
    """

    def __init__(self, repo_path: str):
        """
        初始化 Git 管理器

        Args:
            repo_path: Git 仓库根目录路径
        """
        self.repo_path = Path(repo_path)
        self._verify_git_repo()
        
        # 线程锁:保证 Git 操作的原子性(防止并发 checkout/commit/merge 冲突)
        self._lock = threading.RLock()
        logger.info(f"GitManager 初始化: {repo_path} (线程安全模式)")
    
    def _verify_git_repo(self):
        """验证是否是有效的 Git 仓库"""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise ValueError(f"不是有效的 Git 仓库: {self.repo_path}")

    def _run_git(
        self,
        *args: str,
        check: bool = True,
        timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """
        执行 Git 命令 (线程安全)

        Args:
            *args: Git 命令参数
            check: 是否检查返回码
            timeout: 超时时间（秒）

        Returns:
            subprocess.CompletedProcess: 命令执行结果
        """
        cmd = ["git", "-C", str(self.repo_path)] + list(args)
        logger.debug(f"执行 Git命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8"
            )

            if check and result.returncode != 0:
                logger.error(f"Git 命令失败: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode,
                    cmd,
                    result.stdout,
                    result.stderr
                )

            return result

        except subprocess.TimeoutExpired:
            logger.error(f"Git 命令超时: {' '.join(cmd)}")
            raise

    def get_status(self) -> GitStatus:
        """
        获取当前 Git 状态

        Returns:
            GitStatus: Git 状态快照
        """
        # 获取当前分支
        branch_result = self._run_git("branch", "--show-current")
        branch = branch_result.stdout.strip()

        # 获取精简状态
        status_result = self._run_git("status", "--porcelain")
        lines = status_result.stdout.strip().split("\n") if status_result.stdout.strip() else []

        modified = []
        staged = []
        untracked = []

        for line in lines:
            if not line.strip():
                continue
            status_code = line[:2]
            file_path = line[3:].strip()

            if status_code[0] != ' ' and status_code[0] != '?':
                staged.append(file_path)
            if status_code[1] != ' ' and status_code[1] != '?':
                modified.append(file_path)
            if status_code == "??":
                untracked.append(file_path)

        is_clean = len(modified) == 0 and len(staged) == 0 and len(untracked) == 0

        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            modified_files=modified,
            staged_files=staged,
            untracked_files=untracked
        )

    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> bool:
        """
        创建新分支 (线程安全)

        Args:
            branch_name: 新分支名称
            from_branch: 基于的分支（默认当前分支）

        Returns:
            bool: 是否成功
        """
        with self._lock:
            return self._create_branch_unsafe(branch_name, from_branch)
    
    def _create_branch_unsafe(self, branch_name: str, from_branch: Optional[str] = None) -> bool:
        """内部方法:创建分支(假设已持有锁)"""
        try:
            if from_branch:
                # 切换到基础分支
                self._run_git("checkout", from_branch)

            # 创建并切换到新分支
            self._run_git("checkout", "-b", branch_name)
            logger.info(f"创建分支: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"创建分支失败: {e.stderr}")
            return False

    def switch_branch(self, branch_name: str, create_if_not_exists: bool = False) -> bool:
        """
        切换分支 (线程安全)

        Args:
            branch_name: 分支名称
            create_if_not_exists: 如果不存在是否创建

        Returns:
            bool: 是否成功
        """
        with self._lock:
            return self._switch_branch_unsafe(branch_name, create_if_not_exists)
    
    def _switch_branch_unsafe(self, branch_name: str, create_if_not_exists: bool = False) -> bool:
        """内部方法:切换分支(假设已持有锁)"""
        try:
            if create_if_not_exists:
                self._run_git("checkout", "-b", branch_name)
            else:
                self._run_git("checkout", branch_name)
            logger.info(f"切换到分支: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"切换分支失败: {e.stderr}")
            return False

    def add_files(self, files: list[str]) -> bool:
        """
        添加文件到暂存区

        Args:
            files: 文件路径列表

        Returns:
            bool: 是否成功
        """
        try:
            if not files:
                return True
            
            self._run_git("add", *files)
            logger.info(f"添加 {len(files)} 个文件到暂存区")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"添加文件失败: {e.stderr}")
            return False

    def add_all(self) -> bool:
        """
        添加所有更改到暂存区

        Returns:
            bool: 是否成功
        """
        try:
            self._run_git("add", "-A")
            logger.info("添加所有更改到暂存区")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"添加所有更改失败: {e.stderr}")
            return False

    def commit(
        self,
        message: str,
        files: Optional[list[str]] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> CommitResult:
        """
        提交更改 (线程安全)

        Args:
            message: 提交消息
            files: 要提交的文件（None 表示提交所有暂存的文件）
            author_name: 作者名称
            author_email: 作者邮箱

        Returns:
            CommitResult: 提交结果
        """
        with self._lock:
            return self._commit_unsafe(message, files, author_name, author_email)
    
    def _commit_unsafe(
        self,
        message: str,
        files: Optional[list[str]] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> CommitResult:
        """内部方法:提交更改(假设已持有锁)"""
        try:
            # 如果指定了文件,先添加
            if files:
                self.add_files(files)

            # 构建提交命令
            cmd = ["commit", "-m", message]

            if author_name:
                cmd.extend(["--author", f"{author_name} <{author_email or 'agent@orchestrator.local'}>"])

            result = self._run_git(*cmd)

            # 获取提交哈希
            commit_hash = self._run_git("rev-parse", "HEAD").stdout.strip()

            # 获取提交的文件列表
            diff_result = self._run_git("diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash)
            files_committed = diff_result.stdout.strip().split("\n") if diff_result.stdout.strip() else []

            logger.info(f"提交成功: {commit_hash[:8]} - {message}")

            return CommitResult(
                success=True,
                commit_hash=commit_hash,
                message=message,
                files_committed=files_committed
            )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"提交失败: {error_msg}")

            return CommitResult(
                success=False,
                commit_hash=None,
                message=message,
                files_committed=[],
                error=error_msg
            )

    def commit_with_retry(
        self,
        message: str,
        files: Optional[list[str]] = None,
        max_retries: int = 3
    ) -> CommitResult:
        """
        带重试的提交

        Args:
            message: 提交消息
            files: 文件列表
            max_retries: 最大重试次数

        Returns:
            CommitResult: 提交结果
        """
        for attempt in range(max_retries):
            result = self.commit(message, files)
            if result.success:
                return result
            
            logger.warning(f"提交失败，第 {attempt + 1}/{max_retries} 次重试")
        
        return result

    def rollback(self, target: str, mode: str = "soft") -> bool:
        """
        回滚提交 (线程安全)

        Args:
            target: 回滚目标（commit hash 或相对位置如 HEAD~1）
            mode: 回滚模式 (soft: 保留更改在暂存区, mixed: 保留更改在工作区, hard: 丢弃所有更改)

        Returns:
            bool: 是否成功
        """
        with self._lock:
            return self._rollback_unsafe(target, mode)
    
    def _rollback_unsafe(self, target: str, mode: str = "soft") -> bool:
        """内部方法:回滚提交(假设已持有锁)"""
        try:
            self._run_git("reset", f"--{mode}", target)
            logger.info(f"回滚到 {target} (模式: {mode})")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"回滚失败: {e.stderr}")
            return False

    def revert_commit(self, commit_hash: str) -> bool:
        """
        撤销提交（创建新的反向提交）

        Args:
            commit_hash: 要撤销的提交哈希

        Returns:
            bool: 是否成功
        """
        try:
            self._run_git("revert", "--no-edit", commit_hash)
            logger.info(f"撤销提交: {commit_hash}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"撤销提交失败: {e.stderr}")
            return False

    def merge_branch(
        self,
        branch: str,
        into_branch: Optional[str] = None,
        no_ff: bool = True,
        commit_message: Optional[str] = None
    ) -> MergeResult:
        """
        合并分支 (线程安全)

        Args:
            branch: 要合并的分支
            into_branch: 合并到哪个分支（默认当前分支）
            no_ff: 是否使用 --no-ff 模式
            commit_message: 自定义提交消息

        Returns:
            MergeResult: 合并结果
        """
        with self._lock:
            return self._merge_branch_unsafe(branch, into_branch, no_ff, commit_message)
    
    def _merge_branch_unsafe(
        self,
        branch: str,
        into_branch: Optional[str] = None,
        no_ff: bool = True,
        commit_message: Optional[str] = None
    ) -> MergeResult:
        """内部方法:合并分支(假设已持有锁)"""
        try:
            # 切换到目标分支
            if into_branch:
                self.switch_branch(into_branch)

            # 构建合并命令
            cmd = ["merge"]

            if no_ff:
                cmd.append("--no-ff")
            
            if commit_message:
                cmd.extend(["-m", commit_message])
            
            cmd.append(branch)

            result = self._run_git(*cmd, check=False)

            if result.returncode == 0:
                logger.info(f"成功合并分支: {branch}")
                return MergeResult(
                    success=True,
                    branch=branch,
                    conflicts=[],
                    message=commit_message or f"Merge branch '{branch}'"
                )
            else:
                # 检查是否是冲突导致的失败
                if "CONFLICT" in result.stderr or "CONFLICT" in result.stdout:
                    # 获取冲突文件
                    status_result = self._run_git("diff", "--name-only", "--diff-filter=U")
                    conflicts = status_result.stdout.strip().split("\n") if status_result.stdout.strip() else []
                    
                    logger.warning(f"合并冲突: {conflicts}")
                    return MergeResult(
                        success=False,
                        branch=branch,
                        conflicts=conflicts,
                        message="合并冲突"
                    )
                else:
                    logger.error(f"合并失败: {result.stderr}")
                    return MergeResult(
                        success=False,
                        branch=branch,
                        conflicts=[],
                        message=result.stderr
                    )

        except subprocess.CalledProcessError as e:
            logger.error(f"合并分支失败: {e.stderr}")
            return MergeResult(
                success=False,
                branch=branch,
                conflicts=[],
                message=str(e)
            )

    def abort_merge(self) -> bool:
        """
        中止合并

        Returns:
            bool: 是否成功
        """
        try:
            self._run_git("merge", "--abort")
            logger.info("中止合并")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"中止合并失败: {e.stderr}")
            return False

    def squash_merge(
        self,
        branch: str,
        into_branch: Optional[str] = None,
        commit_message: Optional[str] = None
    ) -> MergeResult:
        """
        Squash 合并分支 (线程安全)

        将目标分支的所有提交压缩为一次提交，保持主干历史干净。

        Args:
            branch: 要合并的分支
            into_branch: 合并到哪个分支（默认当前分支）
            commit_message: 自定义提交消息

        Returns:
            MergeResult: 合并结果
        """
        with self._lock:
            return self._squash_merge_unsafe(branch, into_branch, commit_message)

    def _squash_merge_unsafe(
        self,
        branch: str,
        into_branch: Optional[str] = None,
        commit_message: Optional[str] = None
    ) -> MergeResult:
        """内部方法: squash 合并 (假设已持有锁)"""
        try:
            if into_branch:
                self._switch_branch_unsafe(into_branch)

            cmd = ["merge", "--squash", branch]
            result = self._run_git(*cmd, check=False)

            if result.returncode != 0:
                # 检查是否冲突
                status_result = self._run_git("status", "--porcelain", check=False)
                conflicts = []
                if "both modified" in result.stderr or "both added" in result.stderr:
                    for line in status_result.stdout.strip().split("\n"):
                        if line.startswith("UU") or line.startswith("AA"):
                            conflicts.append(line[3:].strip())

                return MergeResult(
                    success=False,
                    branch=branch,
                    conflicts=conflicts,
                    message="Squash 合并冲突"
                )

            # squash 合并成功，需要手动提交
            commit_cmd = ["commit"]
            if commit_message:
                commit_cmd.extend(["-m", commit_message])

            commit_result = self._run_git(*commit_cmd, check=False)

            if commit_result.returncode != 0:
                return MergeResult(
                    success=False,
                    branch=branch,
                    conflicts=[],
                    message=f"Squash 提交失败: {commit_result.stderr}"
                )

            commit_hash = self._run_git("rev-parse", "HEAD").stdout.strip()
            logger.info(f"Squash 合并成功: {branch} -> {commit_hash[:8]}")

            return MergeResult(
                success=True,
                branch=branch,
                conflicts=[],
                message=commit_message or f"Squash merge '{branch}'"
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Squash 合并分支失败: {e.stderr}")
            return MergeResult(
                success=False,
                branch=branch,
                conflicts=[],
                message=str(e)
            )

    def delete_branch(self, branch_name: str, force: bool = True) -> bool:
        """
        删除分支 (线程安全)

        Args:
            branch_name: 要删除的分支名称
            force: 是否强制删除（忽略未合并警告）

        Returns:
            bool: 是否成功
        """
        with self._lock:
            return self._delete_branch_unsafe(branch_name, force)

    def _delete_branch_unsafe(self, branch_name: str, force: bool = True) -> bool:
        """内部方法: 删除分支 (假设已持有锁)"""
        try:
            flag = "-D" if force else "-d"
            self._run_git("branch", flag, branch_name)
            logger.info(f"删除分支: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"删除分支失败: {e.stderr}")
            return False

    def gc_prune(self) -> bool:
        """
        执行 Git 垃圾回收，立即清理不可达对象。

        用于在所有任务完成后缩减 .git 体积。

        Returns:
            bool: 是否成功
        """
        try:
            self._run_git("gc", "--prune=now", timeout=120)
            logger.info("Git GC 完成 (立即清理不可达对象)")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git GC 失败: {e.stderr}")
            return False

    def create_feature_branch(self, task_id: str) -> Optional[str]:
        """
        为任务创建特性分支

        Args:
            task_id: 任务 ID

        Returns:
            Optional[str]: 分支名称，失败返回 None
        """
        branch_name = f"feature/{task_id.lower()}"
        
        if self.create_branch(branch_name):
            return branch_name
        return None

    def submit_task_work(
        self,
        task_id: str,
        task_title: str,
        files: Optional[list[str]] = None,
        agent_name: str = "Developer Agent"
    ) -> CommitResult:
        """
        提交任务工作成果

        Args:
            task_id: 任务 ID
            task_title: 任务标题
            files: 提交的文件列表
            agent_name: Agent 名称

        Returns:
            CommitResult: 提交结果
        """
        # 构建提交消息
        message = f"feat({task_id}): {task_title}\n\nBy: {agent_name}"

        # 添加所有更改
        if not self.add_all():
            return CommitResult(
                success=False,
                commit_hash=None,
                message=message,
                files_committed=[],
                error="添加文件失败"
            )

        # 提交
        return self.commit_with_retry(message, files)

    def get_diff(self, files: Optional[list[str]] = None) -> str:
        """
        获取差异

        Args:
            files: 文件列表（None 表示所有更改）

        Returns:
            str: 差异内容
        """
        try:
            if files:
                result = self._run_git("diff", "--", *files)
            else:
                result = self._run_git("diff")
            
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"获取差异失败: {e.stderr}")
            return ""

    def get_log(self, count: int = 10) -> list[dict]:
        """
        获取提交历史

        Args:
            count: 获取条数

        Returns:
            list[dict]: 提交历史列表
        """
        try:
            result = self._run_git(
                "log",
                f"-{count}",
                "--pretty=format:%H|%h|%an|%ae|%ai|%s"
            )

            logs = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                
                parts = line.split("|", 5)
                if len(parts) == 6:
                    logs.append({
                        "hash": parts[0],
                        "short_hash": parts[1],
                        "author": parts[2],
                        "email": parts[3],
                        "date": parts[4],
                        "message": parts[5]
                    })

            return logs
        except subprocess.CalledProcessError as e:
            logger.error(f"获取提交历史失败: {e.stderr}")
            return []
