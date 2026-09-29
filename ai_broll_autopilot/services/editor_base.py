"""Base Editor Adapter Specification.

Establishes a clean architectural boundary between Stockpile's AI Director
intelligence layer and downstream editor implementations (OpenReel, Diffusion Studio).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ai_broll_autopilot.services.edit_director import EditPlan


class EditorAdapter(ABC):
    """Abstract base adapter converting a Stockpile EditPlan into an editor project."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Name of the target editor engine (e.g., 'openreel', 'diffusion')."""
        pass

    @property
    @abstractmethod
    def schema_version(self) -> str:
        """Schema or spec version of the target editor output."""
        pass

    @abstractmethod
    def create_project(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert a declarative Stockpile EditPlan into a target project representation.

        Args:
            edit_plan: Canonical Stockpile EditPlan instance.
            project_name: Optional project name override.
            resolved_broll_map: Map of shot_id -> local disk path for B-roll assets.
            base_asset_url: Base HTTP URL for streaming media.

        Returns:
            JSON-serializable dict representing the project.
        """
        pass
