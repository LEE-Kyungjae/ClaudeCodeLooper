"""Queue command for managing post-restart task automation."""

import click
from typing import List


@click.group()
@click.pass_context
def queue(ctx):
    """Manage tasks that run automatically after a restart."""
    pass


@queue.command()
@click.argument("task_words", nargs=-1, required=True)
@click.option("--template", "template_id", help="사전 정의된 템플릿 ID")
@click.option("--note", help="추가 메모나 컨텍스트")
@click.option(
    "--guideline",
    "extra_guidelines",
    multiple=True,
    help="추가 체크리스트 항목 (여러 번 사용 가능)",
)
@click.option(
    "--post",
    "extra_post_commands",
    multiple=True,
    help="업무 후 실행할 명령 (여러 번 사용 가능)",
)
@click.pass_context
def add(
    ctx,
    task_words: tuple,
    template_id: str,
    note: str,
    extra_guidelines: tuple,
    extra_post_commands: tuple,
):
    """Add a task to the queue."""
    cli_ctx = ctx.find_root().obj
    template_manager = getattr(cli_ctx, "template_manager", None)
    description = " ".join(task_words).strip()

    if not description:
        click.echo("Error: Task description cannot be empty", err=True)
        raise SystemExit(1)

    template = None
    persona_prompt = None
    guideline_prompt = None
    post_commands = list(extra_post_commands)

    if template_id:
        if not template_manager:
            click.echo("Error: Template manager unavailable", err=True)
            raise SystemExit(1)

        template = template_manager.get(template_id)
        if not template:
            available = ", ".join(
                t.template_id for t in template_manager.available_templates()
            )
            click.echo(
                f"Error: Unknown template '{template_id}'. Available: {available}",
                err=True,
            )
            raise SystemExit(1)

        persona_prompt = template.persona_prompt
        template_guidelines = template.build_guideline_prompt()
        if template_guidelines:
            guideline_prompt = template_guidelines
        post_commands = list(template.post_commands) + post_commands

    if extra_guidelines:
        extra_section = ["### 추가 체크리스트"] + [
            f"- {item}" for item in extra_guidelines
        ]
        extra_text = "\n".join(extra_section)
        guideline_prompt = (
            f"{guideline_prompt}\n\n{extra_text}" if guideline_prompt else extra_text
        )

    try:
        task = cli_ctx.controller.add_task_to_queue(
            description,
            template_id=template.template_id if template else None,
            persona_prompt=persona_prompt,
            guideline_prompt=guideline_prompt,
            notes=note,
            post_commands=post_commands,
        )
        if not cli_ctx.quiet:
            timestamp = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
            queue_size = len(cli_ctx.controller.list_queued_tasks())
            label = task.template_id or "custom"
            click.echo(f"✓ Queued task #{queue_size} [{label}]: {task.description}")
            click.echo(f"  Added at: {timestamp}")
            if template and not cli_ctx.quiet:
                click.echo(f"  Template: {template.template_id}")
            if note:
                click.echo(f"  Note: {note}")
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
        label = task.template_id or "custom"
        click.echo(f"{idx}. [{label}] {task.description}  (added {timestamp})")
        if task.notes:
            click.echo(f"    note: {task.notes}")


@queue.command()
@click.argument("indices", nargs=-1)
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
@click.option("--confirm", is_flag=True, help="Confirm clearing without prompt")
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


@queue.command(name="templates")
@click.pass_context
def list_templates(ctx):
    """List available task templates."""
    cli_ctx = ctx.find_root().obj
    template_manager = getattr(cli_ctx, "template_manager", None)

    if not template_manager:
        click.echo("No templates configured.")
        return

    templates = template_manager.available_templates()
    if not templates:
        click.echo("No templates configured.")
        return

    click.echo("=== Available Templates ===")
    for template in templates:
        click.echo(f"- {template.template_id}")
        if template.persona_prompt:
            first_line = template.persona_prompt.splitlines()[0]
            click.echo(f"  Persona: {first_line}")
        if template.quality_guidelines:
            click.echo("  Quality checks:")
            for guideline in template.quality_guidelines:
                click.echo(f"    • {guideline}")
        if template.post_commands:
            click.echo(f"  Post commands: {'; '.join(template.post_commands)}")
