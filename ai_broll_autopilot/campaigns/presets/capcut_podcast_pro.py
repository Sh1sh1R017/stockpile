"""CapCut Cyber Before & After Podcast Campaign Preset.

Replicates the viral CapCut Before & After showcase editing style:
- Neon green cyber grid canvas with deep forest green radial vignette
- Dual floating cards:
    - Left ("BEFORE"): Raw footage, standard colors, 352x600, rounded corners
    - Right ("AFTER"): Punch-in zoom, vibrant color grading, cutaway B-roll overlays, 600x1060, rounded corners
- Bold neon cyan headers ("BEFORE" and "AFTER")
- Kinetic cyan / golden amber / white typography centered horizontally over the AFTER card.
"""

from ai_broll_autopilot.campaigns.base import CampaignConfig

CAPCUT_PODCAST_PRO_CAMPAIGN = CampaignConfig(
    id="capcut_podcast_pro",
    name="CapCut Cyber Before & After Podcast",
    client="Podcast Viral Showcase",
    rate="High-End Studio Workflow",
    total_budget="N/A",
    platforms=["YouTube Shorts", "TikTok", "Instagram Reels"],
    description=(
        "Signature Before & After podcast showcase: glowing cyber grid canvas, "
        "dual floating rounded cards, punch-in color-graded AFTER window with B-roll cutaways, "
        "and neon cyan & golden amber kinetic captions."
    ),

    # Video specs
    target_width=1080,
    target_height=1920,
    duration_min=15.0,
    duration_max=60.0,
    target_duration=30.0,

    # Audio rules
    allow_bgm=True,
    bgm_genre="cyber_electronic",
    preserve_dialogue_only=False,

    # Visual & B-roll rules
    allow_ai_broll=True,
    max_broll_ratio=0.50,
    max_cutaway_seconds=2.5,
    speed_multiplier=1.20,
    niche_id="podcast_showcase",

    # Layout rules
    layout_mode="before_after_cyber_grid",
    frame_overlay_required=False,

    # Subtitle rules
    subtitles_required=True,
    subtitle_style="capcut_cyber",
    subtitle_position="bottom",
    subtitle_margin_v=780,
    hook_required=False,

    rules_checklist=[
        "Forest green cyber grid canvas (1080x1920) with ambient drop shadow cards.",
        "Left BEFORE card: 352x600 raw camera video with rounded corners.",
        "Right AFTER card: 600x1060 punch-in zoom, color-graded with cutaways.",
        "Bold neon cyan BEFORE and AFTER headers floating above cards.",
        "Dual-color kinetic typography (neon cyan & golden amber) inside AFTER card.",
        "Dynamic audio auto-ducking beneath spoken dialogue."
    ],
    instant_rejections=[
        "Missing cyber grid canvas or background.",
        "Captions overlapping outside the AFTER card boundaries.",
        "Lack of color grading contrast between BEFORE and AFTER windows."
    ],
    director_system_prompt=None,
    curated_moments=[]
)
