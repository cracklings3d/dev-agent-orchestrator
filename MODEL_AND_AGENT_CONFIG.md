# 模型和 Agent 配置指南

## 🎯 核心设计

Orchestrator **直接调用你的全局 Qwen Agent** (`~/.qwen/agents/`)，无需维护两套配置。

整个系统由 **LangGraph 状态机** 驱动，Agent 只负责在各自节点内执行任务。

## 📋 Agent 映射

| LangGraph 节点中的 Agent | 全局 Agent | 默认模型 | 职责 |
|--------------------------|-----------|---------|------|
| **Developer** | `full-stack-impl-engineer` | `qwen-coder` | 代码实现 |
| **Tester** | `qa-test-engineer` | `qwen-coder` | 测试验证 |

> **Architect Agent** 不在 LangGraph 工作流内。它是独立工具，用于生成 `.qwen/tasks/TASK-*.md` 文件。

## 🔧 工作原理

```python
# 当你运行 orchestrator run 时
# LangGraph 工作流自动执行：
#
# 1. load_tasks 节点: 读取 .qwen/tasks/TASK-*.md
# 2. execute_tasks 节点: Developer Agent 实现功能
# 3. test_task 节点:    Tester Agent 验证质量
# 4. rework_task 节点:  测试失败则回滚并重试 (最多 3 次)
# 5. merge_branches:    合并成功的分支
# 6. summarize:         生成总结
# 7. archive_finalize:  时间戳归档
```

## ⚙️ 自定义模型配置

### 方式 1: 为每个 Agent 指定不同模型

```bash
orchestrator run --developer-model qwen-coder --tester-model qwen-plus
```

### 方式 2: 使用默认模型

```bash
orchestrator run
# Developer → qwen-coder
# Tester → qwen-coder
```

## 📁 全局 Agent 位置

你的全局 Agent 定义在：

```
C:\Users\The_u\.qwen\agents\
├── full-stack-impl-engineer.md      ← Developer 使用
└── qa-test-engineer.md              ← Tester 使用
```

**修改这些文件会直接影响 Orchestrator 的行为！**

## ✅ 验证配置

运行以下命令查看当前配置：

```bash
orchestrator info
```

## 🔍 故障排除

### 问题: "Agent 文件不存在"

**原因**: `~/.qwen/agents/` 下缺少对应的 Agent 文件

**解决**: 确保以下文件存在：
- `~/.qwen/agents/full-stack-impl-engineer.md`
- `~/.qwen/agents/qa-test-engineer.md`

### 问题: 模型调用失败

**原因**: 模型名称不正确或未配置

**解决**:
1. 运行 `qwen --help` 查看支持的模型
2. 使用 `--developer-model` 等参数明确指定模型

## 🎓 最佳实践

1. **保持单一来源**: 只维护 `~/.qwen/agents/` 下的 Agent 定义
2. **按角色选模型**:
   - 开发用代码优化模型 (`qwen-coder`)
   - 测试用代码优化模型 (`qwen-coder`)
3. **测试配置**: 先用小任务测试，确认 Agent 行为符合预期

## 🚀 总结

- ✅ **只需维护一套 Agent**: `~/.qwen/agents/`
- ✅ **LangGraph 驱动**: 工作流由状态机控制，非 Agent 自由发挥
- ✅ **灵活模型配置**: 每个 Agent 可用不同模型
- ✅ **开箱即用**: 默认配置已优化
