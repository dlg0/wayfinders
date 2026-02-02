from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .validate import validate_episode
from .placeholders import create_placeholders
from .plan import build_plan
from .schema import Episode
from .render.animatic_stub import build_animatic_from_placeholders
from .render.timeline import write_timeline, export_timeline_jsonschema
from .gen.generate import generate_episode_assets
from .scaffolding import render_episode_scaffold
from .build import build_final as do_build_final
from .qc.checker import QCChecker
from .qc.report import generate_qc_report, generate_cost_report
from .provenance.bundle import create_provenance_bundle

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command()
def validate(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    allow_missing_assets: bool = typer.Option(False, "--allow-missing-assets"),
):
    res = validate_episode(episode_yaml, allow_missing_assets=allow_missing_assets)
    if res.errors:
        console.print("[bold red]Errors[/bold red]")
        for e in res.errors:
            console.print(f"- {e}")
    if res.missing_files:
        console.print("[bold yellow]Missing asset files[/bold yellow]")
        for m in sorted(set(res.missing_files)):
            console.print(f"- {m}")
    if res.ok:
        console.print("[bold green]OK[/bold green]")
        raise typer.Exit(code=0)
    raise typer.Exit(code=2 if res.errors else 3)


@app.command()
def plan(episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False)):
    payload = build_plan(episode_yaml)
    logs_dir = episode_yaml.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "plan.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print_json(json.dumps(payload))


@app.command()
def placeholders(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    force: bool = typer.Option(False, "--force"),
):
    res = create_placeholders(episode_yaml, force=force)
    table = Table(title="Placeholder generation")
    table.add_column("Created")
    table.add_column("Skipped")
    table.add_row(str(len(res.created)), str(len(res.skipped)))
    console.print(table)


@app.command("new-episode")
def new_episode(
    season: int = typer.Argument(..., min=1, max=99),
    episode: int = typer.Argument(..., min=1, max=99),
    title: str = typer.Option(..., "--title"),
    biome: str = typer.Option("windglass_plains", "--biome"),
    runtime_target_sec: int = typer.Option(780, "--runtime"),
    template_dir: Path = typer.Option(None, "--template", help="Custom template directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing episode"),
):
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in title).strip("_")
    slug = "_".join([s for s in slug.split("_") if s])[:64]
    ep_id = f"s{season:02d}e{episode:02d}"
    ep_dir = Path("episodes") / f"{ep_id}_{slug}"
    cast = ["charlie", "spencer", "fletcher", "fold"]

    try:
        result = render_episode_scaffold(
            ep_dir=ep_dir,
            ep_id=ep_id,
            title=title,
            biome=biome,
            runtime_target_sec=runtime_target_sec,
            cast=cast,
            template_dir=template_dir,
            force=force,
        )
    except FileExistsError as e:
        console.print(f"[bold red]Episode already exists:[/bold red] {ep_dir}")
        console.print("Use --force to overwrite.")
        raise typer.Exit(code=2) from e

    console.print(f"[bold green]Created[/bold green] {result.ep_dir}")
    console.print(f"Files: {', '.join(result.files_created)}")

    validation_result = validate_episode(ep_dir / "episode.yaml", allow_missing_assets=True)
    if validation_result.ok:
        console.print("[bold green]Validation passed[/bold green]")
    else:
        console.print("[bold yellow]Validation warnings:[/bold yellow]")
        for e in validation_result.errors:
            console.print(f"  - {e}")


@app.command("build")
def build_final_cmd(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    force: bool = typer.Option(False, "--force", help="Force regenerate all assets"),
    skip_validation: bool = typer.Option(False, "--skip-validation", help="Skip validation stage"),
    skip_qc: bool = typer.Option(False, "--skip-qc", help="Skip QC check stage"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
):
    """Run the full build pipeline: validate → generate → timeline → render → assemble → qc."""
    if dry_run:
        console.print("[bold cyan]Dry run mode[/bold cyan] - showing planned stages:")
        result = do_build_final(episode_yaml, force=force, skip_validation=skip_validation, skip_qc=skip_qc, dry_run=True)
        for stage in result.stages_completed:
            console.print(f"  → {stage}")
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[bold]Building[/bold] {episode_yaml}")
    result = do_build_final(episode_yaml, force=force, skip_validation=skip_validation, skip_qc=skip_qc)

    for sr in result.stage_results:
        status = "[green]✓[/green]" if sr.success else "[red]✗[/red]"
        console.print(f"  {status} {sr.name} ({sr.duration_sec:.2f}s): {sr.message}")

    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in result.warnings:
            console.print(f"  - {w}")

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for e in result.errors:
            console.print(f"  - {e}")

    if result.success:
        console.print("\n[bold green]Build complete[/bold green]")
        if result.output_path:
            console.print(f"Output: {result.output_path}")
        raise typer.Exit(code=0)
    else:
        console.print("\n[bold red]Build failed[/bold red]")
        raise typer.Exit(code=1)


@app.command("build-timeline")
def build_timeline_cmd(episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False)):
    out = write_timeline(episode_yaml)
    console.print(f"Wrote {out}")


@app.command("build-animatic")
def build_animatic_cmd(episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False)):
    out = build_animatic_from_placeholders(episode_yaml)
    console.print(f"Wrote {out}")


@app.command("gen")
def gen_assets(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    force: bool = typer.Option(False, "--force", help="Regenerate all assets"),
    changed_only: bool = typer.Option(False, "--changed", help="Only generate changed assets"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Override default provider"),
):
    """Generate assets for an episode using the configured provider."""
    result = generate_episode_assets(
        episode_yaml,
        force=force,
        changed_only=changed_only,
        provider_override=provider,
    )

    table = Table(title="Asset Generation")
    table.add_column("Generated", style="green")
    table.add_column("Skipped", style="yellow")
    table.add_column("Errors", style="red")
    table.add_row(
        str(len(result.generated)),
        str(len(result.skipped)),
        str(len(result.errors)),
    )
    console.print(table)

    if result.generated:
        console.print("\n[bold green]Generated:[/bold green]")
        for asset_id in result.generated:
            console.print(f"  - {asset_id}")

    if result.skipped:
        console.print("\n[bold yellow]Skipped (cache hit):[/bold yellow]")
        for asset_id in result.skipped:
            console.print(f"  - {asset_id}")

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for asset_id, error in result.errors:
            console.print(f"  - {asset_id}: {error}")
        raise typer.Exit(code=1)


@app.command("qc")
def qc_cmd(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    report_only: bool = typer.Option(False, "--report-only", help="Generate reports without gating"),
):
    """Run QC checks on an episode."""
    import yaml

    checker = QCChecker()
    qc_result = checker.run(episode_yaml)

    ep_data = yaml.safe_load(episode_yaml.read_text(encoding="utf-8"))
    episode_id = ep_data.get("id", "unknown")
    logs_dir = episode_yaml.parent / "logs"

    json_path, md_path = generate_qc_report(qc_result, logs_dir, episode_id)
    cost_json, cost_md = generate_cost_report(logs_dir, logs_dir)

    console.print(f"[bold]QC Report:[/bold] {json_path}")
    console.print(f"[bold]Cost Report:[/bold] {cost_json}")

    status = "[green]PASSED[/green]" if qc_result.passed else "[red]FAILED[/red]"
    console.print(f"\n[bold]Status:[/bold] {status}")

    if qc_result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for e in qc_result.errors:
            console.print(f"  - {e}")

    if qc_result.warnings:
        console.print(f"\n[bold yellow]Warnings ({len(qc_result.warnings)}):[/bold yellow]")
        for w in qc_result.warnings[:10]:
            console.print(f"  - {w}")
        if len(qc_result.warnings) > 10:
            console.print(f"  ... and {len(qc_result.warnings) - 10} more")

    if report_only:
        raise typer.Exit(code=0)

    if not qc_result.passed:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


canon_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(canon_app, name="canon")


@canon_app.command("export-jsonschema")
def export_episode_schema(out_dir: Path = typer.Option(Path("docs/jsonschema"), "--out-dir")):
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = Episode.model_json_schema()
    out_path = out_dir / "episode.schema.json"
    out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    console.print(f"Wrote {out_path}")


render_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(render_app, name="render")


@render_app.command("export-jsonschema")
def export_timeline_schema(out_dir: Path = typer.Option(Path("docs/jsonschema"), "--out-dir")):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "timeline.schema.json"
    export_timeline_jsonschema(out_path)
    console.print(f"Wrote {out_path}")


@app.command("bundle")
def bundle_cmd(
    episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False),
    include_prompts: Optional[Path] = typer.Option(
        None, "--include-prompts", help="Include source prompts directory"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path for bundle zip"
    ),
):
    """Create a provenance bundle for an episode."""
    bundle_path = create_provenance_bundle(
        episode_yaml,
        output_path=output,
        include_prompts_dir=include_prompts,
    )
    console.print(f"[bold green]Created[/bold green] {bundle_path}")


if __name__ == "__main__":
    app()
