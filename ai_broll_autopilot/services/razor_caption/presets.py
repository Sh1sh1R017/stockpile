"""ZapCap Font Presets, Color Palettes, and Semantic Emoji Mappings.

Provides 21 visual style presets inspired by creator short-form video standards
(Hormozi, Beast, Clean, Gstaad, Beth, Lira, Felix, Cairo, Kendrick, Cora, Theo,
Milo, Skye, Finn, Hugo, Axel, Aurora, Neon, Ember, Frost, Velvet).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ZapCapPreset:
    """Defines a typography and motion style for kinetic captions."""
    key: str
    name: str
    category: str  # "Impactful", "Minimal", "Playful", "Editorial", "Cyber", "Retro"
    font_family: str
    font_weight: str  # "Normal", "Bold", "ExtraBold", "Black"
    font_size: int
    uppercase: bool
    fill_color: str
    highlight_color: str
    secondary_color: str
    stroke_color: str
    stroke_width: int
    shadow_color: str
    shadow_blur: int
    letter_spacing: float
    line_spacing: float
    default_animation: str  # "pop", "bounce", "scale", "fade", "snap"
    description: str


ZAPCAP_PRESETS: Dict[str, ZapCapPreset] = {
    "cinematic_social": ZapCapPreset(
        key="cinematic_social",
        name="Cinematic Social",
        category="Editorial",
        font_family="Arial",
        font_weight="Bold",
        font_size=64,
        uppercase=False,
        fill_color="#FFFFFF",
        highlight_color="#F1D98B",
        secondary_color="#B9B0A0",
        stroke_color="#000000",
        stroke_width=2,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=6,
        letter_spacing=0.01,
        line_spacing=1.05,
        default_animation="scale",
        description="Center-stacked editorial captions with restrained warm-word emphasis and minimal outline.",
    ),
    "hormozi": ZapCapPreset(
        key="hormozi",
        name="Hormozi",
        category="Impactful",
        font_family="Montserrat",
        font_weight="Black",
        font_size=68,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#FFE600",  # Yellow punch
        secondary_color="#00FF66",  # Money green
        stroke_color="#000000",
        stroke_width=8,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.04,
        line_spacing=1.1,
        default_animation="pop",
        description="Bold yellow punch with heavy black outline. High-converting creator classic.",
    ),
    "beast": ZapCapPreset(
        key="beast",
        name="Beast",
        category="Impactful",
        font_family="Impact",
        font_weight="Black",
        font_size=74,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#00FF66",  # Neon viral green
        secondary_color="#FFE600",
        stroke_color="#000000",
        stroke_width=9,
        shadow_color="rgba(0, 0, 0, 0.95)",
        shadow_blur=12,
        letter_spacing=0.02,
        line_spacing=1.05,
        default_animation="bounce",
        description="Massive high-voltage green and yellow captions for extreme viral retention.",
    ),
    "clean": ZapCapPreset(
        key="clean",
        name="Clean",
        category="Minimal",
        font_family="Inter",
        font_weight="Bold",
        font_size=60,
        uppercase=False,
        fill_color="#FFFFFF",
        highlight_color="#38BDF8",  # Sky blue
        secondary_color="#94A3B8",
        stroke_color="#000000",
        stroke_width=5,
        shadow_color="rgba(0, 0, 0, 0.75)",
        shadow_blur=6,
        letter_spacing=0.01,
        line_spacing=1.2,
        default_animation="scale",
        description="Modern Swiss typography with subtle sky blue active word emphasis.",
    ),
    "gstaad": ZapCapPreset(
        key="gstaad",
        name="Gstaad",
        category="Editorial",
        font_family="Playfair Display",
        font_weight="Bold",
        font_size=64,
        uppercase=False,
        fill_color="#FDF6E2",
        highlight_color="#E2B714",  # Luxury gold
        secondary_color="#C29B38",
        stroke_color="#1A1A1A",
        stroke_width=5,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=8,
        letter_spacing=0.03,
        line_spacing=1.2,
        default_animation="fade",
        description="Timeless luxury serif with warm gold active word highlight.",
    ),
    "beth": ZapCapPreset(
        key="beth",
        name="Beth",
        category="Playful",
        font_family="Caveat",
        font_weight="Bold",
        font_size=70,
        uppercase=False,
        fill_color="#FFFFFF",
        highlight_color="#F472B6",  # Soft rose pink
        secondary_color="#FB7185",
        stroke_color="#1E1B4B",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=8,
        letter_spacing=0.02,
        line_spacing=1.15,
        default_animation="bounce",
        description="Handwritten storytelling vibe with playful pink accents.",
    ),
    "lira": ZapCapPreset(
        key="lira",
        name="Lira",
        category="Impactful",
        font_family="Poppins",
        font_weight="ExtraBold",
        font_size=66,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#FB923C",  # Sunset coral
        secondary_color="#FDE047",
        stroke_color="#000000",
        stroke_width=7,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.03,
        line_spacing=1.1,
        default_animation="pop",
        description="Vibrant sunset coral with punchy geometric weight.",
    ),
    "felix": ZapCapPreset(
        key="felix",
        name="Felix",
        category="Cyber",
        font_family="Orbitron",
        font_weight="Bold",
        font_size=62,
        uppercase=True,
        fill_color="#E0E7FF",
        highlight_color="#818CF8",  # Electric violet
        secondary_color="#38BDF8",
        stroke_color="#0F172A",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.06,
        line_spacing=1.1,
        default_animation="snap",
        description="Futuristic tech aesthetic with cyber purple and blue active glow.",
    ),
    "cairo": ZapCapPreset(
        key="cairo",
        name="Cairo",
        category="Impactful",
        font_family="Oswald",
        font_weight="Black",
        font_size=76,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#FACC15",  # Golden yellow
        secondary_color="#EF4444",
        stroke_color="#000000",
        stroke_width=9,
        shadow_color="rgba(0, 0, 0, 0.95)",
        shadow_blur=12,
        letter_spacing=0.02,
        line_spacing=1.05,
        default_animation="pop",
        description="Condensed heavy headline font. Dominates the frame with authority.",
    ),
    "kendrick": ZapCapPreset(
        key="kendrick",
        name="Kendrick",
        category="Impactful",
        font_family="Bebas Neue",
        font_weight="Black",
        font_size=78,
        uppercase=True,
        fill_color="#FAFAFA",
        highlight_color="#EF4444",  # Crimson red
        secondary_color="#F59E0B",
        stroke_color="#000000",
        stroke_width=9,
        shadow_color="rgba(0, 0, 0, 0.95)",
        shadow_blur=14,
        letter_spacing=0.04,
        line_spacing=1.0,
        default_animation="pop",
        description="Raw documentary feel with intense crimson red hook highlights.",
    ),
    "cora": ZapCapPreset(
        key="cora",
        name="Cora",
        category="Playful",
        font_family="Nunito",
        font_weight="Black",
        font_size=64,
        uppercase=False,
        fill_color="#FFFFFF",
        highlight_color="#34D399",  # Mint green
        secondary_color="#60A5FA",
        stroke_color="#064E3B",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=8,
        letter_spacing=0.02,
        line_spacing=1.15,
        default_animation="bounce",
        description="Friendly rounded curves with fresh mint highlights.",
    ),
    "theo": ZapCapPreset(
        key="theo",
        name="Theo",
        category="Editorial",
        font_family="Merriweather",
        font_weight="Black",
        font_size=62,
        uppercase=False,
        fill_color="#FFFBEB",
        highlight_color="#D97706",  # Warm whiskey amber
        secondary_color="#92400E",
        stroke_color="#1C1917",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.85)",
        shadow_blur=9,
        letter_spacing=0.02,
        line_spacing=1.18,
        default_animation="pop",
        description="Rich editorial serif crafted for high-signal conversational podcasts.",
    ),
    "milo": ZapCapPreset(
        key="milo",
        name="Milo",
        category="Impactful",
        font_family="Syne",
        font_weight="ExtraBold",
        font_size=66,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#A855F7",  # Grape purple
        secondary_color="#EC4899",
        stroke_color="#000000",
        stroke_width=7,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.05,
        line_spacing=1.1,
        default_animation="pop",
        description="Avant-garde streetwear typography with electric purple pop.",
    ),
    "skye": ZapCapPreset(
        key="skye",
        name="Skye",
        category="Minimal",
        font_family="Outfit",
        font_weight="Bold",
        font_size=62,
        uppercase=True,
        fill_color="#F0FDF4",
        highlight_color="#22D3EE",  # Neon cyan
        secondary_color="#A7F3D0",
        stroke_color="#083344",
        stroke_width=5,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=8,
        letter_spacing=0.08,
        line_spacing=1.15,
        default_animation="scale",
        description="Wide tracked futuristic sans with bright cyan focal emphasis.",
    ),
    "finn": ZapCapPreset(
        key="finn",
        name="Finn",
        category="Playful",
        font_family="Bangers",
        font_weight="Black",
        font_size=74,
        uppercase=True,
        fill_color="#FEF08A",
        highlight_color="#F97316",  # Tiger orange
        secondary_color="#EF4444",
        stroke_color="#000000",
        stroke_width=8,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.03,
        line_spacing=1.05,
        default_animation="bounce",
        description="Comic book punch with snappy bounce and comic book drop shadow.",
    ),
    "hugo": ZapCapPreset(
        key="hugo",
        name="Hugo",
        category="Editorial",
        font_family="Barlow",
        font_weight="Black",
        font_size=68,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#3B82F6",  # Electric blue
        secondary_color="#10B981",
        stroke_color="#000000",
        stroke_width=7,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.03,
        line_spacing=1.1,
        default_animation="pop",
        description="Crisp corporate authority with decisive blue keyword pop.",
    ),
    "axel": ZapCapPreset(
        key="axel",
        name="Axel",
        category="Impactful",
        font_family="Roboto",
        font_weight="Black",
        font_size=70,
        uppercase=True,
        fill_color="#FFFFFF",
        highlight_color="#E11D48",  # Speed red
        secondary_color="#F59E0B",
        stroke_color="#000000",
        stroke_width=8,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.02,
        line_spacing=1.05,
        default_animation="slide",
        description="High-velocity italic styling engineered for sports & workout reels.",
    ),
    "aurora": ZapCapPreset(
        key="aurora",
        name="Aurora",
        category="Cyber",
        font_family="Montserrat",
        font_weight="ExtraBold",
        font_size=66,
        uppercase=True,
        fill_color="#F5F3FF",
        highlight_color="#C084FC",  # Neon lavender glow
        secondary_color="#38BDF8",
        stroke_color="#2E1065",
        stroke_width=7,
        shadow_color="rgba(147, 51, 234, 0.5)",
        shadow_blur=14,
        letter_spacing=0.03,
        line_spacing=1.1,
        default_animation="pop",
        description="Dreamy synthwave aesthetic with glowing purple and cyan reflections.",
    ),
    "neon": ZapCapPreset(
        key="neon",
        name="Neon",
        category="Cyber",
        font_family="Rajdhani",
        font_weight="Bold",
        font_size=70,
        uppercase=True,
        fill_color="#ECFEFF",
        highlight_color="#06B6D4",  # Cyan cyber
        secondary_color="#F43F5E",  # Hot pink
        stroke_color="#083344",
        stroke_width=7,
        shadow_color="rgba(6, 182, 212, 0.6)",
        shadow_blur=16,
        letter_spacing=0.05,
        line_spacing=1.05,
        default_animation="pop",
        description="Cyberpunk nightlife neon with luminous cyan and magenta glow.",
    ),
    "ember": ZapCapPreset(
        key="ember",
        name="Ember",
        category="Impactful",
        font_family="Impact",
        font_weight="Black",
        font_size=72,
        uppercase=True,
        fill_color="#FEF2F2",
        highlight_color="#FF4500",  # Blazing orange-red
        secondary_color="#FFD700",
        stroke_color="#450A0A",
        stroke_width=9,
        shadow_color="rgba(255, 69, 0, 0.5)",
        shadow_blur=14,
        letter_spacing=0.02,
        line_spacing=1.05,
        default_animation="bounce",
        description="High-heat fiery glow for intense debates and controversial hooks.",
    ),
    "frost": ZapCapPreset(
        key="frost",
        name="Frost",
        category="Minimal",
        font_family="Plus Jakarta Sans",
        font_weight="ExtraBold",
        font_size=62,
        uppercase=False,
        fill_color="#F0F9FF",
        highlight_color="#67E8F9",  # Ice cyan
        secondary_color="#93C5FD",
        stroke_color="#082F49",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.8)",
        shadow_blur=8,
        letter_spacing=0.02,
        line_spacing=1.15,
        default_animation="scale",
        description="Ultra-clean crystalline aesthetics with cool glacial highlights.",
    ),
    "velvet": ZapCapPreset(
        key="velvet",
        name="Velvet",
        category="Editorial",
        font_family="Cinzel",
        font_weight="Bold",
        font_size=64,
        uppercase=True,
        fill_color="#FAF5FF",
        highlight_color="#C026D3",  # Royal fuchsia
        secondary_color="#E879F9",
        stroke_color="#3B0764",
        stroke_width=6,
        shadow_color="rgba(0, 0, 0, 0.9)",
        shadow_blur=10,
        letter_spacing=0.04,
        line_spacing=1.15,
        default_animation="fade",
        description="Regal cinematic title preset with deep velvet fuchsia brilliance.",
    ),
}


# ---------------------------------------------------------------------------
# Semantic Emoji Dictionary
# ---------------------------------------------------------------------------

SEMANTIC_EMOJI_MAP: Dict[str, str] = {
    # Money & Wealth
    "money": "💵",
    "dollar": "💵",
    "dollars": "💵",
    "cash": "💵",
    "rich": "💰",
    "million": "💰",
    "millions": "💰",
    "billion": "💰",
    "billions": "💰",
    "lottery": "🎰",
    "jackpot": "🎰",
    "gamble": "🎰",
    "crypto": "🪙",
    "bitcoin": "🪙",

    # Negation & Mistakes
    "wrong": "❌",
    "not": "❌",
    "never": "❌",
    "fake": "❌",
    "lie": "❌",
    "mistake": "❌",
    "stop": "🛑",
    "warning": "⚠️",
    "danger": "⚠️",

    # Knowledge & Focus
    "secret": "🤫",
    "brain": "🧠",
    "mind": "🧠",
    "idea": "💡",
    "truth": "🔍",
    "target": "🎯",
    "goal": "🎯",
    "focus": "🎯",
    "growth": "📈",
    "scale": "📈",

    # Action & Time
    "wait": "⏳",
    "time": "⏱️",
    "fast": "⚡",
    "quick": "⚡",
    "change": "🔄",
    "pivot": "🔄",
    "fire": "🔥",
    "insane": "🔥",
    "crazy": "🤯",
    "shocking": "😱",
    "win": "🏆",
    "winner": "🏆",
    "king": "👑",
    "boss": "👑",
    "rocket": "🚀",
    "launch": "🚀",
    "love": "❤️",
}


def get_preset(key: str) -> ZapCapPreset:
    """Return preset by key with fallback to Hormozi."""
    return ZAPCAP_PRESETS.get(key.lower(), ZAPCAP_PRESETS["hormozi"])


def map_word_to_emoji(word: str) -> Optional[str]:
    """Return matching contextual emoji for a given word if recognized."""
    clean = word.lower().strip("$.,!?:;\"'()[]{}")
    return SEMANTIC_EMOJI_MAP.get(clean)


def list_all_presets() -> List[Dict[str, Any]]:
    """Return list of serialized ZapCap style presets for frontend consumption."""
    return [
        {
            "key": p.key,
            "name": p.name,
            "category": p.category,
            "font_family": p.font_family,
            "font_weight": p.font_weight,
            "font_size": p.font_size,
            "uppercase": p.uppercase,
            "fill_color": p.fill_color,
            "highlight_color": p.highlight_color,
            "secondary_color": p.secondary_color,
            "stroke_color": p.stroke_color,
            "stroke_width": p.stroke_width,
            "shadow_color": p.shadow_color,
            "shadow_blur": p.shadow_blur,
            "letter_spacing": p.letter_spacing,
            "line_spacing": p.line_spacing,
            "default_animation": p.default_animation,
            "description": p.description,
        }
        for p in ZAPCAP_PRESETS.values()
    ]

