import unittest

from ai_broll_autopilot.services.meme_reaction_engine import MemeReactionEngine


class MemeReactionEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = MemeReactionEngine(cache_dir="/tmp/stockpile-reactions-test")

    def test_money_word_gets_reaction(self):
        events = self.engine.build_events([
            {
                "word": "$10M",
                "start": 2.0,
                "end": 2.4,
                "importance": 0.95,
                "semantic_type": "money",
                "sentence": "He made $10M from this",
            }
        ])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reaction_type"], "celebration")
        self.assertLessEqual(events[0]["duration"], 1.25)

    def test_chaotic_words_are_reaction_candidates(self):
        events = self.engine.build_events([
            {
                "word": "INSANE",
                "start": 5.0,
                "end": 5.3,
                "importance": 0.9,
                "semantic_type": "strong",
            }
        ])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reaction_type"], "chaos")

    def test_normal_words_do_not_create_meme_spam(self):
        events = self.engine.build_events([
            {
                "word": "the",
                "start": 1.0,
                "end": 1.2,
                "importance": 0.2,
                "semantic_type": "normal",
            }
        ])
        self.assertEqual(events, [])

    def test_reactions_are_rate_limited(self):
        events = self.engine.build_events([
            {"word": "NEVER", "start": 1.0, "end": 1.2, "importance": 0.9, "semantic_type": "negation"},
            {"word": "INSANE", "start": 1.5, "end": 1.8, "importance": 0.95, "semantic_type": "strong"},
            {"word": "STOP", "start": 3.5, "end": 3.7, "importance": 0.9, "semantic_type": "negation"},
        ])
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
