from ai_broll_autopilot.services.razor_caption.caption_event import CaptionEvent, EmphasisLevel
from ai_broll_autopilot.services.razor_caption.state_machine import CaptionStateMachine


def test_sentence_gets_hero_and_support_roles():
    events = [
        CaptionEvent(word="JOEY", phrase_id=1, start_time=0.0, end_time=0.3, word_importance_score=0.30),
        CaptionEvent(word="DIAZ", phrase_id=1, start_time=0.3, end_time=0.6, word_importance_score=0.35),
        CaptionEvent(word="WAS", phrase_id=1, start_time=0.6, end_time=0.8, word_importance_score=0.20),
        CaptionEvent(word="PURE", phrase_id=1, start_time=0.8, end_time=1.0, word_importance_score=0.40),
        CaptionEvent(word="CHAOS", phrase_id=1, start_time=1.0, end_time=1.5, word_importance_score=0.96, emphasis=EmphasisLevel.HOOK, semantic_type="chaos"),
    ]
    CaptionStateMachine().wire(events)
    hero = next(e for e in events if e.word == "CHAOS")
    assert hero.composition_role == "hero"
    assert hero.typography_style == "impact-hero"
    assert hero.motion_recipe == "kinetic:word-impact-camera"
    assert hero.motion_params["frame_bleed"] is True
    assert all(e.composition_role == "support" for e in events if e is not hero)


def test_normal_sentence_is_not_forced_into_chaos_composition():
    events = [
        CaptionEvent(word="I", phrase_id=2, word_importance_score=0.1),
        CaptionEvent(word="started", phrase_id=2, word_importance_score=0.2),
        CaptionEvent(word="working", phrase_id=2, word_importance_score=0.2),
        CaptionEvent(word="today", phrase_id=2, word_importance_score=0.2),
    ]
    CaptionStateMachine().wire(events)
    assert all(e.composition_role == "normal" for e in events)
