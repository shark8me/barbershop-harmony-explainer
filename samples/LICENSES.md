# Sample licenses

## `salamander/` — Salamander Grand Piano V3 (Ogg Vorbis release)
- Author: Alexander Holm (Yamaha C5, recorded by Alexander Holm)
- License: **CC-BY 3.0** (Creative Commons Attribution 3.0)
- Source: https://archive.org/details/SalamanderGrandPianoV3
- Attribution string to display alongside any public use:
  > Piano samples from "Salamander Grand Piano V3" by Alexander Holm
  > (https://archive.org/details/SalamanderGrandPianoV3), licensed CC-BY 3.0.
  > Modifications: notes extracted (velocity layer v10), renamed to MIDI numbers.

## `vcsl/` — Versilian Community Sample Library (VCSL)
- License: **CC0 1.0** (public domain, no attribution required)
- Source: https://github.com/sgossner/VCSL (master branch, 2026-11)
- Files taken (one OGG per note, C3–C5 range where sampled):
  - harp: Chordophones/Composite Chordophones/Concert Harp (KSHarp_*)
  - vibraphone: Idiophones/Struck Idiophones/Vibraphone, Hard Mallets (Vibes_hard_*)
  - harmonica: Aerophones/Free Aerophones/Harmonica-Hohner-Special20-C, Sustains/Normal
  - sax: Aerophones/Reed Aerophones/Tenor Saxophone, Non-Vibrato (BrettTenor_NV_*)
  - organ_full: Aerophones/Edge-blown Aerophones/Renaissance Organ/Full (RenOrgan_Full_Room_*)
  - balafon: Idiophones/Struck Idiophones/Balafon, Traditional Mallet (EthnicXylo_tradM_*)
  - clavisynth: Electrophones/TX81Z/Clavisynth
  - recorder_alto_sus: Aerophones/Edge-blown Aerophones/Baroque Alto Recorder/Sustain
  - kalimba: Idiophones/Plucked Idiophones/Kalimba, Kenya (Mbira6_Normal_MainSpirit_*)
- Modifications: WAV → OGG Vorbis (-q 4), renamed to MIDI numbers.

## `musyng/` — MusyngKite soundfont (midi-js-soundfonts)
- Source: https://github.com/gleitz/midi-js-soundfonts (gh-pages branch,
  MusyngKite), built from the FluidR3_GM soundfont.
- License: FluidR3_GM is released by Dean M. Harmon under the MIT license
  (see https://github.com/gleitz/midi-js-soundfonts#musyngkite).
- Instruments taken (10 notes each, C3–C5 range): string_ensemble_1, violin,
  french_horn, trumpet, trombone, acoustic_guitar_nylon,
  acoustic_guitar_steel, electric_guitar_clean.
- Modifications: base64 MP3 extracted from the data-URI JS bundles, trimmed to
  the requested notes, MP3 → OGG Vorbis (-q 4), renamed to MIDI numbers
  (see samples/build_musyng.py).

No NC-licensed material is used.
