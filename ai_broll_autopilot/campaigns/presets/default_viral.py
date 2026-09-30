"""Default Viral Shorts Campaign Preset.

Reference-driven cinematic editorial short-form editing with contextual B-roll, phrase-level captions, centered landscape-card framing, and auto-ducked BGM.
"""

from ai_broll_autopilot.campaigns.base import CampaignConfig

DEFAULT_VIRAL_CAMPAIGN = CampaignConfig(
    id="default",
    name="Default Viral Shorts",
    client="General Short-Form Studio",
    rate="N/A (Standard Studio Workflow)",
    total_budget="N/A",
    platforms=["TikTok", "Instagram Reels", "YouTube Shorts"],
    description="Cinematic editorial short workflow derived from the supplied reference edit: contextual/archival cutaways, phrase-level editorial captions, restrained motion, centered card framing, and auto-ducked music.",

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
    max_broll_ratio=0.55,
    max_cutaway_seconds=5.0,
    speed_multiplier=1.0,
    niche_id="generic",
    editing_style="cinematic_editorial",
    frame_viewport=(20, 410, 1040, 1100),

    # Watermark rules
    watermark_required=False,
    watermark_asset_path=None,
    watermark_position="none",

    # Subtitle rules
    subtitles_required=True,
    subtitle_style="editorial_story",
    subtitle_position="center",
    subtitle_margin_v=0,
    hook_required=False,

    rules_checklist=[
        "Use the cinematic editorial reference style: black 9:16 canvas with a centered contained landscape card and rounded corners.",
        "Use fewer, stronger contextual cutaways. Prefer archival, documentary, news, film, TV, location, object, and reaction visuals directly tied to the dialogue.",
        "Captions are phrase-level (about 2-4 words), centered inside the video card, with restrained white typography and selective warm-yellow/cool accent emphasis.",
        "Use hard cuts and subtle 1.04x-1.08x punch-ins only on genuine emphasis; do not constantly zoom or add flashy transitions.",
        "Allow longer visual holds near the payoff when the source material benefits from it.",
        "Sidechain audio auto-ducking under dialogue; SFX should land on major visual/caption hits rather than every cut.",
        "Do not inject unrelated streamer memes or generic corporate stock into documentary/editorial stories."
    ],
    instant_rejections=[],
    director_system_prompt=None,
    curated_moments=[]
)
