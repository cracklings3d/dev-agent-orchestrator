from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.models import (
    DifficultyLevel,
    ModelAssignment,
    ModelPool,
    ModelProfile,
    ModelSelector,
    PeakHoursConfig,
    ROLE_MODEL_WEIGHTS,
    _adjust_weights,
)


GLM_51 = ModelProfile(name="glm-5.1", provider="zhipu", reasoning=9.5, coding=9.0, speed=3.0, cost=1.1, api_key_env="TEST_KEY_GLM51", rate_limit_risk=1.0)
GLM_5 = ModelProfile(name="glm-5", provider="zhipu", reasoning=9.0, coding=8.5, speed=4.0, cost=2.0, api_key_env="TEST_KEY_GLM5", rate_limit_risk=0.7)
GLM_47 = ModelProfile(name="glm-4.7", provider="zhipu", reasoning=8.0, coding=8.5, speed=5.0, cost=5.0, api_key_env="TEST_KEY_GLM47", rate_limit_risk=0.3)
GLM_5T = ModelProfile(name="glm-5-turbo", provider="zhipu", reasoning=7.5, coding=7.0, speed=8.0, cost=6.0, api_key_env="TEST_KEY_GLM5T", rate_limit_risk=0.1)
GLM_47F = ModelProfile(name="glm-4.7-flash", provider="zhipu", reasoning=5.5, coding=5.5, speed=9.5, cost=10.0, api_key_env="TEST_KEY_GLM47F", rate_limit_risk=0.0)

ALL_MODELS = [GLM_51, GLM_5, GLM_47, GLM_5T, GLM_47F]

ROLE_DEFAULTS = {
    "architect": "glm-5.1",
    "developer": "glm-4.7",
    "tester": "glm-5-turbo",
    "reviewer": "glm-4.7",
    "controller": "glm-5-turbo",
}

TZ_UTC8 = timezone(timedelta(hours=8))


def _pool() -> ModelPool:
    return ModelPool.from_profiles(ALL_MODELS, ROLE_DEFAULTS)


class TestModelProfile:
    def test_score_basic(self):
        weights = {"reasoning": 0.5, "coding": 0.3, "speed": 0.1, "cost": 0.1}
        s = GLM_51.score(weights)
        assert s == pytest.approx(0.5 * 9.5 + 0.3 * 9.0 + 0.1 * 3.0 + 0.1 * 1.1)

    def test_score_ignores_missing_dims(self):
        s = GLM_51.score({"reasoning": 1.0})
        assert s == pytest.approx(9.5)

    def test_score_with_peak_penalty(self):
        weights = {"cost": 1.0}
        normal = GLM_51.score(weights)
        penalized = GLM_51.score(weights, peak_penalty=2.0)
        assert penalized < normal
        assert penalized == pytest.approx(max(0.0, 1.1 - 2.0 * 1.0))

    def test_peak_penalty_zero_for_no_risk(self):
        weights = {"cost": 1.0}
        normal = GLM_47F.score(weights)
        penalized = GLM_47F.score(weights, peak_penalty=5.0)
        assert penalized == normal

    def test_validation_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            ModelProfile(name="bad", provider="x", reasoning=11.0, coding=5.0, speed=5.0, cost=5.0)

    def test_validation_rejects_negative(self):
        with pytest.raises(ValueError):
            ModelProfile(name="bad", provider="x", reasoning=-1.0, coding=5.0, speed=5.0, cost=5.0)

    def test_validation_rejects_invalid_rate_limit_risk(self):
        with pytest.raises(ValueError):
            ModelProfile(name="bad", provider="x", reasoning=5, coding=5, speed=5, cost=5, rate_limit_risk=1.5)

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "sk-test-123")
        p = ModelProfile(name="m", provider="x", reasoning=5, coding=5, speed=5, cost=5, api_key_env="MY_KEY")
        assert p.get_api_key() == "sk-test-123"

    def test_get_api_key_missing_env(self):
        p = ModelProfile(name="m", provider="x", reasoning=5, coding=5, speed=5, cost=5, api_key_env="NONEXISTENT_KEY_XYZ")
        assert p.get_api_key() == ""

    def test_get_api_key_no_env_configured(self):
        p = ModelProfile(name="m", provider="x", reasoning=5, coding=5, speed=5, cost=5)
        assert p.get_api_key() == ""

    def test_boundary_zero(self):
        p = ModelProfile(name="zero", provider="x", reasoning=0, coding=0, speed=0, cost=0)
        assert p.score({"reasoning": 1.0}) == 0.0

    def test_boundary_ten(self):
        p = ModelProfile(name="ten", provider="x", reasoning=10, coding=10, speed=10, cost=10)
        assert p.score({"reasoning": 0.25, "coding": 0.25, "speed": 0.25, "cost": 0.25}) == pytest.approx(10.0)


class TestModelPool:
    def test_from_profiles(self):
        pool = _pool()
        assert len(pool) == 5
        assert pool.get("glm-5.1") is GLM_51
        assert pool.get("nonexistent") is None

    def test_role_defaults(self):
        pool = _pool()
        assert pool.role_default("architect") is GLM_51
        assert pool.role_default("developer") is GLM_47
        assert pool.role_default("tester") is GLM_5T
        assert pool.role_default("unknown_role") is None

    def test_all_models(self):
        pool = _pool()
        names = {m.name for m in pool.all_models()}
        assert names == {"glm-5.1", "glm-5", "glm-4.7", "glm-5-turbo", "glm-4.7-flash"}

    def test_empty_pool(self):
        pool = ModelPool()
        assert len(pool) == 0
        assert pool.all_models() == []

    def test_from_config_json(self, tmp_path):
        config = {
            "models": [
                {"name": "model-a", "provider": "test", "reasoning": 7, "coding": 6, "speed": 5, "cost": 4, "api_key_env": "KEY_A", "rate_limit_risk": 0.5},
                {"name": "model-b", "provider": "test", "reasoning": 3, "coding": 3, "speed": 9, "cost": 9},
            ],
            "role_defaults": {"architect": "model-a"},
        }
        config_path = tmp_path / "models.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        pool = ModelPool.from_config(config_path)
        assert len(pool) == 2
        assert pool.get("model-a").reasoning == 7
        assert pool.get("model-a").rate_limit_risk == 0.5
        assert pool.get("model-b").api_key_env == ""
        assert pool.get("model-b").rate_limit_risk == 0.0
        assert pool.role_default("architect").name == "model-a"

    def test_from_config_defaults_missing_fields(self, tmp_path):
        config = {
            "models": [
                {"name": "minimal", "provider": "test"},
            ],
        }
        config_path = tmp_path / "models.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        pool = ModelPool.from_config(config_path)
        m = pool.get("minimal")
        assert m.reasoning == 5.0
        assert m.coding == 5.0
        assert m.speed == 5.0
        assert m.cost == 5.0
        assert m.rate_limit_risk == 0.0


class TestAdjustWeights:
    def test_moderate_no_change(self):
        base = {"reasoning": 0.5, "coding": 0.2, "speed": 0.15, "cost": 0.15}
        result = _adjust_weights(base, DifficultyLevel.MODERATE)
        assert result["reasoning"] == pytest.approx(0.5, abs=0.01)

    def test_critical_shifts_toward_reasoning(self):
        base = {"reasoning": 0.5, "coding": 0.2, "speed": 0.15, "cost": 0.15}
        result = _adjust_weights(base, DifficultyLevel.CRITICAL)
        assert result["reasoning"] > 0.5

    def test_trivial_shifts_toward_cost(self):
        base = {"reasoning": 0.5, "coding": 0.2, "speed": 0.15, "cost": 0.15}
        result = _adjust_weights(base, DifficultyLevel.TRIVIAL)
        assert result["cost"] > 0.15

    def test_weights_still_normalized(self):
        base = {"reasoning": 0.5, "coding": 0.2, "speed": 0.15, "cost": 0.15}
        for diff in DifficultyLevel:
            result = _adjust_weights(base, diff)
            assert sum(result.values()) == pytest.approx(1.0, abs=0.001)

    def test_no_negative_weights(self):
        base = {"reasoning": 0.5, "coding": 0.2, "speed": 0.15, "cost": 0.15}
        for diff in DifficultyLevel:
            result = _adjust_weights(base, diff)
            for v in result.values():
                assert v >= 0.0


class TestPeakHoursConfig:
    def test_peak_time_detected(self):
        cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8)
        peak = datetime(2026, 4, 17, 15, 0, 0, tzinfo=TZ_UTC8)
        assert cfg.is_peak(now=peak)

    def test_non_peak_time_detected(self):
        cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8)
        non_peak = datetime(2026, 4, 17, 10, 0, 0, tzinfo=TZ_UTC8)
        assert not cfg.is_peak(now=non_peak)

    def test_boundary_start(self):
        cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8)
        at_start = datetime(2026, 4, 17, 14, 0, 0, tzinfo=TZ_UTC8)
        assert cfg.is_peak(now=at_start)

    def test_boundary_end(self):
        cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8)
        at_end = datetime(2026, 4, 17, 18, 0, 0, tzinfo=TZ_UTC8)
        assert not cfg.is_peak(now=at_end)

    def test_utc_conversion(self):
        cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8)
        utc_time = datetime(2026, 4, 17, 7, 0, 0, tzinfo=timezone.utc)
        assert cfg.is_peak(now=utc_time)

    def test_custom_penalty(self):
        cfg = PeakHoursConfig(peak_penalty=3.5)
        assert cfg.peak_penalty == 3.5


class TestModelSelector:
    def test_architect_prefers_reasoning(self):
        selector = ModelSelector(_pool())
        m = selector.select("architect", DifficultyLevel.COMPLEX)
        assert m.name == "glm-5.1"

    def test_developer_prefers_coding(self):
        selector = ModelSelector(_pool())
        m = selector.select("developer", DifficultyLevel.MODERATE)
        assert m.name == "glm-4.7"

    def test_tester_prefers_speed(self):
        selector = ModelSelector(_pool())
        m = selector.select("tester", DifficultyLevel.TRIVIAL)
        assert m.name == "glm-4.7-flash"

    def test_controller_prefers_speed(self):
        selector = ModelSelector(_pool())
        m = selector.select("controller", DifficultyLevel.TRIVIAL)
        assert m.name == "glm-4.7-flash"

    def test_difficulty_escalation(self):
        selector = ModelSelector(_pool())
        trivial = selector.select("developer", DifficultyLevel.TRIVIAL)
        critical = selector.select("developer", DifficultyLevel.CRITICAL)
        assert critical.reasoning >= trivial.reasoning or critical.coding >= trivial.coding

    def test_select_for_retry_bumps_model(self):
        selector = ModelSelector(_pool())
        base = selector.select("developer", DifficultyLevel.MODERATE)
        retry = selector.select_for_retry("developer", 2, DifficultyLevel.MODERATE)
        assert retry.reasoning >= base.reasoning or retry.coding >= base.coding

    def test_select_for_retry_caps_at_critical(self):
        selector = ModelSelector(_pool())
        result = selector.select_for_retry("developer", 10, DifficultyLevel.MODERATE)
        assert result is not None

    def test_empty_pool_raises(self):
        selector = ModelSelector(ModelPool())
        with pytest.raises(ValueError, match="empty"):
            selector.select("architect")

    def test_unknown_role_uses_developer_defaults(self):
        selector = ModelSelector(_pool())
        m = selector.select("unknown_role", DifficultyLevel.MODERATE)
        assert m is not None

    def test_custom_role_weights(self):
        custom = {"custom_role": {"reasoning": 1.0, "coding": 0.0, "speed": 0.0, "cost": 0.0}}
        selector = ModelSelector(_pool(), role_weights=custom)
        m = selector.select("custom_role", DifficultyLevel.MODERATE)
        assert m.name == "glm-5.1"

    def test_each_role_gets_a_model(self):
        selector = ModelSelector(_pool())
        for role in ("architect", "developer", "tester", "reviewer", "controller"):
            m = selector.select(role, DifficultyLevel.MODERATE)
            assert m is not None

    def test_each_difficulty_gets_a_model(self):
        selector = ModelSelector(_pool())
        for diff in DifficultyLevel:
            m = selector.select("developer", diff)
            assert m is not None


class TestModelSelectorPeakHours:
    def test_peak_avoids_rate_limited_flagship(self):
        flagship = ModelProfile(name="flagship", provider="x", reasoning=9.5, coding=8.5, speed=3.0, cost=5.0, rate_limit_risk=1.0)
        midrange = ModelProfile(name="midrange", provider="x", reasoning=8.0, coding=8.0, speed=6.0, cost=7.0, rate_limit_risk=0.1)
        pool = ModelPool.from_profiles([flagship, midrange])
        custom_weights = {"test_role": {"reasoning": 0.55, "coding": 0.15, "speed": 0.05, "cost": 0.25}}
        peak_cfg = PeakHoursConfig(peak_penalty=2.0)
        selector = ModelSelector(pool, peak_hours=peak_cfg, role_weights=custom_weights)

        non_peak = datetime(2026, 4, 17, 10, 0, 0, tzinfo=TZ_UTC8)
        peak_time = datetime(2026, 4, 17, 15, 0, 0, tzinfo=TZ_UTC8)

        normal_m = selector.select("test_role", DifficultyLevel.MODERATE, now=non_peak)
        peak_m = selector.select("test_role", DifficultyLevel.MODERATE, now=peak_time)
        assert normal_m.name == "flagship"
        assert peak_m.name == "midrange"

    def test_non_peak_uses_normal_selection(self):
        peak_cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8, peak_penalty=2.0)
        selector = ModelSelector(_pool(), peak_hours=peak_cfg)
        non_peak = datetime(2026, 4, 17, 10, 0, 0, tzinfo=TZ_UTC8)
        m = selector.select("architect", DifficultyLevel.COMPLEX, now=non_peak)
        assert m.name == "glm-5.1"

    def test_peak_developer_downgrades_from_47(self):
        peak_cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8, peak_penalty=2.0)
        selector = ModelSelector(_pool(), peak_hours=peak_cfg)
        peak_time = datetime(2026, 4, 17, 15, 0, 0, tzinfo=TZ_UTC8)
        non_peak = datetime(2026, 4, 17, 10, 0, 0, tzinfo=TZ_UTC8)
        normal = selector.select("developer", DifficultyLevel.MODERATE, now=non_peak)
        peak = selector.select("developer", DifficultyLevel.MODERATE, now=peak_time)
        assert peak.cost >= normal.cost

    def test_peak_critical_still_gets_best_available(self):
        peak_cfg = PeakHoursConfig(start_hour=14, end_hour=18, utc_offset_hours=8, peak_penalty=2.0)
        selector = ModelSelector(_pool(), peak_hours=peak_cfg)
        peak_time = datetime(2026, 4, 17, 15, 0, 0, tzinfo=TZ_UTC8)
        m = selector.select("developer", DifficultyLevel.CRITICAL, now=peak_time)
        assert m is not None
        assert m.coding >= 8.0

    def test_no_peak_config_same_as_no_penalty(self):
        selector = ModelSelector(_pool())
        m_no_peak = selector.select("architect", DifficultyLevel.COMPLEX)
        peak_time = datetime(2026, 4, 17, 15, 0, 0, tzinfo=TZ_UTC8)
        m_with_time = selector.select("architect", DifficultyLevel.COMPLEX, now=peak_time)
        assert m_no_peak.name == m_with_time.name


class TestModelAssignment:
    def test_from_profile(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_GLM51", "sk-abc")
        assignment = ModelAssignment.from_profile(GLM_51)
        assert assignment.model == "glm-5.1"
        assert assignment.provider == "zhipu"
        assert assignment.api_key == "sk-abc"

    def test_from_profile_no_key(self):
        p = ModelProfile(name="m", provider="x", reasoning=5, coding=5, speed=5, cost=5)
        assignment = ModelAssignment.from_profile(p)
        assert assignment.api_key == ""

    def test_repr_masks_api_key(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_GLM51", "sk-secret-do-not-leak")
        assignment = ModelAssignment.from_profile(GLM_51)
        r = repr(assignment)
        assert "sk-secret-do-not-leak" not in r
        assert "***" in r
        assert "glm-5.1" in r

    def test_repr_empty_key_shows_blank(self):
        assignment = ModelAssignment(model="m", provider="x", api_key="")
        assert repr(assignment) == "ModelAssignment(model='m', provider='x', api_key='')"


class TestModelSelectorFromConfig:
    def test_loads_from_project_config(self):
        config_path = Path(__file__).parent.parent / "models.json"
        if not config_path.exists():
            pytest.skip("models.json not found")
        pool = ModelPool.from_config(config_path)
        assert len(pool) >= 5
        selector = ModelSelector(pool)
        m = selector.select("architect", DifficultyLevel.COMPLEX)
        assert m is not None
        glm51 = pool.get("glm-5.1")
        assert glm51 is not None
        assert glm51.cost == pytest.approx(1.1)
        assert glm51.rate_limit_risk == 1.0
