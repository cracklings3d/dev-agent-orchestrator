"""
LangGraph Send API 全并行工作流 V2 - 状态定义

定义 ExecutorState 和 TaskState TypedDict，以及 Markdown 解析辅助函数。
符合 HC-3 (Markdown 驱动)：从任务文件解析验收标准和测试要求。
"""

import re
from typing import TypedDict, Optional


class TaskState(TypedDict, total=False):
    """
    单个任务的完整状态

    字段来源:
    - 解析自 .qwen/tasks/TASK-*.md 文件 (HC-3)
    - 执行追踪由工作流节点更新
    """
    # 任务元数据 (从 Markdown 文件解析)
    task_id: str
    title: str
    objective: str  # 完整 Markdown 内容 (HC-3)
    files_to_modify: list[str]
    files_to_create: list[str]
    forbidden_files: list[str]
    acceptance_criteria: list[str]  # 从 Markdown ## 验收标准 解析
    test_requirements: Optional[dict]  # {'need_tests': bool, 'test_command': str or None}
    constraints: list[str]
    references: list[str]
    notes: list[str]

    # 执行追踪 (由 execute_single_task 更新)
    success: bool
    output: str
    files_changed: list[str]
    branch_name: str
    commit_hash: Optional[str]

    # 测试追踪 (由 test_single_task 更新)
    test_result: Optional[str]
    test_passed: bool
    retry_count: int


class ExecutorState(TypedDict, total=False):
    """
    全局执行器状态

    由 LangGraph 状态图读写，所有节点通过返回 dict 更新此状态。
    """
    # 控制参数
    parallel_limit: int
    max_retries: int

    # 任务状态字典 (key = task_idx)
    task_states: dict  # dict[int, TaskState]

    # 追踪集合
    pending_indices: list[int]       # 待分发任务
    running_indices: list[int]       # 正在执行的任务
    completed_indices: list[int]     # 测试通过的任务
    failed_indices: list[int]        # 最终失败的任务

    # 归档
    archive_dir: Optional[str]

    # 最终结果
    final_summary: Optional[str]
    error: Optional[str]


def parse_acceptance_criteria(markdown: str) -> list[str]:
    """
    从 Markdown 中提取 '## 验收标准' 到下一个 '##' 之间的所有 '- [ ]' 项。

    Args:
        markdown: 完整的 Markdown 任务文件内容

    Returns:
        验收标准列表（去除 '- [ ]' 前缀和空白）

    示例:
        >>> parse_acceptance_criteria("## 验收标准\\n- [ ] 标准1\\n- [ ] 标准2\\n## 测试要求")
        ['标准1', '标准2']
    """
    # 匹配 ## 验收标准 到下一个 ## 之间的内容
    pattern = r"##\s*验收标准\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, markdown, re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    criteria = []
    for line in section.strip().split("\n"):
        line = line.strip()
        # 匹配 '- [ ] xxx' 或 '- [x] xxx' 格式
        criterion_match = re.match(r"^-\s*\[\s*\]\s*(.+)$", line)
        if criterion_match:
            criteria.append(criterion_match.group(1).strip())

    return criteria


def parse_test_requirements(markdown: str) -> Optional[dict]:
    """
    从 Markdown 中提取 '## 测试要求' 部分。

    Args:
        markdown: 完整的 Markdown 任务文件内容

    Returns:
        {'need_tests': bool, 'test_command': str or None}
        如果没有测试要求部分，返回 None
    """
    # 匹配 ## 测试要求 到下一个 ## 之间的内容
    pattern = r"##\s*测试要求\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, markdown, re.DOTALL)
    if not match:
        return None

    section = match.group(1).strip()
    if not section:
        return None

    need_tests = False
    test_command: Optional[str] = None

    for line in section.split("\n"):
        line = line.strip().rstrip("\n")
        # 检查是否需要编写测试
        if re.search(r"需要.*测试|need.*test|编写.*测试", line, re.IGNORECASE):
            need_tests = True
        # 提取测试命令
        cmd_match = re.search(r"(?:测试命令|test[_\s]?command)\s*[:：]\s*`?([^`\n]+)`?", line, re.IGNORECASE)
        if cmd_match:
            test_command = cmd_match.group(1).strip()
            # 如果有测试命令，隐含需要测试
            need_tests = True

    # 如果部分内容为空（没有有效信息），返回 None
    if not need_tests and test_command is None:
        return None

    return {"need_tests": need_tests, "test_command": test_command}
