"""
Git Manager 单元测试
测试 Git 自动化管理功能
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.git_manager import GitManager, GitStatus, CommitResult, MergeResult


@pytest.fixture
def temp_git_repo(tmp_path):
    """创建临时 Git 仓库"""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    
    # 初始化 Git 仓库
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)
    
    # 创建初始文件并提交
    initial_file = repo_path / "README.md"
    initial_file.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True)
    
    return repo_path


class TestGitManager:
    """GitManager 测试类"""

    def test_init_valid_repo(self, temp_git_repo):
        """测试初始化有效的 Git 仓库"""
        manager = GitManager(str(temp_git_repo))
        assert manager.repo_path == temp_git_repo

    def test_init_invalid_repo(self, tmp_path):
        """测试初始化无效的 Git 仓库"""
        with pytest.raises(ValueError):
            GitManager(str(tmp_path))

    def test_get_status(self, temp_git_repo):
        """测试获取 Git 状态"""
        manager = GitManager(str(temp_git_repo))
        status = manager.get_status()
        
        assert isinstance(status, GitStatus)
        assert status.branch == "master" or status.branch == "main"
        assert status.is_clean is True
        assert len(status.modified_files) == 0
        assert len(status.staged_files) == 0
        assert len(status.untracked_files) == 0

    def test_get_status_with_changes(self, temp_git_repo):
        """测试获取有更改的 Git 状态"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建新文件
        new_file = temp_git_repo / "test.txt"
        new_file.write_text("test content")
        
        status = manager.get_status()
        assert status.is_clean is False
        assert len(status.untracked_files) == 1
        assert "test.txt" in status.untracked_files

    def test_create_and_switch_branch(self, temp_git_repo):
        """测试创建和切换分支"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建分支
        assert manager.create_branch("test-feature") is True
        
        # 验证当前分支
        status = manager.get_status()
        assert status.branch == "test-feature"
        
        # 切换回主分支
        manager.switch_branch("master" if status.branch == "test-feature" else "main")
        status = manager.get_status()
        assert status.branch in ["master", "main"]

    def test_commit_changes(self, temp_git_repo):
        """测试提交更改"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建新文件
        new_file = temp_git_repo / "feature.txt"
        new_file.write_text("feature content")
        
        # 提交
        result = manager.commit("feat: add feature file", ["feature.txt"])
        
        assert result.success is True
        assert result.commit_hash is not None
        assert len(result.files_committed) > 0
        assert "feature.txt" in result.files_committed

    def test_commit_with_author(self, temp_git_repo):
        """测试带作者的提交"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建文件
        new_file = temp_git_repo / "authored.txt"
        new_file.write_text("authored content")
        
        # 提交
        result = manager.commit(
            "feat: add authored file",
            ["authored.txt"],
            author_name="Test Agent",
            author_email="agent@test.com"
        )
        
        assert result.success is True
        assert result.commit_hash is not None

    def test_rollback_soft(self, temp_git_repo):
        """测试软回滚"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建并提交文件
        new_file = temp_git_repo / "rollback.txt"
        new_file.write_text("rollback content")
        manager.commit("feat: add rollback file", ["rollback.txt"])
        
        # 软回滚
        assert manager.rollback("HEAD~1", "soft") is True

    def test_create_feature_branch(self, temp_git_repo):
        """测试创建特性分支"""
        manager = GitManager(str(temp_git_repo))
        
        branch_name = manager.create_feature_branch("TASK-001")
        
        assert branch_name is not None
        assert branch_name == "feature/task-001"
        
        status = manager.get_status()
        assert status.branch == "feature/task-001"

    def test_submit_task_work(self, temp_git_repo):
        """测试提交任务工作"""
        manager = GitManager(str(temp_git_repo))
        
        # 创建文件
        new_file = temp_git_repo / "task_work.txt"
        new_file.write_text("task work content")
        
        # 提交任务工作
        result = manager.submit_task_work(
            task_id="TASK-001",
            task_title="Implement feature",
            agent_name="Test Developer"
        )
        
        assert result.success is True
        assert result.commit_hash is not None
        assert "TASK-001" in result.message
        assert "Test Developer" in result.message

    def test_get_log(self, temp_git_repo):
        """测试获取提交历史"""
        manager = GitManager(str(temp_git_repo))
        
        logs = manager.get_log(5)
        
        assert isinstance(logs, list)
        assert len(logs) > 0
        assert "hash" in logs[0]
        assert "message" in logs[0]

    def test_get_diff(self, temp_git_repo):
        """测试获取差异"""
        manager = GitManager(str(temp_git_repo))
        
        # 修改已追踪的文件
        readme = temp_git_repo / "README.md"
        original_content = readme.read_text()
        readme.write_text(original_content + "\n\n## New Section")
        
        diff = manager.get_diff()
        assert "README.md" in diff


class TestMergeResult:
    """MergeResult 测试类"""

    def test_successful_merge(self):
        """测试成功的合并结果"""
        result = MergeResult(
            success=True,
            branch="feature/test",
            conflicts=[],
            message="Merged feature/test"
        )
        
        assert result.success is True
        assert len(result.conflicts) == 0

    def test_failed_merge_with_conflicts(self):
        """测试有冲突的失败合并"""
        result = MergeResult(
            success=False,
            branch="feature/test",
            conflicts=["file1.txt", "file2.txt"],
            message="合并冲突"
        )
        
        assert result.success is False
        assert len(result.conflicts) == 2


class TestCommitResult:
    """CommitResult 测试类"""

    def test_successful_commit(self):
        """测试成功的提交结果"""
        result = CommitResult(
            success=True,
            commit_hash="abc123",
            message="feat: test commit",
            files_committed=["file1.txt"]
        )
        
        assert result.success is True
        assert result.commit_hash == "abc123"

    def test_failed_commit(self):
        """测试失败的提交结果"""
        result = CommitResult(
            success=False,
            commit_hash=None,
            message="feat: failed commit",
            files_committed=[],
            error="Permission denied"
        )
        
        assert result.success is False
        assert result.error == "Permission denied"
