from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from ..schema import Episode, ShotList
from .rules import (
    Rule,
    RuleResult,
    DialogueLanguageCheck,
    RuntimeBoundsCheck,
    AssetCoverageCheck,
    CharacterConsistencyCheck,
    KidsContentCheck,
    IPChecklistReminder,
)


@dataclass
class QCResult:
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rule_results: list[RuleResult] = field(default_factory=list)

    def merge(self, other: RuleResult) -> None:
        self.rule_results.append(other)
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)
        if other.errors:
            self.passed = False


@dataclass
class QCContext:
    episode: Episode
    shotlist: Optional[ShotList]
    episode_dir: Path
    canon_characters: list[str] = field(default_factory=list)


class QCChecker:
    def __init__(self, rules: Optional[list[Rule]] = None):
        if rules is None:
            rules = self._default_rules()
        self.rules = rules

    def _default_rules(self) -> list[Rule]:
        return [
            DialogueLanguageCheck(),
            RuntimeBoundsCheck(),
            AssetCoverageCheck(),
            CharacterConsistencyCheck(),
            KidsContentCheck(),
            IPChecklistReminder(),
        ]

    def run(self, episode_yaml: Path) -> QCResult:
        result = QCResult(passed=True)
        ctx = self._build_context(episode_yaml, result)
        if ctx is None:
            return result

        for rule in self.rules:
            try:
                rule_result = rule.check(ctx)
                result.merge(rule_result)
            except Exception as e:
                result.errors.append(f"{rule.name}: {e}")
                result.passed = False

        return result

    def _build_context(self, episode_yaml: Path, result: QCResult) -> Optional[QCContext]:
        try:
            ep_data = yaml.safe_load(episode_yaml.read_text(encoding="utf-8"))
            episode = Episode.model_validate(ep_data)
        except Exception as e:
            result.errors.append(f"Failed to load episode: {e}")
            result.passed = False
            return None

        episode_dir = episode_yaml.parent
        shotlist_path = episode_dir / "shotlist.yaml"
        shotlist: Optional[ShotList] = None

        if shotlist_path.exists():
            try:
                sl_data = yaml.safe_load(shotlist_path.read_text(encoding="utf-8"))
                shotlist = ShotList.model_validate(sl_data)
            except Exception as e:
                result.warnings.append(f"Failed to load shotlist: {e}")

        canon_characters = self._load_canon_characters()

        return QCContext(
            episode=episode,
            shotlist=shotlist,
            episode_dir=episode_dir,
            canon_characters=canon_characters,
        )

    def _load_canon_characters(self) -> list[str]:
        canon_path = Path("show/canon/characters.yaml")
        if not canon_path.exists():
            return []
        try:
            data = yaml.safe_load(canon_path.read_text(encoding="utf-8"))
            return [c["id"] for c in data.get("characters", [])]
        except Exception:
            return []
