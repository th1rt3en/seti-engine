"""Build the card definitions re-check page for the cards the owner marked with a difference.

Usage: python build_card_defs_page.py <card-definitions.json> <art-meta.json> <urls.json> <out.html>
urls.json maps sheet file names (sheet-cards-1.webp ...) to the stored asset url of the page's artifact.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'board'))
import check_page as cp  # noqa: E402

defs = json.load(open(sys.argv[1], encoding='utf-8'))
meta = json.load(open(sys.argv[2], encoding='utf-8'))['sheets']
urls = json.load(open(sys.argv[3], encoding='utf-8')) if os.path.exists(sys.argv[3]) else {}
GRID = {'sheet-cards-1.webp': (7, 10), 'sheet-cards-2.webp': (7, 10), 'sheet-alien-exertians.webp': (3, 5), 'sheet-alien-anomalies.webp': (2, 5), 'sheet-alien-centaurians.webp': (2, 5),
        'sheet-alien-mascamites.webp': (2, 5), 'sheet-alien-oumuamua.webp': (2, 5)}


def sheet_of(src):
    m = re.search(r'/cards/(cards-\d)\.webp$', src)
    if m: return 'sheet-' + m.group(1) + '.webp'
    m = re.search(r'/aliens/([a-z]+)\.webp$', src)
    return 'sheet-alien-' + m.group(1) + '.webp' if m else None


def crop(c, width=380):
    if not c.get('pos'): return ''
    sh = sheet_of(c['pos'][0])
    if not sh or sh not in GRID: return ''
    rows, cols = GRID[sh]
    r, k = c['pos'][1], c['pos'][2]
    m = meta[sh]
    cw, ch = m['w'] / cols, m['h'] / rows
    x = k / (cols - 1) * 100 if cols > 1 else 0
    y = r / (rows - 1) * 100 if rows > 1 else 0
    return '<div class="cardimg" role="img" aria-label="%s" style="width:%dpx;max-width:100%%;aspect-ratio:%.4f;background-image:url(%s);background-size:%d%% %d%%;background-position:%.2f%% %.2f%%;background-repeat:no-repeat;border-radius:8px;border:1px solid var(--line);flex:0 0 auto"></div>' % (cp.esc(c['name']), width, cw / ch, urls.get(sh, ''), cols * 100, rows * 100, x, y)


def danger(c):
    for a in c['owner_additions']:
        m = re.search(r'danger (\d+), endgame scoring: (.*?) -> (\d+) score', a['text'])
        if m: return int(m.group(1)), m.group(2), int(m.group(3))
    return None


def item(c):
    d = danger(c)
    head = '<dl class="kv"><dt>Cost</dt><dd>%s %s</dd><dt>Income</dt><dd>%s</dd><dt>Sector</dt><dd>%s</dd><dt>Free action</dt><dd>%s</dd></dl>' % (
        cp.esc(c['cost'] or '-'), cp.esc(c['cost_type'] or ''), cp.esc(c['income'] or '-'), cp.esc(c['sector'] or '-'), cp.esc(c['free_action'] or '-'))
    effs = ''.join('<li>%s</li>' % cp.esc(e) for e in c['repo_effects']) or '<li class="cap">the repo has no effect data for this card</li>'
    body = head + '<h3 style="margin-top:12px">Full effect as the repo stores it, read in words</h3><ul class="rwdiff" style="color:var(--ink)">%s</ul>' % effs
    if d:
        body += '<h3 style="margin-top:12px">From your note (the repo has nothing for this)</h3><dl class="kv"><dt>Danger</dt><dd>%d</dd><dt>Condition at the end of the game</dt><dd>%s</dd><dt>Points if met</dt><dd>%d VP</dd></dl>' % (d[0], cp.esc(d[1]), d[2])
    else:
        body += '<h3 style="margin-top:12px">Your note</h3><p style="margin:0">%s</p><p class="cap">Result of comparing it with the repo: %s</p>' % (
            cp.esc(c['owner_note'].replace('\n', ' / ')), 'the repo already stores everything the note lists.' if all(a['kind'] == 'dup' for a in c['owner_additions']) else 'check the lines the repo does not seem to contain.')
    img = crop(c)
    html = '<div class="row">%s<div class="read" style="flex:1 1 360px">%s</div></div>' % (img, body)
    return {'key': '%s-%s' % ('b' if c['group'] == 'base' else 'a', c['id'].replace(' ', '_')), 'title': '%s  %s' % (c['id'], c['name']) + ('  [danger %d]' % d[0] if d else ''), 'html': html}


diff = [c for c in defs if c['owner_note']]
base = [c for c in diff if c['group'] == 'base']
alien = [c for c in diff if c['group'] == 'alien-base' and not danger(c)]
exer = [c for c in diff if danger(c)]
secs = [{'title': 'What this page is', 'intro': 'My tracker did not show the effects of these 81 cards, because my extraction missed them. You wrote what the cards print, and the notes were useful, but the repo had most of those effects all along. Below, each card shows the full effect as the repo stores it, in words, next to the card image. Please check that the card and the text agree, then mark the card. For the 15 Exertian cards the repo has no danger or end-of-game rule, so your note is the only source.', 'images': [],
         'items': [{'key': 'summary', 'title': 'Summary of the comparison', 'html': '<ul class="rwdiff" style="color:var(--ink)"><li>81 cards had a note from you.</li><li>For 66 of them the repo already stores every effect you listed.</li><li>For the 15 Exertian cards ET.41 to ET.55 the repo has no danger value and no end-game scoring rule.</li></ul>'}]},
        {'title': 'Base deck cards with a note (%d)' % len(base), 'intro': '', 'images': [], 'items': [item(c) for c in base]},
        {'title': 'Alien cards with a note (%d)' % len(alien), 'intro': '', 'images': [], 'items': [item(c) for c in alien]},
        {'title': 'Exertian danger cards (%d): your notes become the rule' % len(exer), 'intro': 'Danger is hidden until the end of the game (ALIEN-EXE-06). The end-of-game condition is the line printed on the card; if it is met the player gains the points shown.', 'images': [], 'items': [item(c) for c in exer]}]
html = cp.build('SETI Card Definitions Check', 'SETI card definitions check', 'The 81 cards you marked with a difference, re-read with the repo\'s full effects in words.', 'card-defs-check', secs, urls)
open(sys.argv[4], 'w', encoding='utf-8').write(html)
print(len(diff), 'cards;', len(base), 'base,', len(alien), 'alien,', len(exer), 'exertian;', len(html), 'bytes')
