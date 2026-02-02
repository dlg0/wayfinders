from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, UndefinedError

from wayfinders_cli.gen.provenance import now_utc_iso


class PromptResolutionError(Exception):
    """Raised when a prompt template cannot be resolved."""

    pass


@dataclass
class ResolvedPrompt:
    """Container for a resolved prompt with its metadata."""

    template_name: str
    params: dict[str, Any]
    resolved_text: str


class PromptResolver:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, params: dict[str, Any]) -> str:
        """Render a template and return the resolved text.

        Raises:
            PromptResolutionError: If template not found or variable undefined.
        """
        try:
            tpl = self.env.get_template(template_name)
            return tpl.render(**params).strip() + "\n"
        except TemplateNotFound as e:
            raise PromptResolutionError(
                f"Template '{template_name}' not found in {self.templates_dir}"
            ) from e
        except UndefinedError as e:
            raise PromptResolutionError(
                f"Undefined variable in template '{template_name}': {e}"
            ) from e

    def resolve(self, template_name: str, params: dict[str, Any]) -> ResolvedPrompt:
        """Resolve a prompt and return both template name and resolved text.

        Raises:
            PromptResolutionError: If template not found or variable undefined.
        """
        resolved_text = self.render(template_name, params)
        return ResolvedPrompt(
            template_name=template_name,
            params=params,
            resolved_text=resolved_text,
        )


def log_resolved_prompt(
    episode_dir: Path,
    asset_id: str,
    resolved_prompt: ResolvedPrompt,
) -> Path:
    """Log a resolved prompt to the episode's prompts log directory.

    Writes atomically (via temp file + rename) to avoid partial writes.

    Args:
        episode_dir: Path to the episode directory (e.g., episodes/s01e01_...)
        asset_id: Unique identifier for the asset (used as filename)
        resolved_prompt: The resolved prompt to log

    Returns:
        Path to the written log file.
    """
    prompts_dir = episode_dir / "logs" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    log_path = prompts_dir / f"{asset_id}.json"

    payload = {
        "asset_id": asset_id,
        "template_name": resolved_prompt.template_name,
        "params": resolved_prompt.params,
        "resolved_prompt": resolved_prompt.resolved_text,
        "timestamp": now_utc_iso(),
    }

    content = json.dumps(payload, indent=2, ensure_ascii=False)

    fd, tmp_path = tempfile.mkstemp(dir=prompts_dir, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, log_path)
    except Exception:
        os.close(fd)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    return log_path
