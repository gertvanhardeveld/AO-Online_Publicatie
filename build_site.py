"""Generator voor de statische publicatie van een AO-online handboek.
Invoer: handboek.json (in productie: de export van gepubliceerde content).
Uitvoer: map site/ met HTML per deelproces, activiteit en functie, plus een zoekindex."""
import json, re, html, os, shutil, unicodedata, textwrap, sys

# Gebruik: python3 build_site.py            -> volledige HTML-pagina's (Vercel, eigen server)
#          python3 build_site.py --artifact -> startpagina zonder eigen <html>-skelet (Claude-artifact)
ARTIFACT = '--artifact' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'handboek.json'), encoding='utf-8'))
OUT = os.path.join(HERE, 'site')
shutil.rmtree(OUT, ignore_errors=True)
for sub in ('p', 'a', 'f'):
    os.makedirs(f'{OUT}/{sub}', exist_ok=True)

VERSIE = 'v12'
DATUM = '31 oktober 2026'
ORG = 'AO-online DEMO'
e = lambda s: html.escape(str(s or ''), quote=True)


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]


def clean(s):
    return (s or '').strip()

# ---------- model opbouwen ----------
hoofd = D['hoofdprocessen']
for i, h in enumerate(hoofd, 1):
    h['idx'] = i
    h['id'] = 'h-' + slug(h['name'])
    h['deel'] = []

deel_by_key = {}
for d in D['deelprocessen']:
    parts = d['num'].split('.')
    d['hidx'] = int(parts[2]); d['didx'] = int(parts[3]) if len(parts) > 3 else 0
    d['code'] = f"{d['hidx']}.{d['didx']}" + (('.' + '.'.join(parts[4:])) if len(parts) > 4 else '')
    d['path'] = f"p/{d['code'].replace('.', '-')}-{slug(d['name'])}.html"
    d['acts'] = []
    d['parent'] = clean(d.get('Onderdeel van (hoofd)proces'))
    h = hoofd[d['hidx'] - 1]
    d['hoofd'] = h
    h['deel'].append(d)
    if len(parts) <= 4:
        deel_by_key[(d['hidx'], d['didx'])] = d

for a in D['activiteiten']:
    p = [int(x) for x in a['num'].split('.')]
    a['code'] = a['num'][2:]  # 6.1.1
    d = deel_by_key.get((p[1], p[2]))
    a['deel'] = d
    a['path'] = f"a/{a['code'].replace('.', '-')}-{slug(a['name'])}.html"
    a['name'] = clean(a['name'])
    d['acts'].append(a)

# volgorde: rollenmatrix uit het handboek, anders nummering
for d in D['deelprocessen']:
    order = d.get('volgorde') or []
    pos = {n: i for i, n in enumerate(order)}
    d['acts'].sort(key=lambda a: (pos.get(a['name'], 999), a['num']))

act_by_name = {}
for a in D['activiteiten']:
    act_by_name.setdefault(a['name'].lower(), a)
deel_by_name = {d['name'].lower(): d for d in D['deelprocessen']}

functies = {}
for a in D['activiteiten']:
    for r in a.get('rollen', []):
        f = functies.setdefault(r['functie'], {'name': r['functie'], 'path': f"f/{slug(r['functie'])}.html", 'rollen': {}})
        f['rollen'].setdefault(r['rol'], []).append(a)
for d in D['deelprocessen']:
    eig = clean(d.get('Proceseigenaar'))
    if eig:
        f = functies.setdefault(eig, {'name': eig, 'path': f"f/{slug(eig)}.html", 'rollen': {}})
        f.setdefault('eigenaar', []).append(d)

ROL = {'R': 'Uitvoerend', 'A': 'Eindverantwoordelijk', 'S': 'Ondersteunend', 'C': 'Geconsulteerd', 'I': 'Geïnformeerd'}
ROLLANG = {'R': 'Taken (uitvoerend)', 'A': 'Eindverantwoordelijk voor', 'S': 'Ondersteunt bij', 'C': 'Wordt geconsulteerd bij', 'I': 'Wordt geïnformeerd over'}


def link_target(name):
    n = (name or '').strip().lower()
    if n in act_by_name: return act_by_name[n]['path'], 'activiteit'
    if n in deel_by_name: return deel_by_name[n]['path'], 'deelproces'
    return None, None

# ---------- gedeelde HTML ----------
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">'
MINISEARCH = '<script src="https://cdn.jsdelivr.net/npm/minisearch@6.3.0/dist/umd/index.min.js"></script>'


def page(title, body, root, full=True, crumbs=None):
    head = f'''<title>{e(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
{FONTS}
<link rel="stylesheet" href="{root}style.css">'''
    crumb = ''
    if crumbs:
        crumb = '<nav class="crumbs" aria-label="Kruimelpad">' + ' <span aria-hidden="true">›</span> '.join(
            f'<a href="{root}{p}">{e(t)}</a>' if p is not None else f'<span>{e(t)}</span>' for t, p in crumbs) + '</nav>'
    header = f'''<div class="proto-band"><div class="wrap">Prototype statische publicatie · voorbeelddata uit het handboek {ORG}</div></div>
<header class="top"><div class="wrap top-in">
  <a class="brand" href="{root}index.html"><span class="brand-mark" aria-hidden="true">AO</span><span><strong>Kwaliteitshandboek</strong><small>{ORG}</small></span></a>
  <div class="search" role="search">
    <label class="sr" for="q">Zoek in het handboek</label>
    <input id="q" type="search" autocomplete="off" placeholder="Zoek processen, werkinstructies, functies…">
    <div class="results" id="results" hidden></div>
  </div>
</div></header>'''
    footer = f'''<footer class="foot"><div class="wrap foot-in">
  <span>Publicatie {VERSIE} · vastgesteld op {DATUM} · alleen goedgekeurde processen</span>
  <span>Gegenereerd door AO-online · statische pagina's, geen toegang tot de applicatie</span>
</div></footer>
{MINISEARCH}
<script>window.ROOT = "{root}";</script>
<script src="{root}app.js"></script>'''
    inner = f'{head}\n{header}\n<main class="wrap main">{crumb}{body}</main>\n{footer}'
    if not full:
        return inner
    return f'<!doctype html>\n<html lang="nl">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n{head}\n</head>\n<body>\n{header}\n<main class="wrap main">{crumb}{body}</main>\n{footer}\n</body>\n</html>'


def chip(rol):
    return f'<span class="raci raci-{rol}" title="{e(ROL[rol])}">{rol}</span>'


def wrap_text(s, width):
    return textwrap.wrap(s, width=width, break_long_words=True) or ['']

# ---------- SIPOC-schema als SVG ----------
CW = {'s': 150, 'i': 150, 'p': 232, 'o': 150, 'c': 150}
GAP = 34
X = {}
x = 8
for k in 'sipoc':
    X[k] = x; x += CW[k] + GAP
SVG_W = x - GAP + 8


def svg_textblock(lines, cx, cy, cls, lh=15):
    y0 = cy - (len(lines) - 1) * lh / 2
    return ''.join(f'<text class="{cls}" x="{cx}" y="{y0 + i * lh:.1f}" text-anchor="middle" dominant-baseline="middle">{e(t)}</text>' for i, t in enumerate(lines))


def sipoc_svg(d, root):
    acts = d['acts']
    out = []
    y = 46
    ITEM_H, ITEM_GAP, ROW_GAP = 46, 10, 34
    prev_bottom = None
    for a in acts:
        ins = [i for i in a.get('io', []) if i['richting'] == 'Input']
        outs = [i for i in a.get('io', []) if i['richting'] == 'Output']
        n = max(len(ins), len(outs), 1)
        row_h = max(n * ITEM_H + (n - 1) * ITEM_GAP, 64)
        cy = y + row_h / 2
        # activiteit
        r = next((r['functie'] for r in a.get('rollen', []) if r['rol'] == 'R'), '')
        ah = max(row_h if n > 1 else 64, 64)
        ay = cy - ah / 2
        if prev_bottom is not None:
            mx = X['p'] + CW['p'] / 2
            out.append(f'<line class="flow" x1="{mx}" y1="{prev_bottom}" x2="{mx}" y2="{ay - 3}" marker-end="url(#arr)"/>')
        name_lines = wrap_text(a['name'], 28)[:3]
        out.append(f'<a href="{root}{a["path"]}" class="act-link"><rect class="act" x="{X["p"]}" y="{ay}" width="{CW["p"]}" height="{ah}" rx="6"/>')
        tl = name_lines + ([r] if r else [])
        y0 = cy - (len(tl) - 1) * 15 / 2
        for i, t in enumerate(tl):
            cls = 'act-sub' if (r and i == len(tl) - 1) else 'act-t'
            out.append(f'<text class="{cls}" x="{X["p"] + CW["p"] / 2}" y="{y0 + i * 15:.1f}" text-anchor="middle" dominant-baseline="middle">{e(t)}</text>')
        out.append(f'<text class="act-num" x="{X["p"] + 8}" y="{ay + 12}">{e(a["code"])}</text></a>')
        prev_bottom = ay + ah

        def items(lst, kl, kr, side):
            tot = len(lst) * ITEM_H + (len(lst) - 1) * ITEM_GAP
            yy = cy - tot / 2
            for it in lst:
                ext = '' if it['intern'] else ' ext'
                iy = yy
                icy = iy + ITEM_H / 2
                # label (input/output)
                out.append(f'<rect class="io{ext}" x="{X[kl]}" y="{iy}" width="{CW[kl]}" height="{ITEM_H}" rx="4"/>')
                ll = wrap_text(it['label'], 20)[:2]
                if it.get('communicatie'):
                    # twee regels label plus communicatieregel: label hoger en compacter, zodat niets overlapt
                    two = len(ll) > 1
                    out.append(svg_textblock(ll, X[kl] + CW[kl] / 2, icy - (8 if two else 5), 'io-t', lh=13 if two else 15))
                    out.append(f'<text class="io-sub" x="{X[kl] + CW[kl] / 2}" y="{icy + (16 if two else 13)}" text-anchor="middle">{e(wrap_text(it["communicatie"], 24)[0])}</text>')
                else:
                    out.append(svg_textblock(ll, X[kl] + CW[kl] / 2, icy, 'io-t'))
                # herkomst / bestemming
                tgt, _ = link_target(it['waar'])
                box = f'<rect class="party{ext}" x="{X[kr]}" y="{iy}" width="{CW[kr]}" height="{ITEM_H}" rx="{ITEM_H / 2 if not it["intern"] else 4}"/>' + svg_textblock(wrap_text(it['waar'] or '—', 20)[:2], X[kr] + CW[kr] / 2, icy, 'party-t')
                out.append(f'<a href="{root}{tgt}" class="act-link">{box}</a>' if tgt else box)
                # pijlen
                if side == 'in':
                    out.append(f'<line class="flow" x1="{X["s"] + CW["s"]}" y1="{icy}" x2="{X["i"] - 3}" y2="{icy}" marker-end="url(#arr)"/>')
                    out.append(f'<line class="flow" x1="{X["i"] + CW["i"]}" y1="{icy}" x2="{X["p"] - 3}" y2="{cy}" marker-end="url(#arr)"/>')
                else:
                    out.append(f'<line class="flow" x1="{X["p"] + CW["p"]}" y1="{cy}" x2="{X["o"] - 3}" y2="{icy}" marker-end="url(#arr)"/>')
                    out.append(f'<line class="flow" x1="{X["o"] + CW["o"]}" y1="{icy}" x2="{X["c"] - 3}" y2="{icy}" marker-end="url(#arr)"/>')
                yy += ITEM_H + ITEM_GAP
        items(ins, 'i', 's', 'in')
        items(outs, 'o', 'c', 'out')
        y += row_h + ROW_GAP
    H = y - ROW_GAP + 12
    heads = ''.join(f'<text class="col-h" x="{X[k] + CW[k] / 2}" y="18" text-anchor="middle">{t}</text>' for k, t in zip('sipoc', ['HERKOMST', 'INPUT', 'ACTIVITEIT', 'OUTPUT', 'BESTEMMING']))
    guides = ''.join(f'<rect class="lane" x="{X[k] - GAP / 2 + 2}" y="30" width="{CW[k] + GAP - 4}" height="{H - 30}" rx="6"/>' for k in 'p')
    return (f'<svg class="sipoc" viewBox="0 0 {SVG_W} {H}" width="{SVG_W}" role="img" aria-label="Processchema {e(d["name"])} in vijf kolommen">'
            f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrhead"/></marker></defs>'
            f'{guides}{heads}{"".join(out)}</svg>')


def sipoc_steps(d, root):
    """Zelfde SIPOC-gegevens als verticale stappenlijst: leesbaar op een smal scherm."""
    def io_html(it, richting):
        tgt, _ = link_target(it['waar'])
        waar = e(it['waar'] or 'onbekend')
        if tgt: waar = f'<a href="{root}{tgt}">{waar}</a>'
        ext = '' if it['intern'] else ' ext'
        voor = 'Van' if richting == 'in' else 'Naar'
        return (f'<div class="vio{ext}"><span class="vwho">{voor} {waar}'
                f'{"" if it["intern"] else " <span class=vext>extern</span>"}</span>'
                f'<strong>{e(it["label"])}</strong>'
                f'{"<small>" + e(it["communicatie"]) + "</small>" if it.get("communicatie") else ""}</div>')
    li = ''
    for a in d['acts']:
        ins = [i for i in a.get('io', []) if i['richting'] == 'Input']
        outs = [i for i in a.get('io', []) if i['richting'] == 'Output']
        r = next((r['functie'] for r in a.get('rollen', []) if r['rol'] == 'R'), '')
        li += '<li class="vstep">'
        if ins: li += '<div class="vgroup vin">' + ''.join(io_html(i, 'in') for i in ins) + '</div>'
        li += (f'<a class="vact" href="{root}{a["path"]}"><span class="code">{e(a["code"])}</span>'
               f'<strong>{e(a["name"])}</strong>{"<small>" + e(r) + "</small>" if r else ""}</a>')
        if outs: li += '<div class="vgroup vout">' + ''.join(io_html(o, 'out') for o in outs) + '</div>'
        li += '</li>'
    return f'<ol class="vflow" aria-label="Processchema {e(d["name"])} als stappen">{li}</ol>'


# ---------- pagina's ----------
search_docs = []


def snippet(*parts, n=180):
    s = ' '.join(p for p in parts if p)
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def normen_table(normen):
    if not normen: return ''
    rows = ''.join(f'<tr><td><span class="ntype">{e(n["type"])}</span></td><td>{e(n["indicator"])}</td><td class="num">{e(n["target"])}</td></tr>' for n in normen)
    return f'<div class="tbl"><table><thead><tr><th>Type</th><th>Indicator of normparagraaf</th><th>Norm</th></tr></thead><tbody>{rows}</tbody></table></div>'


def docs_list(docs, root):
    if not docs: return ''
    li = ''.join(f'<li><span class="doc-ico" aria-hidden="true">{e(dd["naam"].rsplit(".", 1)[-1].upper())}</span><span><span class="doc-n">{e(dd["naam"])}</span>{"<small>" + e(dd["type"]) + "</small>" if dd.get("type") else ""}</span></li>' for dd in docs)
    return f'<ul class="docs">{li}</ul>'


def improve_box(owner):
    return f'''<section class="improve">
  <div><h3>Klopt dit niet meer?</h3><p>Stel een verbetering voor. Uw voorstel gaat naar de proceseigenaar{", " + e(owner) if owner else ""}.</p></div>
  <button type="button" class="btn" data-improve>Verbetering voorstellen</button>
  <p class="improve-note" hidden>In de echte publicatie opent hier het verbeterformulier van AO-online. U logt dan in met uw eigen werkaccount; deze pagina zelf heeft geen toegang tot de applicatie.</p>
</section>'''


# deelproces-pagina's
for d in D['deelprocessen']:
    root = '../'
    h = d['hoofd']
    owner = clean(d.get('Proceseigenaar'))
    meta = []
    if owner:
        fo = functies.get(owner)
        meta.append(('Proceseigenaar', f'<a href="{root}{fo["path"]}">{e(owner)}</a>' if fo else e(owner)))
    meta.append(('Hoofdproces', f'<a href="{root}index.html#{h["id"]}">{e(h["name"])}</a>'))
    if d['parent'] and d['parent'] != h['name']:
        pd = deel_by_name.get(d['parent'].lower())
        meta.append(('Onderdeel van', f'<a href="{root}{pd["path"]}">{e(d["parent"])}</a>' if pd else e(d['parent'])))
    meta.append(('Versie', f'{e(d.get("Versie", "–"))} · {e(d.get("Status", ""))}'))
    meta_html = ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in meta)
    subs = [x for x in D['deelprocessen'] if x['parent'].lower() == d['name'].lower()]
    body = f'''<header class="phead">
  <p class="eyebrow"><span class="code">{e(d["code"])}</span> Deelproces · {e(h["name"])}</p>
  <h1>{e(d["name"])}</h1>
  {f'<p class="lead">{e(d.get("Doelstelling"))}</p>' if d.get("Doelstelling") else ''}
  <dl class="meta">{meta_html}</dl>
</header>'''
    if subs:
        body += '<section class="sec"><h2>Subprocessen</h2><ul class="steps">' + ''.join(f'<li><a href="{root}{s["path"]}"><span class="code">{e(s["code"])}</span>{e(s["name"])}</a></li>' for s in subs) + '</ul></section>'
    if d['acts']:
        body += f'''<section class="sec flowsec"><div class="sec-h"><h2>Processchema</h2>
  <div class="viewsw" role="group" aria-label="Weergave processchema"><button type="button" data-view="schema" aria-pressed="false">Schema</button><button type="button" data-view="stappen" aria-pressed="false">Stappen</button></div></div>
  <ul class="legend"><li><span class="lg lg-int"></span>Intern</li><li><span class="lg lg-ext"></span>Extern</li><li><span class="lg lg-act"></span>Activiteit, met uitvoerende functie</li></ul>
  <figure class="schema">{sipoc_svg(d, root)}</figure>
  {sipoc_steps(d, root)}
  <p class="hint">Klik op een activiteit voor de werkinstructie.</p></section>'''
        # rollenmatrix
        fns = []
        for a in d['acts']:
            for r in a.get('rollen', []):
                if r['functie'] not in fns: fns.append(r['functie'])
        if fns:
            th = ''.join(f'<th class="vh"><span><a href="{root}{functies[f]["path"]}">{e(f)}</a></span></th>' for f in fns)
            rows = ''
            for a in d['acts']:
                cells = ''
                for f in fns:
                    rs = [r['rol'] for r in a.get('rollen', []) if r['functie'] == f]
                    rs = sorted(set(rs), key='RASCI'.index)
                    cells += '<td class="c">' + ''.join(chip(r) for r in rs) + '</td>'
                rows += f'<tr><th scope="row"><a href="{root}{a["path"]}">{e(a["name"])}</a></th>{cells}</tr>'
            body += f'''<section class="sec"><div class="sec-h"><h2>Rollenmatrix</h2>
  <ul class="legend">{"".join(f"<li>{chip(k)}{v}</li>" for k, v in ROL.items())}</ul></div>
  <div class="tbl"><table class="matrix"><thead><tr><th></th>{th}</tr></thead><tbody>{rows}</tbody></table></div></section>'''
        body += '<section class="sec"><h2>Activiteiten</h2><ol class="steps">' + ''.join(
            f'<li><a href="{root}{a["path"]}"><span class="code">{e(a["code"])}</span><span><strong>{e(a["name"])}</strong>{"<small>" + e(snippet(a.get("Doelstelling") or " ".join(a.get("werkinstructie", [])), n=110)) + "</small>" if (a.get("Doelstelling") or a.get("werkinstructie")) else ""}</span></a></li>' for a in d['acts']) + '</ol></section>'
    if d.get('normen'):
        body += f'<section class="sec"><h2>Normen en prestatie-indicatoren</h2>{normen_table(d["normen"])}</section>'
    if d.get('documenten'):
        body += f'<section class="sec"><h2>Documenten</h2>{docs_list(d["documenten"], root)}</section>'
    body += improve_box(owner)
    open(f'{OUT}/{d["path"]}', 'w', encoding='utf-8').write(page(f'{d["name"]} · Kwaliteitshandboek', body, root, crumbs=[('Handboek', 'index.html'), (h['name'], f'index.html#{h["id"]}'), (d['name'], None)]))
    search_docs.append({'id': d['path'], 'type': 'Proces', 'title': d['name'], 'path': d['path'], 'hoofd': h['name'],
                        'context': f'{h["name"]} · {len(d["acts"])} activiteiten', 'text': ' '.join([d.get('Doelstelling', ''), owner] + [a['name'] for a in d['acts']]),
                        'snippet': snippet(d.get('Doelstelling', '')), 'functies': owner, 'normen': ' '.join(n['indicator'] for n in d.get('normen', []))})

# activiteit-pagina's
for a in D['activiteiten']:
    root = '../'
    d = a['deel']; h = d['hoofd']
    acts = d['acts']; i = acts.index(a)
    prev_a = acts[i - 1] if i > 0 else None
    next_a = acts[i + 1] if i < len(acts) - 1 else None
    owner = clean(d.get('Proceseigenaar'))
    wi = a.get('werkinstructie', [])
    body = f'''<header class="phead">
  <p class="eyebrow"><span class="code">{e(a["code"])}</span> Activiteit {i + 1} van {len(acts)} · <a href="{root}{d["path"]}">{e(d["name"])}</a></p>
  <h1>{e(a["name"])}</h1>
  {f'<p class="lead">{e(a.get("Doelstelling"))}</p>' if clean(a.get("Doelstelling")) else ''}
</header>
<div class="cols">
<div class="col-main">
<section class="sec wi"><h2>Werkinstructie</h2>
  {"".join(f"<p>{e(p)}</p>" for p in wi) if wi else '<p class="empty">Voor deze activiteit is geen werkinstructie vastgelegd.</p>'}
</section>'''
    io = a.get('io', [])
    if io:
        rows = ''
        for it in io:
            tgt, _ = link_target(it['waar'])
            waar = f'<a href="{root}{tgt}">{e(it["waar"])}</a>' if tgt else e(it['waar'])
            rows += f'<tr><td><span class="dir dir-{it["richting"].lower()}">{e(it["richting"])}</span></td><td><strong>{e(it["label"])}</strong></td><td>{"Van" if it["richting"] == "Input" else "Naar"} {waar} <span class="tag{"" if it["intern"] else " tag-ext"}">{"intern" if it["intern"] else "extern"}</span></td><td>{e(it["communicatie"])}</td></tr>'
        body += f'<section class="sec"><h2>Input en output</h2><div class="tbl"><table><thead><tr><th>Richting</th><th>Wat</th><th>Herkomst of bestemming</th><th>Via</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    for r in a.get('risicos', []):
        ms = ''.join(f'''<li><strong>{e(m["naam"])}</strong>{"<p>" + e(m.get("Beheersmaatregel")) + "</p>" if m.get("Beheersmaatregel") else ""}{"<small>Verantwoordelijk: " + e(m.get("Verantwoordelijke")) + "</small>" if m.get("Verantwoordelijke") else ""}</li>''' for m in r.get('maatregelen', []))
        imp, kans = r.get('Impact', '?'), r.get('Waarschijnlijkheid', '?')
        body += f'''<section class="sec risk"><h2>Risico en beheersmaatregelen</h2>
  <div class="risk-h"><div><h3>{e(r["naam"])}</h3><p>{e(r.get("Omschrijving van risico"))}</p></div>
  <dl class="score"><div><dt>Impact</dt><dd>{e(imp)}<small>/5</small></dd></div><div><dt>Kans</dt><dd>{e(kans)}<small>/5</small></dd></div><div><dt>Categorie</dt><dd class="cat">{e(r.get("Risico categorie"))}</dd></div></dl></div>
  <ul class="measures">{ms}</ul></section>'''
    body += '</div><aside class="col-side">'
    if a.get('rollen'):
        rl = ''.join(f'<li>{chip(r["rol"])}<span><a href="{root}{functies[r["functie"]]["path"]}">{e(r["functie"])}</a><small>{e(ROL[r["rol"]])}{" · " + e(r["frequentie"].lower()) if r["frequentie"] else ""}</small></span></li>' for r in sorted(a['rollen'], key=lambda r: 'RASCI'.index(r['rol'])))
        body += f'<section class="side"><h2>Wie doet wat</h2><ul class="roles">{rl}</ul></section>'
    facts = []
    if clean(a.get('Hulpmiddelen')): facts.append(('Hulpmiddelen', e(a['Hulpmiddelen'])))
    dl = clean(a.get('Doorlooptijd'))
    if dl and not dl.startswith('0') and dl != 'uur': facts.append(('Doorlooptijd', e(dl)))
    if facts:
        body += '<section class="side"><dl class="facts">' + ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in facts) + '</dl></section>'
    if a.get('normen'):
        nl = ''.join(f'<li><span class="ntype">{e(n["type"])}</span><span>{e(n["indicator"])}{"<small>Norm: " + e(n["target"]) + "</small>" if n["target"] else ""}</span></li>' for n in a['normen'])
        body += f'<section class="side"><h2>Normen</h2><ul class="nlist">{nl}</ul></section>'
    if a.get('documenten'):
        body += f'<section class="side"><h2>Documenten</h2>{docs_list(a["documenten"], root)}</section>'
    CUR = ' aria-current="step"'
    st = ''.join(f'<li{CUR if x is a else ""}><a href="{root}{x["path"]}"><span class="code">{e(x["code"])}</span>{e(x["name"])}</a></li>' for x in acts)
    body += f'<section class="side"><h2>In dit proces</h2><ol class="mini">{st}</ol></section></aside></div>'
    nav = '<nav class="pn" aria-label="Vorige en volgende activiteit">'
    nav += f'<a href="{root}{prev_a["path"]}" class="pn-prev"><small>Vorige stap</small>{e(prev_a["name"])}</a>' if prev_a else '<span></span>'
    nav += f'<a href="{root}{next_a["path"]}" class="pn-next"><small>Volgende stap</small>{e(next_a["name"])}</a>' if next_a else '<span></span>'
    nav += '</nav>'
    body += nav + improve_box(owner)
    open(f'{OUT}/{a["path"]}', 'w', encoding='utf-8').write(page(f'{a["name"]} · Kwaliteitshandboek', body, root, crumbs=[('Handboek', 'index.html'), (h['name'], f'index.html#{h["id"]}'), (d['name'], d['path']), (a['name'], None)]))
    search_docs.append({'id': a['path'], 'type': 'Werkinstructie' if wi else 'Activiteit', 'title': a['name'], 'path': a['path'], 'hoofd': h['name'],
                        'context': f'{h["name"]} › {d["name"]}',
                        'text': ' '.join([a.get('Doelstelling', '') or ''] + wi + [x['label'] + ' ' + x['waar'] for x in io] + [a.get('Hulpmiddelen', '') or ''] + [r['naam'] + ' ' + (r.get('Omschrijving van risico') or '') for r in a.get('risicos', [])]),
                        'snippet': snippet(' '.join(wi) or a.get('Doelstelling', '')),
                        'functies': ' '.join(r['functie'] for r in a.get('rollen', [])),
                        'normen': ' '.join(n['type'] + ' ' + n['indicator'] for n in a.get('normen', []))})

# functie-pagina's
for f in functies.values():
    root = '../'
    body = f'''<header class="phead"><p class="eyebrow">Functie</p><h1>{e(f["name"])}</h1>
<p class="lead">Alle procesgerelateerde taken en verantwoordelijkheden van deze functie, afgeleid uit de rollen in de processen.</p></header>'''
    if f.get('eigenaar'):
        body += '<section class="sec"><h2>Proceseigenaar van</h2><ul class="steps">' + ''.join(f'<li><a href="{root}{d["path"]}"><span class="code">{e(d["code"])}</span><span><strong>{e(d["name"])}</strong><small>{e(d["hoofd"]["name"])}</small></span></a></li>' for d in f['eigenaar']) + '</ul></section>'
    for k in 'RASCI':
        lst = f['rollen'].get(k)
        if not lst: continue
        body += f'<section class="sec"><h2>{chip(k)} {ROLLANG[k]}</h2><ul class="steps">' + ''.join(f'<li><a href="{root}{a["path"]}"><span class="code">{e(a["code"])}</span><span><strong>{e(a["name"])}</strong><small>{e(a["deel"]["name"])}</small></span></a></li>' for a in lst) + '</ul></section>'
    open(f'{OUT}/{f["path"]}', 'w', encoding='utf-8').write(page(f'{f["name"]} · Kwaliteitshandboek', body, root, crumbs=[('Handboek', 'index.html'), ('Functies', 'index.html#functies'), (f['name'], None)]))
    n_taken = len(f['rollen'].get('R', []))
    search_docs.append({'id': f['path'], 'type': 'Functie', 'title': f['name'], 'path': f['path'], 'hoofd': '',
                        'context': f'{n_taken} uitvoerende taken' + (f' · eigenaar van {len(f["eigenaar"])} processen' if f.get('eigenaar') else ''),
                        'text': ' '.join(a['name'] for v in f['rollen'].values() for a in v), 'snippet': '', 'functies': f['name'], 'normen': ''})

# ---------- startpagina ----------
TYPES = [('Primair', 'Primaire processen', 'Leveren rechtstreeks het product of de dienst aan de klant.'),
         ('Ondersteunend', 'Ondersteunende processen', 'Zorgen voor mensen, middelen, informatie en geld.'),
         ('Besturend', 'Besturende processen', 'Plannen, coördineren en bewaken de andere processen.')]
groups = ''
for t, label, uitleg in TYPES:
    hs = [h for h in hoofd if clean(h.get('Type')) == t]
    if not hs: continue
    cards = ''
    for h in hs:
        dl = ''.join(f'<li><a href="{d["path"]}"><span class="code">{e(d["code"])}</span>{e(d["name"])}<span class="cnt">{len(d["acts"]) or ""}</span></a></li>' for d in h['deel'] if d['parent'] == h['name'])
        cards += f'''<article class="hcard" id="{h["id"]}"><h3><span class="code">{h["idx"]}</span>{e(h["name"])}</h3>
  {f'<p>{e(h.get("Doelstelling"))}</p>' if clean(h.get("Doelstelling")) else ''}
  <ul class="dlist">{dl}</ul></article>'''
    groups += f'<section class="tgroup"><div class="tg-h"><h2>{label}</h2><p>{uitleg}</p></div><div class="hgrid">{cards}</div></section>'

fl = ''.join(f'<li><a href="{f["path"]}">{e(f["name"])}<span class="cnt">{sum(len(v) for v in f["rollen"].values())}</span></a></li>' for f in sorted(functies.values(), key=lambda f: f['name'].lower()))
n_wi = sum(1 for a in D['activiteiten'] if a.get('werkinstructie'))
types_opt = ''.join(f'<option value="{e(h["name"])}">{e(h["name"])}</option>' for h in hoofd)
index_body = f'''<section class="hero">
  <div class="hero-t">
    <p class="eyebrow">{ORG} · publicatie {VERSIE}</p>
    <h1>Hoe werken wij?</h1>
    <p class="lead">Zoek een werkinstructie of blader door de processen. Dit handboek bevat {len(D["deelprocessen"])} processen, {len(D["activiteiten"])} activiteiten en {n_wi} werkinstructies, zoals vastgesteld op {DATUM}.</p>
  </div>
  <div class="bigsearch">
    <label for="bq">Waar ben je naar op zoek?</label>
    <div class="bq-row"><input id="bq" type="search" autocomplete="off" placeholder="Bijvoorbeeld: offerte, uren, klacht, factuur"></div>
    <div class="filters" role="group" aria-label="Filter op soort">
      <button type="button" class="fchip" aria-pressed="true" data-type="">Alles</button>
      <button type="button" class="fchip" aria-pressed="false" data-type="Werkinstructie">Werkinstructies</button>
      <button type="button" class="fchip" aria-pressed="false" data-type="Proces">Processen</button>
      <button type="button" class="fchip" aria-pressed="false" data-type="Functie">Functies</button>
      <label class="sr" for="fh">Hoofdproces</label>
      <select id="fh"><option value="">Alle hoofdprocessen</option>{types_opt}</select>
    </div>
    <p class="try">Probeer: <button type="button" class="link" data-try="offerte">offerte</button> <button type="button" class="link" data-try="calculatie">calculatie</button> <button type="button" class="link" data-try="uren">uren</button> <button type="button" class="link" data-try="9001">ISO 9001</button> <button type="button" class="link" data-try="hoofd calculatie">hoofd calculatie</button></p>
  </div>
</section>
<section class="bigresults" id="bigresults" hidden aria-live="polite"></section>
<div id="landscape">
{groups}
<section class="tgroup" id="functies"><div class="tg-h"><h2>Functies</h2><p>Per functie de taken en verantwoordelijkheden uit alle processen.</p></div><ul class="flist">{fl}</ul></section>
</div>
<section class="about">
  <h2>Over deze publicatie</h2>
  <div class="about-g">
    <div><h3>Los van de applicatie</h3><p>Deze site bestaat uit vaste pagina's die AO-online bij publiceren genereert. Er is geen database en geen inlog naar AO-online achter. Wie hier binnenkomt, kan alleen lezen.</p></div>
    <div><h3>Alleen vastgestelde inhoud</h3><p>Alleen processen met de status Goedgekeurd worden gepubliceerd. Concepten, opmerkingen en namen van auteurs blijven in de applicatie.</p></div>
    <div><h3>Zoeken zonder server</h3><p>Zoeken gebeurt in de browser met een kleine index van <span id="idxsize">enkele</span> kB. In productie splitst de index zich in stukjes, zodat ook grote handboeken snel blijven.</p></div>
  </div>
</section>'''
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(page('Kwaliteitshandboek Publicatie', index_body, '', full=not ARTIFACT))
with open(os.path.join(OUT, 'robots.txt'), 'w') as fh:
    fh.write('User-agent: *\nDisallow: /\n')
if not ARTIFACT:
    # vercel.json in de hoofdmap verwijst naar site/; in site/ zelf alleen de headers,
    # zodat het project werkt met Root Directory leeg of op 'site'.
    vc = json.load(open(os.path.join(HERE, 'vercel.json'), encoding='utf-8'))
    for k in ('framework', 'installCommand', 'buildCommand', 'outputDirectory'):
        vc.pop(k, None)
    with open(os.path.join(OUT, 'vercel.json'), 'w', encoding='utf-8') as fh:
        json.dump(vc, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
for asset in ('style.css', 'app.js'):
    shutil.copy(os.path.join(HERE, asset), os.path.join(OUT, asset))

json.dump(search_docs, open(f'{OUT}/search-index.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('pagina\'s:', sum(len(fs) for _, _, fs in os.walk(OUT)), 'index kB:', os.path.getsize(f'{OUT}/search-index.json') // 1024)
