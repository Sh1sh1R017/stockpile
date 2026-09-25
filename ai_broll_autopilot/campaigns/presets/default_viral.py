"""Default Viral Shorts Campaign Preset.

Standard high-velocity viral short-form editing with ~60% B-roll coverage,
Alex Hormozi kinetic subtitles, streamer reaction cutaways, and auto-ducked upbeat phonk BGM.
"""

from ai_broll_autopilot.campaigns.base import CampaignConfig

DEFAULT_VIRAL_CAMPAIGN = CampaignConfig(
    id="default",
    name="Default Viral Shorts",
    client="General Short-Form Studio",
    rate="N/A (Standard Studio Workflow)",
    total_budget="N/A",
    platforms=["TikTok", "Instagram Reels", "YouTube Shorts"],
    description="High-retention viral editing formula featuring ~60% B-roll coverage, creator reaction cutaways (Speed, CaseOh, Jynxzi), Hormozi punch subtitles, and auto-ducked upbeat phonk music.",

    # Video specs
    target_width=1080,
    target_height=1920,
    duration_min=15.0,
    duration_max=75.0,
    target_duration=30.0,

    # Audio rules
    allow_bgm=True,
    bgm_genre="upbeat_phonk",
    preserve_dialogue_only=False,

    # Visual & B-roll rules
    allow_ai_broll=False,
    max_broll_ratio=0.45,
    max_cutaway_seconds=2.5,
    speed_multiplier=1.25,
    niche_id="generic",

    # Watermark rules
    watermark_required=False,
    watermark_asset_path=None,
    watermark_position="none",

    # Subtitle rules
    subtitles_required=True,
    subtitle_style="hormozi",
    subtitle_position="bottom",
    subtitle_margin_v=280,
    hook_required=False,

    rules_checklist=[
        "Keep pacing rapid with cuts every 1.5s to 2.4s.",
        "Include punchy creator reaction memes in first 5s.",
        "Word-by-word kinetic subtitle highlighting.",
        "Sidechain audio auto-ducking under dialogue."
    ],
    instant_rejections=[],
    director_system_prompt=None,
    curated_moments=[]
)
