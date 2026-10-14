"""Report which spec rule IDs are cited in the engine code and in the tests (CLAUDE.md rule 2).

Run from the repo root: python tools/engine/rule_coverage.py
A rule counts as implemented when its ID appears in services/engine/src, and as tested when it appears in services/engine/tests.
IDs are read from the generated docs/spec/rules-index.md; data tasks (BOARD-xx, ALIEN-DATA-xx and so on) are listed separately.
"""
import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ID = re.compile(r'\b[A-Z]+(?:-[A-Z0-9]+)*-\d+\b')
idx = open(os.path.join(ROOT, 'docs', 'spec', 'rules-index.md'), encoding='utf-8').read()
by_file, current = {}, None
for line in idx.splitlines():
    if line.startswith('## '):
        current = line[3:].strip()
        by_file[current] = []
    m = re.match(r'\| ([A-Z][A-Z0-9-]*-\d+) \|', line)
    if m and current:
        by_file[current].append(m.group(1))


def cited(pattern):
    found = set()
    for f in glob.glob(os.path.join(ROOT, 'services', 'engine', pattern), recursive=True):
        found |= set(ID.findall(open(f, encoding='utf-8').read()))
    return found


code, tests = cited('src/**/*.py'), cited('tests/**/*.py')
print('%-30s %6s %8s %8s' % ('spec file', 'rules', 'in code', 'in tests'))
tot = [0, 0, 0]
for f, ids in by_file.items():
    if f in ('faq.md', 'solo-rival-cards.md') or f.startswith('board-') or f == 'aliens.md' and False:
        pass
    c = sum(1 for i in ids if i in code)
    t = sum(1 for i in ids if i in tests)
    print('%-30s %6d %8d %8d' % (f, len(ids), c, t))
    tot[0] += len(ids); tot[1] += c; tot[2] += t
print('%-30s %6d %8d %8d' % ('total', *tot))
if '-v' in sys.argv:
    for f, ids in by_file.items():
        print(f, 'not yet in code:', ', '.join(i for i in ids if i not in code)[:400])
