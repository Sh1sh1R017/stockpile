# GPT-6 REPO-WIDE STOCKPILE AUDIT — MASTER WORK ORDER

This appendix extends the B-roll source audit into a repository-wide engineering audit. Treat the supplied source dump plus the entire repository checkout as one system.

## OBJECTIVE
Find bugs, broken implementations, duplicate/obsolete systems, inconsistent contracts, unsafe assumptions, dead code, incorrect fallbacks, performance traps, hydration/runtime issues, and features that appear implemented in the UI but are incomplete or disconnected in the backend.

Do not blindly rewrite working features. First establish evidence, then make the smallest coherent fix.

## MANDATORY REPO-WIDE PASSES

### 1. Build / import integrity
- Run the project's actual Python test/import path.
- Run frontend typecheck/build/lint commands defined by package.json.
- Find broken imports, circular imports, missing optional dependencies, stale module paths, and code that only works in one working directory.
- Check Python/Node version assumptions against project configuration.

### 2. Duplicate implementations / merge leftovers
Search for:
- duplicate functions/classes with similar names
- old and new versions of the same engine
- parallel B-roll selectors/directors/renderers
- duplicate campaign registration
- duplicate API endpoints
- compatibility shims that are no longer needed
- dead feature flags
- stale branch/merge artifacts
- code paths that implement the same feature differently

When duplicates exist, identify the canonical implementation and explain which one should be removed or redirected.

### 3. Frontend runtime / React / Next.js
Audit every client component for:
- duplicate React keys
- hydration mismatches
- browser-only APIs during SSR
- Date.now()/Math.random()/locale-dependent rendering in initial markup
- unstable list ordering
- invalid HTML nesting
- effects that race or update after unmount
- stale closures
- excessive polling
- duplicated fetches
- state that can diverge from backend truth
- dynamic imports used incorrectly
- missing error/loading/empty states

Known observed issue to verify and fix:
`web/app/page.tsx` renders `{campaigns.map((c) => <option key={c.id}>...)}` and the running app has emitted duplicate-key warnings for `capcut_podcast_pro`. Trace the actual source of duplicate campaign records rather than merely changing the React key to an array index.

Known hydration warning from the running app included extension-injected attributes (`__processed_*`, `bis_register`) on `<body>`. Distinguish browser-extension noise from genuine application hydration defects and do not hide genuine mismatches with suppressHydrationWarning unless justified.

### 4. API / backend correctness
Audit FastAPI routes for:
- missing validation
- path traversal
- unsafe file paths
- unrestricted CORS
- incorrect authentication/authorization assumptions
- race conditions
- background task failures
- leaked file handles/processes
- subprocess shell injection
- unbounded uploads
- missing size/type checks
- swallowed exceptions
- inconsistent HTTP status codes
- duplicate endpoint behavior
- mutable global state
- stale DB state
- filesystem/DB synchronization bugs

Pay particular attention to upload, YouTube import, file streaming, B-roll swap, timeline editing, rendering, OpenReel sync, HDR, diffusion, Google Drive, and job queue endpoints.

### 5. Data model / persistence
Audit SQLite/database/job serialization for:
- schema drift
- fields written but never read
- fields read but not persisted
- incompatible old edit plans
- JSON shape inconsistencies
- partial writes
- concurrent job corruption
- missing transactions
- stale render flags
- revision counters that can go backwards
- OpenReel sync losing fields

### 6. Video pipeline / timeline invariants
Trace the full lifecycle:
input -> transcribe -> moments -> edit director -> B-roll -> memes -> captions -> SFX -> BGM -> timeline -> render -> output -> preview/download.

Check that every stage preserves:
- source duration
- approved intervals
- non-overlap rules
- A-roll fallback
- media bounds
- audio synchronization
- frame-rate assumptions
- aspect ratio
- output path
- render-stale state

No stage may silently mutate an approved editorial decision without recording why.

### 7. FFmpeg / rendering
Search all FFmpeg invocations for:
- unnecessary re-encoding
- accidental CPU encoding where NVENC is available
- repeated full-video renders
- temporary-file leaks
- incorrect pixel formats
- audio drift
- broken stream mapping
- missing `-shortest` where appropriate
- unsafe concat/filter assumptions
- accidental quality loss
- resolution changes
- filters that force expensive CPU paths
- commands that fail only on Windows
- commands that assume bash utilities

Do not optimize blindly. Preserve output correctness first, then identify safe quick-render paths.

### 8. GPU / performance
Audit:
- redundant model loads
- repeated subprocess startup
- sequential work that could safely be parallel
- unnecessary frame extraction
- repeated transcription/embedding calls
- missing caches
- huge intermediate files
- expensive operations performed for candidates that will later be rejected
- CPU/GPU copies
- VRAM spikes
- synchronous API calls inside hot paths

For the user's GTX 1050 Ti, identify safe optimizations that do not require changing quality-critical output defaults.

### 9. AI / retrieval quality
Audit:
- prompts that are too broad
- keyword-only fallbacks
- weak semantic thresholds
- score normalization mismatches
- duplicate retrieval
- hallucinated asset metadata
- candidates accepted without verification
- expensive vision/model calls performed unnecessarily
- inconsistent model configuration
- missing caching
- failures that silently downgrade to generic footage

B-roll must prioritize proposition-level visual support over generic topic similarity.

### 10. Captions / behind-subject / overlays
Audit the actual implementation, not UI labels:
- Is behind-subject truly implemented end-to-end?
- Are masks/detections applied to the final render?
- Do captions preserve word timing?
- Can overlay layers escape their intended bounds?
- Are styles consistent between preview and master render?
- Are settings persisted and reloaded correctly?

### 11. Meme engine
Audit:
- template registration
- duplicate keys
- fallback behavior
- caption injection
- SFX synchronization
- duration handling
- random/deterministic rendering
- asset existence
- failure recovery
- standalone vs shot-targeted meme behavior

Do not weaken the meme engine while fixing unrelated systems.

### 12. SFX / BGM / ducking
Audit:
- event-to-SFX mapping
- duplicate cues
- excessive cartoonish effects
- missing files
- gain normalization
- ducking sidechain behavior
- timing drift
- preview/master mismatch

Prefer subtle snap/whoosh/swipe/click/fade accents unless a deliberate meme/comedic cue is selected.

### 13. OpenReel / NLE / export
Audit serialization compatibility, schema versions, round trips, timing preservation, captions, overlays, cutaways, and whether an OpenReel edit can be reopened and rendered without losing data.

### 14. Security
Search for:
- hardcoded secrets
- tokens/API keys
- unsafe subprocess usage
- path traversal
- arbitrary URL fetching
- SSRF risks
- unrestricted CORS
- missing upload limits
- command injection
- unsafe deserialization
- exposed local filesystem paths
- debug endpoints accidentally exposed

Do not expose or reproduce secret values in the audit. Report only file/path and secret type.

### 15. Tests
Audit coverage and add tests for every confirmed high-risk defect. Prefer regression tests that reproduce the bug before fixing it.

Required categories:
- B-roll relevance
- B-roll duration
- timeline invariants
- campaign registry uniqueness
- API validation
- frontend build/typecheck
- hydration-sensitive rendering
- OpenReel round-trip
- render command construction
- fallback/error behavior

### 16. Dead / obsolete code
Find files/classes/functions that appear unused or superseded. Do not delete merely because they are not referenced by a simple search; verify dynamic imports, registry loading, CLI entry points, workflows, and plugin-style discovery first.

## KNOWN ISSUE TO INVESTIGATE FIRST

The running frontend has reported:
`Encountered two children with the same key, capcut_podcast_pro.`
The offending render is in `web/app/page.tsx` at the campaign `<option>` map.

The campaign backend uses `campaign_registry.list_campaigns()`, so trace registry construction and API serialization. Fix the duplicate data at its source. Do not mask it with `key={`${c.id}-${index}`}`.

## OUTPUT CONTRACT FOR GPT-6

Return a repository-wide engineering audit with:

1. EXECUTIVE SUMMARY
2. VERIFIED BUGS — only evidence-backed defects
3. HIGH-RISK BUGS — security/data-loss/render corruption
4. FUNCTIONAL BUGS
5. PERFORMANCE / RENDERING BOTTLENECKS
6. FRONTEND / HYDRATION ISSUES
7. B-ROLL QUALITY ISSUES
8. DUPLICATE / OBSOLETE IMPLEMENTATIONS
9. ARCHITECTURE / CONTRACT INCONSISTENCIES
10. TEST GAPS
11. SECURITY FINDINGS
12. EXACT FILE + FUNCTION LOCATIONS
13. PATCH PLAN ORDERED BY IMPACT
14. CONCRETE CODE DIFFS
15. REGRESSION TESTS
16. WHAT NOT TO CHANGE
17. POST-PATCH VERIFICATION CHECKLIST

For every finding use:
- Severity: P0/P1/P2/P3
- Confidence: confirmed / likely / needs runtime verification
- File
- Function/class
- Evidence
- Why it breaks
- Minimal fix
- Regression test
- Compatibility risk

## IMPORTANT EXECUTION RULE

GPT-6 is allowed to make changes only after identifying the exact current implementation. Do not replace working architecture with a generic rewrite. Preserve existing features and reconcile conflicting implementations into one canonical path.

The goal is not merely to produce an audit. The goal is to leave Stockpile in a state where the recommended fixes can be implemented safely in one focused engineering session.
