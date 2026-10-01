# Stockpile Editorial Policy

## Relevance-first B-roll

Stockpile treats B-roll relevance as the objective. **B-roll coverage percentage is descriptive telemetry, not a quota.**

A planner, timeline audit, quality gate, or renderer must not:
- insert B-roll merely to fill an empty interval;
- shift an approved B-roll interval merely to improve coverage;
- extend an approved B-roll interval to hit a coverage percentage;
- prefer a weak visual because a campaign has a target coverage ratio.

An approved cutaway may be dropped only when it violates a hard timeline, media-eligibility, safety, or rendering invariant. Dropping a cutaway does not authorize a replacement unless a new editorial decision is made upstream.

Coverage fields such as `broll_coverage_seconds` and `broll_coverage_percentage` remain useful for diagnostics and analytics, but they must never be used as acceptance criteria.

## Opening-face protection

Unless an explicit campaign contract says otherwise, A-roll remains unobscured for the first **1.2 seconds**. A B-roll interval beginning before 1.2 seconds is a blocking quality violation and must be replanned upstream; the quality gate must not silently retime it.

## Approved interval ownership

B-roll timing is owned by the editorial decision that approves the shot. Downstream pacing, QA, rendering, and export stages may validate an interval or reject it, but they may not lengthen it.

Any future feature that intentionally changes an approved interval must create a new editorial revision and record the reason.
