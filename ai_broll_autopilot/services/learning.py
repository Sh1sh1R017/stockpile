"""Feedback Learning and Emotional Memory Engine for B-Roll Autopilot.

Maintains persistent user preferences, emotional resonance rules, and metaphor
guidelines across video editing jobs. Injects learned feedback into the AI Director
and AI Scorer so the system continuously adapts to human-relatable storytelling.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ai_broll_autopilot.config import Config

logger = logging.getLogger("autopilot.learning")


class FeedbackLearningEngine:
    """Manages persistent emotional B-roll feedback and learning rules in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()
        self._seed_initial_rules()

    def _init_db(self):
        """Initialize the feedback and learning tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS broll_feedback_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                dialogue_pattern TEXT,
                preferred_metaphors TEXT NOT NULL,
                avoided_metaphors TEXT NOT NULL,
                preferred_queries TEXT,
                user_rating INTEGER DEFAULT 10,
                user_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS job_broll_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                shot_id TEXT NOT NULL,
                clip_title TEXT,
                emotional_score INTEGER,
                user_rating INTEGER,
                user_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _seed_initial_rules(self):
        """Seed foundational human-relatable storytelling rules and user mandates."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        count = c.execute("SELECT COUNT(*) FROM broll_feedback_learning").fetchone()[0]
        if count <= 3:
            logger.info("Seeding foundational emotional B-roll rules and user mandates...")
            # Clear old hardcoded rules if only initial 3 existed
            c.execute("DELETE FROM broll_feedback_learning WHERE id <= 3")
            initial_rules = [
                (
                    "focus / discipline / deep work",
                    r"focus|focused|discipline|hard work|concentrat|clipboard|lesson|routine|habit|practice|daily|impart",
                    json.dumps([
                        "intense person writing notes on clipboard at desk",
                        "focused professional deep in work on laptop",
                        "athlete tying running shoes training with determination",
                        "hands checking off items on planner checklist"
                    ]),
                    json.dumps([
                        "office worker getting fired",
                        "packing cardboard box",
                        "computer rage",
                        "empty abandoned dark office"
                    ]),
                    json.dumps([
                        "focused man writing desk",
                        "deep focus working laptop",
                        "businessman clipboard checklist",
                        "hands writing planner"
                    ]),
                    10,
                    "USER MANDATE: Visualizing focus, discipline, and daily habits must show deep, locked-in work, clipboard checklists, and athletic determination. Never use firing or cardboard boxes."
                ),
                (
                    "winning / victory / high achievement",
                    r"winner|winners|win|winning|success|succeed|achievement|goals|victory|champion|top|greatest",
                    json.dumps([
                        "runner crossing finish line with arms raised in victory",
                        "businessman celebrating success in bright office",
                        "teammates high-fiving and celebrating",
                        "modern stock market chart soaring upward green"
                    ]),
                    json.dumps([
                        "laid off employee",
                        "cardboard box",
                        "depressed office worker",
                        "empty office"
                    ]),
                    json.dumps([
                        "runner winning finish line",
                        "business celebration modern office",
                        "hands high five team",
                        "stock chart upward"
                    ]),
                    10,
                    "USER MANDATE: Visualizing winning and success must show triumphant achievement, finish line victory, high-fives, and celebration."
                ),
                (
                    "distraction / losing habits / procrastination",
                    r"loser|losers|distract|distraction|wasting time|procrastinat|unfocused|doomscroll",
                    json.dumps([
                        "person mindlessly scrolling smartphone on couch in dark room",
                        "distracted student zoning out looking at notifications",
                        "slouching gamer ignoring real life"
                    ]),
                    json.dumps([
                        "empty office cubicle",
                        "laid off worker",
                        "cardboard box"
                    ]),
                    json.dumps([
                        "person scrolling smartphone couch",
                        "distracted phone notifications",
                        "bored person scrolling phone"
                    ]),
                    10,
                    "USER MANDATE: Visualizing losers / lack of focus must show the real modern vice: endless smartphone doomscrolling, couch distraction, and notifications."
                ),
                (
                    "mentorship / father / family wisdom",
                    r"dad|father|mother|mentor|coach|lesson|advice|teach|impart|guidance",
                    json.dumps([
                        "father talking with son outdoors with warm wisdom",
                        "experienced mentor advising young professional",
                        "respectful handshake and guidance"
                    ]),
                    json.dumps([
                        "boss firing someone",
                        "angry shouting"
                    ]),
                    json.dumps([
                        "father teaching son",
                        "mentor advising student",
                        "handshake business agreement"
                    ]),
                    10,
                    "USER MANDATE: Lessons from fathers or mentors must show warm, respectful guidance, father-son advice, or mentor teaching."
                ),
                (
                    "corporate firing / layoffs",
                    r"fire you|laid off|terminate|cut employees|let people go|suffer some people",
                    json.dumps([
                        "person packing personal belongings into a brown cardboard box at office desk",
                        "employee carrying a cardboard box walking out through office glass doors",
                        "devastated employee packing desk photo frame and coffee mug",
                        "boss aggressively pointing to exit or slamming termination notice"
                    ]),
                    json.dumps([
                        "generic modern building exterior",
                        "industrial robotic factory assembly line",
                        "generic calm desk with monitor"
                    ]),
                    json.dumps([
                        "fired employee packing box",
                        "employee packing desk"
                    ]),
                    10,
                    "USER MANDATE: ONLY when someone is actually fired or laid off, show a person packing a cardboard box."
                ),
                (
                    "falling behind / sluggish / slow work",
                    r"slows people down|lagging behind|drowning|falling behind|frustrated",
                    json.dumps([
                        "frustrated office worker pulling hair at computer monitor",
                        "overwhelmed employee with head in hands at messy desk",
                        "exhausted worker staring at frozen loading screen"
                    ]),
                    json.dumps([
                        "calm productive office worker smiling",
                        "metronome or simple countdown timer"
                    ]),
                    json.dumps([
                        "Frustrated Office Worker",
                        "Angry Office Worker",
                        "stressed employee b roll"
                    ]),
                    10,
                    "USER MANDATE: Visualizing inefficiency must show real human emotion—frustration, head in hands."
                )
            ]
            c.executemany("""
                INSERT INTO broll_feedback_learning 
                (theme, dialogue_pattern, preferred_metaphors, avoided_metaphors, preferred_queries, user_rating, user_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, initial_rules)
            conn.commit()
        conn.close()

    def get_learned_instructions(self, transcript: str = "") -> str:
        """Format learned rules into directive prompt constraints filtered by transcript context."""
        import re
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        rows = c.execute("""
            SELECT theme, dialogue_pattern, preferred_metaphors, avoided_metaphors, user_feedback 
            FROM broll_feedback_learning 
            ORDER BY id ASC
        """).fetchall()
        conn.close()

        lines = [
            "CRITICAL LEARNED USER PREFERENCES & CONTEXTUAL STORYTELLING RULES (MANDATORY):",
            "1. CONTEXTUAL RELEVANCE IS SUPREME:",
            "   - The B-roll visuals MUST match the literal and thematic meaning of the spoken words.",
            "   - NEVER force unrelated negative tropes (like layoffs, firing, or cardboard boxes) onto positive or unrelated speech!",
            "   - Match each beat to its true topic: focus, victory, mentorship, discipline, coding, finance, etc."
        ]

        matching_themes = []
        transcript_lower = (transcript or "").lower()

        for theme, pattern, pref_json, avoid_json, feedback in rows:
            # If transcript is given and pattern exists, check if it matches
            if transcript_lower and pattern:
                try:
                    if not re.search(pattern, transcript_lower):
                        continue
                except Exception:
                    pass

            try:
                prefs = json.loads(pref_json)
                avoids = json.loads(avoid_json)
                rule_str = f"• APPLICABLE THEME: [{theme.upper()}]\n  - PREFERRED VISUALS: {', '.join(prefs[:3])}\n  - STRICTLY FORBIDDEN: {', '.join(avoids[:3])}"
                if feedback:
                    rule_str += f"\n  - USER RULE: \"{feedback}\""
                matching_themes.append(rule_str)
            except Exception:
                continue

        if matching_themes:
            lines.append("2. THEMATIC MATCHES DETECTED IN THIS CLIP:")
            lines.extend(matching_themes)

        lines.append("Every single B-roll shot MUST evaluate and visualize the true narrative context of the dialogue!")
        return "\n".join(lines)

    def record_job_feedback(
        self,
        job_id: str,
        shot_id: str,
        clip_title: str,
        emotional_score: int,
        user_rating: int,
        user_feedback: str,
        theme: Optional[str] = None,
        preferred_metaphor: Optional[str] = None,
        avoided_metaphor: Optional[str] = None
    ):
        """Record explicit user feedback for a specific shot and update learning database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO job_broll_feedback 
            (job_id, shot_id, clip_title, emotional_score, user_rating, user_feedback)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, shot_id, clip_title, emotional_score, user_rating, user_feedback))

        # If user gave specific guidelines or low rating, learn for next time
        if theme and preferred_metaphor:
            c.execute("""
                INSERT INTO broll_feedback_learning 
                (theme, preferred_metaphors, avoided_metaphors, user_rating, user_feedback)
                VALUES (?, ?, ?, ?, ?)
            """, (
                theme,
                json.dumps([preferred_metaphor]),
                json.dumps([avoided_metaphor or clip_title]),
                user_rating,
                user_feedback
            ))

        conn.commit()
        conn.close()
        logger.info(f"Recorded user feedback for [{shot_id}] in job {job_id} (Rating: {user_rating}/10)")

    def get_active_rules(self) -> List[Dict[str, Any]]:
        """Return list of active learning rules from SQLite."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        rows = c.execute("SELECT id, theme, preferred_metaphors, avoided_metaphors, user_feedback FROM broll_feedback_learning ORDER BY id ASC").fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "theme": r[1],
                "preferred": json.loads(r[2]) if r[2] else [],
                "avoided": json.loads(r[3]) if r[3] else [],
                "feedback": r[4],
            }
            for r in rows
        ]


# Singleton instance
feedback_engine = FeedbackLearningEngine()
