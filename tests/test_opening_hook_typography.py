"""Regression tests for the reference-style opening hook typography."""

from ai_broll_autopilot.services.razor_caption.caption_event import CaptionEvent, LayerMode


def test_behind_subject_hook_keeps_semantic_text_clean_but_renders_stacked():
    event = CaptionEvent(word="TUTORIAL")
    event.layer = LayerMode.BEHIND_SUBJECT

    # Canonical/edit-plan text remains clean.
    assert str(event.word) == "TUTORIAL"
    assert event.to_edit_plan_entry()["text"] == "TUTORIAL"

    # The existing ASS renderer calls .strip().upper(), which now produces
    # the oversized stacked-letter treatment without changing the data model.
    rendered = event.word.strip().upper()
    assert r"{\fs180\bord7\shad4}" in rendered
    assert r"\N" in rendered
    assert rendered.endswith("T\NU\NT\NO\NR\NI\NA\NL")
