# Stockpile

AI-powered video editing and short-form production.

Stockpile turns long-form footage into editable short-form projects with AI-assisted clip discovery, contextual B-roll, animated captions, subject-aware typography, audio layers, and a non-destructive timeline.

## Features

- AI Clip Generator for long-form video
- Smart B-Roll with contextual matching
- Smart Captions with word-level timing
- Caption Motion presets
- Subject-Aware Typography
- Editable multitrack Timeline Editor
- Music and Sound Effects
- Deterministic rendering
- Google Drive workflows

## Caption Motion

Word Pop, Bounce, Typewriter, True Focus, Text Scramble, Slide Up, Karaoke, Reveal, Impact, and Subtle Fade.

## Non-destructive editing

The EditPlan is the canonical source of truth. The raw source remains editable and B-Roll stays on independent timeline tracks. The final rendered MP4 is a delivery artifact, never the editable source.

Deleting a B-Roll clip changes the EditPlan. Rendering consumes the current EditPlan and does not regenerate deleted editorial decisions.

## Architecture

```
LONG VIDEO
  ↓
INGEST
  ↓
TRANSCRIPT + MEDIA INTELLIGENCE
  ↓
AI CLIP GENERATOR
  ↓
AI EDIT DIRECTOR
  ↓
CANONICAL EDITPLAN
  ↓
TIMELINE EDITOR
  ↓
USER EDITS
  ↓
UPDATED EDITPLAN
  ↓
RENDER
  ↓
FINAL VIDEO
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Product Branding](docs/PRODUCT_BRANDING.md)
- [Third-Party Software & Credits](docs/THIRD_PARTY.md)

## Open-source credits

Stockpile uses and integrates with selected open-source projects. Relevant repositories, attribution, and licensing references are documented in [Third-Party Software & Credits](docs/THIRD_PARTY.md).

## Development principles

- EditPlan is canonical.
- User edits are non-destructive.
- Deleted clips are never silently recreated.
- Provider-specific implementations stay behind adapters.
- Customer-facing UI uses Stockpile terminology.
- Third-party software is credited accurately.
