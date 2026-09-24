"""Style Registry managing available visual aesthetic and editing styles."""

import logging
from typing import Dict, List, Optional
from ai_broll_autopilot.styles.base import StyleProfile
from ai_broll_autopilot.styles.profiles import PROFILES

logger = logging.getLogger(__name__)


class StyleRegistry:
    """Registry maintaining active StyleProfiles."""

    def __init__(self):
        self._styles: Dict[str, StyleProfile] = {}
        for style in PROFILES:
            self.register(style)

    def register(self, style: StyleProfile):
        """Register a visual style profile."""
        self._styles[style.id.lower()] = style
        logger.debug(f"Registered style profile: {style.id} ('{style.name}')")

    def get_style(self, style_id: Optional[str]) -> StyleProfile:
        """Retrieve style profile by ID with fallback to clean_podcast or first style."""
        if not style_id:
            return self._styles.get("clean_podcast", PROFILES[0])
        clean_id = style_id.strip().lower()
        if clean_id in self._styles:
            return self._styles[clean_id]
        logger.info(f"Style profile '{style_id}' not found, falling back to 'clean_podcast'.")
        return self._styles.get("clean_podcast", PROFILES[0])

    def list_styles(self) -> List[StyleProfile]:
        """List all registered style profiles."""
        return list(self._styles.values())

    def list_ids(self) -> List[str]:
        """List all registered style profile IDs."""
        return list(self._styles.keys())


# Global singleton instance
style_registry = StyleRegistry()
