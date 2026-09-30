from ai_broll_autopilot.services.editorial.creative_director import CreativeDirector
from ai_broll_autopilot.services.editorial.types import (
    EditIntent,
    EditorialMoment,
    NarrativeRole,
    SentimentCategory,
)


def make_moment(**kwargs):
    values = {
        "moment_id": "m1",
        "start_time": 0.0,
        "end_time": 1.5,
        "duration": 1.5,
        "text": "This was actually insane",
        "narrative_role": NarrativeRole.PAYOFF,
        "sentiment": SentimentCategory.FUNNY,
        "emotional_intensity": 0.9,
        "speaker_emphasis": 0.9,
        "information_density": 0.8,
        "visual_opportunity": 0.7,
        "energy_level": 0.9,
    }
    values.update(kwargs)
    return EditorialMoment(**values)


def test_creative_director_returns_shared_intent_contract():
    moment = make_moment()
    intent = CreativeDirector().analyze([moment], hook_moment_id="m1")[0]

    assert isinstance(intent, EditIntent)
    assert intent.hook_relevance == 1.0
    assert intent.chaos_score > 0.6
    assert intent.treatment in {"impact", "absurd"}


def test_creative_director_preserves_quiet_moments():
    moment = make_moment(
        text="And then I sat there for a while.",
        narrative_role=NarrativeRole.REFLECTIVE if hasattr(NarrativeRole, "REFLECTIVE") else NarrativeRole.EXPLANATION,
        sentiment=SentimentCategory.REFLECTIVE,
        emotional_intensity=0.1,
        speaker_emphasis=0.1,
        information_density=0.2,
        visual_opportunity=0.1,
        energy_level=0.1,
    )
    intent = CreativeDirector().analyze([moment])[0]

    assert intent.quietness_score > 0.5
    assert intent.broll_pressure < 0.5
    assert intent.treatment in {"quiet", "normal"}


def test_creative_director_serializes_every_attention_dimension():
    intent = CreativeDirector().analyze([make_moment()])[0]
    payload = intent.to_dict()

    for key in (
        "semantic_importance",
        "emotional_importance",
        "hook_relevance",
        "meme_opportunity",
        "caption_energy",
        "broll_pressure",
        "sfx_opportunity",
        "chaos_score",
        "quietness_score",
        "treatment",
    ):
        assert key in payload
