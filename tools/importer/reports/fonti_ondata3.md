# Terza ondata: fonti alternative per il Centro-Sud (PROPOSTE, nessuna attivata)

Ricerca del 28/10/2026 (delegata a un subagente haiku, risultati ricontrollati da me su Puglia). Cortesia invariata: un solo accesso per host, robots.txt letto, User-Agent identificativo.

## 1. Portali regionali e comunali con eventi in licenza aperta

| fonte | licenza | aggiornamento | copertura | formato | esito |
|---|---|---|---|---|---|
| dati.puglia.it: "Eventi culturali ricorrenti" (Comune di Lecce) `/ckan/dataset/eventi-culturali-ricorrenti` | CC BY 4.0 (campo `license_id` CKAN) | 23/10/2026 | Lecce | JSON, CSV su dati.comune.lecce.it | licenza ok, **eventi futuri non verificati**, nessun dry-run (vedi sotto) |
| dati.puglia.it: "VisitLecce – Eventi, percorsi, POI…" `/ckan/dataset/visitlecce-eventi-percorsi-poi-coupon-prodotti` | CC BY 4.0 | 23/10/2026 | Lecce | JSON/CSV/XML su `services.visitlecce.eu/Data/Eventi.*` | **non utilizzabile**: il server risponde 403 al nostro User-Agent, anche per robots.txt (verificato il 28/10/2026 con 2 richieste). Non si aggira. |
| dati.puglia.it: "Eventi condivisi con la cittadinanza" (Lecce) | CC BY 4.0 | 23/10/2026 | Lecce | CSV/XLSX su link accorciati goo.gl | scartato: link accorciati, non stabili |
| dati.puglia.it: Melpignano, Montemesola, Teatro Comunale | CC BY 4.0 | 23–26/10/2026 | singoli comuni | CSV | troppo piccoli per un adapter; i comuni si coprono già con il sito comunale |
| dati.puglia.it: "Eventi in Puglia" 2016, 2020-21 | IODL 2.0 / CC BY 4.0 | 2023-24 | Puglia | CSV | **dati vecchi**, nessun evento futuro |
| dati.regione.sicilia.it: "Eventi" | CC BY 4.0 | 30/06/2022 | Sicilia | JSON/CSV | probabilmente fermo, non utile |

Nessun dataset di eventi trovato per **Lazio** (dati.lazio.it: 7 risultati per "eventi", nessuno di eventi), **Campania**, **Abruzzo**, **Molise**, **Calabria**, **Basilicata** (Matera 2019 Open Data Center: licenza non indicata → non usabile), **Sardegna** (il portale dati.sardegna.it non risolve). Per Campania e Abruzzo c'è solo un indizio del 2016 su licenze NC, non verificato e non usato. `dati.gov.it` ha risposto 404 all'endpoint CKAN `package_search`.

## 2. Fornitori di siti comunali al Sud

Dalla colonna `fornitore` dei CSV (comuni con adapter `design_comuni_html` o `wordpress-dci`): la grande maggioranza dei comuni del Sud usa gli stessi modelli già coperti (Design Comuni Italia su piattaforme ASP.NET/Maggioli/Halley/WordPress). Le ricerche non hanno trovato API o feed pubblici documentati per Maggioli, Halley o Dedagroup. Nessun nuovo adapter proposto: lo scraping HTML dei siti con note legali CC-BY resta l'unica via.

Fornitore con difetto nel robots.txt corretto in questa fase: i siti ASP.NET (es. Cirigliano, Oliveto Lucano, Rotondella e Stigliano in Basilicata) dichiarano `Sitemap: /SiteMap.aspx` con percorso relativo; il fetcher lo risolve ora sull'host. Prima 34 comuni lucani finivano in "errore imprevisto".

## 3. Dry-run di aggiunta (eventi aggiunti / duplicati con le fonti comunali)

Nessuna fonte aggregata ha licenza **e** accesso verificati con eventi futuri, quindi **non ho eseguito dry-run di aggregati e non ne propongo l'attivazione**. L'unico candidato plausibile è il dataset di Lecce (CC BY 4.0): Lecce oggi è "irraggiungibile" nel rilevamento (sito comunale con robots.txt non raggiungibile). Per valutarlo servono: (a) conferma che `dati.comune.lecce.it` consenta il download automatico (robots.txt e condizioni) e (b) presenza di eventi futuri. Prossimo passo suggerito: scrivere al Comune di Lecce per un feed consentito.
