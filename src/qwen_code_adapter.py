"""
Qwen Code CLI 适配器
负责通过 CLI 调用 Qwen Code，执行 Agent 任务
"""

import subprocess
import json
import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QwenCodeResult:
    """Qwen Code 执行结果"""
    success: bool
    output: str
    error: str
    exit_code: int
    files_changed: list[str]


class QwenCodeCLI:
    """Qwen Code CLI 调用适配器"""

    def __init__(self, project_root: str, model: Optional[str] = None, agent_name: Optional[str] = None):
        """
        初始化 Qwen Code CLI 适配器

        Args:
            project_root: 项目根目录路径
            model: 使用的模型名称 (可选，默认使用 Qwen Code 全局配置)
            agent_name: Agent 名称 (可选，从 ~/.qwen/agents/ 读取)
        """
        self.project_root = Path(project_root)
        self.model = model
        self.agent_name = agent_name
        self.agent_prompt = self._load_agent_prompt(agent_name) if agent_name else None
    
    def _load_agent_prompt(self, agent_name: str) -> Optional[str]:
        """从 ~/.qwen/agents/ 读取 Agent prompt"""
        agents_dir = Path.home() / ".qwen" / "agents"
        agent_file = agents_dir / f"{agent_name}.md"
        
        if agent_file.exists():
            return agent_file.read_text(encoding="utf-8")
        else:
            print(f"⚠️  Agent 文件不存在: {agent_file}")
            return None
    
    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        working_dir: Optional[str] = None,
        approval_mode: str = "yolo",
        output_format: str = "text",
        max_turns: Optional[int] = None,
    ) -> QwenCodeResult:
        """
        执行 Qwen Code 命令

        Args:
            prompt: 任务提示
            system_prompt: 系统提示 (用于定义 Agent 角色)
            working_dir: 工作目录
            approval_mode: 审批模式 (默认 yolo 自动执行)
            output_format: 输出格式
            max_turns: 最大会话轮次

        Returns:
            QwenCodeResult: 执行结果
        """
        # 构建命令
        cmd = ["qwen"]

        # 添加模型参数 (如果指定)
        if self.model:
            cmd.extend(["-m", self.model])

        # 添加审批模式
        cmd.extend(["--approval-mode", approval_mode])

        # 添加输出格式
        cmd.extend(["-o", output_format])

        # 添加最大轮次限制
        if max_turns:
            cmd.extend(["--max-session-turns", str(max_turns)])

        # 添加系统提示 (使用 --system-prompt 参数)
        full_system = ""
        if self.agent_prompt:
            full_system += f"{self.agent_prompt}\n\n"
        if system_prompt:
            full_system += f"{system_prompt}\n\n"

        if full_system.strip():
            cmd.extend(["--system-prompt", full_system.strip()])

        # 添加工作目录
        work_dir = Path(working_dir) if working_dir else self.project_root

        # 添加 prompt (使用 positional argument，而不是 -p)
        cmd.append(prompt)

        try:
            # 执行命令
            # Windows 需要 shell=True 和字符串命令
            cmd_str = " ".join(cmd)
            result = subprocess.run(
                cmd_str,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=600,  # 10 分钟超时
                encoding="utf-8",
                shell=True  # Windows 兼容性
            )
            
            # 解析输出
            return QwenCodeResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                files_changed=self._detect_files_changed(work_dir)
            )
            
        except subprocess.TimeoutExpired:
            return QwenCodeResult(
                success=False,
                output="",
                error="任务执行超时 (10 分钟)",
                exit_code=-1,
                files_changed=[]
            )
        except Exception as e:
            return QwenCodeResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                files_changed=[]
            )
    
    def _create_temp_system_prompt(self, system_prompt: str) -> Path:
        """创建临时系统提示文件"""
        temp_dir = self.project_root / ".orchestrator" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_file = temp_dir / "system_prompt.md"
        temp_file.write_text(system_prompt, encoding="utf-8")

        return temp_file
    
    def _create_temp_prompt(self, prompt: str) -> Path:
        """创建临时任务提示文件(用于绕过 Windows 命令行长度限制)"""
        temp_dir = self.project_root / ".orchestrator" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        import time
        temp_file = temp_dir / f"prompt_{int(time.time())}.md"
        temp_file.write_text(prompt, encoding="utf-8")
        
        return temp_file
    
    def _detect_files_changed(self, working_dir: Path) -> list[str]:
        """
        检测哪些文件被修改了
        通过 git status 或文件时间戳判断
        """
        try:
            # 尝试使用 git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        # 格式: " M file.txt" 或 "A file.txt"
                        parts = line.strip().split(" ", 1)
                        if len(parts) == 2:
                            files.append(parts[1])
                return files
        except:
            pass
        
        return []
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        temp_dir = self.project_root / ".orchestrator" / "temp"
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
