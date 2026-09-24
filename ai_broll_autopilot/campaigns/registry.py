"""Campaign registry managing available campaign presets."""

import logging
from typing import Dict, List, Optional
from ai_broll_autopilot.campaigns.base import CampaignConfig
from ai_broll_autopilot.campaigns.presets.default_viral import DEFAULT_VIRAL_CAMPAIGN
from ai_broll_autopilot.campaigns.presets.curious_mike import CURIOUS_MIKE_CAMPAIGN

logger = logging.getLogger(__name__)


class CampaignRegistry:
    """Registry maintaining active clipping campaigns and their editing rules."""

    def __init__(self):
        self._campaigns: Dict[str, CampaignConfig] = {}
        # Register built-in campaigns
        self.register(DEFAULT_VIRAL_CAMPAIGN)
        self.register(CURIOUS_MIKE_CAMPAIGN)

    def register(self, campaign: CampaignConfig):
        """Register a campaign preset."""
        self._campaigns[campaign.id] = campaign
        logger.info(f"Registered campaign preset: {campaign.id} ('{campaign.name}')")

    def get_campaign(self, campaign_id: Optional[str]) -> CampaignConfig:
        """Retrieve campaign preset by ID with fallback to default."""
        if not campaign_id:
            return self._campaigns.get("default", DEFAULT_VIRAL_CAMPAIGN)
        clean_id = campaign_id.strip().lower()
        if clean_id in self._campaigns:
            return self._campaigns[clean_id]
        logger.warning(f"Campaign '{campaign_id}' not found, falling back to default.")
        return self._campaigns.get("default", DEFAULT_VIRAL_CAMPAIGN)

    def list_campaigns(self) -> List[CampaignConfig]:
        """List all registered campaign presets."""
        return list(self._campaigns.values())


# Global singleton instance
campaign_registry = CampaignRegistry()
