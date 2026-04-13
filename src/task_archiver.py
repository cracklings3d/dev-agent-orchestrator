"""
Task Archiver - 任务归档管理器
职责：
1. 执行开始时：创建时间戳归档目录，将所有 TASK-*.md 移入 unfinished/
2. 任务完成时：将任务文件从 unfinished/ 移到 success/ 或 failure/
3. 执行结束时：处理 unfinished/ 中剩余的文件（未执行或中断的任务）

归档目录结构：
<tasks_dir>/<timestamp>/
├── unfinished/    ← 执行开始时所有待执行任务
├── success/       ← 成功完成的任务
└── failure/       ← 失败的任务
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TaskArchiver:
    """
    任务归档管理器

    管理任务文件在整个执行生命周期中的位置：
    - 执行开始: tasks/TASK-*.md → tasks/<timestamp>/unfinished/
    - 任务成功: tasks/<timestamp>/unfinished/TASK-XXX.md → tasks/<timestamp>/success/
    - 任务失败: tasks/<timestamp>/unfinished/TASK-XXX.md → tasks/<timestamp>/failure/
    """

    def __init__(self, tasks_dir: Path):
        """
        初始化任务归档管理器

        Args:
            tasks_dir: 任务文件根目录 (通常是 <project>/.qwen/tasks/)
        """
        self.tasks_dir = tasks_dir
        self.archive_dir: Optional[Path] = None
        self.unfinished_dir: Optional[Path] = None
        self.success_dir: Optional[Path] = None
        self.failure_dir: Optional[Path] = None
        self.timestamp: Optional[str] = None

    def start_execution(self) -> Path:
        """
        执行开始时调用：
        1. 创建时间戳命名的归档目录
        2. 创建 unfinished/、success/、failure/ 子目录
        3. 将 tasks_dir 根目录下所有 TASK-*.md 移入 unfinished/

        Returns:
            Path: 归档目录路径
        """
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.archive_dir = self.tasks_dir / self.timestamp
        self.unfinished_dir = self.archive_dir / "unfinished"
        self.success_dir = self.archive_dir / "success"
        self.failure_dir = self.archive_dir / "failure"

        # 创建子目录
        self.unfinished_dir.mkdir(parents=True, exist_ok=True)
        self.success_dir.mkdir(parents=True, exist_ok=True)
        self.failure_dir.mkdir(parents=True, exist_ok=True)

        # 移动根目录下的所有 TASK-*.md 到 unfinished/
        moved_count = 0
        for task_file in self.tasks_dir.glob("TASK-*.md"):
            if task_file.is_file():
                dest = self.unfinished_dir / task_file.name
                shutil.move(str(task_file), str(dest))
                moved_count += 1
                logger.info(f"归档任务文件: {task_file.name} → unfinished/")

        logger.info(
            f"归档目录已创建: {self.archive_dir}, "
            f"移动了 {moved_count} 个任务文件到 unfinished/"
        )

        print(f"📁 创建归档目录: {self.archive_dir}")
        if moved_count > 0:
            print(f"   📦 移动 {moved_count} 个任务文件到 unfinished/")
        else:
            print(f"   ℹ️  tasks/ 根目录没有待执行的任务文件")

        return self.archive_dir

    def archive_success(self, task_id: str) -> bool:
        """
        任务成功时调用：将任务文件从 unfinished/ 移到 success/

        Args:
            task_id: 任务 ID（如 TASK-001）

        Returns:
            bool: 是否成功移动
        """
        if not self.unfinished_dir or not self.success_dir:
            logger.error("归档目录未初始化，请先调用 start_execution()")
            return False

        return self._move_task(task_id, self.unfinished_dir, self.success_dir)

    def archive_failure(self, task_id: str) -> bool:
        """
        任务失败时调用：将任务文件从 unfinished/ 移到 failure/

        Args:
            task_id: 任务 ID（如 TASK-001）

        Returns:
            bool: 是否成功移动
        """
        if not self.unfinished_dir or not self.failure_dir:
            logger.error("归档目录未初始化，请先调用 start_execution()")
            return False

        return self._move_task(task_id, self.unfinished_dir, self.failure_dir)

    def _move_task(self, task_id: str, src_dir: Path, dst_dir: Path) -> bool:
        """
        移动任务文件

        Args:
            task_id: 任务 ID
            src_dir: 源目录
            dst_dir: 目标目录

        Returns:
            bool: 是否成功
        """
        # 尝试多种文件名格式
        candidates = [
            f"{task_id}.md",
            f"{task_id.lower()}.md",
        ]

        for filename in candidates:
            src_file = src_dir / filename
            if src_file.exists():
                dst_file = dst_dir / filename
                shutil.move(str(src_file), str(dst_file))
                logger.info(f"移动任务 {task_id}: {src_dir.name} → {dst_dir.name}")
                return True

        logger.warning(f"未找到任务文件 {task_id} 在 {src_dir} 中")
        return False

    def finalize(self) -> dict:
        """
        执行结束时调用：统计各目录中的任务文件数量

        Returns:
            dict: 包含 success_count, failure_count, unfinished_count 的统计信息
        """
        if not self.archive_dir:
            logger.error("归档目录未初始化")
            return {"success_count": 0, "failure_count": 0, "unfinished_count": 0}

        success_count = len(list(self.success_dir.glob("*.md"))) if self.success_dir else 0
        failure_count = len(list(self.failure_dir.glob("*.md"))) if self.failure_dir else 0
        unfinished_count = len(list(self.unfinished_dir.glob("*.md"))) if self.unfinished_dir else 0

        summary = {
            "archive_dir": str(self.archive_dir),
            "success_count": success_count,
            "failure_count": failure_count,
            "unfinished_count": unfinished_count,
        }

        logger.info(f"归档完成: {summary}")

        print(f"\n📁 归档统计:")
        print(f"   ✅ 成功: {success_count}")
        print(f"   ❌ 失败: {failure_count}")
        if unfinished_count > 0:
            print(f"   ⚠️  未完成: {unfinished_count}")
        print(f"   📂 归档目录: {self.archive_dir}")

        return summary

    def get_task_file(self, task_id: str) -> Optional[Path]:
        """
        获取任务文件的当前路径（从 unfinished/ 中读取）

        Args:
            task_id: 任务 ID

        Returns:
            Optional[Path]: 任务文件路径，不存在则返回 None
        """
        if not self.unfinished_dir:
            logger.error("归档目录未初始化")
            return None

        # 尝试多种文件名格式
        candidates = [
            f"{task_id}.md",
            f"{task_id.lower()}.md",
        ]

        for filename in candidates:
            task_file = self.unfinished_dir / filename
            if task_file.exists():
                return task_file

        return None

    def get_all_task_files(self) -> list[Path]:
        """
        获取 unfinished/ 中所有任务文件的路径

        Returns:
            list[Path]: 任务文件路径列表
        """
        if not self.unfinished_dir:
            logger.error("归档目录未初始化")
            return []

        return list(self.unfinished_dir.glob("*.md"))

    @property
    def is_initialized(self) -> bool:
        """是否已初始化归档目录"""
        return self.archive_dir is not None
