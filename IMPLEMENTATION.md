# Barbershop Tag Explorer — Implementation Summary

A demo viewer for five real barbershop tags with MusicXML, original learning-track audio, animated keyboard visualization, roman-numeral analysis, and cadence identification.

**Deliverable:** `/home/kiran/src/music/barbershop-harmony-explainer/tag-viewer.html` (self-contained; serve the project dir over HTTP, e.g. `npx http-server -p 8291`)

## Data Source

Tags and audio come from barbershoptags.com (official `api.php` endpoint):

- Of 6,878 sheet-music tags in the catalog, **47 have true MusicXML** (`Notation type="xml"`); the rest are PDF or Finale `.musx`.
- MusicXML downloaded via `dbaction.php?action=DownloadFile&dbase=tags&id={ID}&fldname=Notation`; audio via `fldname=AllParts` (the full-mix learning track mp3).
- Full 47-tag corpus downloaded and analyzed with music21 (`/usr/bin/python3.10`); five tags with both XML and mp3 selected for the demo.

## The Five Demo Tags

| ID | Title | Key | Cadence (named) |
|----|-------|-----|-----------------|
| 1682 | My Heart Broke Last Night | G major | **"Two-Door Finish"** — backdoor sweeper: iv–iii–ii–V7–bVI–bVII7→I |
| 2296 | My Funny Valentine | B minor | **Backdoor into minor** (VII7→i) after a key-flip ending |
| 4833 | Too Darn Hot | G minor | **Chromatic climb** (ii°7 → #I°7 → i) |
| 3856 | Don't Make Toast | Ab major | **Bluesy plagal** ("glorified Amen", IV7→I) |
| 2501 | Lonesome Road | D | **Picardy slip** (#v°→I, purely chromatic approach) |

Unusual cadences were given descriptive names rather than forcing textbook categories (classic ii–V–I occurs in only 1 of 46 analyzed tags; dominant-7ths and borrowed minor-subdominant color chords dominate the corpus).

## Analysis Pipeline (Python + music21)

1. **Voice extraction** — the MusicXML files store 2 singers per staff as `stream.Voice` objects inside measures. Voices are collected per measure, sorted low→high by average pitch, then grouped by voice index across measures; piano-style staves (stacked chords) are split by note index from the bottom. The four resulting lines are assigned Bass/Bari/Lead/Tenor by average register.
2. **Chordification** — `score.chordify()`; segments shorter than 0.25 quarterLengths skipped. Each chord gets: measure number, offset/duration in quarter lengths, chord symbol (root + quality via interval-set classification), and a roman numeral.
3. **Key anchoring** — roman numerals are re-derived against a key chosen by scoring every candidate tonic (whose scale contains the final chord's root, restricted to common tag-ending roles: I, iii, iv, v, bVI, vi, bVII) by duration-weighted diatonic root coverage, with a bonus for ending on the tonic.
4. **Cadence detection** — examines the last ~4 chords: dominant presence (V7→I), borrowed subdominant (iv/bVI), backdoor (bVII7→I), plagal (IV→I), or non-tonic "hanger" endings.
5. **Timing** — mp3 duration (via mutagen) ÷ total quarter lengths = `sec_per_ql`, mapping beat position to audio time. The final chord/voice events are trimmed so nothing runs past the end of the mp3.

Output: `data/tags_all.json` (one object per tag: id, title, key, chords[], events{Bass,Bari,Lead,Tenor}, cadence{type,desc,measure}, mp3 timing) — **embedded directly into the HTML** as `TAGS_ALL` so the viewer needs no server-side data endpoints.

## The Viewer (single HTML file)

- **Dropdown** — 5 tags; switching swaps audio, score, chips, cadence box.
- **Animated SVG keyboard** (C2–F6) — driven by `requestAnimationFrame` against the mp3's `currentTime ÷ sec_per_ql`. Chord tones colored by function (root=red, third=blue, fifth=green, seventh=purple); each singer's current note outlined in voice color; Tenor/Lead/Bari/Bass panels show note names. Clicking any chord chip seeks the audio there.
- **Harmony timeline** — every chord as a chip: roman numeral + measure number; the cadence-final chord highlighted.
- **Cadence box** — type, measure number, and a description; unusual cadences carry invented names (see table above).
- **Sheet music** — OpenSheetMusicDisplay (OSMD) v2.2.1 UMD build rendering the original MusicXML in an SVG backend.

## Bugs Found and Fixed During Verification

1. **Animation frozen except on stop/start** — `voiceNoteAt` iterated `TAG.events[name]` without a guard; for 4 of 5 tags Lead/Tenor lists were absent (extractor bug), so `showAt` threw inside the rAF callback, killing the requestAnimationFrame chain after one frame. Fixed by (a) guarding missing voice data, (b) rebuilding all four voice lines for every tag from `stream.Voice` traversal, and (c) hardening `loop()` — try/catch around `showAt` with unconditional re-scheduling so no frame error can stop playback sync.
2. **`noteToMidi` couldn't parse double accidentals** (`Cb4`, `Fb4` in Don't Make Toast → `NaN` → undefined key lookups). Rewritten to accumulate accidentals arithmetically instead of a lookup table.
3. **OSMD import** — the `.mjs` module build doesn't exist on jsDelivr (404); switched to the v2.2.1 UMD script whose global is `window.opensheetmusicdisplay.OpenSheetMusicDisplay`.
4. **Final-chord overrun** — trailing padding in the XML could push the last chord past the mp3's end; durations are now clamped to audio length.

## Known Limitations

- 47-tag MusicXML corpus is small (~0.7% of the catalog); expanding coverage would require OMR (Audiveris) on the 125 Classic Tags PDFs.
- music21's chordify labels on quartal/barbershop sonorities are fussy (`#643`, `ø65b3`); figures are snapped to root+quality before display, which occasionally mislabels color chords.
- Voice→staff mapping is by register, not by notated part name, since the source files are inconsistent.
- Playback sync assumes constant tempo between audio time and beat position (learning tracks have pick-ups/intros that may offset the mapping slightly; chip seek adds a −0.15s pre-roll to compensate).

## Verification Performed

- Browser-driven: all 5 tags load with score SVG rendered, status "ready"; `showAt` sampled at 8 timestamps → distinct keyboard states; voice panels populate for all four voices on all tags; cadence boxes render with correct measure numbers.
- `window.__dbg` handle exposed (`audio`, `TAG`, `showAt`, `noteToMidi`) for console-driven testing.
- Full-corpus artifacts preserved in `~/.hermes/cache/scratch/bs-tags/` (xml_tags.json, analysis.json, ROMAN_NUMERALS.md, xml/, audio/).
