"""Command line interface for AI B-Roll Autopilot."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.core.job import Job, JobState
from ai_broll_autopilot.orchestrator import Orchestrator

console = Console(legacy_windows=False)


def setup_cli_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
    )
    # Silence noisy libraries
    for lib in ("google_genai", "httpx", "urllib3", "yt_dlp"):
        logging.getLogger(lib).setLevel(logging.WARNING)


async def cmd_run(args):
    setup_cli_logging()
    video_path = Path(args.video_file).resolve()
    if not video_path.exists():
        console.print(f"[red]Error: Video file not found: {video_path}[/red]")
        sys.exit(1)

    console.print(f"[bold green]Starting AI B-Roll Autopilot for:[/bold green] {video_path.name}")
    orchestrator = Orchestrator()
    campaign_id = getattr(args, "campaign", "default")
    job = Job.create(str(video_path), campaign_id=campaign_id)
    if getattr(args, "moment", None):
        job.moment_id = args.moment
    orchestrator.db.save_job(job)

    # Process job directly
    await orchestrator.process_job(job)

    # Print final result
    updated_job = orchestrator.db.get_job(job.job_id)
    if updated_job.status == JobState.COMPLETED:
        console.print(f"\n[bold green]SUCCESS: Final video generated![/bold green]")
        console.print(f"[cyan]Output File:[/cyan] {updated_job.output_video_path}")
        if updated_job.drive_file_url:
            console.print(f"[cyan]Google Drive:[/cyan] {updated_job.drive_file_url}")
    else:
        console.print(f"\n[bold red]FAILED: Job exited with status {updated_job.status.value}[/bold red]")
        console.print(f"[red]Error:[/red] {updated_job.error_message}")


async def cmd_watch(args):
    setup_cli_logging()
    console.print("[bold cyan]Starting AI B-Roll Autopilot Watcher Daemon...[/bold cyan]")
    console.print(f"[yellow]Monitoring input directory:[/yellow] {Config.INPUT_DIR}")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    orchestrator = Orchestrator()
    await orchestrator.start()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping autopilot daemon...[/yellow]")
        await orchestrator.stop()
        console.print("[green]Daemon stopped cleanly.[/green]")


def cmd_list(args):
    db = Database()
    jobs = db.list_jobs(limit=args.limit, status=args.status)

    if not jobs:
        console.print("[yellow]No jobs found in database.[/yellow]")
        return

    table = Table(title="AI B-Roll Autopilot Jobs")
    table.add_column("Job ID", style="cyan", no_wrap=True)
    table.add_column("Source Video", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Progress", style="magenta")
    table.add_column("Created", style="dim")
    table.add_column("Output File", style="green")

    for j in jobs:
        status_color = "green" if j.status == JobState.COMPLETED else ("red" if j.status == JobState.FAILED else "yellow")
        table.add_row(
            j.job_id,
            j.source_filename,
            f"[{status_color}]{j.status.value}[/{status_color}]",
            f"{int(j.progress * 100)}%",
            j.created_at[:19].replace("T", " "),
            Path(j.output_video_path).name if j.output_video_path else "-"
        )

    console.print(table)


def cmd_inspect(args):
    db = Database()
    job = db.get_job(args.job_id)
    if not job:
        console.print(f"[red]Error: Job not found: {args.job_id}[/red]")
        return

    console.print(f"[bold cyan]Job Inspection:[/bold cyan] {job.job_id}")
    console.print(f"Source: {job.source_file}")
    console.print(f"Status: {job.status.value} (Progress: {int(job.progress * 100)}%)")
    console.print(f"Created: {job.created_at}")
    console.print(f"Updated: {job.updated_at}")
    if job.error_message:
        console.print(f"[red]Error:[/red] {job.error_message}")
    if job.output_video_path:
        console.print(f"[green]Final Output:[/green] {job.output_video_path}")

    if job.edit_plan and "shots" in job.edit_plan:
        console.print(f"\n[bold yellow]Visual Edit Plan ({len(job.edit_plan['shots'])} shots):[/bold yellow]")
        for s in job.edit_plan["shots"]:
            st = s.get("start_time")
            et = s.get("end_time")
            sty = s.get("style")
            pr = s.get("search_prompt")
            console.print(f"  - {st}s to {et}s ({sty}): {pr}")

    if job.review_data:
        console.print(f"\n[bold magenta]AI Review Report:[/bold magenta]")
        console.print(f"  Score: {job.review_data.get('score')}/10 | Verdict: {job.review_data.get('verdict')}")
        console.print(f"  Feedback: {job.review_data.get('feedback')}")


def cmd_feedback(args):
    from ai_broll_autopilot.services.learning import feedback_engine
    feedback_engine.record_job_feedback(
        job_id=args.job_id,
        shot_id=args.shot_id or "all",
        clip_title=args.title or "broll",
        emotional_score=args.score or 10,
        user_rating=args.rating,
        user_feedback=args.feedback,
        theme=args.theme,
        preferred_metaphor=args.preferred,
        avoided_metaphor=args.avoided
    )
    console.print(f"[bold green]Successfully saved user feedback and updated learning memory for future edits![/bold green]")


def main():
    parser = argparse.ArgumentParser(description="AI B-Roll Autopilot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    p_run = subparsers.add_parser("run", help="Process a video file end-to-end")
    p_run.add_argument("video_file", help="Path to input video file")
    p_run.add_argument("--campaign", type=str, default="default", help="Campaign preset ID (e.g. curious_mike)")
    p_run.add_argument("--moment", type=str, default=None, help="Curated moment ID (e.g. C04)")

    # watch command
    p_watch = subparsers.add_parser("watch", help="Start background input folder watcher")

    # list command
    p_list = subparsers.add_parser("list", help="List recent jobs")
    p_list.add_argument("--limit", type=int, default=20, help="Number of jobs to show")
    p_list.add_argument("--status", type=str, default=None, help="Filter by JobState")

    # inspect command
    p_inspect = subparsers.add_parser("inspect", help="Inspect job details and edit plan")
    p_inspect.add_argument("job_id", help="Job ID")

    # feedback command
    p_feed = subparsers.add_parser("feedback", help="Submit feedback and teach learning engine")
    p_feed.add_argument("job_id", help="Job ID to provide feedback for")
    p_feed.add_argument("--rating", type=int, required=True, help="User rating 1-10 for emotional connection")
    p_feed.add_argument("--feedback", type=str, required=True, help="User feedback and guidance")
    p_feed.add_argument("--shot_id", type=str, default="all", help="Shot ID (e.g. broll_1)")
    p_feed.add_argument("--title", type=str, default="", help="Clip title")
    p_feed.add_argument("--score", type=int, default=10, help="Emotional score")
    p_feed.add_argument("--theme", type=str, default=None, help="Thematic category")
    p_feed.add_argument("--preferred", type=str, default=None, help="Preferred visual metaphor")
    p_feed.add_argument("--avoided", type=str, default=None, help="Avoided visual metaphor")

    # serve command
    p_serve = subparsers.add_parser("serve", help="Start FastAPI REST API server for Next.js web dashboard")
    p_serve.add_argument("--host", type=str, default="0.0.0.0", help="Host interface to bind to")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to listen on")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(cmd_run(args))
    elif args.command == "watch":
        asyncio.run(cmd_watch(args))
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("ai_broll_autopilot.api.app:app", host=args.host, port=args.port, reload=False)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "feedback":
        cmd_feedback(args)


if __name__ == "__main__":
    main()
