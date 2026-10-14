"""Build the stars and planets check page: python build_stars_planets.py <urls.json> <out.html>"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
spec = os.path.join(here, '..', '..', 'docs', 'spec', 'data')
stars = json.load(open(os.path.join(spec, 'stars.json'), encoding='utf-8'))
planets = json.load(open(os.path.join(spec, 'planets.json'), encoding='utf-8'))
urls = json.load(open(sys.argv[1], encoding='utf-8')) if os.path.exists(sys.argv[1]) else {}
data = {'boards': stars['boards'], 'star_common': stars['star_common'], 'planets': planets['planets']}
tpl = open(os.path.join(here, 'stars-planets-template.html'), encoding='utf-8').read()
out = tpl.replace('/*DATA*/', json.dumps(data).replace('</', '<\\/')).replace('/*URLS*/', json.dumps(urls))
open(sys.argv[2], 'w', encoding='utf-8').write(out)
print(len(out), 'bytes')
