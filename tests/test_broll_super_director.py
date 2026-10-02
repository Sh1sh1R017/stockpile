from ai_broll_autopilot.services.broll_super_director import BrollSuperDirector


def test_super_director_apply_retimes_shots_to_emotional_moments():
    director = BrollSuperDirector(api_key=None)
    plan = {
        "shots": [
            {"shot_id": "broll_1", "start_time": 2.0, "end_time": 4.0, "duration": 2.0},
            {"shot_id": "broll_2", "start_time": 8.0, "end_time": 10.0, "duration": 2.0},
        ]
    }
    analysis = {
        "model": "test",
        "moments": [
            {
                "start": 14.0,
                "end": 16.0,
                "anchor_quote": "I almost gave up.",
                "emotion": "vulnerability",
                "sentiment": "negative",
                "tone_of_voice": "quiet",
                "tone_intensity": 91,
                "impact_score": 98,
                "visualizability": 96,
                "broll_priority": 99,
                "best_for_broll": True,
                "visual_strategy": "person sitting alone reflecting after failure",
                "search_queries": [
                    "person sitting alone reflection",
                    "exhausted person empty room",
                ],
                "why_broll": "High-impact confession with a strong human visual metaphor.",
                "recommended_duration": 1.8,
            },
            {
                "start": 30.0,
                "end": 32.0,
                "anchor_quote": "Then everything changed.",
                "emotion": "surprise",
                "sentiment": "positive",
                "tone_of_voice": "excited",
                "tone_intensity": 84,
                "impact_score": 92,
                "visualizability": 94,
                "broll_priority": 93,
                "best_for_broll": True,
                "visual_strategy": "sudden breakthrough and positive momentum",
                "search_queries": [
                    "startup breakthrough celebration",
                    "person reacting good news",
                ],
                "why_broll": "Clear narrative turn with visible emotional payoff.",
                "recommended_duration": 2.0,
            },
        ],
    }

    result = director.apply_to_plan(plan, analysis, 45.0)

    assert result["broll_selection_policy"] == "emotion-first"
    assert result["shots"][0]["dialogue_quote"] == "I almost gave up."
    assert result["shots"][0]["tone_of_voice"] == "quiet"
    assert result["shots"][0]["impact_score"] == 98
    assert result["shots"][0]["search_prompt"] == "person sitting alone reflection"
    assert result["shots"][1]["dialogue_quote"] == "Then everything changed."


def test_super_director_prompt_explicitly_requires_audio_tone():
    prompt = BrollSuperDirector._build_prompt(
        transcript_text="[0.00-2.00] I almost gave up.",
        video_duration=20.0,
        niche="podcast",
        style="clean_podcast",
        requested_shots=4,
    )

    assert "LISTEN TO THE ATTACHED AUDIO" in prompt
    assert "tone, vocal intensity, pauses" in prompt
    assert "exact impactful dialogue" in prompt
    assert "visualizability" in prompt


def test_super_director_prompt_rejects_vague_broll_and_requires_observable_actions():
    prompt = BrollSuperDirector._build_prompt(
        transcript_text="[0.00-3.00] I searched my name online and felt pathetic.",
        video_duration=20.0,
        niche="generic",
        style="clean_podcast",
        requested_shots=4,
    )

    assert "WHO is visible, WHAT are they physically doing, WHERE are they" in prompt
    assert "never invent negative drama" in prompt.lower()
