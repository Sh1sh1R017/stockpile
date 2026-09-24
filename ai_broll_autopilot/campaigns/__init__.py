"""Campaigns package exposing base models, presets, and the campaign registry."""

from ai_broll_autopilot.campaigns.base import CampaignConfig, CuratedMoment
from ai_broll_autopilot.campaigns.registry import campaign_registry

__all__ = ["CampaignConfig", "CuratedMoment", "campaign_registry"]
