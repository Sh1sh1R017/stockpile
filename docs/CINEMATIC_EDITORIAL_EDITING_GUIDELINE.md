# Cinematic Editorial Short — Reference-Derived Editing Guideline

This guideline encodes the visual grammar observed in the user-provided final edit
for the "House of Cards" example. It is a reusable Stockpile editing profile, not
a copy of any source asset.

## 1. Canvas and framing

- Output canvas: 1080x1920 (9:16).
- Preserve the natural source aspect ratio rather than forcing the speaker into a
  full-height crop.
- Keep the main video centered inside a landscape-oriented card with black negative
  space above and below.
- Use a restrained rounded-corner treatment on the card.
- B-roll should inherit the same card bounds so the layout does not jump between
  A-roll and B-roll.
- Avoid decorative frames unless the story itself calls for one.

## 2. Caption grammar

- Captions are not traditional bottom subtitles.
- Use phrase-level beats of about 2-4 words.
- Let the caption update when the semantic idea changes, a reveal lands, or a
  high-value word is spoken.
- Use white as the default text color.
- Emphasize only the strongest word or phrase with a warm yellow or cool accent.
- Keep typography large enough to read on mobile but restrained enough that it does
  not cover the speaker's expression.
- Default placement is center or center-lower inside the card; move toward upper
  center only when the composition calls for it.
- Use behind-subject typography only for deliberate hero words/phrases.

## 3. Visual storytelling

- Direct the edit around meaning, not a checklist of effects.
- A-roll should establish the statement; contextual B-roll should visually prove,
  extend, contrast, or dramatize the idea; then return to A-roll or move to a
  stronger visual payoff.
- Prefer literal or strongly grounded visuals: people, locations, objects,
  documents, screens, architecture, public events, archival footage, film/TV
  references, reactions, and visible actions.
- Avoid generic office shots, smiling-business footage, or random "emotional"
  stock when a more specific visual exists.
- Abstract dialogue should become an observable visual situation.
- One dominant visual idea per B-roll shot.

## 4. B-roll pacing

- Default B-roll duration: about 1.2-3.2 seconds.
- Use fewer stronger inserts rather than continuous random cutaways.
- Aim for roughly 45-60% contextual visual coverage depending on story density.
- Hard cuts are the default transition.
- Place cuts on phrase starts, reveals, concrete nouns/actions, consequences,
  reactions, or narrative turns.
- A strong archival/payoff shot may hold for 3-5 seconds when the story benefits
  from the hold.
- Do not force a B-roll cut merely because several seconds have passed.

## 5. Camera movement

- Use restrained punch-ins, generally around 1.04x-1.08x.
- Apply zooms only to genuine emphasis or emotional escalation.
- Avoid constant digital zoom, aggressive face tracking, and stacked motion effects.
- Let the cut and typography carry most of the energy.

## 6. Sound design

- Dialogue remains dominant.
- BGM is ducked under speech.
- SFX should reinforce important edits, caption impacts, reveals, or archival
  transitions.
- Avoid a whoosh on every cut.
- Quiet moments can stay quiet.

## 7. Narrative pacing by phase

### Opening
Start with A-roll long enough to establish the speaker and hook. Introduce the
first strong contextual visual quickly, but do not front-load the entire montage.

### Development
Alternate A-roll and specific contextual visuals. Use typography to clarify the
most important idea rather than repeating the whole sentence visually.

### Payoff
Let the most meaningful visual or archival beat breathe. A final visual can hold
longer with simpler captions when the story has reached its conclusion.

## 8. Editorial anti-patterns

Do not use:
- generic corporate stock for abstract business phrases
- unrelated sports or streamer reaction clips
- giant captions on every word
- constant zooming
- excessive transition packs
- B-roll with no dialogue relationship
- random meme inserts unless the spoken story actually calls for them

## Stockpile implementation

Profile ID: `cinematic_editorial`

Production routing:
- default campaign uses this profile
- OpenReel export uses a contained rounded landscape card
- captions use `editorial_story`
- B-roll Super Director receives the editorial/archival grammar
- A-roll, B-roll, captions, text, and SFX remain editable in OpenReel
