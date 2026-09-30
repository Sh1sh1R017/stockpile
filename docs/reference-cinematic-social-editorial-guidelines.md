# Cinematic Social Editorial Reference Guideline

Stockpile reference style modeled from the supplied final edit:
**The SECRET to Power House of Cards - Winter Media** (18.6s, 544x960 reference).

## Visual composition
- Output stays 9:16 but uses a centered editorial card rather than filling the entire vertical canvas.
- The observed card is approximately 94.4% of canvas width and 57.4% of canvas height, centered vertically.
- Canvas outside the card is near-black (#050505).
- Card corners are strongly rounded (about 52px at 1080x1920).
- Source footage is center-cropped into the card. Do not stretch.
- Apply only restrained contrast/saturation shaping; preserve the source's cinematic character.

## Editorial rhythm
- First 0.8–1.3s should establish the speaker/hook before the first supporting visual.
- Cut on meaning, not on a mechanical timer: new idea, reveal, concrete noun, consequence, emotional change, or punchline.
- Typical B-roll duration: 0.8–2.2s.
- High-impact beats can use shorter 0.8–1.3s inserts.
- Cinematic establishing/archival shots can run to ~2.2s when the visual needs time to register.
- Keep continuous A-roll gaps below about 3.5s.
- Preserve breathing room between cutaways; do not cover complete thoughts with unrelated visuals.
- Hard cuts are the default. Decorative slides, glows, and constant transitions are not part of this style.

## B-roll selection
- B-roll is narrative punctuation, not filler.
- Prefer literal, specific visuals: locations, architecture, historical footage, screens, money/property, people performing the described action, objects, crowds, archival/documentary moments.
- Retrieval prompts should describe an observable shot in 4–8 words.
- micro_prompts must describe alternate searches for the same visual event.
- Avoid generic motivational footage, random business stock, unrelated sports, and emotion-only prompts.
- On sentences with multiple distinct visual beats, allow multiple short cutaways rather than one generic clip.

## Typography
- Large, elegant, sentence-aware captions.
- Usually 2–4 words visible at once.
- White/off-white primary text.
- Restrained pale-green emphasis for important words.
- Center or slightly-above-center placement; keep text inside the visual card safe area.
- Avoid giant all-caps meme caption treatment.
- Motion should be subtle word-pop / emphasis, not continuous kinetic chaos.

## Camera motion
- Punch-ins are selective, not constant.
- Default punch-in range: 1.02x–1.045x.
- Use only on high-impact dialogue, emotional emphasis, or a deliberate visual beat.
- Never zoom simply to create activity.

## Audio
- Dialogue stays dominant.
- Keep BGM low and ducked under speech.
- Use SFX only on major visual punctuation, reveal/punchline beats, or occasional card changes.
- Do not place a whoosh on every cut.

## Automatic QA targets
A cinematic_social_editorial plan should be rejected or repaired when:
- B-roll is generic or contradicts the spoken topic.
- B-roll is clustered early and leaves the back half visually static.
- A-roll is hidden for an entire thought without a strong reason.
- B-roll clips exceed the style duration ceiling without narrative justification.
- Captions become giant all-caps blocks or lose sentence context.
- Zooms appear on ordinary lines.
- SFX fires on every cut.
- The central card treatment is lost.

## Machine-readable style ID
Use: cinematic_social_editorial

This style is automatically selected for generic/podcast-oriented content unless an explicit niche/style overrides it.