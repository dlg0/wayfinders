from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ContentHash:
    algo: str
    value: str

    def short(self, n: int = 12) -> str:
        return self.value[:n]


def hash_dict(d: dict[str, Any]) -> ContentHash:
    return ContentHash("sha256", sha256_text(stable_json(d)))
