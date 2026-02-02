from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .checker import QCContext


@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Rule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def check(self, ctx: "QCContext") -> RuleResult:
        ...


INAPPROPRIATE_WORDS = frozenset([
    "kill", "murder", "death", "die", "dead", "blood", "bloody",
    "hate", "stupid", "idiot", "dumb", "shut up",
    "damn", "hell", "crap",
])

_WORD_PATTERNS = {word: re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in INAPPROPRIATE_WORDS}


class DialogueLanguageCheck(Rule):
    @property
    def name(self) -> str:
        return "dialogue_language_check"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)

        if ctx.shotlist is None:
            result.warnings.append("No shotlist available for dialogue check")
            return result

        for shot in ctx.shotlist.shots:
            for dialogue in shot.audio.dialogue:
                for word, pattern in _WORD_PATTERNS.items():
                    if pattern.search(dialogue):
                        result.errors.append(
                            f"Shot {shot.id}: inappropriate word '{word}' in dialogue: {dialogue}"
                        )
                        result.passed = False

        return result


class RuntimeBoundsCheck(Rule):
    MIN_RUNTIME_SEC = 60
    MAX_RUNTIME_SEC = 1800  # 30 minutes

    @property
    def name(self) -> str:
        return "runtime_bounds"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)

        target = ctx.episode.runtime_target_sec
        if target < self.MIN_RUNTIME_SEC:
            result.errors.append(f"Runtime target {target}s is below minimum {self.MIN_RUNTIME_SEC}s")
            result.passed = False
        elif target > self.MAX_RUNTIME_SEC:
            result.warnings.append(f"Runtime target {target}s exceeds recommended max {self.MAX_RUNTIME_SEC}s")

        if ctx.shotlist:
            actual = sum(shot.dur_sec for shot in ctx.shotlist.shots)
            variance = abs(actual - target) / target if target > 0 else 0
            if variance > 0.2:
                result.warnings.append(
                    f"Actual runtime {actual:.1f}s differs from target {target}s by {variance*100:.0f}%"
                )

        return result


class AssetCoverageCheck(Rule):
    @property
    def name(self) -> str:
        return "asset_coverage"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)

        if ctx.shotlist is None:
            result.warnings.append("No shotlist available for asset coverage check")
            return result

        assets_dir = ctx.episode_dir / "assets"

        for shot in ctx.shotlist.shots:
            if shot.bg:
                bg_path = assets_dir / "backgrounds" / f"{shot.bg}.png"
                if not bg_path.exists():
                    placeholder_path = assets_dir / "backgrounds" / f"{shot.bg}_placeholder.png"
                    if not placeholder_path.exists():
                        result.warnings.append(f"Shot {shot.id}: missing background asset {shot.bg}")

            for actor in shot.actors:
                pose_dir = assets_dir / "poses" / actor.character
                if pose_dir.exists():
                    pose_file = pose_dir / f"{actor.pose}.png"
                    placeholder_file = pose_dir / f"{actor.pose}_placeholder.png"
                    if not pose_file.exists() and not placeholder_file.exists():
                        result.warnings.append(
                            f"Shot {shot.id}: missing pose {actor.pose} for {actor.character}"
                        )

        return result


class CharacterConsistencyCheck(Rule):
    @property
    def name(self) -> str:
        return "character_consistency"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)
        cast = set(ctx.episode.cast)

        if ctx.shotlist is None:
            result.warnings.append("No shotlist available for character consistency check")
            return result

        for shot in ctx.shotlist.shots:
            for actor in shot.actors:
                if actor.character not in cast:
                    result.errors.append(
                        f"Shot {shot.id}: character '{actor.character}' not in episode cast {list(cast)}"
                    )
                    result.passed = False

        if ctx.canon_characters:
            for char in cast:
                if char not in ctx.canon_characters:
                    result.warnings.append(f"Cast member '{char}' not in canon characters")

        return result


VIOLENCE_KEYWORDS = frozenset([
    "fight", "hit", "punch", "kick", "attack", "weapon", "sword", "gun",
    "battle", "war", "destroy", "explosion", "explode",
])


class KidsContentCheck(Rule):
    @property
    def name(self) -> str:
        return "kids_content"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)

        if ctx.shotlist is None:
            result.warnings.append("No shotlist available for kids content check")
            return result

        for shot in ctx.shotlist.shots:
            for dialogue in shot.audio.dialogue:
                dialogue_lower = dialogue.lower()
                for word in VIOLENCE_KEYWORDS:
                    if word in dialogue_lower:
                        result.warnings.append(
                            f"Shot {shot.id}: review violence-adjacent word '{word}' in dialogue"
                        )

        return result


class IPChecklistReminder(Rule):
    @property
    def name(self) -> str:
        return "ip_checklist"

    def check(self, ctx: "QCContext") -> RuleResult:
        result = RuleResult(rule_name=self.name, passed=True)

        result.warnings.append("IP Checklist Reminder: Verify characters are on-model")
        result.warnings.append("IP Checklist Reminder: Verify biome consistency with show canon")
        result.warnings.append("IP Checklist Reminder: Review all generated assets for style consistency")

        return result
