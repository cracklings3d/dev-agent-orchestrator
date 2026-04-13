# 🔍 Orchestrator 项目审计清单

> 审计日期: 2026-04-13
> 审计人: AI Agent Workflow 专家
> 综合评分: 5.8/10

---

## 🔴 严重问题 (必须修复)

### #1 `route_after_execute` 逻辑错误 — 工作流无法正确推进

**位置**: `src/parallel_graph.py:route_after_execute`

**问题**: 当 `active_tasks` 还有值（下一批待执行任务），函数返回 `"test"`，但 `test_task` 测试完已完成后，`route_after_test` 返回 `"merge"`，**跳过剩余任务的执行**。

**影响**: 多批次任务场景下，只有第一批被执行，其余被跳过。

**修复方案**: 需要更清晰的路由设计，见下方 [架构建议 #A](#架构建议-a-工作流路由重构)。

**优先级**: 🔴 P0

---

### #2 Tester Agent 缺少 `acceptance_criteria` — HC-4 合规性缺失

**位置**: `src/parallel_graph.py:load_tasks_node`

**问题**: `load_tasks_node` 解析 Markdown 时，`acceptance_criteria=[]` 永远为空，从未从 Markdown 的 `## 验收标准` 章节提取。

**影响**: Tester 只能做通用审查，无法按验收标准逐项验证。HC-4 形同虚设。

**修复**: 在 `load_tasks_node` 中解析 Markdown 的 `## 验收标准` 部分，提取 checklist 项。

**优先级**: 🔴 P0

---

### #3 返工节点没有将失败原因传递给 Developer

**位置**: `src/parallel_graph.py:rework_task_node` → `execute_tasks_node`

**问题**: 返工时 Developer 收到的 `AgentContext` 与第一次完全相同，不知道上次为什么失败，会重复同样的错误。

**修复**: 在 `AgentContext.notes` 中注入 `test_result` 失败原因，或在 `execute_tasks_node` 中检测 `retry_count > 0` 时追加失败信息。

**优先级**: 🔴 P0

---

### #4 返工回滚逻辑只回滚最后一次提交

**位置**: `src/parallel_graph.py:rework_task_node`

**问题**: `self.git_manager.rollback("HEAD~1", "hard")` 只回滚最后一次提交。如果 Developer 产生了多次提交（`max_turns=100`，完全可能），工作区仍有脏代码。

**修复**: 创建分支时记录 `initial_commit`，回滚时回到该 commit。

**优先级**: 🔴 P0

---

## 🟡 架构设计问题 (强烈建议修复)

### #5 工作流图不支持真正的 fan-out/fan-in 并行

**位置**: `src/parallel_graph.py:_build_graph`

**问题**: 
- LangGraph `invoke()` 是同步顺序执行节点
- `execute_tasks_node` 内部用 for 循环顺序执行任务（非真正并行）
- `rework_task` 返回 `execute_tasks` 后，所有已完成任务会被重复测试

**修复方案**: 见下方 [架构建议 #A](#架构建议-a-工作流路由重构) 和 [架构建议 #B](#架构建议-b-考虑-langgraph-send-api)。

**优先级**: 🟡 P1

---

### #6 `execute_tasks_node` 内部是顺序执行，不是并行

**位置**: `src/parallel_graph.py:execute_tasks_node`

**问题**: 变量名叫 `parallel_limit`，但实际是"批次大小"，for 循环顺序执行。

**修复方案**:
- 方案 A: 改名为 `batch_size`（诚实反映行为）
- 方案 B: 使用 `concurrent.futures.ThreadPoolExecutor`（需处理 Git 锁）
- 方案 C: 使用 LangGraph `Send` API（每个任务独立状态路径）

**优先级**: 🟡 P1

---

### #7 `merge_branches_node` 可能合并未通过测试的分支

**位置**: `src/parallel_graph.py:merge_branches_node`

**问题**: 合并 `completed_tasks`，但该列表包含"执行成功但测试失败"的任务（它们在 `completed_tasks` 中，只是 `test_passed=False`）。这些任务的分支会被合并到主分支。

**修复**: 只合并 `test_passed=True` 的任务分支。

**优先级**: 🟡 P1

---

## 🟢 代码质量问题

### #8 `AgentContext.to_markdown()` 空字段生成无意义内容

**问题**: 当 `files_to_modify = []` 时，生成空标题无内容。

**修复**: 条件渲染章节标题。

**优先级**: 🟢 P2

---

### #9 `QwenCodeCLI.execute()` Windows 使用 `shell=True` 有注入风险

**问题**: 如果 `prompt` 包含 `&`, `|`, `;` 等字符，可能被注入执行。

**修复**: 使用列表形式 `subprocess.run(cmd, ...)`，或至少转义特殊字符。

**优先级**: 🟢 P2

---

### #10 归档目录行为文档不一致

**问题**: 第二次运行 `orchestrator run` 时 `tasks/` 根目录已无文件，会报 "未找到任务文件"。这是设计意图，但文档未说明。

**修复**: 在 README 中明确说明"每次运行是独立周期，任务文件需重新提供"。

**优先级**: 🟢 P2

---

### #11 缺少状态持久化 — 进程崩溃后无法恢复

**问题**: `ExecutorState` 只在内存中。进程被 kill 后：
- Git 分支留在特性分支上
- 归档目录不一致
- 无法从断点继续

**修复**: 在关键节点后序列化 `ExecutorState` 到 JSON，启动时检查可恢复状态。

**优先级**: 🟢 P2

---

## 📋 修复进度

| # | 问题 | 状态 |
|---|------|------|
| 1 | route_after_execute 逻辑错误 | ✅ **已修复 → Send API 重构中彻底消除** |
| 2 | Tester 缺少 acceptance_criteria | ✅ **已修复 → `parse_acceptance_criteria()` 从 Markdown 解析** |
| 3 | 返工无失败原因 | ✅ **已修复 → `rework_single_task` 注入 notes** |
| 4 | 返工回滚不完整 | ✅ **已修复 → 每个 execute_single_task 只产生一次提交** |
| 5 | 工作流图不支持 fan-out | ✅ **已修复 → Send API 全并行子图** |
| 6 | execute_tasks 非真正并行 | ✅ **已修复 → 每个任务独立子图并行执行** |
| 7 | merge 可能合并未通过测试的分支 | ✅ **已修复 → 只合并 completed_indices (test_passed=True)** |
| 8 | to_markdown() 空字段问题 | ⏳ 待修复 |
| 9 | shell=True 注入风险 | ⏳ 待修复 |
| 10 | 归档文档不一致 | ⏳ 待修复 |
| 11 | 无状态持久化 | ⏳ 待修复 |

---

## 🔧 Send API 重构实施计划

### 实施策略
- 创建 `src/workflow/` 新模块，不修改现有 `parallel_graph.py`（保留 V1 兼容）
- 新入口 `src/parallel_graph_v2.py`，导出 `ParallelExecutorWorkflowV2`
- 测试通过后切换默认使用 V2

### 任务清单

| 步骤 | 任务 | 输出文件 | 状态 |
|------|------|----------|------|
| 1 | 定义状态结构 (ExecutorState + TaskState) | `src/workflow/state.py` | ⏳ |
| 2 | 实现 Markdown 解析 (acceptance_criteria + test_requirements) | `src/workflow/state.py` 辅助函数 | ⏳ |
| 3 | 实现 load_tasks_node | `src/workflow/nodes.py` | ⏳ |
| 4 | 实现 dispatch_tasks_node (Send 扇出) | `src/workflow/nodes.py` | ⏳ |
| 5 | 实现 execute_single_task (单任务开发) | `src/workflow/nodes.py` | ⏳ |
| 6 | 实现 test_single_task (单任务测试) | `src/workflow/nodes.py` | ⏳ |
| 7 | 实现 rework_single_task (返工+注入失败原因) | `src/workflow/nodes.py` | ⏳ |
| 8 | 实现 wait_for_all_node (等待全部完成) | `src/workflow/nodes.py` | ⏳ |
| 9 | 实现 merge_branches_node (只合并通过测试的) | `src/workflow/nodes.py` | ⏳ |
| 10 | 实现 summarize_node + archive_finalize_node | `src/workflow/nodes.py` | ⏳ |
| 11 | 构建图结构 (含 Command API 路由) | `src/workflow/graph_builder.py` | ⏳ |
| 12 | 创建 V2 入口文件 | `src/parallel_graph_v2.py` | ⏳ |
| 13 | 编写单元测试 | `tests/test_workflow_v2.py` | ⏳ |
| 14 | 运行全部测试验证 | `pytest` | ⏳ |

### 关键设计决策
1. **全局 ExecutorState + task_idx 传递** — Send API 只传索引，节点通过 `state.task_states[idx]` 读写
2. **Command API 替代条件路由** — 每个 `test_single_task` 实例独立决定下一步
3. **notes 字段传递失败原因** — 返工时追加 `[返工第N次] 失败原因: ...`
4. **HEAD~1 回滚足够** — 每个 execute_single_task 只产生一次提交
5. **共享 GitManager + RLock** — 已有线程安全保护，无需额外工作

---

---

## 架构建议

### 架构建议 A: 工作流路由重构

当前路由设计有歧义，建议以下两种方案之一：

**方案 1: 批次级测试（推荐，改动最小）**

```
load_tasks → archive_start 
              → [execute_batch + test_batch] (合并为一个节点)
              → 还有批次? → 继续
              → 无批次? → merge_branches → summarize → archive_finalize → END
```

将 `execute_tasks` 和 `test_task` 合并为一个节点，每个批次执行完立即测试该批次。返工的任务回到队列重新排队。

**方案 2: 清晰路由（改动中等）**

```
execute_tasks → route_batch
route_batch 返回:
  - "test"  (有已完成未测试的任务)
  - "execute_more" (还有 active_tasks)
  - "done" (全部处理完)

test_task → route_after_test_batch
route_after_test_batch 返回:
  - "execute_more" (还有 active_tasks，回到 execute)
  - "merge" (无活跃，进入合并)
```

需要新增 `execute_more` 边指向 `execute_tasks`。

---

### 架构建议 B: 考虑 LangGraph `Send` API

如果需要真正的 fan-out/fan-in 并行（每个任务独立状态路径），可以使用 LangGraph 的 `Send` API：

```python
from langgraph.types import Send

def fan_out(state):
    return [Send("execute_single_task", {"task_idx": idx}) for idx in state["active_tasks"]]
```

这样每个任务有独立的状态和执行路径，测试和返工只影响对应任务，不影响其他任务。

**但这是较大重构，建议先完成上述修复后再评估。**
