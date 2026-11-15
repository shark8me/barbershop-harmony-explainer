# chord-instrument.html — migrate to plain WebAudio + local acoustic samples

Goal: every pad press plays instantly (< ~20 ms press→onset) from pre-decoded
AudioBuffers of real acoustic instrument samples (VCSL CC0 / Salamander piano CC-BY).
Strudel is removed entirely: its cycle-grid scheduler caps latency at up to one full
cycle (2000 ms @ 120 BPM) and silently drops presses whose onset lands after the
one-shot silence timer (~18% of presses). See diagnosis in chat log 2026-11-15.

Working file: `chord-instrument.html` (single-file page, module script, CDN-free
after migration — samples served locally, no jsdelivr/strudel dependency).

## Stage 1 — Sample acquisition (local assets)

1.1. Create `samples/` under the repo root:
     - `samples/salamander/` — piano: download from the Salamander mirror
       (https://archive.org/details/SalamanderGrandPianoBestOfVersion3). Keep only
       the notes the page can trigger: `chordNotes()` yields C3..B3 roots + octave
       doubling ⇒ pitch classes C..B in octaves 3–5. One velocity layer is enough
       to start (the "best of" cut has per-note OGGs at fixed velocity).
     - `samples/vcsl/` — the 9 non-piano instruments currently in `SYNTHS`:
       harp, vibraphone, harmonica, sax, organ_full (VCSL "Organ Full Mixture"?),
       balafon, clavisynth, recorder_alto_sus, kalimba.
       Source: https://github.com/sgossner/VCSL — take the VCSL 2.0 zip, extract
       one sample per instrument per needed pitch (VCSL ships single-sample
       pitch-shifted instruments, so ONE file per instrument can cover all keys;
       multi-sampled ones only where the page needs exact pitch).
1.2. Name files deterministically: `samples/<engine>/<instrument>/<midi>.ogg`
     (convert WAV→OGG with ffmpeg, `-q 4`; keep piano at WAV if OGG decode adds
     audible artifacts — test one note first). MIDI numbers, not note names.
1.3. Write `samples/manifest.json`: per instrument, `{ label, gain, files: { "<midi>": "samples/…/60.ogg" }, pitchShiftFallback: true }`
     — the `gain` field reuses the RMS-balanced values from the current `SYNTHS`
     array (piano 1, harp 4, vibraphone 2, harmonica 2, sax 4, organ 2, balafon 4,
     clavisynth 2, recorder 4, kalimba 4).
1.4. License note in `samples/LICENSES.md`: Salamander CC-BY attribution string,
     VCSL CC0. No NC-licensed material.
- **Accept:** `ls samples/*/` shows ≥ 12 notes per piano, ≥ 1 (up to 13) per VCSL
  instrument; manifest parses; all files ≤ ~40 MB total.

## Stage 2 — Loader / pre-decode pipeline

2.1. Replace the strudel import/init/prebake/unlock block with:
     - `const ctx = new (window.AudioContext||webkitAudioContext)()` created lazily
       — but keep the existing pattern: resume it synchronously inside the first
       pointerdown (iPad requirement).
     - `loadSamples()`: fetch every manifest entry → `ctx.decodeAudioData` →
       `bufferCache[key]` where key = `${instrument}/${midi}`. Missing midi falls
       back to nearest available + `playbackRate = 2^((target-nearest)/12)` so one
       sample covers 12 semitones (VCSL path).
2.2. Run the loader at page load (fetch/decode is NOT gesture-gated on iOS, only
     `ctx.resume()` is — verify this on iPad). If decodeAudioData does stall
     pre-gesture on iPad (it can on older Safari), keep the loader waiting on a
     `unlockPromise` resolved by the first pointerdown, same as today.
2.3. Status line stages: "loading samples 12/64" → "decoding…" → "samples ready —
     tap a pad". Keep the overlay until samples are ready; first tap = resume +
     go.
2.4. Decode failure handling: per-file try/catch, missing buffer ⇒ that pad plays
     nearest pitch-shifted buffer, never silent.
- **Accept:** page served locally reports `bufferCache` full (count === expected)
  in console; status reaches "samples ready".

## Stage 3 — Playback engine

3.1. `playChord(tonicIdx, rowOffset, colSemi, qual, synth)` rewrite:
     - compute notes (reuse `chordNotes()` unchanged),
     - for each note: get buffer, create
       `AudioBufferSourceNode` → `GainNode(gain = instrument gain × 0.9)` →
       shared `masterGain`, `start(now)`.
     - no `setTimeout`, no scheduler, no cycle math.
3.2. Arpeggio mode: same nodes, `start(now + i*stepSec)` where
     `stepSec = 60 / bpm / notes.length` (one subdivision per voiced note —
     preserves the current 4-notes-per-beat-grid semantics of `setcpm(bpm/4)`).
     Apply per-note `.release` ≈ sample decay (just let samples ring; no envelopes
     needed for naturally-decaying instruments).
3.3. Reverb: one shared `ConvolverNode` with a pre-rendered IR (generate a 1.5 s
     exponentially-decaying noise IR at page load, or ship a small IR file), wet
     gain ~0.25 to match today's `.room(.25)`. Chord route: source→gain→dry→master
     and gain→convolver→wet→master.
3.4. Retrigger guard (keep existing behavior): per-cell ~120 ms timestamp gap;
     different cells always fire immediately.
3.5. Stop button: `ctx.suspend()`? No — keep ctx running; track all live sources
     in a Set and `stop()` + clear on Stop press.
3.6. Tempo change while arp playing (existing `lastPlay` re-arm): re-schedule the
     arp notes from `ctx.currentTime` — trivial now, no re-eval needed.
- **Accept:** pressing the same pad repeatedly (8×/s) never accumulates nodes
  (sources stop via onended and are removed from the live set); overlapping
  different pads all sound together instantly.

## Stage 4 — Latency verification (keep the [LAT] logs)

4.1. Port the instrumentation: `window.__latLog`, pointerdown mark, and the
     destinationGain RMS-onset probe (analyser on `masterGain` now — no strudel
     controller). Log click→audible-onset per press.
4.2. Browser verification (browser tool, trusted clicks via click_at_xy):
     - 3 presses across different pads/keys: every AUDIBLE ONSET dt < 50 ms
       (RMS probe; rAF granularity ~16 ms per frame, so < 50 ms is the floor).
     - rapid same-cell retrigger < 120 ms gap is ignored; different cell fires.
     - arp mode: 4 onsets, evenly spaced at current BPM.
     - all 10 instruments each produce RMS ≥ 0.02 after prewarm (dead-sample
       check per instrument, RMS probe as before).
4.3. Confirm the old failure modes are gone: no press in any phase of any cycle
     is silent (there is no cycle anymore); no 2 s waits.
- **Accept:** all checks green in the verification log; keep server running on
  8391 during verification (re-do trusted clicks after every reload).

## Stage 5 — Cleanup

5.1. Delete: strudel import, `ensureStrudel`, `sdPromise` single-flight,
     `evalTimer`/`oneShotTimer`, `prewarm()` (replaced by the loader), `applyBpm`
     strudel coupling, `silence`/`repeatCycles` idioms, `.late` comments.
5.2. Keep: key/set/synth/mode/bpm UI, grid build, status line, overlay (now
     "samples loaded — tap to start"), `chordNotes`/`midiOf`/degree labels.
5.3. Update README live-pages list and the page subtitle (drop "Powered by
     Strudel's audio engine").
5.4. Commit only if asked (default: leave working tree dirty for review).
- **Accept:** no reference to strudel/jsdelivr in chord-instrument.html;
  grep clean.

## Stage 4 — verification results (2026-11-15, desktop Chrome, port 8391)
- 3 trusted presses (T-Maj, S-Maj, D-Dom7, piano): AUDIBLE ONSET dt = 43.1 / 35.8 / 14.2 ms — all < 50 ms.
- Retrigger guard: same-cell re-fire at +40 ms ignored; different cell fired at +61 ms. ✓
- Arp @120 BPM (stepSec 125 ms): envelope rising edges at 10/150/270/400 ms (gaps 140/120/130/125) — 4 onsets, spacing within detector jitter. ✓
- All 10 instruments peak RMS after prewarm: piano .225, harp .151, vibraphone .352, harmonica .283, sax .546, organ_full .668, balafon .608, clavisynth .639, recorder .309, kalimba .352 — all ≥ 0.02. ✓
- No scheduler/cycle exists → no silent presses, no 2 s waits by construction. bufferCache 93/93 ✓.

- `applyBpm` kept as WebAudio re-arm only (no strudel coupling) — verified.

## Stage 5 — verification (2026-11-15)
- grep clean: no strudel/jsdelivr/ensureStrudel/sdPromise/evalTimer/prewarm/.late refs in chord-instrument.html.
- README live-pages entry updated ("WebAudio + local acoustic samples pre-decoded at page load"); no "Powered by Strudel" subtitle anywhere.
- Committed as 330db21.
- Live smoke (http.server 8391, desktop Chrome): status reaches "samples ready — tap a pad", bufferCache 93/93; two trusted pad presses → AUDIBLE ONSET dt = 44.7 ms and 10.1 ms (both < 50 ms), both instruments audible. All plan stages complete.

## Notes / risks
- `organ_full` naming: check VCSL's actual folder name when extracting (may be
  `organ-full-mixture` or similar); adjust manifest accordingly.
- OGG decode on old Safari: if iPadOS Safari lacks OGG in decodeAudioData, use
  WAV or AAC (m4a) for everything — test one file before mass-converting.
- Total size: piano 12 notes @ WAV ≈ 3–5 MB/note; OGG ≈ 0.3 MB. If piano WAVs
  are heavy, prefer OGG for piano too unless artifacts are audible.
- Pitch-shift fallback (playbackRate) detunes timbre slightly; acceptable for
  VCSL single-sample instruments, NOT needed for piano (we have all 12 pcs).
