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
        # 构建命令 (列表形式，不使用 shell，避免注入风险)
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

        # 添加系统提示
        # Windows CreateProcess 命令行长度限制约 32768 字符
        # 超过阈值时使用临时文件传递，避免参数过长
        full_system = ""
        if self.agent_prompt:
            full_system += f"{self.agent_prompt}\n\n"
        if system_prompt:
            full_system += f"{system_prompt}\n\n"

        full_system = full_system.strip()

        work_dir = Path(working_dir) if working_dir else self.project_root

        # 估算命令行总长度 (参数 + 空格分隔符)
        estimated_len = sum(len(a) for a in cmd) + len(cmd) + len(prompt) + len(full_system)

        # Windows CreateProcess 限制约 32768 字符，留 2000 字符余量
        WINDOWS_CMD_SAFE_LIMIT = 30000

        temp_files_to_cleanup = []

        try:
            if estimated_len > WINDOWS_CMD_SAFE_LIMIT:
                # 使用临时文件传递长参数，避免命令行溢出
                temp_sys = self._create_temp_system_prompt(full_system)
                temp_prompt = self._create_temp_prompt(prompt)
                temp_files_to_cleanup.extend([temp_sys, temp_prompt])

                cmd.extend(["--system-prompt-file", str(temp_sys)])
                cmd.append(str(temp_prompt))
            else:
                if full_system:
                    cmd.extend(["--system-prompt", full_system])
                cmd.append(prompt)

            # 直接调用可执行文件，不使用 shell (消除注入风险)
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=600,  # 10 分钟超时
                encoding="utf-8",
            )

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
        finally:
            # 清理临时文件
            for tf in temp_files_to_cleanup:
                try:
                    tf.unlink(missing_ok=True)
                except OSError:
                    pass
    
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
