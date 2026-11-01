# AO-online publicatie

Statische, alleen-lezen publicatie van een AO-online kwaliteitshandboek voor "kijkers" (medewerkers die
processen en werkinstructies raadplegen). Team: Gert van Hardeveld, Mathijs Gaalman (techniek), Joost van Haren.
Nu: prototype om samen verder te ontwikkelen en te testen op Vercel.

## Waarom dit bestaat
- Klanten deelden één kijkersaccount (bijv. verkoop@bedrijfx.nl). Onveilig, werkt niet met MFA, en via gelekte
  accounts is in de applicatie rondgeklikt op zoek naar zwakke plekken.
- Oplossing: beheerders werken in de AO-online-applicatie (persoonlijk account + MFA of SSO). Kijkers krijgen een
  statische site die bij publiceren wordt gegenereerd. Daar zit geen database, geen applicatielogica en geen
  inlog naar AO-online achter.
- Toegang voor klanten komt in drie routes: (1) SSO voor grotere klanten, (2) persoonlijk account met MFA plus
  vaste IP-adressen, (3) statische publicatie, afgeschermd met IP-controle, e-mailcode of SSO. Gedeelde accounts
  worden uitgesloten.

## Ontwerpkeuzes (vasthouden)
- Alleen content met status Goedgekeurd wordt gepubliceerd. Geen concepten, opmerkingen, chatberichten of
  namen van auteurs; toon functies, geen personen.
- Elke pagina is vooraf gegenereerde HTML; zoeken gebeurt in de browser op een zoekindex.
- Processchema in SIPOC (5 kolommen: herkomst, input, activiteit, output, bestemming) als SVG. Op schermen
  smaller dan 760px een verticale stappenweergave uit dezelfde data, met schakelaar Schema/Stappen.
- Volgorde van activiteiten: volgorde uit de rollenmatrix, anders de nummering.
- Elke publicatie krijgt een versie; in productie ook een PDF-momentopname voor audits.

## Structuur
- `build_site.py`: generator, leest `handboek.json`, schrijft `site/` (wordt telkens opnieuw gemaakt).
  Pagina's: `p/` deelprocessen, `a/` activiteiten, `f/` functies, `index.html`, `search-index.json`.
- `handboek.json`: voorbeelddata uit het DEMO-handboek (via `parse.py` uit een tekstuitdraai `hb.txt`).
  In productie komt deze data uit de AO-online-export (XML/database).
- `style.css`, `app.js`: opmaak (tokens, licht en donker) en zoeken (MiniSearch via jsDelivr, met eenvoudige
  terugvaloptie) plus schakelaar schemaweergave. Houd `app.js` ASCII (gebruik \u-escapes).
- `vercel.json`, `robots.txt`: niet indexeren, beveiligingsheaders, geen caching van HTML/JSON.

## Commando's
- Bouwen: `python3 build_site.py` (Python 3.10+, geen pakketten). `--artifact` alleen voor een Claude-artifact.
- Lokaal bekijken: `cd site && python3 -m http.server 8000`
- Publiceren: `cd site && vercel` (preview) of `vercel --prod`. In Vercel: Root Directory `site`, geen build.
- Toegang tijdens testen: Vercel Authentication aan voor All Deployments (alleen teamleden).

## Volgende stappen
1. Generator laten lezen uit de echte AO-online-export in plaats van `handboek.json`.
2. Zoeken naar Pagefind (index in stukjes, Nederlandse stemming).
3. Lettertypen zelf hosten (nu Google Fonts).
4. Knop "Verbetering voorstellen" koppelen aan het verbeterformulier in AO-online (proceseigenaar).
5. Bijlagen (Word/PDF bij werkinstructies) mee publiceren achter hetzelfde slot.
6. Toegang voor klanten via Vercel Routing Middleware: IP-controle per klant, e-mailcode, later SSO (Entra/Google).
   Let op: Vercel Password Protection en Vercel Authentication zijn niet geschikt voor klantmedewerkers.
7. PDF-momentopname per publicatie.
8. Navragen bij grote klanten (overheid, zorg) of hosting bij een Amerikaanse partij akkoord is; alternatief EU-hosting.

## Schrijfstijl
Alle tekst in de interface is Nederlands, kort en actief. Geen gedachtestreepjes voor tussenzinnen; gebruik komma's.
