# Stockpile Architecture

Stockpile is designed as a unified AI video-production application with a provider-neutral product layer.

## Public product flow

User

↓

Stockpile Studio

↓

Media Ingestion

↓

Transcription & Media Intelligence

↓

AI Clip Generator

↓

AI Edit Director

↓

Canonical EditPlan

↓

Timeline Editor

↓

Render Engine

↓

Final Video

## Canonical editing model

The EditPlan is the source of truth.

The final rendered MP4 is a delivery artifact and must never become the editable timeline source.

### Editable layers

- A-Roll
- B-Roll
- Captions
- Text & Graphics
- Subject-aware layers
- Music
- Sound Effects
- Transitions
- Motion

## Provider boundary

Provider-specific implementations live behind internal service adapters.

Example:

```
Stockpile Clip Generation Service
        |
        +-- provider adapter

Stockpile Motion Service
        |
        +-- motion recipe adapter

Stockpile Timeline Service
        |
        +-- timeline adapter
```

The public API and UI expose Stockpile concepts rather than provider branding.

## Non-destructive editing

User actions modify the canonical EditPlan.

```
USER EDIT
    ↓
EDITPLAN
    ↓
SYNC
    ↓
EDITPLAN
    ↓
RENDER
```

Rendering does not regenerate editorial decisions.

Deleting a B-Roll clip removes that clip from the EditPlan. Rendering must not recreate it unless the user explicitly invokes an Auto Fill Gap operation.

## Long-form clipping

The AI Clip Generator accepts long-form sources and can combine provider-generated candidates with Stockpile's own transcript and editorial intelligence.

Candidate flow:

```
LONG VIDEO
    ↓
TRANSCRIPT
    ↓
CANDIDATE GENERATION
    ↓
QUALITY FILTERING
    ↓
OVERLAP / DUPLICATE REMOVAL
    ↓
RANKING
    ↓
SHORT-FORM PROJECT
```

## Caption motion

Caption Motion is represented in the EditPlan so the selected animation survives preview, synchronization, and final rendering.

## Subject-aware typography

When enabled, subject-aware typography follows:

```
BACKGROUND
    ↓
TEXT
    ↓
SUBJECT MATTE
    ↓
FOREGROUND SUBJECT
```

The system must retain safe fallbacks when segmentation is unavailable.

## Documentation

Third-party implementation details and licensing belong in `docs/THIRD_PARTY.md`, while this document describes Stockpile's own architectural model.
