"""
Orchestrator CLI 入口 (纯执行模式)

使用流程:
1. 确保 .qwen/tasks/ 目录下有 TASK-*.md 任务文件
2. orchestrator run  # 读取任务 → 并行执行 → Tester 验证 → 归档

示例:
  orchestrator run
  orchestrator run --parallel-limit 5
  orchestrator status
  orchestrator info
"""

import click
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.parallel_graph import ParallelExecutorWorkflow

console = Console()


def get_project_root() -> str:
    """获取项目根目录"""
    return str(Path(__file__).parent)


@click.group()
def cli():
    """🤖 LangGraph Orchestrator - 并行任务执行器

    前提: .qwen/tasks/ 目录下必须存在 TASK-*.md 文件

    使用:
      orchestrator run                  # 执行所有任务
      orchestrator run -p 5             # 指定并行度
      orchestrator status               # 查看历史
      orchestrator info                 # 查看配置
    """
    pass


@cli.command()
@click.option("--parallel-limit", "-p", default=3, help="最大并行任务数 (默认 3)")
@click.option("--developer-model", default=None, help="Developer Agent 使用的模型")
@click.option("--tester-model", default=None, help="Tester Agent 使用的模型")
def run(parallel_limit: int, developer_model: str, tester_model: str):
    """执行 .qwen/tasks/ 中的所有任务"""
    project_root = get_project_root()

    # 检查任务文件是否存在
    tasks_dir = Path(project_root) / ".qwen" / "tasks"
    task_files = list(tasks_dir.glob("TASK-*.md"))
    if not task_files:
        console.print(f"[red]❌ 未找到任务文件![/red]")
        console.print(f"[yellow]请先在 {tasks_dir} 目录下创建 TASK-*.md 文件[/yellow]")
        sys.exit(1)

    models = {}
    if developer_model:
        models["developer"] = developer_model
    if tester_model:
        models["tester"] = tester_model

    console.print()
    console.print(Panel(
        f"[bold]项目:[/bold] {project_root}\n"
        f"[bold]任务:[/bold] {len(task_files)} 个\n"
        f"[bold]并行度:[/bold] {parallel_limit}",
        title="🚀 开始并行执行",
        border_style="green"
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="初始化执行器...", total=None)
            workflow = ParallelExecutorWorkflow(
                project_root,
                models,
                parallel_limit=parallel_limit
            )

        console.print("\n[bold green]✅ 执行器初始化完成[/bold green]")
        console.print("\n[bold cyan]⏳ 正在执行任务...[/bold cyan]\n")
        final_state = workflow.execute()

        console.print()
        if final_state.get("error"):
            console.print(Panel(
                f"[red]{final_state['error']}[/red]",
                title="❌ 执行失败",
                border_style="red"
            ))
            sys.exit(1)
        elif final_state.get("final_summary"):
            console.print(Panel(
                Markdown(final_state["final_summary"]),
                title="📊 执行结果",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "工作流执行完成，但未生成总结",
                title="⚠️  警告",
                border_style="yellow"
            ))

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  用户中断执行[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ 执行失败: {e}[/red]")
        console.print_exception()
        sys.exit(1)


@cli.command()
def status():
    """查看任务历史记录"""
    project_root = get_project_root()
    tasks_dir = Path(project_root) / ".qwen" / "tasks"

    if not tasks_dir.exists():
        console.print("[yellow]📭 暂无任务历史[/yellow]")
        return

    archive_dirs = [d for d in tasks_dir.iterdir() if d.is_dir()]
    if not archive_dirs:
        console.print("[yellow]📭 暂无归档历史[/yellow]")
        return

    console.print(f"\n[bold]📋 任务历史 ({len(archive_dirs)} 个归档)[/bold]\n")

    for archive_dir in sorted(archive_dirs):
        console.print(f"\n[bold cyan]📁 {archive_dir.name}[/bold cyan]")
        for category in ["success", "failure", "unfinished"]:
            category_dir = archive_dir / category
            if not category_dir.exists():
                continue
            task_files = list(category_dir.glob("*.md"))
            if not task_files:
                continue
            icon = {"success": "✅", "failure": "❌", "unfinished": "⏸️"}.get(category, "❓")
            console.print(f"  {icon} {category.title()}: {len(task_files)} 个任务")
            for tf in sorted(task_files):
                console.print(f"    • {tf.stem}")


@cli.command()
def info():
    """显示配置信息"""
    project_root = get_project_root()
    tasks_dir = Path(project_root) / ".qwen" / "tasks"
    task_count = len(list(tasks_dir.glob("TASK-*.md"))) if tasks_dir.exists() else 0

    console.print(Panel(
        f"[bold]项目根目录:[/bold] {project_root}\n"
        f"[bold]任务目录:[/bold] {tasks_dir}\n"
        f"[bold]待执行任务:[/bold] {task_count} 个\n"
        f"[bold]工作流引擎:[/bold] LangGraph\n"
        f"[bold]任务驱动:[/bold] Markdown 文件 (HC-3)\n"
        f"[bold]测试策略:[/bold] Tester Agent (HC-4)\n"
        f"[bold]归档策略:[/bold] 时间戳分类 (HC-5)",
        title="🤖 Orchestrator 信息",
        border_style="blue"
    ))


def main():
    cli()


if __name__ == "__main__":
    main()
