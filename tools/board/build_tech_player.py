"""Build the tech board and player board check page: python build_tech_player.py <urls.json> <out.html>
The style block is taken from the stars and planets template so the pages look the same."""
import json
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
spec = os.path.join(here, '..', '..', 'docs', 'spec', 'data')
tech = json.load(open(os.path.join(spec, 'tech-board.json'), encoding='utf-8'))
urls = json.load(open(sys.argv[1], encoding='utf-8')) if os.path.exists(sys.argv[1]) else {}
stars_tpl = open(os.path.join(here, 'stars-planets-template.html'), encoding='utf-8').read()
head = stars_tpl[:stars_tpl.index('<div class="wrap">')].replace('SETI Stars and Planets Check', 'SETI Tech and Player Board Check')
head = head.replace('.p-signal_planet, .p-signal_color {', '.p-sig, .p-signal_planet, .p-signal_color {')
body = open(os.path.join(here, 'tech-player-body.html'), encoding='utf-8').read()
data = {'stacks': tech['stacks'], 'bonuses_per_stack': tech['bonuses_per_stack']}
out = head + body.replace('/*DATA*/', json.dumps(data).replace('</', '<\\/')).replace('/*URLS*/', json.dumps(urls))
open(sys.argv[2], 'w', encoding='utf-8').write(out)
print(len(out), 'bytes')
