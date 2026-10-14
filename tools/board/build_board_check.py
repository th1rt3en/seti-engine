"""Build the board check page: python build_board_check.py <urls.json> <out.html>"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(here, '..', '..', 'docs', 'spec', 'data', 'solar-system.json'), encoding='utf-8'))
urls = json.load(open(sys.argv[1], encoding='utf-8')) if os.path.exists(sys.argv[1]) else {}
for k in ('disc1', 'disc2', 'disc3', 'disc3o', 'base'):
    urls.setdefault(k, '')
tpl = open(os.path.join(here, 'board-check-template.html'), encoding='utf-8').read()
slim = {'wheels': data['wheels'], 'oumuamua_slot': data['oumuamua_slot']}
# wheels keys are strings in JSON; the template indexes them by number which works for both
out = tpl.replace('/*DATA*/', json.dumps(slim).replace('</', '<\\/')).replace('/*URLS*/', json.dumps(urls))
open(sys.argv[2], 'w', encoding='utf-8').write(out)
print(len(out), 'bytes')
