"""Generic builder for owner check pages (same look and behavior as the other check pages).

build(title, heading, subtitle, collection, sections, urls) -> html

A section is {'title', 'intro' (html), 'images': [{'key', 'caption', 'width'}], 'items': [{'key', 'title', 'html'}]}.
Each item gets Matches / Mark a difference / Clear buttons and a note box; marks are stored in the artifact db collection `collection`.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
_tpl = open(os.path.join(HERE, 'stars-planets-template.html'), encoding='utf-8').read()
HEAD_CSS = _tpl[_tpl.index('<link rel="preconnect"'):_tpl.index('</style>') + len('</style>')]
EXTRA_CSS = """
<style>
:root { --p-alien: #1d6f6a; --p-alien-bg: #d6efec; --p-exo: #5b3fa0; --p-exo-bg: #e8e0f7; --p-cost: #8a2f1d; --p-cost-bg: #fbe3df; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --p-alien: #7fd8d0; --p-alien-bg: #12332f; --p-exo: #c0a8f5; --p-exo-bg: #2e2250; --p-cost: #ff9a84; --p-cost-bg: #3a1b14; } }
:root[data-theme="dark"] { --p-alien: #7fd8d0; --p-alien-bg: #12332f; --p-exo: #c0a8f5; --p-exo-bg: #2e2250; --p-cost: #ff9a84; --p-cost-bg: #3a1b14; }
.p-alien_card { background: var(--p-alien-bg); color: var(--p-alien); } .p-exofossil { background: var(--p-exo-bg); color: var(--p-exo); } .p-credit { background: var(--inc-bg); color: var(--inc); }
.p-cost { background: var(--p-cost-bg); color: var(--p-cost); } .p-signal_oumuamua, .p-info { background: var(--sig-bg); color: var(--sig); }
table.tb { border-collapse: collapse; width: 100%; font-size: 16px; } table.tb th, table.tb td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
table.tb th { background: var(--todo-bg); font-weight: 600; }
.tbwrap { overflow-x: auto; } .sec-intro { color: var(--muted); max-width: 90ch; margin: 0 0 12px; }
.imgs { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; margin-bottom: 8px; } .imgs figure { margin: 0; flex: 1 1 360px; min-width: 0; }
.imgs img { width: 100%; border-radius: 8px; border: 1px solid var(--line); display: block; } .imgs figcaption { color: var(--muted); font-size: 15px; margin-top: 4px; }
</style>
"""


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def txt(r):
    t, n = r['t'], r.get('n', 1)
    s = 's' if n > 1 else ''
    m = {'vp': '%d VP' % n, 'publicity': '%d publicity' % n, 'credit': '%d credit%s' % (n, s), 'energy': '%d energy' % n, 'data': '%d data' % n,
         'card_any': '%d card%s' % (n, s), 'card_random': '%d random card%s' % (n, s), 'alien_card': '%d alien card%s' % (n, s), 'exofossil': '%d exofossil%s' % (n, s),
         'trace': '%d %s life trace%s' % (n, r.get('kind', 'any'), s), 'signal_oumuamua': "%d signal at 'Oumuamua" % n}
    return m.get(t, t)


def pill(r, cost=False):
    cls = 'p-cost' if cost else 'p-' + ('trace-' + r['kind'] if r['t'] == 'trace' else r['t'])
    return '<li class="pill %s">%s%s</li>' % (cls, 'pay ' if cost else '', esc(txt(r)))


def pills(rs, cost=False):
    return '<ul class="pills">%s</ul>' % ''.join(pill(r, cost) for r in rs) if rs else '<span class="cap">none</span>'


def table(head, rows):
    return '<div class="tbwrap"><table class="tb"><tr>%s</tr>%s</table></div>' % (''.join('<th>%s</th>' % h for h in head), ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % c for c in r) for r in rows))


SCRIPT = r"""
<script>
const PAGE = /*PAGE*/;
const URLS = /*URLS*/;
const state = {};
let db = null, uid = null, canWrite = true, local = false;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ITEMS = PAGE.sections.flatMap((s) => s.items);
const safe = (k) => k.replace(/[^A-Za-z0-9_\-.~:@+]/g, '_');
function itemHtml(it) {
  const st = state[it.key]?.status || 'unchecked', label = { unchecked: 'Unchecked', confirmed: 'Confirmed', difference: 'Difference' }[st];
  return `<details class="item s-${st}" data-key="${esc(it.key)}"><summary><span class="t">${esc(it.title)}</span><span class="badge">${label}</span></summary><div class="body">${it.html}
    <textarea class="note" placeholder="Required for a difference: what is wrong or missing?" ${canWrite ? '' : 'disabled'}>${esc(state[it.key]?.note || '')}</textarea>
    <div class="actions"><button class="btn ok" data-act="confirmed" type="button" ${canWrite ? '' : 'disabled'}>Matches</button>
    <button class="btn diff" data-act="difference" type="button" ${canWrite ? '' : 'disabled'}>Mark a difference</button>
    <button class="btn" data-act="unchecked" type="button" ${canWrite ? '' : 'disabled'}>Clear</button><span class="hint" hidden></span></div></div></details>`;
}
function render() {
  const open = new Set([...document.querySelectorAll('details.item[open]')].map((d) => d.dataset.key));
  $('sections').innerHTML = PAGE.sections.map((s) => `<h2>${esc(s.title)}</h2><div class="panel">${s.intro ? `<p class="sec-intro">${s.intro}</p>` : ''}
    ${s.images.length ? `<div class="imgs">${s.images.map((im) => `<figure style="${im.width ? 'flex-basis:' + im.width + 'px;max-width:' + im.width + 'px' : ''}"><img src="${URLS[im.key] || ''}" alt="${esc(im.caption)}" loading="lazy"><figcaption>${esc(im.caption)}</figcaption></figure>`).join('')}</div>` : ''}
    <div class="items">${s.items.map(itemHtml).join('')}</div></div>`).join('');
  document.querySelectorAll('details.item').forEach((d) => { if (open.has(d.dataset.key)) d.open = true; });
}
function summary() {
  const total = ITEMS.length; let ok = 0, diff = 0;
  for (const it of ITEMS) { const s = state[it.key]?.status; if (s === 'confirmed') ok++; else if (s === 'difference') diff++; }
  $('meter').innerHTML = `<span><b>${ok}</b> of ${total} confirmed</span><span class="cap">${diff} with differences, ${total - ok - diff} unchecked</span><div class="bar" role="img" aria-label="${ok} confirmed, ${diff} differences"><i class="b-ok" style="width:${ok / total * 100}%"></i><i class="b-diff" style="width:${diff / total * 100}%"></i></div>`;
}
function sync(t, e) { $('sync').textContent = t; $('sync').classList.toggle('err', !!e); }
const LS = 'seti-check-' + PAGE.collection;
const lsRead = () => { try { return JSON.parse(localStorage.getItem(LS) || '{}'); } catch { return {}; } };
const queues = new Map();
function persist(key, rec) {
  const prev = queues.get(key) || Promise.resolve();
  queues.set(key, prev.then(async () => {
    if (local) { const o = lsRead(); if (rec) o[key] = rec; else delete o[key]; try { localStorage.setItem(LS, JSON.stringify(o)); } catch {} return; }
    const ref = db.collection(PAGE.collection).doc(safe(key)); if (rec) await ref.set(rec); else await ref.delete();
  }).then(() => sync(local ? 'Saved in this browser only' : 'All changes saved'), (e) => sync('Could not save: ' + (e && e.message || 'error'), true)));
}
function commit(key, patch) {
  if (!canWrite) return;
  const cur = state[key] || { status: 'unchecked', note: '' }, rec = { status: cur.status, note: cur.note || '', ...patch, at: Date.now(), by: uid || 'local' };
  if (rec.status === 'unchecked' && !rec.note) { delete state[key]; persist(key, null); } else { state[key] = rec; persist(key, rec); }
  sync('Saving...'); render(); summary();
}
document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-act]'); if (!b) return;
  const d = b.closest('details.item'), key = d.dataset.key, ta = d.querySelector('textarea'), note = ta.value.trim(), hint = d.querySelector('.hint');
  if (b.dataset.act === 'difference' && !note) { hint.textContent = 'Write what is different first.'; hint.hidden = false; ta.focus(); return; }
  if (b.dataset.act === 'unchecked') commit(key, { status: 'unchecked', note: '' }); else commit(key, { status: b.dataset.act, note });
  document.querySelector(`details.item[data-key="${CSS.escape(key)}"]`)?.setAttribute('open', '');
});
document.addEventListener('change', (e) => {
  if (!e.target.matches('textarea.note')) return;
  const key = e.target.closest('details.item').dataset.key, cur = state[key] || { status: 'unchecked' };
  commit(key, { status: cur.status, note: e.target.value.trim() });
});
render(); summary();
(async () => {
  let d = null, u = null;
  try { [d, u] = await Promise.all([claude.use('db'), claude.use('user')]); } catch {}
  db = d;
  if (u) { try { uid = await u.id(); } catch {} try { if ((await u.can('data.write')) === false) canWrite = false; } catch {} }
  if (!db) { local = true; const o = lsRead(); for (const k of Object.keys(o)) state[k] = o[k]; $('banner').innerHTML = '<div class="banner">Shared storage is unavailable here, so checks are kept in this browser only.</div>'; sync('Saved in this browser only'); render(); summary(); return; }
  if (!canWrite) $('banner').innerHTML = '<div class="banner">You have view-only access, so checks cannot be saved.</div>';
  const idMap = new Map(ITEMS.map((i) => [safe(i.key), i.key]));
  db.collection(PAGE.collection).onSnapshot((snap) => {
    for (const k of Object.keys(state)) delete state[k];
    for (const doc of snap.docs) { const k = idMap.get(doc.id); if (k) state[k] = doc.data(); }
    sync(snap.metadata.hasPendingWrites ? 'Saving...' : 'All changes saved');
    if (!document.activeElement || !document.activeElement.matches('textarea.note')) render();
    summary();
  }, (err) => sync('Lost connection to storage: ' + (err && err.message || err.code), true));
})();
</script>
"""


def build(title, heading, subtitle, collection, sections, urls):
    page = {'collection': collection, 'sections': sections}
    head = '<title>%s</title>\n' % esc(title) + HEAD_CSS + EXTRA_CSS
    body = ('<div class="wrap"><header><div><h1>%s</h1><p class="sub">%s</p></div><div class="sync" id="sync" role="status">Connecting...</div></header>'
            '<div id="banner"></div><div class="meter" id="meter"></div><div id="sections"></div></div>') % (esc(heading), esc(subtitle))
    js = SCRIPT.replace('/*PAGE*/', json.dumps(page).replace('</', '<\\/')).replace('/*URLS*/', json.dumps(urls))
    return head + body + js
