#!/usr/bin/env python3
"""Fetch selected instruments from MusyngKite (midi-js-soundfonts, FluidR3_GM
derived), extract a few notes each, convert to OGG, and emit a manifest snippet
with RMS-balanced gains. Outputs into samples/musyng/<inst>/<midi>.ogg."""
import base64, json, os, re, subprocess, sys, urllib.request

BASE = 'https://raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/MusyngKite/{}-mp3.js'
OUT = os.path.join(os.path.dirname(__file__), 'musyng')

# inst id -> list of note names to extract (stay in the chord voicing range ~C3..C5)
WANT = {
    'string_ensemble_1': ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'violin':            ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'french_horn':       ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'trumpet':           ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'trombone':          ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'acoustic_guitar_nylon': ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'acoustic_guitar_steel': ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
    'electric_guitar_clean': ['C3','E3','G3','C4','E4','G4','C5','B4','B3','D4'],
}

NOTE_RE = re.compile(r'^([A-G](?:#|b)?)(-?\d+)$')
PC = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def note_to_midi(n):
    m = NOTE_RE.match(n)
    p = PC[m.group(1)[0]] + (1 if '#' in m.group(1) else -1 if 'b' in m.group(1) else 0)
    return p + (int(m.group(2)) + 1) * 12

def rms_of(path):
    """RMS level via ffmpeg volumedetect parse (mean_volume dB)."""
    r = subprocess.run(['ffmpeg','-hide_banner','-i',path,'-af','volumedetect','-f','null','-'],
                       capture_output=True, text=True)
    m = re.search(r'mean_volume:\s*(-?[\d.]+) dB', r.stderr)
    return float(m.group(1)) if m else None

def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for inst, notes in WANT.items():
        url = BASE.format(inst)
        print(f'fetching {inst} ...', flush=True)
        src = urllib.request.urlopen(url).read().decode()
        m = re.search(r'MIDI\.Soundfont\.\w+\s*=\s*', src)
        start = src.index('{', m.end())
        blob = re.sub(r',\s*}', '}', src[start:src.rindex('}') + 1])
        data = json.loads(blob)
        d = os.path.join(OUT, inst)
        os.makedirs(d, exist_ok=True)
        got = {}
        for n in notes:
            if n not in data:
                print('  missing note', n); continue
            b64 = data[n].split('base64,', 1)[1]
            mp3 = os.path.join(d, n + '.mp3')
            ogg = os.path.join(d, str(note_to_midi(n)) + '.ogg')
            with open(mp3, 'wb') as f:
                f.write(base64.b64decode(b64))
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',mp3,'-q','4',ogg],
                           check=True)
            os.remove(mp3)
            got[str(note_to_midi(n))] = ogg
            print('  ', n, '->', ogg)
        # mean RMS across extracted notes
        dbs = [v for v in (rms_of(p) for p in got.values()) if v is not None]
        mean_db = sum(dbs) / len(dbs) if dbs else None
        report[inst] = {'mean_db': mean_db, 'n': len(got)}
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
