#!/usr/bin/env python3
"""Basic consistency checks for generated paper pages and their source records."""
from pathlib import Path
import json
import re
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DIST=ROOT/'dist'
class Links(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='a' and d.get('href'):self.links.append(d['href'])
        if d.get('id'):self.ids.add(d['id'])

papers=json.loads((DATA/'curated.json').read_text())+json.loads((DATA/'generated.json').read_text())
ids=[p['id'] for p in papers]
assert len(ids)==len(set(ids)), 'Duplicate ID'
assert len({p['doi'].lower() for p in papers})==len(papers),'Duplicate DOI'
for p in papers:
    assert re.fullmatch('[a-z0-9-]+',p['id']),p['id']
    assert p['doi'] and p['takeaway'] and p['novelty'] and p['source_url']
    for key in ['results','limitations','research_links','tags']:
        assert p[key],(p['id'],key)
    path=DIST/'papers'/f'{p["id"]}.html'
    assert path.exists(),path
for page in [DIST/'index.html',*(DIST/'papers').glob('*.html')]:
    parser=Links();parser.feed(page.read_text(encoding='utf-8'))
    for href in parser.links:
        if href.startswith(('http:','https:','mailto:','#')):continue
        base=href.split('#')[0].split('?')[0]
        if not base:continue
        assert (page.parent/base).resolve().exists(),(page,href)
print(f'All checks passed — {len(papers)} papers; {len(list((DIST/"papers").glob("*.html")))} article pages; links valid.')
