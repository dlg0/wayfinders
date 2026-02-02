from __future__ import annotations

from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader, StrictUndefined


class PromptResolver:
    def __init__(self, templates_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, params: dict[str, Any]) -> str:
        tpl = self.env.get_template(template_name)
        return tpl.render(**params).strip() + "\n"
