"""Phase-0 regression tests for import safety and deterministic registries."""

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.campaigns import campaign_registry


def test_float_duration_config_does_not_crash_or_truncate():
    assert isinstance(Config.MAX_CLIP_DURATION_SECONDS, float)
    assert Config.MAX_CLIP_DURATION_SECONDS == 1.8


def test_director_constructor_is_offline_safe_without_api_key():
    director = Director(api_key=None)
    assert director.client is None


def test_campaign_registry_exposes_unique_ids():
    campaigns = campaign_registry.list_campaigns()
    ids = [campaign.id for campaign in campaigns]
    assert len(ids) == len(set(ids))
