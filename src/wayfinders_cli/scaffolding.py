"""Episode scaffolding using Jinja templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader, StrictUndefined


@dataclass
class ScaffoldResult:
    """Result of scaffold generation."""

    ep_dir: Path
    files_created: list[str]


def _create_template_env(template_dir: Optional[Path] = None) -> Environment:
    """Create Jinja environment with StrictUndefined.

    Args:
        template_dir: Optional custom template directory. If None, uses package templates.
    """
    if template_dir:
        from jinja2 import FileSystemLoader

        return Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=StrictUndefined,
        )
    return Environment(
        loader=PackageLoader("wayfinders_cli", "templates"),
        undefined=StrictUndefined,
    )


def render_episode_scaffold(
    ep_dir: Path,
    ep_id: str,
    title: str,
    biome: str,
    runtime_target_sec: int,
    cast: list[str],
    style_profile: str = "comic_low_fps_v1",
    template_dir: Optional[Path] = None,
    force: bool = False,
) -> ScaffoldResult:
    """Render episode scaffold using Jinja templates.

    Args:
        ep_dir: Episode directory to create.
        ep_id: Episode identifier (e.g., "s01e05").
        title: Episode title.
        biome: Environment biome ID.
        runtime_target_sec: Target runtime in seconds.
        cast: List of character IDs.
        style_profile: Style profile ID.
        template_dir: Optional custom template directory.
        force: If True, overwrite existing episode directory.

    Returns:
        ScaffoldResult with created directory and files.

    Raises:
        FileExistsError: If ep_dir exists and force=False.
    """
    if ep_dir.exists() and not force:
        raise FileExistsError(f"Episode directory already exists: {ep_dir}")

    env = _create_template_env(template_dir)

    params = {
        "ep_id": ep_id,
        "title": title,
        "biome": biome,
        "runtime_target_sec": runtime_target_sec,
        "cast": cast,
        "style_profile": style_profile,
    }

    (ep_dir / "assets").mkdir(parents=True, exist_ok=True)
    (ep_dir / "renders").mkdir(parents=True, exist_ok=True)
    (ep_dir / "logs").mkdir(parents=True, exist_ok=True)
    (ep_dir / "assets" / ".keep").write_text("", encoding="utf-8")
    (ep_dir / "renders" / ".keep").write_text("", encoding="utf-8")
    (ep_dir / "logs" / ".keep").write_text("", encoding="utf-8")

    files_created = []

    episode_template = env.get_template("episode.yaml.j2")
    episode_content = episode_template.render(**params)
    (ep_dir / "episode.yaml").write_text(episode_content, encoding="utf-8")
    files_created.append("episode.yaml")

    shotlist_template = env.get_template("shotlist.yaml.j2")
    shotlist_content = shotlist_template.render(**params)
    (ep_dir / "shotlist.yaml").write_text(shotlist_content, encoding="utf-8")
    files_created.append("shotlist.yaml")

    readme_template = env.get_template("README.md.j2")
    readme_content = readme_template.render(**params)
    (ep_dir / "README.md").write_text(readme_content, encoding="utf-8")
    files_created.append("README.md")

    return ScaffoldResult(ep_dir=ep_dir, files_created=files_created)
