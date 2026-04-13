# Orchestrator 安装和使用指南

## ✅ 安装完成！

LangGraph Orchestrator 已成功安装到你的项目中。

## 📁 安装的文件

```
orchestrator/
├── src/
│   ├── agents/
│   │   ├── base_agent.py       # Agent 基类
│   │   └── agent_types.py      # Architect, Developer, Tester
│   ├── graph.py                # LangGraph 工作流
│   └── qwen_code_adapter.py    # Qwen Code CLI 适配器
├── main.py                     # CLI 入口
├── requirements.txt            # Python 依赖 (已安装)
├── setup.py                    # 安装脚本
├── test_basic.py               # 基础测试 (已通过)
└── README.md                   # 详细文档
```

## 🚀 立即使用

### 1. 测试基础功能

```bash
cd orchestrator
python test_basic.py
```

✅ 所有测试已通过！

### 2. 运行第一个任务

```bash
# 简单任务 (会调用 Qwen Code)
python main.py run "创建一个 test.txt 文件，内容为 Hello World"
```

### 3. 查看帮助

```bash
python main.py --help
python main.py run --help
```

## 💡 工作原理

```
你输入: "添加购物车功能"
    ↓
🏗️ Architect Agent (需求分析)
    - 分析需求
    - 拆解为: 数据库、后端、前端 3个子任务
    - 为每个任务生成最小上下文
    ↓
⚙️ Developer Agent (代码实现)
    - 接收任务 1: 数据库 Schema
    - 只看到任务 1 的上下文
    - 实现并保存代码
    ↓
🧪 Tester Agent (测试验证)
    - 验证是否符合验收标准
    - ✅ 通过 → 下一个任务
    - ❌ 失败 → 打回重做 (最多 3 次)
    ↓
📊 总结报告
```

## 🎯 核心特性

### 1. 最小上下文分发

每个 Developer Agent 只收到完成**当前任务**必需的信息：

```markdown
# 任务上下文: 添加 Cart 表

## 🎯 任务目标
在 Prisma Schema 中添加 Cart 模型

## 📁 工作范围
### 需要修改的文件
- `backend/prisma/schema.prisma`

## ✅ 验收标准
- [ ] Cart 包含 id, userId, productId, quantity
- [ ] 执行 prisma generate 无错误
```

### 2. 自动化循环反馈

```
Developer 完成 → Tester 验证
    ├─ ✅ 通过 → 下一个任务
    └─ ❌ 失败 → 打回 + 错误信息 → Developer 修复
```

### 3. 完整任务追溯

每个任务的上下文保存在 `.orchestrator/tasks/task-XXX/task-context.md`

## 📝 使用示例

### 示例 1: Bug 修复

```bash
python main.py run "修复登录后用户信息不显示的问题"
```

### 示例 2: 新功能开发

```bash
python main.py run "实现商品分类管理功能"
```

### 示例 3: 指定模型

```bash
python main.py -m "qwen-plus" run "添加用户权限系统"
```

### 示例 4: 交互模式

```bash
python main.py run -i
# 然后输入任务描述
```

### 示例 5: 查看任务历史

```bash
python main.py status
```

## ⚙️ 架构说明

### LangGraph 状态图

```
[Architect] → [Developer] → [Tester] → [下一个 Developer] → ... → [Summarize] → END
                  ↑              ↓
                  └── [Rework] ──┘ (失败时)
```

### 状态流转

| 状态 | 说明 |
|------|------|
| `pending` | 任务等待中 |
| `in_progress` | Developer 正在执行 |
| `testing` | Tester 正在验证 |
| `done` | 任务完成 |
| `rework` | 测试失败，需要返工 |

## 🔧 配置和定制

### 添加新的 Agent 类型

1. 编辑 `src/agents/agent_types.py`
2. 继承 `BaseAgent` 类
3. 实现 `build_system_prompt()` 和 `build_user_prompt()`

### 修改工作流

编辑 `src/graph.py` 中的 `_build_graph()` 方法，添加新的节点和边。

## ⚠️ 注意事项

1. **Qwen Code CLI 必须可用**
   - 确保 `qwen --help` 能正常工作
   - 确保已登录和配置好模型

2. **项目根目录可写**
   - Orchestrator 会在 `.orchestrator/` 目录保存任务上下文

3. **网络依赖**
   - 需要稳定的网络连接调用 Qwen Code

4. **任务粒度**
   - 建议每个子任务执行时间不超过 10 分钟

## 🐛 故障排除

### 问题: "qwen: command not found"

**解决**: 确保 Qwen Code CLI 已正确安装
```bash
npm install -g @anthropic-ai/qwen-code
```

### 问题: "架构师未输出有效的 JSON"

**原因**: Architect Agent 的输出包含额外文本内容

**解决**: 已在代码中实现智能 JSON 提取，应该能自动处理。如果仍然失败，检查 Qwen Code 的输出。

### 问题: 任务执行超时

**解决**: 默认超时 10 分钟。如果任务太复杂，可以增加超时时间（编辑 `qwen_code_adapter.py` 中的 `timeout` 参数）。

## 📚 更多文档

- [Orchestrator README](README.md) - 详细使用说明
- [Agent 任务契约模板](../docs/AGENT_TASK_CONTRACT_TEMPLATE.md) - 任务输入/输出规范

## 🎉 开始使用！

你现在可以开始使用 Orchestrator 来自动完成开发任务了。

运行第一个任务试试：

```bash
python main.py run "创建一个简单的测试文件"
```

祝使用愉快！🚀
