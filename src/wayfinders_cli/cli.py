from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .validate import validate_episode
from .placeholders import create_placeholders
from .plan import build_plan
from .schema import Episode
from .render.animatic_stub import build_animatic_from_placeholders
from .render.timeline import write_timeline, export_timeline_jsonschema

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
):
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in title).strip("_")
    slug = "_".join([s for s in slug.split("_") if s])[:64]
    ep_id = f"s{season:02d}e{episode:02d}"
    ep_dir = Path("episodes") / f"{ep_id}_{slug}"
    if ep_dir.exists():
        console.print(f"[bold red]Episode already exists:[/bold red] {ep_dir}")
        raise typer.Exit(code=2)

    (ep_dir / "assets").mkdir(parents=True, exist_ok=True)
    (ep_dir / "renders").mkdir(parents=True, exist_ok=True)
    (ep_dir / "logs").mkdir(parents=True, exist_ok=True)
    (ep_dir / "assets" / ".keep").write_text("", encoding="utf-8")
    (ep_dir / "renders" / ".keep").write_text("", encoding="utf-8")
    (ep_dir / "logs" / ".keep").write_text("", encoding="utf-8")

    (ep_dir / "episode.yaml").write_text(
        (
            f'id: "{ep_id}"\n'
            f'title: "{title}"\n'
            f"runtime_target_sec: {runtime_target_sec}\n"
            f'biome: "{biome}"\n'
            "cast: [charlie, spencer, fletcher, fold]\n"
            'style_profile: "comic_low_fps_v1"\n'
            "render:\n  fps: 24\n  resolution: [1920, 1080]\n"
            "assets:\n"
            "  pose_packs:\n"
            "    - posepack_charlie_v1\n"
            "    - posepack_spencer_v1\n"
            "    - posepack_fletcher_v1\n"
            "    - posepack_fold_v1\n"
            f'  bg_pack: "{biome}_v1"\n'
            '  overlay_pack: "overlays_v1"\n'
            "notes:\n"
            '  rule_of_day: "TBD"\n'
            '  logline: "TBD"\n'
        ),
        encoding="utf-8",
    )
    (ep_dir / "shotlist.yaml").write_text("version: 1\nshots: []\n", encoding="utf-8")
    (ep_dir / "dialogue.md").write_text(f"# {ep_id} Dialogue\n\n", encoding="utf-8")
    console.print(f"[bold green]Created[/bold green] {ep_dir}")


@app.command("build-timeline")
def build_timeline_cmd(episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False)):
    out = write_timeline(episode_yaml)
    console.print(f"Wrote {out}")


@app.command("build-animatic")
def build_animatic_cmd(episode_yaml: Path = typer.Argument(..., exists=True, dir_okay=False)):
    out = build_animatic_from_placeholders(episode_yaml)
    console.print(f"Wrote {out}")


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


if __name__ == "__main__":
    app()
