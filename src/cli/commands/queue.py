"""Queue command for managing post-restart task automation."""
import click
from typing import List


@click.group()
@click.pass_context
def queue(ctx):
    """Manage tasks that run automatically after a restart."""
    pass


@queue.command()
@click.argument('task_words', nargs=-1, required=True)
@click.pass_context
def add(ctx, task_words: tuple):
    """Add a task to the queue."""
    cli_ctx = ctx.find_root().obj
    description = " ".join(task_words).strip()

    if not description:
        click.echo("Error: Task description cannot be empty", err=True)
        raise SystemExit(1)

    try:
        task = cli_ctx.controller.add_task_to_queue(description)
        if not cli_ctx.quiet:
            timestamp = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
            queue_size = len(cli_ctx.controller.list_queued_tasks())
            click.echo(f"✓ Queued task #{queue_size}: {task.description}")
            click.echo(f"  Added at: {timestamp}")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


@queue.command(name="list")
@click.pass_context
def list_tasks(ctx):
    """Show queued tasks."""
    cli_ctx = ctx.find_root().obj
    tasks = cli_ctx.controller.list_queued_tasks()

    if not tasks:
        click.echo("No queued tasks.")
        return

    click.echo("=== Queued Tasks (next restart) ===")
    for idx, task in enumerate(tasks, start=1):
        timestamp = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"{idx}. {task.description}  (added {timestamp})")


@queue.command()
@click.argument('indices', nargs=-1)
@click.pass_context
def remove(ctx, indices: tuple):
    """Remove tasks by their displayed numbers."""
    cli_ctx = ctx.find_root().obj

    if not indices:
        click.echo("Error: Provide one or more task numbers to remove.", err=True)
        raise SystemExit(1)

    parsed_indices: List[int] = []
    for value in indices:
        try:
            parsed_indices.append(int(value))
        except ValueError:
            click.echo(f"Error: '{value}' is not a valid task number.", err=True)
            raise SystemExit(1)

    removed = cli_ctx.controller.remove_queued_tasks(parsed_indices)

    if not removed:
        click.echo("No matching tasks found.")
        return

    for task in removed:
        click.echo(f"✓ Removed: {task.description}")


@queue.command()
@click.option('--confirm', is_flag=True, help='Confirm clearing without prompt')
@click.pass_context
def clear(ctx, confirm: bool):
    """Clear all queued tasks."""
    cli_ctx = ctx.find_root().obj

    if not confirm and not cli_ctx.quiet:
        if not click.confirm("Remove all queued tasks?"):
            click.echo("Queue clear cancelled.")
            return

    removed_count = cli_ctx.controller.clear_task_queue()
    if removed_count:
        click.echo(f"✓ Cleared {removed_count} queued task(s).")
    else:
        click.echo("Queue was already empty.")
