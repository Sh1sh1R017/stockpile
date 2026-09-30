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
    max_broll_ratio=0.60,
    max_cutaway_seconds=2.2,
    speed_multiplier=1.0,
    niche_id="generic",

    # Watermark rules
    watermark_required=False,
    watermark_asset_path=None,
    watermark_position="none",

    # Subtitle rules
    subtitles_required=True,
    subtitle_style="cinematic_editorial",
    subtitle_position="center",
    subtitle_margin_v=0,
    hook_required=False,

    rules_checklist=[
        "Open with 0.8–1.3s of clean A-roll, then cut on meaningful sentence beats.",
        "Use B-roll as narrative punctuation with literal, emotionally relevant visuals.",
        "Keep B-roll cutaways roughly 0.8–2.2s and permit micro-cut sequences when the sentence changes visual beat.",
        "Use large sentence-aware center captions, normally 2–4 words visible at a time, with restrained pale-green emphasis.",
        "Avoid generic meme filler, neon effects, constant zooms, and decorative transitions.",
        "Use hard cuts by default; reserve SFX for major visual punctuation and keep BGM low under dialogue."
    ],
    instant_rejections=[],
    director_system_prompt=None,
    curated_moments=[]
)
