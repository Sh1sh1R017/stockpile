"""Retention Engine & Cuts-First Architecture.

Implements the professional Cuts-First timeline paradigm from video-db/Director
and Andrea13235/Retention:
1. Dead-air silence detection (>350ms in short-form, >1.0s in podcast).
2. Filler word detection ('um', 'uh', 'you know', 'literally', 'like', etc.).
3. False starts and stutter repetition detection.
4. Confidence-gated cut model:
   - >= 0.85: Auto-cut (clean silence, obvious filler with breath boundaries)
   - 0.50 - 0.85: Review-flagged (kept by default, flagged for human approval)
   - < 0.50: Preserved (protect natural speech cadence and emotional pauses)
5. Timebase remapping: maps original source media timebase to the post-cut timeline,
   ensuring all downstream layers (captions, B-roll, punch-ins, SFX, graphics) are
   firmly anchored to the tightened edit without straddling cuts.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("autopilot.retention")


class CutType(str, Enum):
    """Classification of cuts detected in audio/transcript."""
    DEAD_AIR = "dead_air"            # Silent pauses between spoken words
    FILLER_WORD = "filler_word"      # 'um', 'uh', 'like', 'you know'
    FALSE_START = "false_start"      # Repeated words or aborted sentence starts
    LOW_CONFIDENCE = "low_info"      # Murmurs or low-speech acoustic dips


class CutDecision(str, Enum):
    """Confidence-gated cut execution decision."""
    AUTO_CUT = "auto_cut"            # Confidence >= 0.85: Cut executed automatically
    REVIEW_FLAGGED = "review_flag"   # 0.50 <= Confidence < 0.85: Flagged for editor review
    PRESERVED = "preserved"          # Confidence < 0.50: Preserved in timeline


@dataclass
class CutCandidate:
    """A detected segment candidate for cutting."""
    cut_id: str
    start_time: float
    end_time: float
    duration: float
    cut_type: CutType
    confidence: float
    decision: CutDecision
    trigger_text: str = ""
    reason: str = ""
    word_indices: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cut_id": self.cut_id,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": round(self.duration, 3),
            "cut_type": self.cut_type.value,
            "confidence": round(self.confidence, 3),
            "decision": self.decision.value,
            "trigger_text": self.trigger_text,
            "reason": self.reason,
            "word_indices": self.word_indices,
        }


@dataclass
class RetentionProfile:
    """Configuration parameters for retention cut thresholds."""
    name: str = "short_form_high_retention"
    min_pause_duration: float = 0.35      # Seconds of dead air to trigger cut (>350ms)
    podcast_min_pause: float = 1.00       # Relaxed threshold for podcast/conversational
    breath_cushion: float = 0.06          # Seconds of audio cushion to keep cut sounding natural
    auto_cut_threshold: float = 0.85      # Confidence threshold for auto execution
    review_threshold: float = 0.50        # Confidence threshold for review flagging
    filler_words: List[str] = field(default_factory=lambda: [
        "um", "uh", "uhh", "umm", "er", "ah", "like", "you know", "sort of",
        "kind of", "literally", "basically", "actually", "i mean", "right",
    ])


class RetentionEngine:
    """Analyzes transcript word timings and audio gaps to plan cuts-first timeline."""

    def __init__(self, profile: Optional[RetentionProfile] = None):
        self.profile = profile or RetentionProfile()

    def analyze_and_detect_cuts(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float,
        is_podcast: bool = False,
    ) -> List[CutCandidate]:
        """Detect dead air, filler words, and repetitions across transcript words.
        
        Args:
            transcript_segments: Whisper-style segments with word-level timings.
            video_duration: Total duration of the clip in seconds.
            is_podcast: If True, uses more relaxed conversational pause tolerances.
            
        Returns:
            List of CutCandidate items sorted by start_time.
        """
        min_pause = self.profile.podcast_min_pause if is_podcast else self.profile.min_pause_duration
        cushion = self.profile.breath_cushion

        # Flatten word list across all segments
        all_words: List[Dict[str, Any]] = []
        for s_idx, seg in enumerate(transcript_segments):
            words = seg.get("words", [])
            if not words and seg.get("text"):
                # Approximate word timings if segment lacks explicit word timestamps
                st = seg.get("start", 0.0)
                et = seg.get("end", st + 1.0)
                tokens = seg.get("text", "").strip().split()
                if tokens:
                    tok_dur = max(0.1, (et - st) / len(tokens))
                    for w_idx, tok in enumerate(tokens):
                        all_words.append({
                            "word": tok,
                            "start": round(st + w_idx * tok_dur, 3),
                            "end": round(st + (w_idx + 1) * tok_dur, 3),
                            "seg_idx": s_idx,
                        })
            else:
                for w in words:
                    all_words.append({
                        "word": w.get("word", "").strip(),
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                        "seg_idx": s_idx,
                    })

        cuts: List[CutCandidate] = []
        cut_counter = 1

        # ------------------------------------------------------------------
        # 1. Opening Silence (before first word)
        # ------------------------------------------------------------------
        if all_words:
            first_word_start = all_words[0]["start"]
            if first_word_start > (min_pause + cushion):
                cut_start = 0.0
                cut_end = max(0.0, first_word_start - cushion)
                dur = cut_end - cut_start
                if dur >= min_pause:
                    cuts.append(CutCandidate(
                        cut_id=f"cut_{cut_counter:03d}",
                        start_time=cut_start,
                        end_time=cut_end,
                        duration=dur,
                        cut_type=CutType.DEAD_AIR,
                        confidence=0.95,
                        decision=CutDecision.AUTO_CUT,
                        trigger_text="[Opening Silence]",
                        reason="Eliminate pre-speech dead air to immediately engage viewer on frame 0.",
                    ))
                    cut_counter += 1

        # ------------------------------------------------------------------
        # 2. Inter-Word Dead Air & Filler Words
        # ------------------------------------------------------------------
        filler_set = {w.lower() for w in self.profile.filler_words}

        for i in range(len(all_words)):
            current = all_words[i]
            word_clean = re.sub(r"[^\w\s]", "", current["word"]).strip().lower()

            # A. Filler word detection
            if word_clean in filler_set:
                w_start = current["start"]
                w_end = current["end"]
                w_dur = w_end - w_start

                # Check if isolated filler or part of connected speech
                prev_end = all_words[i - 1]["end"] if i > 0 else 0.0
                next_start = all_words[i + 1]["start"] if i + 1 < len(all_words) else video_duration
                has_pre_pause = (w_start - prev_end) > 0.15
                has_post_pause = (next_start - w_end) > 0.15

                # High confidence if word has natural pauses around it
                if has_pre_pause or has_post_pause:
                    conf = 0.88
                    decision = CutDecision.AUTO_CUT
                else:
                    # In connected phrase (e.g., "I like apples"), do not accidentally cut verb "like"
                    if word_clean in {"like", "right", "actually"}:
                        conf = 0.45
                        decision = CutDecision.PRESERVED
                    else:
                        conf = 0.72
                        decision = CutDecision.REVIEW_FLAGGED

                if decision != CutDecision.PRESERVED:
                    cuts.append(CutCandidate(
                        cut_id=f"cut_{cut_counter:03d}",
                        start_time=round(w_start, 3),
                        end_time=round(w_end, 3),
                        duration=round(w_dur, 3),
                        cut_type=CutType.FILLER_WORD,
                        confidence=conf,
                        decision=decision,
                        trigger_text=current["word"],
                        reason=f"Remove verbal crutch / filler '{current['word']}' to tighten pacing.",
                        word_indices=[i],
                    ))
                    cut_counter += 1

            # B. False start / Stutter repetition (e.g. "We we", "The the")
            if i + 1 < len(all_words):
                next_word = all_words[i + 1]
                next_clean = re.sub(r"[^\w\s]", "", next_word["word"]).strip().lower()
                if word_clean and word_clean == next_clean and len(word_clean) > 1:
                    stut_dur = round(current["end"] - current["start"], 3)
                    cuts.append(CutCandidate(
                        cut_id=f"cut_{cut_counter:03d}",
                        start_time=current["start"],
                        end_time=current["end"],
                        duration=stut_dur,
                        cut_type=CutType.FALSE_START,
                        confidence=0.90,
                        decision=CutDecision.AUTO_CUT,
                        trigger_text=f"{current['word']} {next_word['word']}",
                        reason=f"Remove false start / duplicated word '{current['word']}'.",
                        word_indices=[i],
                    ))
                    cut_counter += 1

            # C. Dead Air silence between consecutive words
            if i + 1 < len(all_words):
                next_word = all_words[i + 1]
                gap = next_word["start"] - current["end"]

                if gap >= min_pause:
                    # Keep a natural breath cushion
                    silence_start = round(current["end"] + cushion, 3)
                    silence_end = round(next_word["start"] - cushion, 3)
                    silence_dur = round(silence_end - silence_start, 3)

                    if silence_dur >= 0.15:
                        # Dramatic pauses before punchlines get higher threshold
                        is_dramatic = False
                        if gap >= 1.5 and is_podcast:
                            is_dramatic = True

                        conf = 0.70 if is_dramatic else 0.92
                        decision = CutDecision.REVIEW_FLAGGED if is_dramatic else CutDecision.AUTO_CUT

                        cuts.append(CutCandidate(
                            cut_id=f"cut_{cut_counter:03d}",
                            start_time=silence_start,
                            end_time=silence_end,
                            duration=silence_dur,
                            cut_type=CutType.DEAD_AIR,
                            confidence=conf,
                            decision=decision,
                            trigger_text=f"{current['word']} ... {next_word['word']}",
                            reason=f"Cut {silence_dur}s dead air between '{current['word']}' and '{next_word['word']}'.",
                        ))
                        cut_counter += 1

        # ------------------------------------------------------------------
        # 3. Trailing Silence (after last word)
        # ------------------------------------------------------------------
        if all_words:
            last_word_end = all_words[-1]["end"]
            trailing_gap = video_duration - last_word_end
            if trailing_gap > (min_pause + cushion):
                cut_start = round(last_word_end + cushion, 3)
                cut_end = round(video_duration, 3)
                dur = round(cut_end - cut_start, 3)
                if dur >= 0.2:
                    cuts.append(CutCandidate(
                        cut_id=f"cut_{cut_counter:03d}",
                        start_time=cut_start,
                        end_time=cut_end,
                        duration=dur,
                        cut_type=CutType.DEAD_AIR,
                        confidence=0.96,
                        decision=CutDecision.AUTO_CUT,
                        trigger_text="[Trailing Silence]",
                        reason="Cut trailing dead air after last spoken sentence.",
                    ))

        # Sort and merge overlapping cut candidates
        cuts = self._merge_overlapping_cuts(cuts)
        return cuts

    def compute_keep_intervals(
        self,
        video_duration: float,
        cuts: List[CutCandidate],
        apply_review_flagged: bool = False,
    ) -> List[Tuple[float, float]]:
        """Calculate the remaining contiguous A-roll keep intervals [start, end].
        
        Args:
            video_duration: Duration of the uncut source media.
            cuts: Detected cut candidates.
            apply_review_flagged: If True, also cuts segments flagged for review.
                                  If False, cuts only AUTO_CUT segments.
        """
        active_cuts = [
            c for c in cuts
            if c.decision == CutDecision.AUTO_CUT or (apply_review_flagged and c.decision == CutDecision.REVIEW_FLAGGED)
        ]
        active_cuts.sort(key=lambda x: x.start_time)

        if not active_cuts:
            return [(0.0, round(video_duration, 3))]

        keep_intervals: List[Tuple[float, float]] = []
        current_pos = 0.0

        for c in active_cuts:
            if c.start_time > current_pos:
                keep_intervals.append((round(current_pos, 3), round(c.start_time, 3)))
            current_pos = max(current_pos, c.end_time)

        if current_pos < video_duration:
            keep_intervals.append((round(current_pos, 3), round(video_duration, 3)))

        # Filter out negligible intervals (< 0.10s)
        filtered = [(s, e) for s, e in keep_intervals if (e - s) >= 0.10]
        return filtered or [(0.0, round(video_duration, 3))]

    def remap_timestamp(
        self,
        timestamp: float,
        keep_intervals: List[Tuple[float, float]],
    ) -> float:
        """Map a timestamp from the uncut source timeline to the post-cut timeline."""
        post_cut_time = 0.0

        for start, end in keep_intervals:
            if timestamp < start:
                # Timestamp falls within a cut prior to this interval
                return round(post_cut_time, 3)
            elif start <= timestamp <= end:
                # Timestamp falls inside this kept interval
                return round(post_cut_time + (timestamp - start), 3)
            else:
                # Timestamp is past this interval
                post_cut_time += (end - start)

        return round(post_cut_time, 3)

    def unmap_timestamp(
        self,
        post_cut_time: float,
        keep_intervals: List[Tuple[float, float]],
    ) -> float:
        """Map a timestamp from the post-cut timeline back to the original source timeline."""
        accum = 0.0
        for start, end in keep_intervals:
            interval_dur = end - start
            if post_cut_time <= (accum + interval_dur):
                return round(start + (post_cut_time - accum), 3)
            accum += interval_dur

        return round(keep_intervals[-1][1], 3) if keep_intervals else post_cut_time

    def remap_transcript_segments(
        self,
        transcript_segments: List[Dict[str, Any]],
        keep_intervals: List[Tuple[float, float]],
    ) -> List[Dict[str, Any]]:
        """Remap all transcript segments and word timestamps onto the post-cut timeline."""
        remapped_segments = []

        for seg in transcript_segments:
            orig_st = seg.get("start", 0.0)
            orig_et = seg.get("end", 0.0)

            # Check if this segment overlaps any keep intervals
            remap_st = self.remap_timestamp(orig_st, keep_intervals)
            remap_et = self.remap_timestamp(orig_et, keep_intervals)

            if remap_et <= remap_st:
                continue

            # Remap words if present
            remapped_words = []
            for w in seg.get("words", []):
                w_st = float(w.get("start", 0.0))
                w_et = float(w.get("end", 0.0))
                new_w_st = self.remap_timestamp(w_st, keep_intervals)
                new_w_et = self.remap_timestamp(w_et, keep_intervals)
                if new_w_et > new_w_st:
                    remapped_words.append({
                        "word": w.get("word", ""),
                        "start": new_w_st,
                        "end": new_w_et,
                    })

            remapped_segments.append({
                "start": remap_st,
                "end": remap_et,
                "text": seg.get("text", "").strip(),
                "words": remapped_words,
            })

        return remapped_segments

    def _merge_overlapping_cuts(self, cuts: List[CutCandidate]) -> List[CutCandidate]:
        """Merge contiguous or overlapping cut candidates."""
        if not cuts:
            return []

        cuts.sort(key=lambda x: x.start_time)
        merged: List[CutCandidate] = [cuts[0]]

        for current in cuts[1:]:
            prev = merged[-1]
            if current.start_time <= prev.end_time:
                # Merge into previous cut
                new_end = max(prev.end_time, current.end_time)
                new_dur = round(new_end - prev.start_time, 3)
                prev.end_time = new_end
                prev.duration = new_dur
                prev.confidence = max(prev.confidence, current.confidence)
                if current.trigger_text and current.trigger_text not in prev.trigger_text:
                    prev.trigger_text = f"{prev.trigger_text} + {current.trigger_text}"
            else:
                merged.append(current)

        return merged


# Singleton instance for system-wide access
retention_engine = RetentionEngine()
