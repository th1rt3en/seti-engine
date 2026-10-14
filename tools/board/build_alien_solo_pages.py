"""Build the alien species check page and the solo/scoring check page.

Usage: python build_alien_solo_pages.py <urls.json> <out-aliens.html> <out-solo.html>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_page as cp  # noqa: E402
import solo_scoring_data as sd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, '..', '..', 'docs', 'spec', 'data')
urls = json.load(open(sys.argv[1], encoding='utf-8')) if os.path.exists(sys.argv[1]) else {}
alien = json.load(open(os.path.join(SPEC, 'alien-boards.json'), encoding='utf-8'))

COLORS = {'pink': 'pink (scanning trace)', 'yellow': 'yellow (landing trace)', 'blue': 'blue (analyzing trace)'}


def space_cell(sp, tier_danger=None):
    h = cp.pills(sp['rewards']) if sp['rewards'] else ''
    if sp.get('cost'):
        h += cp.pills(sp['cost'], cost=True)
    tags = []
    if sp.get('repeat'): tags.append('top capsule: any number of times')
    if sp.get('tier'): tags.append('tier %d, danger %d per marker' % (sp['tier'], tier_danger[str(sp['tier'])]))
    if sp.get('note'): tags.append(sp['note'])
    if tags: h += '<span class="cap">%s</span>' % cp.esc('; '.join(tags))
    return h


def columns_table(s):
    n = max(len(c['spaces']) for c in s['columns'])
    rows = []
    for i in range(n):
        row = ['<b>%d</b>' % (i + 1)]
        for c in s['columns']:
            row.append(space_cell(c['spaces'][i], s.get('tier_danger')) if i < len(c['spaces']) else '')
        rows.append(row)
    return cp.table(['Row from the top'] + [COLORS[c['color']] for c in s['columns']], rows)


def alien_page():
    secs = []
    secs.append({'title': 'How the species boards work', 'intro': 'Three colored columns per species. When a player gains a life trace they mark ANY empty space of the matching color (rulebook p.20), so the order of the spaces is a position, not a fill order. Position matters for Anomalies (the highest marked space in a column wins an anomaly) and for the Exertian tiers (danger per marker). The three discovery spaces and the overflow spaces (3 VP each) are on the planetary board, not on these boards.',
                 'images': [], 'items': [
                     {'key': 'rule-any-space', 'title': 'Mark any empty space of the trace color', 'html': '<p style="margin:0">A player who gains a pink, yellow or blue life trace marks any empty space of that color on a discovered species board and gains its reward. A wild trace may use any color. Overflow spaces (on the planetary board) are always allowed (LIFE-01 to LIFE-04).</p>'},
                     {'key': 'rule-cost', 'title': 'Spaces with a cost and the top capsule', 'html': '<p style="margin:0">A space with a cost (red cross) can only be marked by a player who pays it: Centaurians cost data from the pool, \'Oumuamua costs exofossils. A top capsule can be marked any number of times by any player, paying its cost each time (the Anomalies top capsule has no cost).</p>'}]})
    names = {'anomalies': 'Anomalies', 'centaurians': 'Centaurians', 'exertians': 'Exertians', 'mascamites': 'Mascamites', 'oumuamua': "'Oumuamua"}
    for key, s in alien.items():
        items = [{'key': key + '-columns', 'title': '%s: the three columns' % names[key], 'html': columns_table(s)}]
        extra = ''
        if 'message_rewards' in s:
            extra += '<dl class="kv"><dt>Message rewards (top hexes)</dt><dd>%s</dd></dl><p class="cap">%s</p>' % (''.join(cp.pills(r) for r in s['message_rewards']), cp.esc(s['message_note']))
            items.append({'key': key + '-message', 'title': 'Centaurians: the four message reward hexes', 'html': extra})
        if 'planet_like' in s:
            p = s['planet_like']; t = s['tile']
            html = '<dl class="kv"><dt>Orbit</dt><dd>%s</dd><dt>First orbiter</dt><dd>%s</dd><dt>Land</dt><dd>%s</dd><dt>First landers get data</dt><dd>%s</dd></dl><p class="cap">%s</p>' % (cp.pills(p['orbit']), cp.pills(p['first_orbiter']), cp.pills(p['land']), ' '.join('<span class="pill p-data">%d data</span>' % x for x in p['first_lander_data']), cp.esc(p['note']))
            items.append({'key': key + '-planet', 'title': "'Oumuamua: the planet-like part at the top of the board", 'html': html})
            html = '<dl class="kv"><dt>Data slot</dt><dd>%d data tokens</dd><dt>First marker</dt><dd>%s</dd><dt>Third marker</dt><dd>%s</dd><dt>On completion</dt><dd>%s</dd></dl>' % (t['data_tokens'], cp.pills(t['slot_rewards']['first_marker']), cp.pills(t['slot_rewards']['third_marker']), cp.esc(t['on_completion']))
            items.append({'key': key + '-tile', 'title': "'Oumuamua tile (on disc 3)", 'html': html})
        if key == 'exertians':
            items.append({'key': key + '-banner', 'title': 'Exertians: danger and the points penalty', 'html': '<p style="margin:0">Danger per marker by tier: top tier 1, middle tier 2, bottom tier 3 (the tiers are the three bands divided by the orange lines on the board). The gold banner at the top shows the penalty: the player with the most danger loses one tenth of their points (rounded down).</p>'})
        for tk in s['tokens']:
            if tk.get('sides'):
                faces = ''.join('<dd>%s</dd>' % cp.pills(x) for x in tk['sides'])
                items.append({'key': key + '-tokens', 'title': '%s: %s' % (names[key], tk['name']), 'html': '<dl class="kv"><dt>Faces</dt>%s</dl><p class="cap">%s</p>' % (faces, cp.esc(tk.get('note', '')))})
            else:
                items.append({'key': key + '-token-' + tk['name'][:8].replace(' ', '-'), 'title': '%s: %s' % (names[key], tk['name']), 'html': '<p style="margin:0">%s</p>' % cp.esc(tk.get('note', ''))})
        if key == 'anomalies':
            items[-1]['html'] = '<dl class="kv"><dt>Pink token</dt><dd>one side 1 credit, other side 4 VP</dd><dt>Yellow token</dt><dd>one side 1 card, other side 2 publicity</dd><dt>Blue token</dt><dd>one side 1 data, other side 1 energy</dd></dl><p class="cap">Three tokens, placed random side up. The colored cap says which column the anomaly belongs to: the player with the highest marked space in that column gains the reward.</p>'
        secs.append({'title': names[key], 'intro': '', 'images': [{'key': 'ab_' + key, 'caption': names[key] + ' board, as supplied', 'width': 520}] + ([{'key': 'anom_tokens', 'caption': 'Anomaly tokens: six faces (two per token, the colored cap shows the column)', 'width': 560}] if key == 'anomalies' else []) + ([{'key': 'strip', 'caption': "'Oumuamua tile (cut-out disc piece)", 'width': 520}] if key == 'oumuamua' else []), 'items': items})
    secs.append({'title': 'Tokens and tiles supplied', 'intro': 'All token and tile images for these species, as supplied. I read them as: brown discs are the 7 Mascamite sample faces and the yellow disc is their back; the teal capsules are the 6 Anomaly token faces; the four colored hexes "+15" are the Centaurian message tiles; the two black tabs "+20" and "+40" are the Exertian milestone tiles; the purple tile is an exofossil. The green shield is a Glyphids piece (expansion, not used now). The green and red tabs and the two small boxes are not identified (see the question below).',
                 'images': [{'key': 'tokens', 'caption': 'Species tokens and tiles (names from my labeling)', 'width': 1100}],
                 'items': [{'key': 'tokens-identified', 'title': 'The token readings above are right', 'html': '<p style="margin:0">Mascamite samples, Anomaly tokens, Centaurian message tiles, Exertian milestone tiles (the second one costs 1 credit to use, per the rule sheet) and exofossils.</p>'},
                           {'key': 'tokens-unknown', 'title': 'Unidentified: the green "2 VP" tab, two red "card with arrow" tabs, two gray boxes and the pink "signal and card" icon', 'html': '<p style="margin:0">I could not identify these from the art. Please write in the note what each is, or that they can be ignored. (They may be Tabletop Simulator helpers.)</p>'}]})
    return cp.build('SETI Alien Species Check', 'SETI alien species check', 'The five base-game alien species boards, read from the images. Each board is shown at readable size, with my reading as a table beside it. Open a row, compare it with the image and your physical board, and mark it.', 'alien-check', secs, urls)


def solo_page():
    secs = []
    # rival boards
    rows = []
    for b in sd.RIVAL_BOARDS:
        for s in b['stars']:
            ob = b['objectives'].get(s)
            rows.append(['%d star' % s, cp.esc(b['image']), '%d basic%s' % (b['basic_cards'], ' + 1 advanced' if b['advanced_cards'] else ''), 'none' if not ob else '%d / %d / %d' % (ob['I'], ob['II'], ob['III']), b['start_space']])
    secs.append({'title': 'Rival boards (solo mode)', 'intro': 'Four boards: 1-star and 2-star share one. The edge strip of each board gives the starting deck, the objective stack and the starting progress space. The big picture of the board is the 4-star one.',
                 'images': [{'key': 'rv4', 'caption': 'Rival board, 4 stars', 'width': 900}, {'key': 'edges', 'caption': 'The difficulty edge of the four boards, left to right: 4-star, 5-star, 1-2 star, 3-star', 'width': 520}],
                 'items': [
                     {'key': 'rv-table', 'title': 'Difficulty table', 'html': cp.table(['Difficulty', 'Board', 'Starting deck', 'Objective stack I / II / III', 'Progress start'], rows)},
                     {'key': 'rv-track', 'title': 'Progress track: 12 spaces, clockwise', 'html': '<p style="margin:0">Clockwise from the top: %s. Color is the preferred tech type (orange probe, pink telescope, blue computer); the glyph is the stack on the tech board (dot, link, branch, cross). The growth icon sits between orange-cross and blue-dot.</p>' % cp.esc(', '.join(sd.PROGRESS_TRACK_CLOCKWISE))},
                     {'key': 'rv-computer', 'title': 'Rival computer and analyze slot', 'html': '<p style="margin:0">6 spaces. The 2nd space gives the rival 1 publicity; the 4th gives 4 progress (the marked space). The slot at the right end shows the computer with 1 energy, then a blue life trace: what the rival gains when it analyzes (after clearing its computer).</p>'},
                     {'key': 'rv-progress', 'title': 'Progress from resources', 'html': '<p style="margin:0">The rival advances 1 on the progress track for each credit, energy and card it gains, and 4 for a tuck-for-income effect (rulebook p.23).</p>'},
                     {'key': 'rv-objtable', 'title': 'Objective table on the left of the board', 'html': '<p style="margin:0">After rounds 1, 2, 3, 4 the player spends 1, 2, 3, 4 completed objectives; each one they cannot spend gives the rival 3 progress. After round 5 each uncompleted objective gives the rival 5 VP (1-star difficulty has no objectives).</p>'}]})
    # objectives
    def objsec(level, label, key):
        its = []
        for o in sd.OBJECTIVES:
            if o['level'] != level: continue
            its.append({'key': 'obj-' + o['id'], 'title': '%s: %s' % (o['id'], '; '.join(' / '.join(sd.tt(x) for x in task) for task in o['tasks'])),
                        'html': '<dl class="kv"><dt>Tasks</dt><dd>%s</dd></dl>%s' % (''.join('<div>%s</div>' % cp.esc(' or '.join(sd.tt(x) for x in task)) for task in o['tasks']), '<p class="cap">%s</p>' % cp.esc(o['note']) if o.get('note') else '')})
        return {'title': label, 'intro': 'Each tile has one to three tasks; a task with a slash is done by either part. Each tile is completed when all its tasks are marked. Read the images as: hexagon = action, chip = tech, triangle = life trace, strip with a check = win a sector, white card with a green check = completed mission.', 'images': [{'key': key, 'caption': label + ', all faces', 'width': 900}], 'items': its}
    secs.append(objsec('I', 'Objectives, level I (4 tiles)', 'obj1'))
    secs.append(objsec('II', 'Objectives, level II (11 tiles)', 'obj2'))
    secs.append(objsec('III', 'Objectives, level III (9 tiles)', 'obj3'))
    # gold
    its = []
    for g in sd.GOLD_TILES:
        its.append({'key': 'gold-%s-%s' % (g['tile'].lower(), g['side']), 'title': '%s, side %s: %s' % (g['tile'], g['side'], ' / '.join(map(str, g['values']))),
                    'html': '<dl class="kv"><dt>Values</dt><dd>first chooser %d, second chooser %d, third and fourth %d</dd><dt>Scores for</dt><dd>%s</dd></dl>' % (g['values'][0], g['values'][1], g['values'][2], cp.esc(g['per']))})
    secs.append({'title': 'Gold scoring tiles (8 faces)', 'intro': 'Four double-sided tiles. The first player to choose a tile takes the highest value, the second the middle one, and the third and fourth share the wide lowest slot (my reading of the wide slot). See END-10 to END-17.', 'images': [{'key': 'gold', 'caption': 'The eight gold tile faces', 'width': 1100}], 'items': its})
    return cp.build('SETI Solo and Scoring Check', 'SETI solo and scoring check', 'The rival boards, the 24 objective tiles and the gold scoring tiles, read from the images. Open a row, compare it with the image and your physical component, and mark it.', 'solo-scoring-check', secs, urls)


open(sys.argv[2], 'w', encoding='utf-8').write(alien_page())
open(sys.argv[3], 'w', encoding='utf-8').write(solo_page())
print('built')
