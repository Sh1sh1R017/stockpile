"""Curious Mike Clipping Campaign Preset.

Tailored specifically to the Curious Mike Clipping Campaign Guidelines
hosted by Michael Porter Jr. (@curiousmike / @mpj).
"""

from pathlib import Path
from ai_broll_autopilot.campaigns.base import CampaignConfig, CuratedMoment

WATERMARK_PATH = str(
    (Path(__file__).resolve().parent.parent.parent.parent / "assets" / "campaigns" / "curious_mike" / "curious_mike_watermark_clean.png").resolve()
)

CURATED_MOMENTS = [
    CuratedMoment(
        moment_id="C01",
        timestamp_range="00:02:16-00:02:44",
        start_time_sec=136.0,
        end_time_sec=164.0,
        screen_hook="Trae called young MPJ a regular guy.",
        post_caption="Trae remembers MPJ before the No. 1 ranking 😂",
        angle=None
    ),
    CuratedMoment(
        moment_id="C02",
        timestamp_range="00:03:07-00:03:37",
        start_time_sec=187.0,
        end_time_sec=217.0,
        screen_hook="MPJ remembers the kid who was already built like an adult.",
        post_caption="Every AAU team had that one kid who looked grown.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C03",
        timestamp_range="00:05:23-00:06:37",
        start_time_sec=323.0,
        end_time_sec=397.0,
        screen_hook="Before the NBA, these two were blowing teams out.",
        post_caption="Trae and MPJ remember when their AAU duo was a problem.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C04",
        timestamp_range="00:06:39-00:07:32",
        start_time_sec=399.0,
        end_time_sec=452.0,
        screen_hook="Who was ranked ahead of Trae Young in high school?",
        post_caption="Trae remembers exactly which guards were ranked above him.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C05",
        timestamp_range="00:08:05-00:08:47",
        start_time_sec=485.0,
        end_time_sec=527.0,
        screen_hook="The coach who changed how Trae thought about rankings.",
        post_caption="The lesson Trae and MPJ still carry from AAU: win first.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C06",
        timestamp_range="00:08:48-00:09:23",
        start_time_sec=528.0,
        end_time_sec=563.0,
        screen_hook="MPJ wanted to quit MOKAN.",
        post_caption="MPJ nearly walked away from the team that helped change his life.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C07",
        timestamp_range="00:10:45-00:11:44",
        start_time_sec=645.0,
        end_time_sec=704.0,
        screen_hook="Their coach had a punishment for saying my bad.",
        post_caption="Saying my bad came with a price on their AAU team 😂",
        angle=None
    ),
    CuratedMoment(
        moment_id="C08",
        timestamp_range="00:11:45-00:12:21",
        start_time_sec=705.0,
        end_time_sec=741.0,
        screen_hook="MPJ had one question for his AAU coach: what about Trae?",
        post_caption="MPJ remembers getting benched while Trae was launching from deep 😂",
        angle=None
    ),
    CuratedMoment(
        moment_id="C09",
        timestamp_range="00:12:21-00:13:09",
        start_time_sec=741.0,
        end_time_sec=789.0,
        screen_hook="MPJ says his high school rise needed Trae Young.",
        post_caption="MPJ gives Trae his flowers for helping him become the No. 1 prospect.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C10",
        timestamp_range="00:13:50-00:14:37",
        start_time_sec=830.0,
        end_time_sec=877.0,
        screen_hook="Even on Team USA, Trae was still waiting for his chance.",
        post_caption="Trae and MPJ remember a very different Team USA experience.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C11",
        timestamp_range="00:14:43-00:17:02",
        start_time_sec=883.0,
        end_time_sec=1022.0,
        screen_hook="A month as roommates ended with THIS argument.",
        post_caption="Trae and MPJ fell out over a light switch 😂",
        angle="The roommate fight"
    ),
    CuratedMoment(
        moment_id="C12",
        timestamp_range="00:17:23-00:18:33",
        start_time_sec=1043.0,
        end_time_sec=1113.0,
        screen_hook="Trae thought he was better than the top-ranked point guard.",
        post_caption="Trae explains why high school hype does not always translate.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C13",
        timestamp_range="00:19:12-00:20:22",
        start_time_sec=1152.0,
        end_time_sec=1222.0,
        screen_hook="One thing MPJ's dad said stayed with Trae for years.",
        post_caption="Trae never forgot what MPJ's dad told him before the NBA.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C14",
        timestamp_range="00:21:14-00:22:44",
        start_time_sec=1274.0,
        end_time_sec=1364.0,
        screen_hook="When did Trae Young actually know he could make the NBA?",
        post_caption="Trae pinpoints when becoming a pro started to feel real.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C15",
        timestamp_range="00:23:15-00:24:57",
        start_time_sec=1395.0,
        end_time_sec=1497.0,
        screen_hook="How does Trae choose between a bucket and an assist?",
        post_caption="Trae explains how he decides whether to score or get everyone involved.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C16",
        timestamp_range="00:24:57-00:25:49",
        start_time_sec=1497.0,
        end_time_sec=1549.0,
        screen_hook="Why does Trae enjoy passing so much?",
        post_caption="For Trae, an assist is about more than the stat sheet.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C17",
        timestamp_range="00:26:13-00:27:08",
        start_time_sec=1573.0,
        end_time_sec=1628.0,
        screen_hook="Trae explains what it means to pass someone open.",
        post_caption="Trae sees the opening before his teammate does.",
        angle="Passing teammates open"
    ),
    CuratedMoment(
        moment_id="C18",
        timestamp_range="00:27:31-00:29:16",
        start_time_sec=1651.0,
        end_time_sec=1756.0,
        screen_hook="How do you defend three players who draw double teams?",
        post_caption="Trae explains why he is excited about Washington's offense.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C19",
        timestamp_range="00:29:16-00:30:32",
        start_time_sec=1756.0,
        end_time_sec=1832.0,
        screen_hook="Trae has now seen AJ up close. Here is his verdict.",
        post_caption="Trae calls AJ the real deal after being around him.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C20",
        timestamp_range="00:30:47-00:31:31",
        start_time_sec=1847.0,
        end_time_sec=1891.0,
        screen_hook="MPJ and Trae react to the draft-lottery changes.",
        post_caption="MPJ and Trae discuss why they want teams competing every night.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C21",
        timestamp_range="00:31:33-00:32:52",
        start_time_sec=1893.0,
        end_time_sec=1972.0,
        screen_hook="Is the East deeper than the West now?",
        post_caption="MPJ and Trae think the East is getting crowded.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C22",
        timestamp_range="00:33:18-00:34:14",
        start_time_sec=1998.0,
        end_time_sec=2054.0,
        screen_hook="Trae calls the change of scenery a fresh start.",
        post_caption="Trae describes the energy of starting again in a new city.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C23",
        timestamp_range="00:34:30-00:37:10",
        start_time_sec=2070.0,
        end_time_sec=2230.0,
        screen_hook="Why does Trae think he gets so much disrespect?",
        post_caption="Trae shares his explanation for why his game gets doubted.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C24",
        timestamp_range="00:38:42-00:40:02",
        start_time_sec=2322.0,
        end_time_sec=2402.0,
        screen_hook="Want Trae's range? Start with your floater.",
        post_caption="Trae's advice for smaller guards starts closer to the basket.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C25",
        timestamp_range="00:40:06-00:40:58",
        start_time_sec=2406.0,
        end_time_sec=2458.0,
        screen_hook="Small guards have another way to stand out.",
        post_caption="Trae gives Davion Mitchell his respect for the defensive work.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C26",
        timestamp_range="00:41:45-00:42:46",
        start_time_sec=2505.0,
        end_time_sec=2566.0,
        screen_hook="Those logo threes are not shots they just try in games.",
        post_caption="Trae says the deep shots start with work you never see.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C27",
        timestamp_range="00:43:54-00:45:09",
        start_time_sec=2634.0,
        end_time_sec=2709.0,
        screen_hook="Does your jumper have to look normal to work?",
        post_caption="Trae and MPJ debate unusual jump shots that still go in.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C28",
        timestamp_range="00:45:11-00:46:18",
        start_time_sec=2711.0,
        end_time_sec=2778.0,
        screen_hook="How can an NBA player practice daily and still struggle at the line?",
        post_caption="MPJ asks the shooting question every fan has wondered about.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C29",
        timestamp_range="00:46:18-00:47:18",
        start_time_sec=2778.0,
        end_time_sec=2838.0,
        screen_hook="MPJ thinks being left open could make him shoot worse.",
        post_caption="MPJ's take on wide-open shots is not what you would expect.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C30",
        timestamp_range="00:48:10-00:48:38",
        start_time_sec=2890.0,
        end_time_sec=2918.0,
        screen_hook="The same shot, over and over: their Kawhi workout story.",
        post_caption="MPJ and Trae talk about the repetition behind Kawhi's jumper.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C31",
        timestamp_range="00:48:40-00:50:34",
        start_time_sec=2920.0,
        end_time_sec=3034.0,
        screen_hook="Trae explains when he knew it was time to move on.",
        post_caption="Trae explains what changed as Atlanta's front office changed.",
        angle="Why it was time to leave Atlanta"
    ),
    CuratedMoment(
        moment_id="C32",
        timestamp_range="00:50:34-00:51:50",
        start_time_sec=3034.0,
        end_time_sec=3110.0,
        screen_hook="What KD and Russ taught Trae about leaving a team.",
        post_caption="Trae wanted to leave Atlanta the right way.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C33",
        timestamp_range="00:52:26-00:53:32",
        start_time_sec=3146.0,
        end_time_sec=3212.0,
        screen_hook="Everyone said MPJ was a lock. Trae warned him otherwise.",
        post_caption="Trae told MPJ the truth when everyone else called him an All-Star lock.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C34",
        timestamp_range="00:54:21-00:55:18",
        start_time_sec=3261.0,
        end_time_sec=3318.0,
        screen_hook="MPJ has heard the not-in-the-lab comments.",
        post_caption="MPJ responds to people who think the podcast means he is not working.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C35",
        timestamp_range="00:55:19-00:55:58",
        start_time_sec=3319.0,
        end_time_sec=3358.0,
        screen_hook="MPJ sees a simple way Julius can create shots for him.",
        post_caption="MPJ explains the two-man chemistry he wants with Julius.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C36",
        timestamp_range="00:56:18-00:57:19",
        start_time_sec=3378.0,
        end_time_sec=3439.0,
        screen_hook="What happens when Trae is not the only player getting doubled?",
        post_caption="Trae is excited to see what happens when someone else draws two.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C37",
        timestamp_range="00:57:19-00:58:25",
        start_time_sec=3439.0,
        end_time_sec=3505.0,
        screen_hook="There is an off-ball side of Trae's game he wants to show.",
        post_caption="Trae and MPJ explain the part of his game fans have seen less of.",
        angle="The off-ball side of Trae"
    ),
    CuratedMoment(
        moment_id="C38",
        timestamp_range="00:58:28-01:00:28",
        start_time_sec=3508.0,
        end_time_sec=3628.0,
        screen_hook="MPJ asked Trae to build a superteam. He backed Washington.",
        post_caption="Asked for a dream team, Trae starts talking about his actual teammates.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C39",
        timestamp_range="01:00:57-01:01:59",
        start_time_sec=3657.0,
        end_time_sec=3719.0,
        screen_hook="Trae builds the perfect starting five around MPJ.",
        post_caption="Trae's lineup around MPJ is loaded.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C40",
        timestamp_range="01:02:00-01:03:17",
        start_time_sec=3720.0,
        end_time_sec=3797.0,
        screen_hook="MPJ tried to leave Jokic off his dream lineup.",
        post_caption="MPJ tried to build a different five, then came back to Jokic.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C41",
        timestamp_range="01:03:42-01:04:34",
        start_time_sec=3822.0,
        end_time_sec=3874.0,
        screen_hook="Trae CUT Jokic in start, bench, cut.",
        post_caption="Trae's start, bench, cut answer: Wemby, Giannis, Jokic 👀",
        angle="Trae cuts Jokic in start, bench, cut"
    ),
    CuratedMoment(
        moment_id="C42",
        timestamp_range="01:04:34-01:05:24",
        start_time_sec=3874.0,
        end_time_sec=3924.0,
        screen_hook="Wemby can take away the lob AND affect the ball.",
        post_caption="MPJ explains why Wemby's defense changes the whole possession.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C43",
        timestamp_range="01:05:25-01:06:22",
        start_time_sec=3925.0,
        end_time_sec=3982.0,
        screen_hook="Ant, Tatum or Booker: Trae had to pick.",
        post_caption="Trae starts Ant, benches Tatum and cuts Booker in the game.",
        angle="Ant, Tatum, Booker"
    ),
    CuratedMoment(
        moment_id="C44",
        timestamp_range="01:06:23-01:06:35",
        start_time_sec=3983.0,
        end_time_sec=3995.0,
        screen_hook="Steph, Luka or SGA? Trae is not touching that one.",
        post_caption="Trae drew the line when the point-guard question came up 😂",
        angle=None
    ),
    CuratedMoment(
        moment_id="C45",
        timestamp_range="01:07:12-01:08:21",
        start_time_sec=4032.0,
        end_time_sec=4101.0,
        screen_hook="Trae says Knicks fans started the rivalry.",
        post_caption="Trae says New York started it, and explains why he answered.",
        angle="Who started the Knicks rivalry"
    ),
    CuratedMoment(
        moment_id="C46",
        timestamp_range="01:08:34-01:10:06",
        start_time_sec=4114.0,
        end_time_sec=4206.0,
        screen_hook="MPJ asked Trae about foul-baiting. He had an answer.",
        post_caption="Trae explains why drawing fouls helps the whole team.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C47",
        timestamp_range="01:10:09-01:11:00",
        start_time_sec=4209.0,
        end_time_sec=4260.0,
        screen_hook="Trae could not believe Bogie played through this contact.",
        post_caption="Trae tells the Bogdanovic story that had him jumping off the bench.",
        angle=None
    ),
    CuratedMoment(
        moment_id="C48",
        timestamp_range="01:11:33-01:12:24",
        start_time_sec=4293.0,
        end_time_sec=4344.0,
        screen_hook="Trae says touching SGA felt like an Iron Man scene.",
        post_caption="Trae's description of SGA selling contact is hilarious 😂",
        angle="The SGA Iron Man story"
    ),
    CuratedMoment(
        moment_id="C49",
        timestamp_range="01:13:10-01:14:06",
        start_time_sec=4390.0,
        end_time_sec=4446.0,
        screen_hook="Trae said no beef with Pat Bev. Then came the ending.",
        post_caption="Trae says there is no beef with Pat Bev, then adds one more line.",
        angle="Pat Bev: no beef, still a jab"
    ),
    CuratedMoment(
        moment_id="C50",
        timestamp_range="01:19:17-01:20:19",
        start_time_sec=4757.0,
        end_time_sec=4819.0,
        screen_hook="Trae never forgot who defended him when people doubted him.",
        post_caption="Trae still remembers MPJ speaking up for him after Summer League.",
        angle="MPJ defended him before the success"
    ),
]

CURIOUS_MIKE_CAMPAIGN = CampaignConfig(
    id="curious_mike",
    name="Curious Mike Clipping Campaign",
    client="Curious Mike (Michael Porter Jr. @curiousmike / @mpj)",
    rate="$1.25 per 1,000 verified views",
    total_budget="$7,500 ($300 cap per clip, min 2,000 views)",
    platforms=["TikTok", "Instagram Reels", "YouTube Shorts"],
    description="Official campaign clipping guidelines for Curious Mike with MPJ. Features the Trae Young episode, 50 pre-curated timestamped moments, zero AI B-roll policy, pure podcast dialogue, and mandatory YT: @mpj watermark.",
    episode_url="https://www.youtube.com/watch?v=uf0q07QagUs",
    
    # Video specs
    target_width=1080,
    target_height=1920,
    duration_min=20.0,
    duration_max=60.0,
    target_duration=35.0,
    
    # Audio rules - strictly pure podcast dialogue (No phonk, No BGM)
    allow_bgm=False,
    bgm_genre=None,
    preserve_dialogue_only=False,  # allow subtle editorial whoosh/impact SFX; allow_bgm=False prevents music
    
    # Visual & B-roll rules - real footage only, max 33% B-roll
    allow_ai_broll=False,
    max_broll_ratio=0.33,
    max_cutaway_seconds=3.0,
    speed_multiplier=1.0,
    
    # Frame Overlay & Framing rules - authentic torn paper cutout border
    frame_overlay_required=True,
    frame_viewport=(65, 378, 950, 1300),

    # Watermark rules - YT: @mpj on screen 100% of duration in safe zone
    watermark_required=True,
    watermark_asset_path=WATERMARK_PATH,
    watermark_position="bottom_safe",
    watermark_scale=0.28,
    watermark_x_offset=0,
    watermark_y_offset=-200,
    
    # Subtitle rules - Curious Mike signature yellow-box highlight inside torn frame
    subtitles_required=True,
    subtitle_style="curious_clean",
    subtitle_position="bottom",
    subtitle_margin_v=760,
    hook_required=True,
    hook_position="top",
    
    rules_checklist=[
        "Rule 1: At least 40% of viewers from US, Canada or UK (Post between 12pm-9pm Eastern, English hook, American B-roll).",
        "Rule 2: At least 1% engagement rate (Clip an argument/hot take/ranking, ask a question in caption).",
        "Rule 3: Strictly NO AI generated video or B-roll (Real footage only, no AI avatars, no AI upscaling).",
        "Rule 4: At least 2,000 views to qualify ($1.25 per 1,000 views, $300 cap per clip).",
        "Rule 5: Only approved episodes (Trae Young or Episode 2).",
        "Rule 6: Mandatory YT: @mpj watermark on screen for full duration of the clip (unmodified, never covered)."
],
    instant_rejections=[
        "No viewer location screenshot",
        "Under 40% US, Canada and UK viewers combined",
        "Under 1% engagement",
        "Under 2,000 views",
        "Any AI generated video, voice or b roll",
        "Footage from an episode outside the 2 approved ones",
        "Another platform's watermark on the video",
        "No burned in captions",
        "Reuploading another clipper's edit",
        "Reposting a video taken from MPJ's socials (removes you from campaign)",
        "Posting the same edit more than once, or across platforms",
        "Music, phonk or any audio over the podcast dialogue",
        "AI auto-clipping tools such as Opus Clips",
        "Aura, glow or skull edits",
        "Misspelled or badly timed subtitles",
        "Drugs or sexual content",
        "Calling yourself the official page or using Michael Porter Jr as display name",
        "Missing the YT: @mpj watermark, covering it up, or editing it",
        "Bought views, bought likes, or engagement pods"
],
    director_system_prompt="""You are the AI Video Director for the CURIOUS MIKE podcast clipping campaign (hosted by Michael Porter Jr. @curiousmike / @mpj).

STRICT CAMPAIGN EDITING RULES:
1. FORMAT & SPEAKER COVERAGE:
   - Format 1 (Straight Talking Head) or Format 2 (Talking Head + Real Sports B-Roll).
   - NEVER cover the speaker for more than 1/3 (33%) of the clip! The speaker's facial reactions and conversation are paramount.
   - Any cutaways must be brief (1.0 to 3.0 seconds max), cutting in directly on the exact keyword (e.g. 'Knicks', 'AAU', 'Jokic').
   - Cut back to the speaker immediately.

2. ZERO AI VIDEO POLICY (CRITICAL):
   - STRICTLY NO AI-generated video, avatars, or fictional cutaways.
   - All B-roll MUST be real footage: NBA game highlights, press conferences, AAU basketball footage, or arena atmosphere.

3. AUDIO INTEGRITY:
   - ZERO background music, phonk, or audio over the dialogue. Podcast audio must run cleanly throughout.

4. FIRST 0.5s HOOK & WORD-BY-WORD SUBTITLES:
   - Screen hook text must be present in the first 0.5 seconds, punchy and all-caps.
   - Captions must be burned-in, word-by-word, clean white with subtle shadow, placed safely so they NEVER overlap the YT: @mpj watermark.
""",
    curated_moments=CURATED_MOMENTS
)
