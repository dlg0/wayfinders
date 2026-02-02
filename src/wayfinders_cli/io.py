from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def read_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {p}")
    return data


def load_model(model_cls: type[T], path: str | Path) -> T:
    return model_cls.model_validate(read_yaml(path))
