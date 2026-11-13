#!/usr/bin/env python3
"""Lead-phrase-aware analysis of barbershop tag MusicXML corpus.

Re-parses all 47 tags: chordify -> key (written-key prior) -> roman numerals ->
lead line extraction -> per-chord lead degree/duration -> phrase-boundary detection.

Phrase anchor (lead phrase resolution point): a lead note whose scale degree
(relative to the tag's key) is 1, 4 or 5 AND that is followed by a rest (gap
>= 0.4 ql) or held for >= 2.0 ql. At each anchor the sounding chord is labeled
'resolved' (tonic-function chord) or 'tension' (subdominant/dominant/chromatic).

Writes:
  data/chord_phrase_rows.json   enriched per-chord rows (offsets, lead degrees, anchors)
  data/chords_phrased.csv       occurrence-level chord rows + phrase columns
  data/ngrams_phrased.csv       4-chord ngrams over normalized collapsed sequences,
                                with boundary/resolution metadata per occurrence
  data/phrase_resolution.csv    distribution of chord function at phrase anchors
"""
import json, re, csv, os, sys
from collections import Counter, defaultdict
from music21 import converter, stream, chord as m21chord, roman, key as m21key, pitch, note as m21note

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
sys.path.insert(0, os.path.expanduser('~/.hermes/skills/research/musicxml-corpus-analysis'))

PC_NAMES = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
ROMAN_SHARP = {0:'I',1:'bII',2:'II',3:'bIII',4:'III',5:'IV',6:'#IV',7:'V',8:'bVI',9:'VI',10:'bVII',11:'VII'}
ROMAN_FLAT  = {0:'I',1:'#I',2:'II',3:'III',4:'bIV',5:'IV',6:'bV',7:'V',8:'VI',9:'bVII',10:'VII',11:'#VII'}

def snap_figure(fig):
    m = re.match(r'^([b#]+)([IViv]+)(.*)$', fig)
    return m.groups() if m else (None, None, fig)

def chord_label(c, k):
    tonic_pc = k.tonic.pitchClass
    root_pc = c.root().pitchClass
    idx = (root_pc - tonic_pc) % 12
    base = (ROMAN_SHARP if k.mode == 'major' else ROMAN_FLAT)[idx]
    q = c.quality
    if q in ('minor', 'diminished'):
        base = re.sub(r'[IV]+', lambda m: m.group(0).lower(), base)
    if q == 'diminished':
        base += 'o'
    elif q == 'augmented':
        base += '+'
    if len(c.pitches) >= 4:
        base += '7'
    bass_pc = c.bass().pitchClass
    if bass_pc != root_pc:
        base += '/' + PC_NAMES[bass_pc]
    return base

def detect_key(s, final_chord, writkey=''):
    ch = s.chordify()
    chords = [c for c in ch.recurse().getElementsByClass(m21chord.Chord) if c.quarterLength >= 0.25]
    if not chords: return m21key.Key('C')
    total = sum(c.quarterLength for c in chords)
    final_root = final_chord.root().pitchClass
    writ_tonic, writ_mode = None, None
    m = re.match(r'(Major|Minor):([A-G][b#]?)', writkey or '')
    if m:
        writ_mode = 'major' if m.group(1) == 'Major' else 'minor'
        writ_tonic = pitch.Pitch(m.group(2)).pitchClass
    best, bestscore = None, -1
    for pc in range(12):
        for mode in ('major', 'minor'):
            k = m21key.Key(PC_NAMES[pc], mode)
            dia = set(int(p.pitchClass) for p in k.pitches)
            score = sum(c.quarterLength or 0.0 for c in chords
                        if c.root().pitchClass in dia) / total
            if final_root == pc: score += 0.15
            if writ_tonic is not None and pc == writ_tonic and mode == writ_mode:
                score += 0.30
            if score > bestscore:
                best, bestscore = k, score
    return best

def extract_lead(s):
    """One line per part (or per voice inside measures), dedupe doubled staves, sort by pitch."""
    lines = []
    for part in s.parts:
        measures = list(part.getElementsByClass(stream.Measure))
        has_voices = any(m.getElementsByClass(stream.Voice) for m in measures) if measures else False
        if has_voices:
            for vi in range(max(len(m.getElementsByClass(stream.Voice)) for m in measures)):
                line = []
                for m in measures:
                    vs = list(m.getElementsByClass(stream.Voice))
                    if vi < len(vs):
                        line += [n for n in vs[vi].flatten().notes if not isinstance(n, m21note.Rest)]
                if line: lines.append(line)
        else:
            line = [n for n in part.flatten().notes if not isinstance(n, m21note.Rest)]
            if line: lines.append(line)
    lines = [l for l in lines if l]
    def sig(l):
        return tuple(tuple(p.nameWithOctave for p in (n.pitches if isinstance(n, m21chord.Chord) else [n.pitch]))
                     for n in l)
    seen, uniq = set(), []
    for l in lines:
        s_ = sig(l)
        if s_ not in seen:
            seen.add(s_); uniq.append(l)
    lines = uniq
    lines.sort(key=lambda l: sum(p.midi for n in l for p in (n.pitches if isinstance(n, m21chord.Chord) else [n.pitch])) / len(l))
    return lines

DEG_MAP = {0: '1', 2: '2', 4: '3', 5: '4', 7: '5', 9: '6', 11: '7'}

def main():
    index = json.load(open(os.path.join(DATA, 'musicxml_index.json')))
    all_rows = []
    for tid in sorted(index, key=int):
        r = index[tid]
        title, writkey = r.get('Title', ''), r.get('WritKey', '')
        path = os.path.join(DATA, f'{tid}.xml')
        try:
            s = converter.parse(path)
        except Exception as e:
            print(f'FAIL {tid}: {e}'); continue
        ch = s.chordify()
        chords = [c for c in ch.recurse().getElementsByClass(m21chord.Chord) if c.quarterLength >= 0.25]
        if not chords:
            print(f'FAIL {tid}: no chords'); continue
        abs_chords = []
        for c in chords:
            try: off = c.getOffsetInHierarchy(s)
            except Exception: off = c.offset
            abs_chords.append((off, c))
        k = detect_key(s, abs_chords[-1][1], writkey)
        tonic, mode = k.tonic.pitchClass, k.mode

        lines = extract_lead(s)
        lead = None
        for part, line in zip(s.parts, lines):
            if (part.partName or '').lower() in ('lead', 'melody') and line:
                lead = line; break
        if lead is None:
            lead = lines[2] if len(lines) >= 4 else (lines[-2] if len(lines) >= 2 else lines[0] if lines else [])
        # lead events: (off, dur, [names], first pc)
        def pc_of(x): return x.pitchClass if hasattr(x, 'pitchClass') else x.pitch.pitchClass
        events = []
        for n in lead:
            ps = n.pitches if isinstance(n, m21chord.Chord) else [n.pitch]
            try: off = n.getOffsetInHierarchy(s)
            except Exception: off = n.offset
            events.append((off, n.quarterLength, [PC_NAMES[pc_of(p)] for p in ps], pc_of(ps[0])))
        events.sort()
        # phrase anchors: degree in {1,4,5} and (rest follows >= 0.4ql or held >= 2.0ql)
        anchor_offs = set()
        for i, (off, dur, names, pc) in enumerate(events):
            deg_pc = (pc - tonic) % 12
            if deg_pc not in (0, 5, 7):
                continue
            nxt = events[i+1][0] if i+1 < len(events) else off + dur
            gap = nxt - (off + dur)
            if gap >= 0.4 or dur >= 2.0:
                anchor_offs.add(round(off, 4))
        n_anchor = len(anchor_offs)

        def norm(rom):
            m = re.match(r'^([b#]*)([IViv]+)', rom)
            return m.group(1) + m.group(2) if m else rom
        def fclass(rom):
            b = norm(rom); fig = b.lstrip('b#').upper()
            if fig in ('I','VI','III'): return 'T'
            if fig in ('IV','II'): return 'S'
            if fig in ('V','VII'): return 'D'
            return 'X'

        total = len(abs_chords)
        for i, (t, c) in enumerate(abs_chords):
            lbl = chord_label(c, k)
            # active lead event at chord start
            act = None
            for (off, dur, names, pc) in events:
                if off <= t + 1e-6 < off + dur + 1e-6:
                    act = (off, dur, names, pc)
            deg = ''
            if act:
                deg_pc = (act[3] - tonic) % 12
                deg = DEG_MAP.get(deg_pc, 'b' + str(DEG_MAP.get((deg_pc+1) % 12, '?')))
            is_anchor = round(t, 4) in anchor_offs
            fc = fclass(lbl)
            all_rows.append({
                'tag_id': tid, 'title': title, 'writkey': writkey,
                'roman': lbl, 'roman_norm': norm(lbl), 'fclass': fc,
                'chord_index': i, 'pos_from_start': i+1, 'pos_from_end': total-i,
                't': float(t), 'tonic': PC_NAMES[tonic], 'key': f'{PC_NAMES[tonic]} {mode}',
                'lead': act[2][0] if act else '',
                'lead_degree': deg, 'lead_dur': float(act[1]) if act else 0.0,
                'phrase_end': is_anchor,
                'resolution': ('resolved' if fc == 'T' else ('tension-'+fc if fc != 'X' else 'tension-X')) if is_anchor else '',
            })
        print(f'OK {tid} chords={total} key={PC_NAMES[tonic]} {mode} anchors={n_anchor}')

    n_ok = len({r['tag_id'] for r in all_rows})
    print(f'{n_ok} tags parsed')
    json.dump(all_rows, open(os.path.join(DATA, 'chord_phrase_rows.json'), 'w'))

    # ---- chords_phrased.csv ----
    with open(os.path.join(DATA, 'chords_phrased.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['roman','roman_norm','function_class','count','tag_id','tag_title',
                    'pos_from_start','pos_from_end','tonic','key','lead',
                    'lead_degree','lead_dur','phrase_end','resolution'])
        cnt = Counter(r['roman'] for r in all_rows)
        by_c = defaultdict(list)
        for r in all_rows: by_c[r['roman']].append(r)
        for rank, (rom, n) in enumerate(cnt.most_common(), 1):
            for o in by_c[rom]:
                w.writerow([rom, o['roman_norm'], o['fclass'], n, o['tag_id'], o['title'],
                            o['pos_from_start'], o['pos_from_end'], o['tonic'], o['key'], o['lead'],
                            o['lead_degree'], o['lead_dur'], o['phrase_end'], o['resolution']])

    # ---- ngrams over collapsed (norm) sequences, with phrase metadata ----
    by_tag = defaultdict(list)
    for r in all_rows: by_tag[r['tag_id']].append(r)
    ngram_rows = []
    for tid, v in by_tag.items():
        collapsed, prev = [], None
        for r in v:
            if r['roman_norm'] != prev:
                collapsed.append(r); prev = r['roman_norm']
        n = len(collapsed)
        for i in range(n - 3):
            gram = collapsed[i:i+4]
            anchors = [j for j, g in enumerate(gram) if g['phrase_end']]
            res = gram[anchors[-1]]['resolution'] if anchors else ''
            ngram_rows.append({
                'ngram': ' | '.join(g['roman'] for g in gram),
                'fnorm': ' | '.join(g['roman_norm'] for g in gram),
                'fseq': '-'.join(g['fclass'] for g in gram),
                'tag_id': tid, 'tag_title': v[0]['title'],
                'pos_from_start': gram[0]['pos_from_start'],
                'pos_from_end': gram[-1]['pos_from_end'],
                'tonic': v[0]['tonic'], 'key': v[0]['key'],
                'lead_sequence': ' -> '.join(g['lead'] or '?' for g in gram),
                'lead_degrees': '-'.join(g['lead_degree'] or '?' for g in gram),
                'anchors_in_window': len(anchors),
                'anchor_slots': ','.join(str(j+1) for j in anchors) or 'none',
                'resolution': res,
            })
    cnt = Counter(nr['fnorm'] for nr in ngram_rows)
    by_g = defaultdict(list)
    for nr in ngram_rows: by_g[nr['fnorm']].append(nr)
    tot = len(ngram_rows)
    with open(os.path.join(DATA, 'ngrams_phrased.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rank','ngram_norm_sequence','ngram_roman_sequence','function_class_sequence',
                    'count','frequency_pct','anchors_in_window','anchor_slots','resolution',
                    'occurrences','tag_id','tag_title','pos_from_start','pos_from_end',
                    'tonic','key','lead_sequence','lead_degrees'])
        for rank, (gram, n) in enumerate(cnt.most_common(), 1):
            for o in by_g[gram]:
                w.writerow([rank, gram, o['ngram'], o['fseq'], n, f'{100*n/tot:.2f}',
                            o['anchors_in_window'], o['anchor_slots'], o['resolution'],
                            f"{o['tag_id']} ({o['tag_title']})@{o['pos_from_start']}|{o['pos_from_end']}",
                            o['tag_id'], o['tag_title'], o['pos_from_start'], o['pos_from_end'],
                            o['tonic'], o['key'], o['lead_sequence'], o['lead_degrees']])

    # ---- phrase resolution distribution ----
    anchors = [r for r in all_rows if r['phrase_end']]
    rc = Counter((r['resolution'], r['lead_degree']) for r in anchors)
    with open(os.path.join(DATA, 'phrase_resolution.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rank','resolution','lead_degree','count','frequency_pct_of_anchors'])
        ta = len(anchors)
        for rank, ((res, deg), n) in enumerate(rc.most_common(), 1):
            w.writerow([rank, res, deg, n, f'{100*n/ta:.2f}'])
    print(f'anchors: {ta} over {n_ok} tags; chords_phrased rows={len(all_rows)}; ngram windows={tot}')

if __name__ == '__main__':
    main()
