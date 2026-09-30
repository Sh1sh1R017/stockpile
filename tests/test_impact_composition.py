from ai_broll_autopilot.services.razor_caption.caption_event import CaptionEvent, EmphasisLevel
from ai_broll_autopilot.services.razor_caption.state_machine import CaptionStateMachine
from ai_broll_autopilot.services.editorial.types import EditIntent


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


def test_chaos_budget_rations_back_to_back_impacts():
    events = [
        CaptionEvent(word="CHAOS", phrase_id=1, start_time=0.0, end_time=0.4,
                     word_importance_score=0.96, hook_relevance=0.9,
                     emphasis=EmphasisLevel.HOOK, semantic_type="chaos"),
        CaptionEvent(word="INSANE", phrase_id=2, start_time=0.3, end_time=0.7,
                     word_importance_score=0.96, hook_relevance=0.9,
                     emphasis=EmphasisLevel.HOOK, semantic_type="chaos"),
    ]
    CaptionStateMachine().wire(events)
    assert events[0].chaos_tier == "absurd"
    assert events[0].motion_recipe == "kinetic:word-impact-camera"
    assert events[1].chaos_tier in {"normal", "kinetic"}
    assert events[1].motion_recipe != "kinetic:word-impact-camera"
    assert events[1].composition_role != "hero"


def test_chaos_budget_recovers_for_later_peak():
    events = [
        CaptionEvent(word="CHAOS", phrase_id=1, start_time=0.0, end_time=0.4,
                     word_importance_score=0.96, emphasis=EmphasisLevel.HOOK,
                     semantic_type="chaos"),
        CaptionEvent(word="INSANE", phrase_id=2, start_time=5.0, end_time=5.4,
                     word_importance_score=0.96, emphasis=EmphasisLevel.HOOK,
                     semantic_type="chaos"),
    ]
    CaptionStateMachine().wire(events)
    assert events[0].chaos_tier == "absurd"
    assert events[1].chaos_tier == "absurd"
    assert all(e.motion_recipe == "kinetic:word-impact-camera" for e in events)


def test_keyword_alone_does_not_spend_chaos_budget():
    events = [
        CaptionEvent(word="CRAZY", phrase_id=3, start_time=0.0, end_time=0.4,
                     word_importance_score=0.1),
    ]
    CaptionStateMachine().wire(events)
    assert events[0].chaos_tier == "normal"
    assert events[0].composition_role == "normal"
    assert events[0].motion_recipe != "kinetic:word-impact-camera"


def test_shared_editorial_intent_overrides_local_keyword_chaos():
    events = [
        CaptionEvent(
            word="CHAOS",
            phrase_id=9,
            start_time=0.0,
            end_time=0.5,
            word_importance_score=0.96,
            emphasis=EmphasisLevel.HOOK,
            semantic_type="chaos",
        )
    ]
    intent = EditIntent(
        start_time=0.0,
        end_time=1.0,
        chaos_score=0.25,
        chaos_tier="normal",
        treatment="normal",
        chaos_budget_remaining=0.75,
    )

    CaptionStateMachine().wire(events, editorial_intents=[intent])

    assert events[0].chaos_tier == "normal"
    assert events[0].motion_recipe != "kinetic:word-impact-camera"
    assert events[0].composition_role == "normal"
