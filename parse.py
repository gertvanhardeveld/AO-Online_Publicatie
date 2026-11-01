"""Zet de tekstuitdraai van een AO-online handboek om naar gestructureerde JSON.
In productie komt deze data rechtstreeks uit de AO-online export (XML/database);
deze parser is alleen nodig om het prototype met echte voorbeelddata te vullen."""
import re, json, sys

lines = open('hb.txt', encoding='utf-8').read().split('\n')
# sla inhoudsopgave over
start = next(i for i, l in enumerate(lines) if l.replace('\f','').startswith('1. Processen') and i > 10)
lines = [re.sub(r'[\uf000-\uf8ff]', '', l.replace('\f', '')) for l in lines[start:]]
lines = [l for l in lines if not re.match(r'^\s*(AO-online DEMO|\d{1,2}-\d{1,2}-\d{4})\s*$', l)]

HEAD = re.compile(r'^\s*(\d+(?:\.\d+)*)\.\s+(Hoofdproces|Deelproces|Activiteit)\s+-\s+(.*?)\s*$')
KEYS = ['Doelstelling', 'Proceseigenaar', 'Type', 'Doorlooptijd', 'Onderdeel van (hoofd)proces',
        'Hulpmiddelen', 'Versie', 'Auteur', 'Status']
SECTIONS = ['WERKINSTRUCTIES', 'NORMEN', 'ROLLENMATRIX', 'ROLLEN', 'INPUTS EN OUTPUTS', 'DOCUMENTEN', 'PROCESSCHEMA', 'ROLLENMATRIX']
ROLMAP = {'Direct verantwoordelijk/uitvoerend': 'R', 'Eindverantwoordelijk': 'A', 'Ondersteunend': 'S',
          'Geconsulteerd': 'C', 'Geïnformeerd': 'I'}

blocks = []
cur = None
for l in lines:
    m = HEAD.match(l)
    if m and l.lstrip() == l.strip() and not l.startswith('    '):
        num, kind, rest = m.groups()
        sub = None
        for suf in [' - Processen details', ' - Processchema', ' - RACI/RASCI']:
            if rest.endswith(suf):
                sub = suf.strip(' -'); rest = rest[:-len(suf)]
        cur = {'num': num, 'kind': kind, 'name': rest.strip(), 'sub': sub, 'lines': []}
        blocks.append(cur)
    elif cur is not None:
        cur['lines'].append(l)

def cols(l):
    return [c.strip() for c in re.split(r'\s{2,}', l.strip()) if c.strip()]

def parse_block(b):
    d = {'kind': b['kind'], 'name': b['name'], 'num': b['num']}
    sec = None; buf = {}
    risks = []; measures = []; cur_r = None
    ls = b['lines']
    i = 0
    while i < len(ls):
        l = ls[i]; s = l.strip()
        if not s:
            i += 1; continue
        # risico's
        if s.startswith('Naam van risico'):
            cur_r = {'naam': s[len('Naam van risico'):].strip(), 'maatregelen': []}; risks.append(cur_r); sec = 'RISICO'; i += 1; continue
        if s.startswith('Naam beheersmaatregel'):
            cur_r = {'naam': s[len('Naam beheersmaatregel'):].strip()}; measures.append(cur_r); sec = 'MAATREGEL'; i += 1; continue
        if sec in ('RISICO', 'MAATREGEL') and (s.startswith('Proces borging') or re.match(r'^(' + '|'.join(re.escape(k) for k in KEYS) + r'):', s) or (s.upper() == s and any(s.startswith(x) for x in SECTIONS))):
            sec = None
        if sec in ('RISICO', 'MAATREGEL'):
            for k in ['Omschrijving van risico', 'Risico categorie', 'Impact', 'Waarschijnlijkheid', 'Beheersmaatregel',
                      'Behorend bij risico', 'Toestand', 'Δ Impact', 'Δ Waarschijnlijkheid', 'Verantwoordelijke']:
                if s.startswith('Δ') and not k.startswith('Δ'): continue
                if s.startswith(k + ' ') or s == k:
                    cur_r['_k'] = k; v = s[len(k):].strip()
                    if v: cur_r[k] = v
                    break
            else:
                k = cur_r.get('_k')
                if k == 'Beheersmaatregel' and sec == 'RISICO':
                    cur_r['maatregelen'].append(re.sub(r'^\d+\.\s*', '', s))
                elif k:
                    cur_r[k] = (cur_r.get(k, '') + ' ' + s).strip()
            i += 1; continue
        # sleutel: waarde
        km = re.match(r'^(' + '|'.join(re.escape(k) for k in KEYS) + r'):\s*(.*)$', s)
        if km:
            k, v = km.groups(); sec = None
            # vervolgregels (zonder lege regel ertussen)
            j = i + 1
            while k == 'Doelstelling' and j < len(ls) and ls[j].strip() and not re.match(r'^\s*\w[^:]{0,30}:', ls[j]):
                v += ' ' + ls[j].strip(); j += 1
            d[k] = v.strip(); i = j; continue
        hit = next((x for x in SECTIONS if s.startswith(x)), None)
        if hit and s.upper() == s:
            sec = hit; buf.setdefault(sec, []); i += 1; continue
        if sec:
            buf.setdefault(sec, []).append(l)
        i += 1
    # werkinstructies: paragrafen
    if 'WERKINSTRUCTIES' in buf:
        paras, p = [], []
        raw = b['lines']
        # opnieuw met lege regels om alinea's te behouden
        inside = False
        for l in raw:
            s = l.strip()
            if s == 'WERKINSTRUCTIES': inside = True; continue
            if inside:
                if (s.upper() == s and any(s.startswith(x) for x in SECTIONS)) or re.match(r'^(' + '|'.join(re.escape(k) for k in KEYS) + r'):', s) or s.startswith('Naam van risico'):
                    break
                if not s:
                    if p: paras.append(' '.join(p)); p = []
                else:
                    p.append(s)
        if p: paras.append(' '.join(p))
        d['werkinstructie'] = paras
    def table(rows, header_word):
        out = []
        for l in rows:
            c = cols(l)
            if not c or c[0] == header_word or c[0] in ('Totaal',) or (len(c) == 2 and c[0] == 'Totaal'): continue
            out.append(c)
        return out
    if 'NORMEN' in buf:
        d['normen'] = [{'type': c[0], 'indicator': c[1] if len(c) > 1 else '', 'target': c[2] if len(c) > 2 else ''}
                       for c in table(buf['NORMEN'], 'Normtype')]
    if 'ROLLEN' in buf:
        rr = []
        for c in table(buf['ROLLEN'], 'Rol'):
            if c[0] in ROLMAP and len(c) > 1:
                rr.append({'rol': ROLMAP[c[0]], 'rolnaam': c[0], 'functie': c[1],
                           'frequentie': next((x for x in c[2:] if x in ('Dagelijks', 'Wekelijks', 'Maandelijks', 'Jaarlijks', 'Per kwartaal', 'Incidenteel', 'Per keer')), '')})
        d['rollen'] = rr
    if 'INPUTS EN OUTPUTS' in buf:
        io = []
        for c in table(buf['INPUTS EN OUTPUTS'], 'Label'):
            if len(c) >= 3 and c[1] in ('Input', 'Output'):
                io.append({'label': c[0], 'richting': c[1], 'intern': c[2] == 'Intern',
                           'waar': c[3] if len(c) > 3 else '', 'communicatie': c[4] if len(c) > 4 else ''})
        d['io'] = io
    if 'DOCUMENTEN' in buf:
        docs = []
        for c in table(buf['DOCUMENTEN'], 'Document naam'):
            if re.search(r'\.\w{2,4}$', c[0]):
                docs.append({'naam': c[0], 'bij': c[1] if len(c) > 1 and not c[1].endswith('kb') else '',
                             'type': c[2] if len(c) > 3 else ''})
        d['documenten'] = docs
    if 'ROLLENMATRIX' in buf:
        order = []
        for l in buf['ROLLENMATRIX']:
            m = re.match(r'^\s*(\S.*?)\s{2,}([RASCI](?:,[RASCI])*)(\s+[RASCI](?:,[RASCI])*)*\s*$', l)
            if m: order.append(m.group(1).strip())
        d['volgorde'] = order
    if risks: d['risicos'] = [{k: v for k, v in r.items() if k != '_k'} for r in risks]
    if measures: d['maatregelen'] = [{k: v for k, v in r.items() if k != '_k'} for r in measures]
    return d

hoofd, deel, act = [], [], []
last_deel = None
for b in blocks:
    d = parse_block(b)
    if b['kind'] == 'Hoofdproces':
        hoofd.append(d)
    elif b['kind'] == 'Deelproces':
        if b['sub'] == 'RACI/RASCI':
            if last_deel and d.get('volgorde'): last_deel['volgorde'] = d['volgorde']
        elif b['sub'] is None:
            deel.append(d); last_deel = d
    elif b['kind'] == 'Activiteit':
        act.append(d)

# risico's: koppel maatregelen
for a in act:
    ms = {m['naam']: m for m in a.pop('maatregelen', [])}
    for r in a.get('risicos', []):
        r['maatregelen'] = [ms.get(n, {'naam': n}) for n in r['maatregelen']]

data = {'hoofdprocessen': hoofd, 'deelprocessen': deel, 'activiteiten': act}
json.dump(data, open('handboek.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(hoofd), len(deel), len(act))
print(sum(1 for a in act if a.get('werkinstructie')), 'met werkinstructie')
print(sum(1 for d in deel if d.get('volgorde')), 'deelprocessen met volgorde')
