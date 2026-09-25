"""Command line interface for Stockpile AI Video Intelligence & OpenReel Integration."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.core.job import Job, JobState
from ai_broll_autopilot.orchestrator import Orchestrator
from ai_broll_autopilot.niches import niche_registry
from ai_broll_autopilot.styles import style_registry
from ai_broll_autopilot.services.niche_detector import niche_detector, content_analyzer
from ai_broll_autopilot.services.clip_detector import clip_detector
from ai_broll_autopilot.services.edit_director import edit_director
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter
from ai_broll_autopilot.services.broll_library import broll_library, extract_media_metadata
from ai_broll_autopilot.services.transcriber import Transcriber

console = Console(legacy_windows=False)


def setup_cli_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
    )
    for lib in ("google_genai", "httpx", "urllib3", "yt_dlp"):
        logging.getLogger(lib).setLevel(logging.WARNING)


async def _get_transcription(file_path: Path):
    """Helper to get transcript text and segments for a video file."""
    transcriber = Transcriber()
    with console.status(f"[bold cyan]Transcribing {file_path.name}...[/bold cyan]"):
        result = await transcriber.transcribe(str(file_path))
    return result


def cmd_niches(args):
    """List all registered content niches."""
    profiles = niche_registry.list_profiles()
    table = Table(title="Registered Content Niches (Stockpile AI Brain)")
    table.add_column("Niche ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold white")
    table.add_column("Parent", style="magenta")
    table.add_column("Pace", style="yellow")
    table.add_column("Max B-Roll", style="green")
    table.add_column("Top Visual Keywords", style="dim")

    for p in profiles:
        kws = ", ".join(p.visual_keywords[:5])
        table.add_row(
            p.id,
            p.name,
            p.parent_niche,
            p.editing.pace,
            f"{int(p.editing.max_broll_ratio * 100)}%",
            kws,
        )
    console.print(table)


def cmd_styles(args):
    """List all registered visual styles."""
    styles = style_registry.list_styles()
    table = Table(title="Registered Visual Styles (OpenReel Compatible)")
    table.add_column("Style ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold white")
    table.add_column("Font", style="yellow")
    table.add_column("Highlight", style="green")
    table.add_column("Captions", style="magenta")
    table.add_column("B-Roll Pacing", style="white")

    for s in styles:
        table.add_row(
            s.id,
            s.name,
            f"{s.font_family} ({s.font_size}px)",
            s.highlight_color,
            s.caption_animation_style,
            f"{s.broll_cut_pacing} (~{s.default_broll_duration}s)",
        )
    console.print(table)


async def cmd_analyze(args):
    """Analyze video for niche, topic entities, and emotional moments."""
    video_path = Path(args.video_file).resolve()
    if not video_path.exists():
        console.print(f"[red]Error: File not found: {video_path}[/red]")
        sys.exit(1)

    t_res = await _get_transcription(video_path)
    full_text = t_res.get("text", "")
    segments = t_res.get("segments", [])

    meta = extract_media_metadata(video_path)

    # 1. Niche Detection
    niche_res = await niche_detector.detect_niche(full_text, title=video_path.stem)
    # 2. Content Understanding
    content_res = await content_analyzer.analyze_content(segments, {"title": video_path.stem})

    console.print(Panel(
        f"[bold green]Niche:[/bold green] {niche_res.niche_name} ([cyan]{niche_res.niche_id}[/cyan])\n"
        f"[bold yellow]Confidence:[/bold yellow] {niche_res.confidence * 100:.1f}%\n"
        f"[bold blue]Suggested Style:[/bold blue] {niche_res.suggested_style_id}\n"
        f"[bold magenta]Detected Keywords:[/bold magenta] {', '.join(niche_res.detected_keywords)}\n"
        f"[dim]{niche_res.explanation}[/dim]",
        title=f"Niche Analysis: {video_path.name}",
    ))

    console.print(Panel(
        f"[bold]Summary:[/bold] {content_res.summary}\n"
        f"[bold]Core Topics:[/bold] {', '.join(content_res.core_topics)}\n"
        f"[bold]Key Entities:[/bold] {', '.join(content_res.key_entities)}\n"
        f"[bold]High Energy Moments:[/bold] {len(content_res.high_energy_moments)} detected",
        title="Content Understanding",
    ))


async def cmd_detect_clips(args):
    """Detect and rank viral short clips using 9-factor virality framework."""
    video_path = Path(args.video_file).resolve()
    if not video_path.exists():
        console.print(f"[red]Error: File not found: {video_path}[/red]")
        sys.exit(1)

    t_res = await _get_transcription(video_path)
    segments = t_res.get("segments", [])
    meta = extract_media_metadata(video_path)
    dur = meta.get("duration") or (segments[-1]["end"] if segments else 60.0)

    # Detect Niche
    niche_res = await niche_detector.detect_niche(t_res.get("text", ""))

    clips = await clip_detector.detect_clips(
        transcript_segments=segments,
        video_duration=dur,
        target_clip_count=args.count,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        niche_id=niche_res.niche_id,
    )

    if not clips:
        console.print("[yellow]No suitable viral clips detected.[/yellow]")
        return

    table = Table(title=f"Top Viral Clips ({video_path.name}) - Niche: {niche_res.niche_name}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Time Window", style="green")
    table.add_column("Dur", style="yellow")
    table.add_column("Viral Score", style="bold magenta")
    table.add_column("Title / Hook", style="white")
    table.add_column("Hook Score", style="dim")

    for c in clips:
        table.add_row(
            c.id,
            f"{c.start_time:.1f}s - {c.end_time:.1f}s",
            f"{c.duration:.1f}s",
            f"{c.viral_score:.1f}/100",
            f"[bold]{c.title}[/bold]\n[dim]\"{c.hook_text}\"[/dim]",
            f"{c.factor_scores.get('hook_strength', 0):.0f}",
        )
    console.print(table)


async def cmd_generate_edit(args):
    """Generate declarative edit plan for video or selected clip."""
    video_path = Path(args.video_file).resolve()
    if not video_path.exists():
        console.print(f"[red]Error: File not found: {video_path}[/red]")
        sys.exit(1)

    t_res = await _get_transcription(video_path)
    segments = t_res.get("segments", [])
    meta = extract_media_metadata(video_path)
    meta["path"] = str(video_path)

    # Resolve Niche & Style
    niche_id = args.niche
    if not niche_id:
        niche_res = await niche_detector.detect_niche(t_res.get("text", ""))
        niche_id = niche_res.niche_id
        console.print(f"[cyan]Auto-detected Niche:[/cyan] {niche_res.niche_name} ({niche_id})")

    style_id = args.style
    if not style_id:
        style_id = niche_detector.detect_niche(t_res.get("text", ""))
        from ai_broll_autopilot.services.niche_detector import NICHE_TO_STYLE_MAP
        style_id = NICHE_TO_STYLE_MAP.get(niche_id, "clean_podcast")
        console.print(f"[cyan]Selected Style:[/cyan] {style_id}")

    in_pt = args.start if args.start is not None else 0.0
    out_pt = args.end if args.end is not None else meta.get("duration", 60.0)

    plan = await edit_director.plan_edit(
        source_media=meta,
        transcript_segments=segments,
        in_point=in_pt,
        out_point=out_pt,
        niche_id=niche_id,
        style_id=style_id,
        custom_hook=args.hook,
    )

    out_dir = Path(args.output_dir) if args.output_dir else (Config.OUTPUT_DIR / "plans" / plan.plan_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "edit_plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan.to_dict(), f, indent=2)

    console.print(Panel(
        f"[bold green]Edit Plan Generated Successfully![/bold green]\n"
        f"[bold]Plan ID:[/bold] {plan.plan_id}\n"
        f"[bold]Clip Interval:[/bold] {in_pt:.1f}s to {out_pt:.1f}s ({plan.target_duration:.1f}s)\n"
        f"[bold]Niche:[/bold] {plan.niche.get('name')} | [bold]Style:[/bold] {plan.style.get('name')}\n"
        f"[bold]B-Roll Cutaways:[/bold] {len(plan.shots)} shots\n"
        f"[bold]Subtitles:[/bold] {len(plan.subtitles)} lines with word highlights\n"
        f"[bold]Text Overlays:[/bold] {len(plan.text_overlays)} graphics\n"
        f"[bold]Punch-in Zooms:[/bold] {len(plan.zooms)}\n"
        f"[bold cyan]Plan File:[/bold cyan] {plan_path}",
        title="Stockpile Edit Director",
    ))


async def cmd_export_openreel(args):
    """Export native OpenReel Schema 1.2.0 project (.oreel / project.json) ready for editing."""
    target_path = Path(args.target).resolve()
    if not target_path.exists():
        console.print(f"[red]Error: Target file not found: {target_path}[/red]")
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else (Config.OUTPUT_DIR / "openreel_projects" / target_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    if target_path.suffix.lower() == ".json":
        # Load existing edit plan
        with open(target_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        from ai_broll_autopilot.services.edit_director import EditPlan
        plan = EditPlan(
            plan_id=plan_data.get("plan_id", "plan_loaded"),
            title=plan_data.get("title", "Imported Clip"),
            target_duration=plan_data.get("target_duration", 30.0),
            source_media=plan_data.get("source_media", {}),
            clip_interval=plan_data.get("clip_interval", {"in_point": 0.0, "out_point": 30.0}),
            niche=plan_data.get("niche", {}),
            style=plan_data.get("style", {}),
            shots=plan_data.get("shots", []),
            text_overlays=plan_data.get("text_overlays", []),
            subtitles=plan_data.get("subtitles", []),
            zooms=plan_data.get("zooms", []),
            audio_cues=plan_data.get("audio_cues", {}),
        )
    else:
        # It's a video file, generate edit plan first
        t_res = await _get_transcription(target_path)
        meta = extract_media_metadata(target_path)
        meta["path"] = str(target_path)
        niche_res = await niche_detector.detect_niche(t_res.get("text", ""))
        from ai_broll_autopilot.services.niche_detector import NICHE_TO_STYLE_MAP
        style_id = NICHE_TO_STYLE_MAP.get(niche_res.niche_id, "clean_podcast")

        plan = await edit_director.plan_edit(
            source_media=meta,
            transcript_segments=t_res.get("segments", []),
            in_point=0.0,
            out_point=min(meta.get("duration", 45.0), 45.0),
            niche_id=niche_res.niche_id,
            style_id=style_id,
        )

    # Export OpenReel project bundle
    files = openreel_adapter.export_project_files(plan, out_dir)

    console.print(Panel(
        f"[bold green]OpenReel Project Exported Successfully![/bold green]\n\n"
        f"[bold cyan]OpenReel Project File (.oreel):[/bold cyan] {files['oreel']}\n"
        f"[bold cyan]OpenReel JSON (project.json):[/bold cyan] {files['project_json']}\n"
        f"[bold cyan]Project Manifest:[/bold cyan] {files['manifest']}\n"
        f"[bold cyan]Edit Plan:[/bold cyan] {files['plan']}\n\n"
        f"[yellow]To edit this project in OpenReel:[/yellow]\n"
        f"1. Start OpenReel web editor (`pnpm --filter @openreel/web dev`)\n"
        f"2. Open {files['oreel']} via File -> Open Project, or pass manifest to OpenReel host.",
        title="OpenReel Integration",
    ))


def cmd_qc(args):
    """Run Quality Control audit on an edit_plan.json or job."""
    from ai_broll_autopilot.services.qc_service import edit_quality_service
    from ai_broll_autopilot.services.edit_director import EditPlan

    target_path = Path(args.target).resolve()
    if not target_path.exists():
        console.print(f"[red]Error: File not found: {target_path}[/red]")
        sys.exit(1)

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    plan_data = data.get("edit_plan", data)
    plan = EditPlan(
        plan_id=plan_data.get("plan_id", "plan_qc"),
        title=plan_data.get("title", "QC Target"),
        target_duration=float(plan_data.get("target_duration") or plan_data.get("total_duration", 30.0)),
        source_media=plan_data.get("source_media", {}),
        clip_interval=plan_data.get("clip_interval", {"in_point": 0.0, "out_point": 30.0}),
        niche=plan_data.get("niche", {}),
        style=plan_data.get("style", {}),
        shots=plan_data.get("shots", []),
        text_overlays=plan_data.get("text_overlays", []),
        subtitles=plan_data.get("subtitles", []),
        zooms=plan_data.get("zooms", []),
        audio_cues=plan_data.get("audio_cues", {}),
    )

    report = edit_quality_service.evaluate_edit_plan(plan)
    status_str = "[bold green]PASSED[/bold green]" if report.passed else "[bold red]FAILED[/bold red]"
    console.print(Panel(
        f"[bold]Target:[/bold] {target_path.name}\n"
        f"[bold]Quality Score:[/bold] {report.overall_score:.1f}/100 ({status_str})\n"
        f"[bold]Checks Passed:[/bold] {sum(1 for c in report.checks if c.passed)}/{len(report.checks)}\n"
        f"[bold]Warnings:[/bold] {len(report.warnings)}",
        title="Stockpile Quality Control Audit",
    ))

    table = Table(title="Audit Checks Breakdown")
    table.add_column("Check", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Status", style="bold")
    table.add_column("Score", style="yellow")
    table.add_column("Message", style="white")

    for c in report.checks:
        c_status = "[green]PASS[/green]" if c.passed else f"[{'yellow' if c.severity == 'warning' else 'red'}]{c.severity.upper()}[/{'yellow' if c.severity == 'warning' else 'red'}]"
        table.add_row(
            c.name,
            c.category,
            c_status,
            f"{c.score * 100:.0f}%",
            c.message,
        )
    console.print(table)


def cmd_library(args):
    """Manage local B-Roll catalog."""
    subcmd = args.subcmd

    if subcmd == "stats":
        stats = broll_library.get_stats()
        console.print(Panel(
            f"[bold]Total Assets:[/bold] {stats['total_assets']}\n"
            f"[bold]Total Footage Duration:[/bold] {stats['total_duration_seconds']}s\n"
            f"[bold]Library Root:[/bold] {stats['library_path']}\n"
            f"[bold]Assets per Niche:[/bold] {json.dumps(stats['niche_counts'], indent=2)}",
            title="Local B-Roll Library Stats",
        ))
    elif subcmd == "index":
        target_dir = Path(args.dir).resolve()
        if not target_dir.exists():
            console.print(f"[red]Error: Directory not found: {target_dir}[/red]")
            return
        n_indexed = broll_library.index_directory(target_dir, niche_id=args.niche)
        console.print(f"[bold green]Successfully indexed {n_indexed} video assets into library![/bold green]")
    elif subcmd == "list":
        assets = broll_library.list_assets(niche_id=args.niche, limit=args.limit)
        if not assets:
            console.print("[yellow]No assets found in library matching criteria.[/yellow]")
            return
        table = Table(title=f"Local B-Roll Assets ({len(assets)})")
        table.add_column("Asset ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Niche", style="magenta")
        table.add_column("Duration", style="yellow")
        table.add_column("Resolution", style="green")
        table.add_column("Tags", style="dim")

        for a in assets:
            table.add_row(
                a.get("asset_id", ""),
                a.get("title", ""),
                a.get("niche_id", "generic"),
                f"{float(a.get('duration') or 0):.1f}s",
                f"{a.get('width', 0)}x{a.get('height', 0)}",
                ", ".join(a.get("tags") or []),
            )
        console.print(table)


# Legacy commands
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

    await orchestrator.process_job(job)
    updated_job = orchestrator.db.get_job(job.job_id)
    if updated_job.status == JobState.COMPLETED:
        console.print(f"\n[bold green]SUCCESS: Final video generated![/bold green]")
        console.print(f"[cyan]Output File:[/cyan] {updated_job.output_video_path}")
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
    if job.edit_plan and "shots" in job.edit_plan:
        console.print(f"\n[bold yellow]Visual Edit Plan ({len(job.edit_plan['shots'])} shots):[/bold yellow]")
        for s in job.edit_plan["shots"]:
            console.print(f"  - {s.get('start_time')}s to {s.get('end_time')}s ({s.get('style')}): {s.get('search_prompt') or s.get('search_query')}")


def main():
    parser = argparse.ArgumentParser(description="Stockpile AI Video Brain & OpenReel Integration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # niches command
    subparsers.add_parser("niches", help="List all registered content niches")

    # styles command
    subparsers.add_parser("styles", help="List all registered visual styles")

    # analyze command
    p_an = subparsers.add_parser("analyze", help="Analyze video for content niche and understanding")
    p_an.add_argument("video_file", help="Path to video or audio file")

    # detect-clips command
    p_dc = subparsers.add_parser("detect-clips", help="Detect viral short clip candidates with 9-factor scores")
    p_dc.add_argument("video_file", help="Path to input video file")
    p_dc.add_argument("--count", type=int, default=5, help="Number of viral clips to detect")
    p_dc.add_argument("--min-duration", type=float, default=25.0, help="Min clip length in seconds")
    p_dc.add_argument("--max-duration", type=float, default=75.0, help="Max clip length in seconds")

    # generate-edit command
    p_ge = subparsers.add_parser("generate-edit", help="Generate declarative Edit Plan")
    p_ge.add_argument("video_file", help="Path to input video file")
    p_ge.add_argument("--niche", type=str, default=None, help="Niche ID (or auto-detect)")
    p_ge.add_argument("--style", type=str, default=None, help="Style ID (or auto-select)")
    p_ge.add_argument("--start", type=float, default=None, help="Clip start in seconds")
    p_ge.add_argument("--end", type=float, default=None, help="Clip end in seconds")
    p_ge.add_argument("--hook", type=str, default=None, help="Custom hook title card text")
    p_ge.add_argument("--output-dir", type=str, default=None, help="Output folder for edit_plan.json")

    # export-openreel / export-project command
    p_eo = subparsers.add_parser("export-openreel", aliases=["export-project"], help="Export native OpenReel Schema 1.2.0 project (.oreel)")
    p_eo.add_argument("target", help="Path to video file OR edit_plan.json")
    p_eo.add_argument("--output-dir", type=str, default=None, help="Output directory for OpenReel files")

    # qc command
    p_qc = subparsers.add_parser("qc", help="Audit video edit plan for safe zones, readability, and pacing")
    p_qc.add_argument("target", help="Path to edit_plan.json or job project manifest")

    # library command
    p_lib = subparsers.add_parser("library", help="Manage local-first B-roll catalog")
    lib_sub = p_lib.add_subparsers(dest="subcmd", required=True)

    lib_stats = lib_sub.add_parser("stats", help="Get B-roll library statistics")
    lib_index = lib_sub.add_parser("index", help="Index video files in directory")
    lib_index.add_argument("dir", help="Directory path to scan and index")
    lib_index.add_argument("--niche", type=str, default=None, help="Assign specific niche ID")

    lib_list = lib_sub.add_parser("list", help="List cataloged B-roll assets")
    lib_list.add_argument("--niche", type=str, default=None, help="Filter by niche ID")
    lib_list.add_argument("--limit", type=int, default=50, help="Max assets to display")

    # Legacy commands preserved
    p_run = subparsers.add_parser("run", help="Legacy: Process a video file end-to-end")
    p_run.add_argument("video_file", help="Path to input video file")
    p_run.add_argument("--campaign", type=str, default="default")
    p_run.add_argument("--moment", type=str, default=None)

    subparsers.add_parser("watch", help="Start background input folder watcher")

    p_list = subparsers.add_parser("list", help="List recent jobs")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--status", type=str, default=None)

    p_ins = subparsers.add_parser("inspect", help="Inspect job details")
    p_ins.add_argument("job_id")

    p_srv = subparsers.add_parser("serve", help="Start FastAPI REST API server")
    p_srv.add_argument("--host", type=str, default="0.0.0.0")
    p_srv.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "niches":
        cmd_niches(args)
    elif args.command == "styles":
        cmd_styles(args)
    elif args.command == "analyze":
        asyncio.run(cmd_analyze(args))
    elif args.command == "detect-clips":
        asyncio.run(cmd_detect_clips(args))
    elif args.command == "generate-edit":
        asyncio.run(cmd_generate_edit(args))
    elif args.command in ("export-openreel", "export-project"):
        asyncio.run(cmd_export_openreel(args))
    elif args.command == "qc":
        cmd_qc(args)
    elif args.command == "library":
        cmd_library(args)
    elif args.command == "run":
        asyncio.run(cmd_run(args))
    elif args.command == "watch":
        asyncio.run(cmd_watch(args))
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("ai_broll_autopilot.api.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
