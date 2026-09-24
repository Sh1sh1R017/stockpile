"""Niche Registry managing available content niche profiles."""

import logging
from typing import Dict, List, Optional
from ai_broll_autopilot.niches.base import NicheProfile
from ai_broll_autopilot.niches.profiles import PROFILES

logger = logging.getLogger(__name__)


class NicheRegistry:
    """Registry maintaining active content niche profiles and their semantic descriptors."""

    def __init__(self):
        self._profiles: Dict[str, NicheProfile] = {}
        for profile in PROFILES:
            self.register(profile)

    def register(self, profile: NicheProfile):
        """Register a content niche profile."""
        self._profiles[profile.id.lower()] = profile
        logger.debug(f"Registered niche profile: {profile.id} ('{profile.name}')")

    def get_profile(self, niche_id: Optional[str]) -> NicheProfile:
        """Retrieve niche profile by ID with fallback to generic.

        Args:
            niche_id: Unique string identifier (e.g. 'sports_basketball', 'tech_ai', 'finance')

        Returns:
            Matched NicheProfile, or generic profile if not found.
        """
        if not niche_id:
            return self._profiles.get("generic", PROFILES[-1])

        clean_id = niche_id.strip().lower()
        if clean_id in self._profiles:
            return self._profiles[clean_id]

        # Check aliases or parent niches
        for p in self._profiles.values():
            if p.parent_niche == clean_id:
                return p

        logger.info(f"Niche profile '{niche_id}' not found, falling back to 'generic'.")
        return self._profiles.get("generic", PROFILES[-1])

    def list_profiles(self) -> List[NicheProfile]:
        """List all registered niche profiles."""
        return list(self._profiles.values())

    def list_ids(self) -> List[str]:
        """List all registered niche profile IDs."""
        return list(self._profiles.keys())

    def find_by_keyword(self, keyword: str) -> Optional[NicheProfile]:
        """Find the best matching niche profile given a keyword or topic term."""
        kw = keyword.strip().lower()
        # Direct id match
        if kw in self._profiles:
            return self._profiles[kw]

        # Check visual keywords and categories
        for profile in self._profiles.values():
            if kw in [k.lower() for k in profile.visual_keywords]:
                return profile
            if kw in [c.lower() for c in profile.broll_categories]:
                return profile

        return None


# Global singleton instance
niche_registry = NicheRegistry()
