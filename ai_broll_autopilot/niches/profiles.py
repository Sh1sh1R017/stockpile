"""Built-in generic Niche Profiles covering major content domains."""

from ai_broll_autopilot.niches.base import NicheProfile, NicheEditingPreferences

PROFILES = [
    # 1. SPORTS - BASKETBALL
    NicheProfile(
        id="sports_basketball",
        name="Basketball",
        parent_niche="sports",
        description="Basketball podcasts, games, tournaments, player interviews, and analysis.",
        visual_keywords=[
            "basketball", "court", "nba", "dunk", "shot", "arena", "hoop",
            "crossover", "defense", "coach", "bench", "crowd", "buzzer beater",
            "training", "highlight", "jersey", "gym"
        ],
        broll_categories=[
            "game_action", "player_reaction", "crowd", "celebration",
            "training", "interview", "arena", "coach", "fans"
        ],
        preferred_energy="high",
        editing=NicheEditingPreferences(
            pace="fast",
            cut_frequency="dynamic",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="minimal",
            zoom_style="subtle",
            max_broll_ratio=0.33,
            meme_cutaways=False,
        ),
        avoid=[
            "generic_stock_footage", "irrelevant_broll", "excessive_zoom",
            "constant_transitions", "AI-looking_visuals", "corporate_office"
        ],
    ),

    # 2. SPORTS - GENERAL
    NicheProfile(
        id="sports",
        name="Sports (General)",
        parent_niche="sports",
        description="General athletics, competitions, athletic training, and sports commentary.",
        visual_keywords=[
            "athlete", "stadium", "field", "competition", "training", "workout",
            "coach", "team", "celebration", "trophy", "fans", "running", "play"
        ],
        broll_categories=["action", "reaction", "stadium", "training", "fans", "celebration"],
        preferred_energy="high",
        editing=NicheEditingPreferences(
            pace="fast",
            cut_frequency="dynamic",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="punchy",
            zoom_style="subtle",
            max_broll_ratio=0.35,
        ),
        avoid=["corporate_stock", "slow_pans", "excessive_effects"],
    ),

    # 3. BUSINESS - STARTUP & ENTREPRENEURSHIP
    NicheProfile(
        id="business_startup",
        name="Startup & Entrepreneurship",
        parent_niche="business",
        description="Founder stories, startup growth, venture capital, pitching, and business strategy.",
        visual_keywords=[
            "founder", "startup", "office", "pitch", "whiteboard", "coding",
            "product launch", "team meeting", "hustle", "laptop", "charts", "revenue",
            "marketing", "ads", "advertising", "ecommerce", "sales", "landing page",
            "campaign", "meta", "funnel", "conversion", "digital marketing"
        ],
        broll_categories=["office_collaboration", "pitch_meeting", "product_work", "data_charts", "founders", "marketing", "ecommerce"],
        preferred_energy="medium",
        editing=NicheEditingPreferences(
            pace="moderate",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="clean",
            transition_style="minimal",
            zoom_style="subtle",
            max_broll_ratio=0.35,
        ),
        avoid=["cliché_handshakes", "fake_business_smiles", "distracting_sound_effects"],
    ),

    # 4. BUSINESS - GENERAL & FINANCE
    NicheProfile(
        id="finance",
        name="Finance & Investing",
        parent_niche="business",
        description="Market analysis, wealth building, investing, stocks, and economic trends.",
        visual_keywords=[
            "stock chart", "market", "trading", "money", "wall street", "banking",
            "economy", "cryptocurrency", "investment", "portfolio", "calculator"
        ],
        broll_categories=["charts", "market_trading", "currency", "financial_district", "analytics"],
        preferred_energy="medium",
        editing=NicheEditingPreferences(
            pace="moderate",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="clean",
            transition_style="minimal",
            zoom_style="none",
            max_broll_ratio=0.30,
        ),
        avoid=["pyramid_schemes", "flashy_money_guns", "distracting_animations"],
    ),

    # 5. TECHNOLOGY - AI & SOFTWARE
    NicheProfile(
        id="tech_ai",
        name="AI & Technology",
        parent_niche="technology",
        description="Artificial intelligence, machine learning, software development, robotics, and hardware.",
        visual_keywords=[
            "artificial intelligence", "code", "neural network", "datacenter", "robotics",
            "terminal", "server", "algorithm", "screen", "developer", "microchip", "interface",
            "software", "programming", "python", "model", "tech", "hardware", "cloud", "api"
        ],
        broll_categories=["datacenter", "code_terminal", "ai_visualization", "robotics", "device_interaction"],
        preferred_energy="medium",
        editing=NicheEditingPreferences(
            pace="dynamic",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="minimal",
            zoom_style="subtle",
            max_broll_ratio=0.40,
        ),
        avoid=["matrix_green_rain", "cheesy_cyborgs", "fake_hacking_interfaces"],
    ),

    # 6. GAMING
    NicheProfile(
        id="gaming",
        name="Gaming & Esports",
        parent_niche="gaming",
        description="Video game commentary, esports tournaments, streamer moments, and gaming culture.",
        visual_keywords=[
            "gameplay", "controller", "pc gaming", "esports", "headset", "victory",
            "defeat", "speedrun", "streamer", "keyboard", "rgb lights", "arena",
            "game", "engine", "shader", "fps", "boss fight", "unreal engine", "steam",
            "playstation", "xbox", "nintendo", "multiplayer", "respawn", "quest"
        ],
        broll_categories=["gameplay_action", "player_reaction", "esports_crowd", "tournament_stage", "equipment"],
        preferred_energy="high",
        editing=NicheEditingPreferences(
            pace="fast",
            cut_frequency="rapid",
            broll_frequency="high",
            caption_style="bold",
            transition_style="punchy",
            zoom_style="dynamic",
            max_broll_ratio=0.50,
            meme_cutaways=True,
        ),
        avoid=["slow_panning", "corporate_footage", "flat_colors"],
    ),

    # 7. COMEDY & ENTERTAINMENT
    NicheProfile(
        id="comedy",
        name="Comedy & Entertainment",
        parent_niche="entertainment",
        description="Standup, funny stories, improv, podcast banter, and humor.",
        visual_keywords=[
            "laughter", "crowd laughing", "standup comedy", "punchline", "comedian",
            "stage", "reaction", "hilarious", "smirk", "banter", "joke", "funny",
            "sketch", "prank", "roast", "sarcasm", "giggle", "spoof"
        ],
        broll_categories=["crowd_laughing", "comedian_stage", "humorous_reaction", "visual_gag"],
        preferred_energy="high",
        editing=NicheEditingPreferences(
            pace="dynamic",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="minimal",
            zoom_style="dynamic",
            max_broll_ratio=0.25,
            meme_cutaways=True,
        ),
        avoid=["spoiling_punchline_early", "overwhelming_bgm", "serious_corporate_broll"],
    ),

    # 8. EDUCATION & SCIENCE
    NicheProfile(
        id="education",
        name="Education & Science",
        parent_niche="education",
        description="Science explainers, academic discussions, tutorials, and educational lectures.",
        visual_keywords=[
            "experiment", "laboratory", "diagram", "space", "nature", "history",
            "microscope", "chalkboard", "astronomy", "research", "scientific"
        ],
        broll_categories=["experiments", "visual_diagrams", "nature_footage", "historical_footage", "laboratory"],
        preferred_energy="calm",
        editing=NicheEditingPreferences(
            pace="moderate",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="clean",
            transition_style="smooth",
            zoom_style="none",
            max_broll_ratio=0.45,
        ),
        avoid=["chaotic_cuts", "loud_distracting_sfx", "irrelevant_memes"],
    ),

    # 9. FITNESS & HEALTH
    NicheProfile(
        id="fitness",
        name="Fitness & Health",
        parent_niche="lifestyle",
        description="Bodybuilding, running, nutrition, mental health, and physical conditioning.",
        visual_keywords=[
            "gym", "workout", "weights", "running", "crossfit", "dumbbells",
            "healthy food", "discipline", "stretching", "athlete training"
        ],
        broll_categories=["gym_workout", "exercise_form", "running", "nutrition", "physique"],
        preferred_energy="high",
        editing=NicheEditingPreferences(
            pace="dynamic",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="punchy",
            zoom_style="subtle",
            max_broll_ratio=0.40,
        ),
        avoid=["slothful_stock", "fake_fitness_actors", "low_energy_footage"],
    ),

    # 10. LAW & POLICY
    NicheProfile(
        id="law",
        name="Law & Legal",
        parent_niche="professional",
        description="Legal cases, constitutional law, court trials, and legal commentary.",
        visual_keywords=[
            "courtroom", "judge", "gavel", "law books", "attorney", "scales of justice",
            "legal document", "jury", "constitution", "trial"
        ],
        broll_categories=["courtroom", "legal_library", "gavel_strikes", "documents"],
        preferred_energy="calm",
        editing=NicheEditingPreferences(
            pace="moderate",
            cut_frequency="sparse",
            broll_frequency="minimal",
            caption_style="clean",
            transition_style="minimal",
            zoom_style="none",
            max_broll_ratio=0.25,
        ),
        avoid=["cheesy_dramatic_gavel_banging", "inaccurate_courtroom_tropes"],
    ),

    # 11. NEWS & JOURNALISM
    NicheProfile(
        id="news",
        name="News & Journalism",
        parent_niche="general",
        description="Breaking news, investigative journalism, press conferences, and current affairs.",
        visual_keywords=[
            "press conference", "news anchor", "microphones", "breaking news",
            "journalism", "broadcast", "cameras", "interview", "reporters"
        ],
        broll_categories=["press_conference", "newsroom", "events", "city_streets", "interviews"],
        preferred_energy="medium",
        editing=NicheEditingPreferences(
            pace="fast",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="clean",
            transition_style="minimal",
            zoom_style="none",
            max_broll_ratio=0.40,
        ),
        avoid=["unverified_stock", "misleading_metaphors"],
    ),

    # 12. GENERIC / DEFAULT
    NicheProfile(
        id="generic",
        name="General Podcast & Speech",
        parent_niche="general",
        description="Universal talking head videos, storytelling, casual interviews, and general commentary.",
        visual_keywords=["interview", "conversation", "studio", "microphone", "speaker", "discussion"],
        broll_categories=["contextual_metaphor", "reaction", "lifestyle", "nature", "city"],
        preferred_energy="medium",
        editing=NicheEditingPreferences(
            pace="dynamic",
            cut_frequency="contextual",
            broll_frequency="contextual",
            caption_style="bold",
            transition_style="minimal",
            zoom_style="subtle",
            max_broll_ratio=0.35,
        ),
        avoid=["generic_business_handshake", "unrelated_nature_cutaways"],
    ),
]
