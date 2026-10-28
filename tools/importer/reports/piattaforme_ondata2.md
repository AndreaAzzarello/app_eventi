# Piattaforme e portali della seconda ondata (Piemonte, Valle d'Aosta, Liguria, Friuli-Venezia Giulia, Trentino-Alto Adige, Marche, Umbria)

Analisi del 28/10/2026. Cortesia invariata: robots.txt, 1 richiesta al secondo per host, User-Agent identificativo, cache HTTP.

## 1. Piattaforme dei siti comunali (2.302 comuni)

CMS rilevato per regione (colonna `cms` dei CSV) e fornitore dei siti `design_comuni_html` (colonna `fornitore`):

| regione | design_comuni_html | wordpress-dci | plone | altro | irraggiungibile | fornitori principali |
|---|---|---|---|---|---|---|
| Piemonte | 789 | 1 | 0 | 80 | 307 | ComWeb 328, ASP.NET 266, WordPress 102, Maggioli 48 |
| Valle d'Aosta | 64 | 0 | 0 | 5 | 5 | WordPress 35, ComWeb 26 |
| Liguria | 134 | 0 | 1 | 85 | 13 | WordPress 49, ASP.NET 39, Maggioli 25, ISWEB 6 |
| Friuli-Venezia Giulia | 184 | 25 | 2 | 1 | 3 | non riconosciuto 172, Maggioli 10 |
| Trentino-Alto Adige | 266 | 0 | 0 | 13 | 1 | non riconosciuto 135, ASP.NET (RIS) 128 |
| Marche | 167 | 0 | 0 | 48 | 9 | Halley 73, WordPress 72, Maggioli 14 |
| Umbria | 45 | 0 | 0 | 41 | 6 | Halley 15, WordPress 15, Maggioli 8 |

Gli adapter esistenti (`design_comuni_html`, `wordpress-dci`, `plone`) coprono già la quasi totalità dei siti con una pagina eventi. Nessun nuovo adapter è stato scritto (vedi sotto).

**Piemonte, "irraggiungibile" 307**: molti timeout/connessioni rifiutate nel giro di rilevamento; sono righe `da_verificare` da ritentare (`detect_cms.py --force --regione piemonte`), non esclusioni.

## 2. Trentino: ComunWEB / Consorzio dei Comuni Trentini (Opencontent)

- Verificato su 3 comuni (Cles, Arco, Pergine Valsugana). L'endpoint `api/opendata/v2/content/search/` risponde ma la classe `evento` non esiste (errore 400 "Class evento not found"): le classi di contenuto cambiano da installazione a installazione.
- **Il robots.txt di tutti e tre dichiara `Disallow: /api/`** (e `/content/search`). L'API non è quindi utilizzabile dall'importer: **non è stato scritto nessun adapter API ComunWEB/OpenCity**. Condizioni d'uso dell'API: non trovate né sul sito né sul robots, nessuna autorizzazione esplicita al riuso.
- Trasparenza: prima di leggere il robots.txt di quei tre host ho inviato 1 richiesta ciascuno a `/api/opendata/...` (3 richieste in tutto, nessun'altra). Non ne farò altre senza un permesso esplicito del Consorzio.
- Strada percorribile: contattare il Consorzio dei Comuni Trentini per chiedere l'autorizzazione all'uso dell'API (o un feed eventi). Nel frattempo i comuni trentini hanno quasi tutti un sito `design_comuni_html` con licenza CC-BY 4.0 sui contenuti, ma **158 su 166 sono respinti dalla regola approvata** perché le note legali contengono anche "Tutti i diritti riservati" (riferito a loghi e marchi del Comune). Solo 1 comune trentino è attivo. Se consideri accettabile quella formula (CC-BY sui contenuti, diritti riservati solo su marchi e loghi), serve una tua decisione per affinare la regola; non l'ho cambiata.

## 3. OpenCity Italia / Opencontent e altri fornitori

Non esiste un'API comune consentita dai robots.txt dei siti verificati, quindi nessun adapter API riusabile da creare. Lo scraping HTML dei siti "Design Comuni" resta l'unico percorso condiviso (ComWeb, Maggioli, ASP.NET/RIS e Halley producono lo stesso markup).

## 4. Bilinguismo

- **Alto Adige** (116 comuni con alias tedesco/ladino) e **Valle d'Aosta**: `city` = nome ufficiale italiano (slug stabile: `bolzano`, `aosta`), alias in `cityAlt` (Bozen, Aoste) e in `coverage/{regione}.comuni[].alt`. Fonte: colonna ISTAT "Denominazione altra lingua", salvata in `comune_alt` nei CSV.
- Le grafie di Nominatim ("Bolzano - Bozen", "Bozen", "Aosta/Aoste") sono ricondotte al comune italiano (`run.use_italian_name`).
- Webapp: ricerca nell'elenco comuni su entrambi i nomi, titolo "Bolzano / Bozen", `/citta/bozen` e `/citta/bolzano-bozen` rispondono 301 a `/citta/bolzano`. Test Playwright su Bolzano/Bozen e Aosta/Aoste.
- Filtro anti-avvisi e categorie: tedesco (Gemeinderat, Sitzung, Kundmachung, Müll, Veranstaltung, Konzert, Ausstellung, Markt, Kinder…) e francese (conseil municipal, séance, avis, déchets, concert, exposition, marché…), con test.
- Nota: i siti della Valle d'Aosta analizzati pubblicano titoli e note legali in italiano; il francese è comunque supportato dal filtro.

## 5. Portali regionali di open data / turismo (proposta, NON attivati)

| regione | portale / dataset | licenza | copertura | stato verifica |
|---|---|---|---|---|
| Alto Adige | **Open Data Hub, API Events**: `https://tourism.opendatahub.com/v1/Event?active=true` (JSON, senza chiave) | **CC0 per singolo record** (campo `LicenseInfo.License`, `ClosedData: false`); verificato 28/10/2026 su un record | 51.623 eventi attivi restituiti (tutta la provincia, incl. passati e lontani); aggiornamento continuo | licenza verificata su un campione di 1 record, robots.txt dell'host: 404 (nessuna restrizione dichiarata) |
| Umbria | ODN Umbria, dataset "Eventi e manifestazioni in Umbria" `https://odn.regione.umbria.it/dataset/eventi` (CSV, JSON, RDF, SPARQL) | CC BY (attribuzione) | eventi del portale umbriatourism.it | pagina ferma al 2016: probabilmente non aggiornato, **sconsigliato** |
| Trentino | dati.trentino.it | non verificato | non verificato | nessun dataset eventi trovato |
| Piemonte | dati.piemonte.it | non verificato (solo "Banca Dati Eventi" ARPA, CC BY 4.0, non turistica) | n/d | nessun dataset eventi turistici |
| Valle d'Aosta | Lovevda | nessuna licenza di riuso indicata | n/d | non utilizzabile |
| Liguria | Regione Liguria open data / Visit Liguria | non verificato | n/d | nessun dataset eventi trovato |
| Friuli-Venezia Giulia | open data regionale / PromoTurismoFVG | non verificato | n/d | nessun feed eventi trovato |
| Marche | GoodPA / Marche tourism | non verificato | n/d | nessun dataset eventi trovato |

**Proposta**: usare solo l'Open Data Hub per l'Alto Adige, come fonte aggiuntiva (nuovo adapter `opendatahub`, API JSON, nessuno scraping). Condizioni suggerite: solo record con `ClosedData == false` e licenza CC0/CC-BY, eventi entro l'orizzonte di 60 giorni, deduplica con le fonti comunali (già presente in `run.dedupe_key`). Coprirebbe anche i comuni altoatesini senza sito scrapabile (oggi 83 su 116 attivi). Richiede la tua conferma; nulla è stato implementato né attivato. Umbria: non conviene, dataset fermo al 2016.
