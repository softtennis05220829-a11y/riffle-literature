#!/usr/bin/env python3
"""RIFFLE static-site build and optional twice-daily OpenAlex discovery.
No key is ever shipped to the browser. Site summaries from OpenAlex require OPENAI_API_KEY.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
DATA = ROOT / 'data'
TZ = ZoneInfo('Asia/Tokyo')
START = dt.date(2026, 11, 17)
SITE_NAME = 'RIFFLE — River Literature Radar'

def load_json(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8'))

def save_json(path, item):
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def e(value): return html.escape(str(value or ''), quote=True)

def date_label(iso):
    d = dt.date.fromisoformat(iso)
    return f'{d.year}.{d.month:02d}.{d.day:02d}'

def tagbits(p):
    return ''.join('<span class="topic-chip">'+e(t)+'</span>' for t in p.get('tags',[])[:4])

def anchor(p, base=''):
    return base + 'papers/' + p['id'] + '.html'

def metrics(p):
    return f'<span>{e(p["year"])} <span class="meta-dot">·</span> {e(p.get("journal",""))}</span><span class="meta-dot">/</span><span>{e(p.get("read_minutes",6))} min read</span>'

def card(p, base='', prominent=False):
    label = 'FOUNDATION' if p['kind']=='classic' else 'FRONTIER'
    return f'''<a href="{e(anchor(p,base))}" class="paper-card {'paper-card--wide' if prominent else ''}" data-search="{e(' '.join([p['title'],p['authors'],p['theme'],*p['tags'],p['brief']]).lower())}" data-type="{e(p['kind'])}" data-id="{e(p['id'])}">
    <div class="card-top"><span class="type-label {'type-classic' if p['kind']=='classic' else 'type-trend'}"><i></i>{label}</span><span class="bookmark-indicator" aria-label="保存済み">✧</span></div>
    <div class="card-main"><p class="card-theme">{e(p['theme'])}</p><h3>{e(p['title'])}</h3><p class="card-brief">{e(p['brief'])}</p></div>
    <div class="card-bottom"><span class="card-journal">{e(p['authors'])} <span>·</span> {e(p['year'])}</span><span class="card-arrow">↗</span></div>
    </a>'''

def shell(content, title, base='', article=False, extra_css=''):
    homepage = base or './'
    top = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="theme-color" content="#172c28"><meta name="description" content="付着藻類・アユ・河川生態学のための研究文献レーダー。重要な古典と最新の研究を毎日2回。"><title>{e(title)} | RIFFLE</title><link rel="icon" href="{e(base)}assets/favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="{e(base)}assets/styles.css">{extra_css}</head><body class="{'article-body' if article else 'home-body'}">
    <div class="site-grid"><aside class="sidebar" aria-label="サイトメニュー"><a class="brand" href="{e(homepage)}"><span class="brand-mark"><svg viewBox="0 0 40 40" width="40" height="40" aria-hidden="true"><path d="M5 26C10 16 14 15 19 22S28 28 35 14" fill="none" stroke="#d5fa8c" stroke-width="2.8" stroke-linecap="round"/><path d="M5 33C11 23 16 23 20 28S29 31 35 23" fill="none" stroke="#91bfb5" stroke-width="2.6" stroke-linecap="round"/></svg></span><span class="brand-type">RIFFLE<small>RIVER LITERATURE RADAR</small></span></a>
    <div class="sidebar-section-label">READING DESK <span>01—04</span></div><nav class="sidebar-nav"><a href="{e(homepage)}#today" class="nav-item"><span class="nav-icon">◉</span> 今日の2本</a><a href="{e(homepage)}#archive" class="nav-item"><span class="nav-icon">▦</span> 論文ライブラリ</a><a href="{e(homepage)}#archive" class="nav-item" data-nav-bookmarks><span class="nav-icon">☆</span> あとで読む <b id="saved-count">0</b></a><a href="{e(homepage)}#topics" class="nav-item"><span class="nav-icon">⌁</span> 研究キーワード</a></nav>
    <div class="sidebar-bottom"><span class="live-spot"></span><span>CURATED FOR<br><b>RIVER ECOLOGY</b></span><div class="sidebar-line"></div><p>水の流れを追うように、<br>研究の流れを追う。</p></div></aside>
    <div class="page-column"><header class="topbar"><div class="topbar-breadcrumb">RESEARCH DESK <span>/</span> {('PAPER NOTE' if article else 'DAILY DISCOVERY')}</div><div class="topbar-right"><span class="topbar-time">07:00 &nbsp;/&nbsp; 18:00 JST</span><span class="status-pill"><i></i> 2 EDITIONS / DAY</span></div></header>{content}<footer class="footer"><span class="footer-brand">RIFFLE <em>／</em> keep exploring.</span><span>論文の原著・DOIを必ず確認してください。自動生成の要約は誤りを含む可能性があります。</span><span>© {dt.datetime.now(TZ).year} RIFFLE</span></footer></div></div><script defer src="{e(base)}assets/site.js"></script></body></html>'''
    return top

def feature(p, slot, date):
    if slot=='morning':
        return f'''<a class="feature feature-morning" href="{e(anchor(p))}"><div class="feature-top"><span class="edition"><span class="edition-sun">◌</span> MORNING EDITION</span><span class="edition-time">07:00 · FOUNDATIONS</span></div><div class="feature-copy"><span class="feature-kicker">01 / 知っておくべき既往研究</span><h3>{e(p['title'])}</h3><p>{e(p['takeaway'])}</p></div><div class="feature-bottom"><span>{e(p['authors'])} · {e(p['year'])}</span><span class="feature-link">研究ノートを読む <b>↗</b></span></div><div class="feature-rings" aria-hidden="true"><i></i><i></i><i></i><i></i></div></a>'''
    return f'''<a class="feature feature-evening" href="{e(anchor(p))}"><div class="feature-top"><span class="edition"><span class="edition-moon">✳</span> EVENING EDITION</span><span class="edition-time">18:00 · FRONTIERS</span></div><div class="feature-copy"><span class="feature-kicker">02 / 新着・注目の研究動向</span><h3>{e(p['title'])}</h3><p>{e(p['takeaway'])}</p></div><div class="feature-bottom"><span>{e(p['authors'])} · {e(p['year'])}</span><span class="feature-link">研究ノートを読む <b>↗</b></span></div><div class="feature-orbit" aria-hidden="true">◌</div></a>'''

def home(papers, today, day_plan, archive):
    byid = {p['id']:p for p in papers}
    morning = byid[day_plan['morning']]; evening = byid.get(day_plan.get('evening'))
    tags = ['藻類食者','アユ','バイオフィルム','三次元構造','出水撹乱','栄養塩','安定同位体','回復力','流速','EPS']
    allp = sorted(papers, key=lambda p:(p['kind']!='trend', -p['year'], p['title']))
    discover = ''.join(card(p) for p in allp)
    topics = ''.join(f'<button class="topic-button" data-topic="{e(t)}">{e(t)} <span>↗</span></button>' for t in tags)
    dates = sorted(archive.keys(), reverse=True)[:14]
    log_parts = []
    for date in dates:
        am = byid.get(archive[date].get('morning')); pm = byid.get(archive[date].get('evening'))
        if not am: continue
        pm_markup = f'<a href="{e(anchor(pm))}">PM / {e(pm["title"])}</a>' if pm else '<span>PM / 18:00 公開予定</span>'
        log_parts.append(f'<div class="history-line"><span>{date_label(date)}</span><a href="{e(anchor(am))}">AM / {e(am["title"])}</a>{pm_markup}</div>')
    log = ''.join(log_parts)
    content = f'''<main id="main" class="home-main">
    <div class="intro"><div class="intro-date"><span class="intro-dot"></span> YOUR RESEARCH BRIEFING <span class="intro-separator">/</span> {date_label(today)} <span class="jst">JST</span></div><div class="hero-flex"><div><h1>研究の流れを、<br><em>毎日の習慣に。</em></h1><p>河川生態学・付着藻類・アユを中心に。<br>定番の重要論文と、新しい発見を1日2回届ける文献デスク。</p></div><div class="hero-aside"><span class="hero-number">02<span>papers</span></span><span>新しい視点を、<br>毎日ふたつ。</span></div></div></div>
    <section id="today" class="today-section"><div class="section-head"><div><p class="eyebrow">01 / YOUR DAILY TWO</p><h2>今日のピックアップ<span class="section-annot">TODAY'S PICKS</span></h2></div><span class="section-rule-label">{date_label(today)}</span></div><div class="features">{feature(morning,'morning',today)}{feature(evening,'evening',today) if evening else '<div class="feature feature-evening feature-pending"><div class="feature-top"><span class="edition">✳ EVENING EDITION</span><span class="edition-time">18:00 · FRONTIERS</span></div><div class="feature-copy"><span class="feature-kicker">02 / 新着・注目の研究動向</span><h3>今日の新しい発見は、夕方に。</h3><p>次の論文ノートは18:00（日本時間）に更新されます。夕方の読書をお楽しみに。</p></div><div class="feature-bottom"><span>COMING THIS EVENING</span><span class="feature-link">18:00 JST</span></div></div>'}</div><p class="source-line"><span>ⓘ</span> 各ノートに原著へのリンクを付けています。新規論文の自動取得・日本語解説にはAPI設定が必要です。</p></section>
    <section id="archive" class="archive-section"><div class="section-head"><div><p class="eyebrow">02 / THE READING LIBRARY</p><h2>文献ライブラリ <span class="section-annot">THE ARCHIVE</span></h2></div><div class="archive-count"><span id="result-count">{len(allp)}</span> PAPERS</div></div><div class="archive-tools"><div class="search-field"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4 4"/></svg><input id="paper-search" type="search" placeholder="著者、テーマ、論文名で検索..." autocomplete="off" aria-label="論文検索"></div><div class="filter-tabs" role="group" aria-label="論文の種類で絞り込み"><button class="filter active" data-filter="all">すべて</button><button class="filter" data-filter="classic">重要な既往研究</button><button class="filter" data-filter="trend">新着・注目</button><button class="filter" data-filter="saved">☆ 保存済み</button></div></div><div id="papers-grid" class="papers-grid">{discover}</div><p id="empty-state" class="empty-state" hidden>該当する論文がありません。キーワードやフィルターを変えてみてください。</p></section>
    <section id="topics" class="topics-section"><div class="section-head"><div><p class="eyebrow">03 / FOLLOW THE CURRENT</p><h2>研究キーワード <span class="section-annot">EXPLORE TOPICS</span></h2></div></div><div class="topic-grid">{topics}</div></section>
    <section class="method-section"><div class="method-mark">✳</div><div><p class="eyebrow">HOW TO READ RIFFLE</p><h2>要点を先に。根拠はその先に。</h2><p>各ノートでは <b>Take-home message → 要点 → 新規性</b> を最初に提示し、研究の問い、方法、結果、解釈の注意点、依田川・博士研究への接続を続けます。著者の結論と独自の研究メモは分けて記載します。</p><a href="#archive" class="text-link">論文を探す <span>↗</span></a></div></section>
    <section class="history-section"><div class="section-head"><div><p class="eyebrow">04 / READING LOG</p><h2>配信履歴 <span class="section-annot">EDITION HISTORY</span></h2></div></div>{log if log else '<p class="muted">公開日以降の更新履歴がここに表示されます。</p>'}</section>
    </main>'''
    return shell(content, '毎日の研究文献', '')

def bullets(items): return ''.join(f'<li>{e(i)}</li>' for i in items)

def paper_page(p,papers):
    related = sorted((x for x in papers if x['id']!=p['id']),key=lambda x:len(set(x['tags'])&set(p['tags'])),reverse=True)[:3]
    rel = ''.join(card(x,base='../') for x in related)
    kind = 'FOUNDATION / CLASSIC' if p['kind']=='classic' else 'FRONTIER / RECENT RESEARCH'
    label = '重要な既往研究' if p['kind']=='classic' else '新着・注目の研究'
    doiurl = 'https://doi.org/' + urllib.parse.quote(p['doi'],safe='/().-')
    note = p.get('evidence','要旨と書誌情報をもとに作成')
    content = f'''<main id="main" class="article-main"><div class="article-nav"><a href="../index.html#archive">← 文献ライブラリへ戻る</a><span>PAPER NOTE / {e(p['year'])}</span></div>
    <div class="article-header"><div class="article-overline"><span class="type-label {'type-classic' if p['kind']=='classic' else 'type-trend'}"><i></i>{kind}</span><span class="article-count">{e(p['read_minutes'])} MIN READ</span></div><p class="article-category">{e(label)} <span>/</span> {e(p['theme'])}</p><h1>{e(p['title'])}</h1><p class="article-authors">{e(p['authors'])}</p><div class="article-meta"><span>{e(p['year'])}</span><span>{e(p['journal'])}</span><a href="{e(doiurl)}" target="_blank" rel="noopener noreferrer">DOI: {e(p['doi'])} ↗</a></div></div>
    <div class="article-controls"><div class="article-tags">{tagbits(p)}</div><div class="control-buttons"><button class="save-button" data-save="{e(p['id'])}" aria-pressed="false">☆ <span>あとで読む</span></button><button class="share-button" data-share-url title="リンクをコピー">⤴ <span>共有</span></button></div></div>
    <div class="article-layout"><article class="article-content"><section class="at-a-glance" id="quick"><div class="glance-head"><span class="eyebrow">THE 60-SECOND READ</span><span class="glance-asterisk">✳</span></div><h2>まず、この3つ。</h2><div class="takeaway"><p class="small-number">01 — TAKE-HOME MESSAGE</p><p>{e(p['takeaway'])}</p></div><div class="glance-columns"><div><p class="small-number">02 — KEY FINDING</p><p>{e(p['brief'])}</p></div><div><p class="small-number">03 — WHAT'S NEW</p><p>{e(p['novelty'])}</p></div></div></section>
    <section class="article-section" id="question"><div class="article-section-heading"><span>01</span><h2>研究の問い</h2><small>RESEARCH QUESTION</small></div><p>{e(p['question'])}</p></section>
    <section class="article-section" id="methods"><div class="article-section-heading"><span>02</span><h2>研究デザイン・方法</h2><small>METHODS</small></div><p>{e(p['methods'])}</p></section>
    <section class="article-section" id="findings"><div class="article-section-heading"><span>03</span><h2>主要な結果</h2><small>MAIN FINDINGS</small></div><ol class="result-list">{bullets(p['results'])}</ol></section>
    <section class="article-section" id="limits"><div class="article-section-heading"><span>04</span><h2>解釈の注意点</h2><small>LIMITATIONS & CAUTIONS</small></div><ul class="caution-list">{bullets(p['limitations'])}</ul></section>
    <section class="article-section research-section" id="relevance"><div class="article-section-heading"><span>05</span><h2>自分の研究にどう活かす？</h2><small>RESEARCH CONNECTIONS</small></div><div class="research-prefix">RESEARCHER'S NOTE <span>／</span> 著者の主張とは区別した考察</div><ul class="insight-list">{bullets(p['research_links'])}</ul></section>
    <section class="references-section" id="source"><div class="article-section-heading"><span>06</span><h2>原著・出典</h2><small>VERIFY THE SOURCE</small></div><p>このノートは<b>{e(note)}</b>。引用に使う場合は、論文本文の該当箇所・図表と照合してください。</p><div class="source-card"><span class="source-icon">↗</span><div><small>PRIMARY SOURCE / DOI</small><b>{e(p['title'])}</b><span>{e(p['journal'])} · {e(p['year'])}</span></div><a href="{e(doiurl)}" target="_blank" rel="noopener noreferrer">原著を開く ↗</a></div><a class="publisher-link" href="{e(p.get('source_url',doiurl))}" target="_blank" rel="noopener noreferrer">確認に用いたページ：{e(p.get('source_label','出版社ページ'))} ↗</a></section>
    </article><aside class="article-toc"><div class="toc-inner"><p>ON THIS PAGE <span>↗</span></p><a href="#quick">00 / 先に要点</a><a href="#question">01 / 研究の問い</a><a href="#methods">02 / 方法</a><a href="#findings">03 / 主要な結果</a><a href="#limits">04 / 注意点</a><a href="#relevance">05 / 研究への応用</a><a href="#source">06 / 原著・出典</a><div class="toc-side-note">原著に戻れること。<br>自分の研究とつながること。<br>その両方を大切に。</div></div></aside></div>
    <section class="related-section"><div class="section-head"><div><p class="eyebrow">KEEP READING</p><h2>次に読みたい論文 <span class="section-annot">RELATED NOTES</span></h2></div></div><div class="papers-grid">{rel}</div></section></main>'''
    return shell(content,p['title'],'../',article=True)

def inverted_abstract(index):
    if not index: return ''
    size = max((max(v) for v in index.values() if v),default=-1)+1
    words = [''] * min(size,1000)
    for word,positions in index.items():
        for pos in positions:
            if 0 <= pos < len(words): words[pos]=word
    return ' '.join(words).strip()

def discover_openalex(existing):
    # Multiple precise streams; OpenAlex is metadata/abstract provider, not a fulltext provider.
    queries=['periphyton stream grazing flood', 'stream biofilm disturbance resilience', 'ayu algae grazing fish', 'stream periphyton nutrient flow velocity', 'river periphyton stable isotope']
    seen={p['doi'].lower() for p in existing}
    results=[]
    for q in queries:
        params={'search':q,'filter':'from_publication_date:2025-01-01,has_abstract:true,is_retracted:false,type:article','per_page':12,'sort':'publication_date:desc','select':'id,doi,title,publication_year,publication_date,authorships,abstract_inverted_index,cited_by_count,primary_location'}
        if os.getenv('OPENALEX_API_KEY'): params['api_key']=os.getenv('OPENALEX_API_KEY')
        url='https://api.openalex.org/works?'+urllib.parse.urlencode(params)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RIFFLE-Research-Radar/1.0 (literature discovery; mailto:research@example.org)'})
            with urllib.request.urlopen(req,timeout=20) as response:
                works=json.load(response).get('results',[])
        except Exception as exc:
            print('OpenAlex unavailable',str(exc),file=sys.stderr)
            continue
        for w in works:
            doi=(w.get('doi') or '').replace('https://doi.org/','')
            abstract=inverted_abstract(w.get('abstract_inverted_index'))
            title=w.get('title') or ''
            if not doi or doi.lower() in seen or len(abstract)<320 or len(title)<10: continue
            if w.get('publication_date','9999-12-31')>dt.datetime.now(TZ).date().isoformat():continue
            blob=(title+' '+abstract).lower()
            terms=['periphyton','biofilm','algal','algae','diatom','benthic']
            if not any(t in blob for t in terms):continue
            relevance=sum(2 for t in ['periphyton','stream','grazing','grazer','river','flow','flood','biofilm','nutrient','disturbance','resilience','ayu'] if t in blob)
            if relevance<6:continue
            w['_doi']=doi;w['_abstract']=abstract;w['_score']=relevance + min(6,w.get('cited_by_count',0)/10)
            results.append(w); seen.add(doi.lower())
    results.sort(key=lambda w:(w['_score'],w.get('publication_date','')),reverse=True)
    return results[:5]

def ai_summarize(w):
    # Strict input: the paper's abstract and its bibliographic metadata only.
    from openai import OpenAI
    client=OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    author=', '.join(x.get('author',{}).get('display_name','') for x in w.get('authorships',[])[:3]) or '著者情報未確認'
    venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name') or '掲載誌未確認'
    prompt=json.dumps({'title':w['title'],'authors':author,'year':w['publication_year'],'journal':venue,'doi':w['_doi'],'abstract':w['_abstract']},ensure_ascii=False)
    schema={'type':'object','properties':{k:{'type':'string'} for k in ['theme','takeaway','brief','novelty','question','methods']}|{k:{'type':'array','items':{'type':'string'}} for k in ['tags','results','limitations','research_links']},'required':['theme','takeaway','brief','novelty','question','methods','tags','results','limitations','research_links'],'additionalProperties':False}
    resp=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),instructions='You are a rigorous Japanese stream-ecology literature curator. Use only supplied English abstract and metadata. Return Japanese text. No invented quantitative effects, experimental methods, causal claims or full text details. If unclear say 抄録からは不明. Separate author results vs interpretive proposal. Research project context: Japanese Ayu grazing, spatial river gradients, nutrient ions, δ13C/δ15N, algal 3D biofilm, resistance to floods; no attributing site differences to Ayu as demonstrated causality. 2-3 succinct bullets per array, tags <=4. No Markdown. Output schema-compliant JSON.',input=prompt,text={'format':{'type':'json_schema','name':'paper_digest','schema':schema,'strict':True}},max_output_tokens=3000)
    data=json.loads(resp.output_text)
    for key in ['results','limitations','research_links']:
        if not data[key]: data[key]=['抄録だけでは詳細を確認できません。']
    return {**data,'id':re.sub('[^a-z0-9-]','-',w['_doi'].lower()).strip('-')[:90],'kind':'trend','title':w['title'],'authors':author,'year':w['publication_year'],'journal':venue,'doi':w['_doi'],'source_url':'https://doi.org/'+w['_doi'],'source_label':'OpenAlex収録書誌・著者要旨','read_minutes':7,'evidence':'OpenAlexの書誌情報と著者要旨に基づくAI生成要約（本文未照合）'}

def do_build(refresh=False, override_slot=None):
    curated=load_json(DATA/'curated.json',[])
    generated=load_json(DATA/'generated.json',[])
    history=load_json(DATA/'archive.json',{})
    today=dt.datetime.now(TZ).date()
    days=max(0,(today-START).days)
    classic=[p for p in curated if p['kind']=='classic']
    trend=[p for p in curated if p['kind']=='trend']
    assert classic and trend
    # Stable rotation with selected meaningful first entry on launch day.
    morning=classic[(days+1)%len(classic)]['id']
    evening=trend[days%len(trend)]['id']
    slot=override_slot or ('morning' if dt.datetime.now(TZ).hour<12 else 'evening')
    all_papers=curated+generated
    day_entry=history.setdefault(today.isoformat(),{'morning':morning,'evening':(evening if dt.datetime.now(TZ).hour>=18 or slot=='evening' else None)})
    day_entry.setdefault('morning',morning)
    if slot=='evening' and not day_entry.get('evening'):
        day_entry['evening']=evening
    if refresh and slot=='evening' and os.getenv('OPENAI_API_KEY'):
        for work in discover_openalex(all_papers):
            try:
                new_paper=ai_summarize(work)
                if new_paper['doi'] not in {p['doi'] for p in all_papers}:
                    generated.append(new_paper)
                    all_papers.append(new_paper)
                    day_entry['evening']=new_paper['id']
                    print('New discovery:',new_paper['title'])
                    break
            except Exception as exc:
                print('AI summary failed:',repr(exc),file=sys.stderr)
    elif refresh and slot=='evening' and not os.getenv('OPENAI_API_KEY'):
        print('No OPENAI_API_KEY: using verified curated recent paper.',file=sys.stderr)
    # Always publish curated papers even if a provider is down.
    save_json(DATA/'archive.json',history)
    save_json(DATA/'generated.json',generated)
    (DIST/'papers').mkdir(parents=True,exist_ok=True)
    (DIST/'assets').mkdir(parents=True,exist_ok=True)
    for asset in (ROOT/'assets').iterdir():
        if asset.is_file(): (DIST/'assets'/asset.name).write_bytes(asset.read_bytes())
    (DIST/'index.html').write_text(home(all_papers,today.isoformat(),day_entry,history),encoding='utf-8')
    for paper in all_papers:
        (DIST/'papers'/f'{paper["id"]}.html').write_text(paper_page(paper,all_papers),encoding='utf-8')
    (DIST/'.nojekyll').write_text('',encoding='utf-8')
    print(f'Built {len(all_papers)} pages: {today.isoformat()} morning={day_entry["morning"]} evening={day_entry["evening"]}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh',action='store_true',help='Find and summarize one new OpenAlex paper if OpenAI key is provided')
    parser.add_argument('--slot',choices=['morning','evening'])
    args=parser.parse_args()
    do_build(args.refresh,args.slot)
