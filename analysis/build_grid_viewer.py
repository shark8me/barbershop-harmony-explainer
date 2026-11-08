#!/usr/bin/env python3
"""Build grid-viewer.html: injects chord-phrase rows + n-gram data as embedded JSON."""
import csv, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- chord rows grouped by tag (dedup by position) ---
rows = list(csv.DictReader(open(ROOT / 'data/chords_phrased.csv')))
tags = {}
for r in rows:
    t = tags.setdefault(r['tag_id'], {'id': r['tag_id'], 'title': r['tag_title'] or r['tag_id'],
                                      'key': r['key'], 'tonic': r['tonic'], 'rows': []})
    t['rows'].append({k: r[k] for k in
                      ['roman', 'roman_norm', 'function_class', 'pos_from_start',
                       'lead_degree', 'lead_dur', 'phrase_end', 'resolution']})
for t in tags.values():
    seen, out = set(), []
    for r in sorted(t['rows'], key=lambda x: int(x['pos_from_start'])):
        if r['pos_from_start'] in seen:
            continue
        seen.add(r['pos_from_start'])
        out.append(r)
    t['rows'] = out
tag_list = sorted(tags.values(), key=lambda t: t['title'].lower())

# --- n-grams: one entry per occurrence (tag, start, end) ---
ng = list(csv.DictReader(open(ROOT / 'data/ngrams_phrased.csv')))
ngrams = {}
for g in ng:
    tid = g['tag_id']
    if not tid:
        continue
    start, end = g['pos_from_start'], g['pos_from_end']
    if not start or not end:
        continue
    ngrams.setdefault(tid, []).append({
        'seq': g['ngram_norm_sequence'],
        'romans': g['ngram_roman_sequence'],
        'lead': g['lead_degrees'],
        'fc': g['function_class_sequence'],
        'rank': int(g['rank']),
        'count': g['count'],
        'start': int(start), 'end': int(end),
        'res': g['resolution'],
    })
for v in ngrams.values():
    v.sort(key=lambda x: (x['rank'], x['start']))

DATA = {'tags': tag_list, 'ngrams': ngrams}
blob = json.dumps(DATA, separators=(',', ':'))

tpl = (ROOT / 'analysis/grid_viewer_template.html').read_text()
html = tpl.replace('__DATA__', blob)
assert '__DATA__' not in html
(ROOT / 'grid-viewer.html').write_text(html)
print('wrote grid-viewer.html', len(html), 'bytes;', len(tag_list), 'tags,', sum(len(v) for v in ngrams.values()), 'ngram occurrences')
