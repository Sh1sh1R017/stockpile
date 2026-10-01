"""Default Viral Shorts Campaign Preset.

Reference-matched cinematic social editorial workflow:
meaning-driven visual punctuation, restrained motion, large sentence-aware captions,
and cinematic/archival B-roll instead of generic meme-heavy coverage.
"""

from ai_broll_autopilot.campaigns.base import CampaignConfig

DEFAULT_VIRAL_CAMPAIGN = CampaignConfig(
    id="default",
    name="Default Viral Shorts",
    client="General Short-Form Studio",
    rate="N/A (Standard Studio Workflow)",
    total_budget="N/A",
    platforms=["TikTok", "Instagram Reels", "YouTube Shorts"],
    description="Cinematic social editorial short-form workflow with narrative B-roll, restrained punch-ins, large center captions, selective SFX, and auto-ducked music.",

    # Video specs
    target_width=1080,
    target_height=1920,
    duration_min=15.0,
    duration_max=75.0,
    target_duration=30.0,

    # Audio rules
    allow_bgm=True,
    bgm_genre="chill_lofi",
    preserve_dialogue_only=False,

    # Visual & B-roll rules
    allow_ai_broll=False,
    max_broll_ratio=0.90,
    max_cutaway_seconds=2.2,
    speed_multiplier=1.0,
    niche_id="generic",
    editing_style="cinematic_social_editorial",

    # Watermark rules
    watermark_required=False,
    watermark_asset_path=None,
    watermark_position="none",

    # Subtitle rules
    subtitles_required=True,
    subtitle_style="cinematic_social",
    subtitle_position="center",
    subtitle_margin_v=0,
    hook_required=False,

    rules_checklist=[
        "Open on the strongest visual beat; do not require a clean A-roll intro.",
        "Use relevant cutaways to create visual progression; do not treat B-roll coverage as a quota or add filler visuals.",
        "Mix 0.8–2.2s cutaways with occasional 3–8s hero visuals when one shot carries the narrative payoff.",
        "Use literal archival/documentary/cinematic visuals that match the spoken idea, tone, and consequence.",
        "Use large sentence-aware center captions, normally 2–4 words visible at a time, with restrained pale-green emphasis.",
        "Avoid generic meme filler, neon effects, constant zooms, flashy transitions, and automatic whoosh-on-every-cut behavior.",
        "Use hard cuts by default; reserve SFX for meaningful reveals or punctuation and keep BGM low under dialogue."
    ],
    instant_rejections=[],
    director_system_prompt=None,
    curated_moments=[]
)
