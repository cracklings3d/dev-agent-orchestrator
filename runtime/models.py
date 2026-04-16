"""Model pool, profiles, and selection logic for differentiated agent model assignment.

Different agent roles have different cognitive demands:
- Architect needs strong reasoning to shape vague requirements
- Developer needs strong coding ability
- Tester values speed for iterative validation
- Reviewer needs reasoning + coding to judge quality
- Controller needs speed and determinism

Task difficulty modulates selection: harder tasks shift weight toward
reasoning/coding, easier tasks allow cheaper/faster models.

On retry, difficulty bumps automatically, causing the system to select
a stronger model — analogous to a junior employee escalating to a senior.

Peak-hour rate-limit awareness: during Zhipu's peak hours (14:00-18:00 UTC+8),
models with high rate_limit_risk get their cost score penalized, making the
system prefer cheaper models with better availability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from pathlib import Path
import os


class DifficultyLevel(IntEnum):
    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    CRITICAL = 5


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    reasoning: float
    coding: float
    speed: float
    cost: float
    api_key_env: str = ""
    rate_limit_risk: float = 0.0

    def __post_init__(self):
        for dim in ("reasoning", "coding", "speed", "cost"):
            val = getattr(self, dim)
            if not (0 <= val <= 10):
                raise ValueError(f"{dim} must be between 0 and 10, got {val}")
        if not (0 <= self.rate_limit_risk <= 1):
            raise ValueError(f"rate_limit_risk must be between 0 and 1, got {self.rate_limit_risk}")

    def get_api_key(self) -> str:
        if not self.api_key_env:
            return ""
        return os.environ.get(self.api_key_env, "")

    def score(self, weights: dict[str, float], *, peak_penalty: float = 0.0) -> float:
        effective_cost = max(0.0, self.cost - peak_penalty * self.rate_limit_risk)
        return (
            weights.get("reasoning", 0.0) * self.reasoning
            + weights.get("coding", 0.0) * self.coding
            + weights.get("speed", 0.0) * self.speed
            + weights.get("cost", 0.0) * effective_cost
        )


ROLE_MODEL_WEIGHTS: dict[str, dict[str, float]] = {
    "architect":  {"reasoning": 0.65, "coding": 0.05, "speed": 0.15, "cost": 0.15},
    "developer":  {"reasoning": 0.10, "coding": 0.60, "speed": 0.15, "cost": 0.15},
    "tester":     {"reasoning": 0.20, "coding": 0.25, "speed": 0.30, "cost": 0.25},
    "reviewer":   {"reasoning": 0.30, "coding": 0.40, "speed": 0.10, "cost": 0.20},
    "controller": {"reasoning": 0.20, "coding": 0.10, "speed": 0.40, "cost": 0.30},
}

_DIFFICULTY_SHIFT: dict[str, float] = {
    "reasoning": 0.06,
    "coding": 0.04,
    "speed": -0.04,
    "cost": -0.06,
}


def _adjust_weights(base: dict[str, float], difficulty: DifficultyLevel) -> dict[str, float]:
    shift = int(difficulty) - 3
    adjusted = {}
    for dim, weight in base.items():
        delta = _DIFFICULTY_SHIFT.get(dim, 0.0) * shift
        adjusted[dim] = max(0.0, weight + delta)
    total = sum(adjusted.values())
    if total > 0:
        for dim in adjusted:
            adjusted[dim] /= total
    return adjusted


@dataclass
class ModelPool:
    _models: dict[str, ModelProfile] = field(default_factory=dict)
    _role_defaults: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config_path: Path) -> ModelPool:
        data = _load_config(config_path)
        models = {}
        for m in data.get("models", []):
            profile = ModelProfile(
                name=m["name"],
                provider=m["provider"],
                reasoning=m.get("reasoning", 5.0),
                coding=m.get("coding", 5.0),
                speed=m.get("speed", 5.0),
                cost=m.get("cost", 5.0),
                api_key_env=m.get("api_key_env", ""),
                rate_limit_risk=m.get("rate_limit_risk", 0.0),
            )
            models[profile.name] = profile
        role_defaults = data.get("role_defaults", {})
        return cls(_models=models, _role_defaults=role_defaults)

    @classmethod
    def from_profiles(
        cls,
        profiles: list[ModelProfile],
        role_defaults: dict[str, str] | None = None,
    ) -> ModelPool:
        models = {p.name: p for p in profiles}
        return cls(_models=models, _role_defaults=role_defaults or {})

    def get(self, name: str) -> ModelProfile | None:
        return self._models.get(name)

    def all_models(self) -> list[ModelProfile]:
        return list(self._models.values())

    def role_default(self, role: str) -> ModelProfile | None:
        name = self._role_defaults.get(role)
        if name is None:
            return None
        return self._models.get(name)

    def __len__(self) -> int:
        return len(self._models)


@dataclass
class PeakHoursConfig:
    start_hour: int = 14
    end_hour: int = 18
    utc_offset_hours: int = 8
    peak_penalty: float = 2.0

    def is_peak(self, *, now: datetime | None = None) -> bool:
        tz = timezone(timedelta(hours=self.utc_offset_hours))
        target_now = now.astimezone(tz) if now else datetime.now(tz)
        return self.start_hour <= target_now.hour < self.end_hour


class ModelSelector:
    def __init__(
        self,
        pool: ModelPool,
        *,
        role_weights: dict[str, dict[str, float]] | None = None,
        peak_hours: PeakHoursConfig | None = None,
    ):
        self._pool = pool
        self._role_weights = role_weights or ROLE_MODEL_WEIGHTS
        self._peak_hours = peak_hours

    @property
    def pool(self) -> ModelPool:
        return self._pool

    def _current_peak_penalty(self, *, now: datetime | None = None) -> float:
        if self._peak_hours is None:
            return 0.0
        if self._peak_hours.is_peak(now=now):
            return self._peak_hours.peak_penalty
        return 0.0

    def select(
        self,
        role: str,
        difficulty: DifficultyLevel = DifficultyLevel.MODERATE,
        *,
        now: datetime | None = None,
    ) -> ModelProfile:
        candidates = self._pool.all_models()
        if not candidates:
            raise ValueError("ModelPool is empty")
        weights = self._adjusted_weights(role, difficulty)
        penalty = self._current_peak_penalty(now=now)
        return max(candidates, key=lambda m: m.score(weights, peak_penalty=penalty))

    def select_for_retry(
        self,
        role: str,
        retry_count: int,
        base_difficulty: DifficultyLevel = DifficultyLevel.MODERATE,
        *,
        now: datetime | None = None,
    ) -> ModelProfile:
        bumped = min(int(base_difficulty) + retry_count, DifficultyLevel.CRITICAL)
        return self.select(role, DifficultyLevel(bumped), now=now)

    def _adjusted_weights(self, role: str, difficulty: DifficultyLevel) -> dict[str, float]:
        base = dict(self._role_weights.get(role, self._role_weights.get("developer", {})))
        return _adjust_weights(base, difficulty)


@dataclass(frozen=True)
class ModelAssignment:
    model: str
    provider: str = ""
    api_key: str = ""

    @classmethod
    def from_profile(cls, profile: ModelProfile) -> ModelAssignment:
        return cls(model=profile.name, provider=profile.provider, api_key=profile.get_api_key())


def _load_config(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            raise ImportError("Install pyyaml for YAML config: pip install pyyaml")
    return json.loads(text)
