# AO-online publicatie, testversie op Vercel

Statische publicatie van een AO-online handboek: een pagina per deelproces, activiteit en functie,
SIPOC-schema (en stappenweergave op mobiel) en zoeken in de browser. Bedoeld om samen verder te ontwikkelen en te testen.

## Mappen

| Pad | Wat |
| --- | --- |
| `build_site.py` | Generator: maakt `site/` uit `handboek.json` |
| `handboek.json` | Voorbeelddata (uit de uitdraai van het DEMO-handboek). In productie: export uit AO-online |
| `parse.py` | Zet een tekstuitdraai (`hb.txt`) om naar `handboek.json`. Alleen nodig voor deze voorbeelddata |
| `style.css`, `app.js` | Opmaak en zoekfunctie, worden door de generator naar `site/` gekopieerd |
| `vercel.json`, `robots.txt` | Vercel-instellingen: niet indexeren, beveiligingsheaders, geen caching van HTML/JSON |
| `site/` | Gegenereerde site, dit is wat Vercel publiceert |

## Opnieuw bouwen

```bash
python3 build_site.py
```

Python 3.10 of nieuwer, geen extra pakketten nodig. De map `site/` wordt telkens helemaal opnieuw gemaakt.

## Publiceren naar Vercel

Eenmalig: `npm i -g vercel` en `vercel login`.

```bash
python3 build_site.py
cd site
vercel            # testversie (preview-URL)
vercel --prod     # vaste URL van het project
```

Of via Git: zet deze map in een repository, koppel die in Vercel aan een project en stel in:
- Framework Preset: Other
- Root Directory: `site`
- Build Command: leeg laten

Commit dan ook de gegenereerde map `site/`, want Vercel bouwt hier niets.

## Toegang tijdens het testen

Zet in het Vercel-project onder Settings > Deployment Protection de optie
**Vercel Authentication** aan voor **All Deployments**. Dan kunnen alleen leden van het Vercel-team
de site openen. Gratis op elk abonnement.

## Bekende punten

- Zoeken gebruikt MiniSearch (via jsDelivr) met de index `search-index.json` (ca. 190 kB).
  Valt de CDN weg, dan zoekt een eenvoudige ingebouwde variant. Voor productie: Pagefind.
- Lettertypen komen van Google Fonts. Voor productie bij klanten: zelf hosten.
- De knop "Verbetering voorstellen" doet nog niets.
- Toegang voor klanten (IP-controle, e-mailcode, SSO) zit er nog niet in; dat wordt Routing Middleware.
