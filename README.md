# LangGraph Orchestrator

AI Agent 编排系统 — **完全由 LangGraph 状态机驱动**。

## 核心约束 (Hard Constraints)

| 约束 | 描述 | 状态 |
|------|------|------|
| HC-1 | LangGraph 状态机驱动 | ✅ |
| HC-2 | 单向隔离的信息流动 | ✅ |
| HC-3 | Markdown 文件驱动 | ✅ |
| HC-4 | Tester 完备性测试 | ✅ |
| HC-5 | 时间戳归档 | ✅ |
| HC-6 | 模式化架构，预留扩展 | ✅ |

## 安装

```bash
cd orchestrator
pip install -r requirements.txt
pip install -e .
```

## 使用

### 前提

确保 `.qwen/tasks/` 目录下存在 `TASK-*.md` 任务文件（由 Architect Agent 生成或手动创建）。

### 执行任务

```bash
# 执行所有任务
orchestrator run

# 指定并行度
orchestrator run --parallel-limit 5

# 指定不同 Agent 的模型
orchestrator run --developer-model qwen-coder --tester-model qwen-plus
```

### 查看历史与配置

```bash
orchestrator status   # 查看归档历史
orchestrator info     # 查看配置信息
```

## 工作流 (LangGraph 状态机)

```
load_tasks → archive_start → execute_tasks (fan-out)
                                  ↓
                               test_task (fan-in)
                                  ↓
                             rework_task? → execute_tasks (重试)
                                  ↓
                             merge_branches → summarize → archive_finalize → END
```

### 节点说明

| 节点 | 职责 |
|------|------|
| `load_tasks` | 从 `.qwen/tasks/` 读取所有 `TASK-*.md`，整文件传递 |
| `archive_start` | 创建时间戳归档目录，移动待执行任务到 `unfinished/` |
| `execute_tasks` | 为每个活跃任务: 创建 feature 分支 → Developer Agent 实现 → Git 提交 |
| `test_task` | Tester Agent 完备性验证 + 运行测试命令 |
| `rework_task` | 测试失败 → 回滚提交 → 标记返工 (最多 3 次) |
| `merge_branches` | 合并所有成功的 feature 分支到主分支 |
| `summarize` | 生成执行总结报告 |
| `archive_finalize` | 按成功/失败分类归档任务文件 |

## 目录结构

```
orchestrator/
├── main.py                         # CLI 入口 (唯一入口)
├── requirements.txt                # 依赖
├── pytest.ini                      # 测试配置
│
├── 📚 设计文档
│   ├── CORE_REQUIREMENTS.md        # 核心硬约束 (HC-1 ~ HC-6)
│   └── ARCHITECT_TASK_SPEC.md      # Architect 任务拆解规范
│
├── src/
│   ├── parallel_graph.py           # LangGraph 状态机 (唯一工作流)
│   ├── git_manager.py              # Git 操作
│   ├── qwen_code_adapter.py        # Qwen Code CLI 适配器
│   ├── task_archiver.py            # HC-5 时间戳归档
│   └── agents/                     # Agent 定义
│       ├── base_agent.py           # Agent 基类 + AgentContext
│       └── agent_types.py          # Architect / Developer / Tester
│
└── tests/                          # 测试套件
    ├── test_agents.py
    ├── test_git_manager.py
    └── test_parallel_workflow.py
```

## 架构原则

1. **LangGraph 是唯一驱动引擎** — 不存在 ThreadPoolExecutor、WorkerManager 等其他调度路径
2. **文件驱动** — 所有任务上下文存储在 `.qwen/tasks/TASK-*.md`，整文件传递
3. **分支隔离** — 每个任务在独立 feature 分支上开发
4. **AI 验证** — Tester Agent 进行代码审查 + 测试命令验证
5. **返工循环** — 测试失败自动返工，最多 3 次
6. **时间戳归档** — 每次执行独立归档，便于追溯

## 测试

```bash
pytest tests/ -v
```

## 许可证

内部项目
