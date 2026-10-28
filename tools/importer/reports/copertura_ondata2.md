# Seconda ondata: copertura, licenze, geocoding e quote

Dry-run completo del 28/10/2026 sulle sole 7 regioni nuove (nessuna scrittura su Firestore). Le 4 regioni della prima ondata non sono state toccate: 532 fonti attive prima e dopo.

## Copertura per regione

| regione | comuni | attivi | da verificare | esclusi | eventi (dry-run) | esclusi dal filtro |
|---|---|---|---|---|---|---|
| Piemonte | 1.180 | 108 | 946 | 126 | 328 | 5 |
| Valle d'Aosta | 74 | 12 | 62 | 0 | 29 | 0 |
| Liguria | 234 | 16 | 140 | 78 | 36 | 2 |
| Friuli-Venezia Giulia | 215 | 12 | 203 | 0 | 36 | 0 |
| Trentino-Alto Adige | 282 | 84 (Alto Adige 83, Trentino 1) | 197 | 1 | 329 | 0 |
| Marche | 225 | 25 | 160 | 40 | 84 | 2 |
| Umbria | 92 | 10 | 44 | 38 | 39 | 0 |
| **Totale** | **2.302** | **267** | **1.752** | **283** | **881** | **9** |

Comuni attivi a zero eventi nel dry-run: Oviglio, Sarzana; con errore di rete: La Spezia, Castions di Strada.

Esclusi dal filtro (9): sedute di consiglio (2, Marche), pagine riassuntive (4), titolo generico (1), avvisi (2). Falso positivo da segnalare: "Lo sciopero delle bambine" (Piemonte, San Giorgio Canavese) è escluso come avviso per la parola "sciopero", ma è uno spettacolo.

### Motivi principali dei "da verificare" (2.019 valutati dall'attivazione)

| motivo | comuni |
|---|---|
| nessun evento futuro valido nel dry-run | 592 |
| clausola restrittiva sui contenuti ("Tutti i diritti riservati" / esclusiva proprietà) | 368 (Trentino 158, Piemonte 187, Marche 8, Valle d'Aosta 7, altre 8) |
| nessun adapter: sito "irraggiungibile" (timeout nel rilevamento, da ritentare) | 345 (Piemonte 307) |
| pagina eventi non trovata | 295 (Friuli-Venezia Giulia 169: la home non ha link a una sezione eventi) |
| licenza dei contenuti non aperta o non chiara | 159 |
| nessun adapter per il CMS (altro / non rilevato) | 71 |

**Decisione per te**: le 368 "clausole restrittive" sono in gran parte la formula ricorrente "…sono rilasciati con licenza CC-BY 4.0" seguita, in altro punto delle note legali, da "Tutti i diritti riservati" riferito a loghi, marchi e segni distintivi del Comune (verificato a mano su Bolzano). Con la regola approvata restano `da_verificare`. Se accetti la formula, si può affinare la regola e riattivare ~360 comuni (Trentino quasi interamente); non l'ho fatto.

## Frasi di licenza riconosciute

**Tedesco** (3 frasi reali dalle note legali dei comuni altoatesini, Impressum; riconosciute come CC-BY-4.0 sui contenuti):

1. Aldino: «…(CAD) und sofern nicht anders angegeben (einschließlich den Inhalten eingebettet von Dritten), werden die auf dieser Website veröffentlichten Daten, Dokumente und Informationen unter der https://creativecommons.org/licenses/by/4.0/legalcode.it Lizenz CC-BY 4.0 ausgegeben.»
2. Brixen/Bressanone: «…und sofern nicht anders angegeben (einschließlich eingebetteter Inhalte Dritter), werden die auf dieser Website veröffentlichten Daten, Dokumente und Informationen unter der Lizenz CC BY 4.0 bereitgestellt.»
3. Welsberg-Taisten/Monguelfo-Tesido: stessa formula, «…unter der …/by/4.0/legalcode.it Lizenz CC-BY 4.0 ausgegeben.»

Altre formule riconosciute (test automatici, non trovate nel campione reale): «Alle Inhalte dieser Website stehen unter der Lizenz Creative Commons Namensnennung 4.0 International» → CC-BY-4.0; «Creative Commons Namensnennung - Nicht kommerziell 4.0» → CC-BY-NC (respinta); «Alle Rechte vorbehalten» → riservata (respinta).

**Francese**: i siti valdostani analizzati pubblicano le note legali in italiano (stessa formula CAD/CC-BY 4.0 dei comuni italiani, es. Aosta: «…i dati, i documenti e le informazioni pubblicati sul sito sono rilasciati con licenza CC-BY 4.0.»). Non ho quindi frasi francesi reali da mostrare. Le formule francesi sono riconosciute e coperte da test, ma sono esempi scritti da me, non frasi lette sui siti:

1. «Les contenus de ce site sont publiés sous licence Creative Commons Attribution 4.0 International.» → CC-BY-4.0
2. «Réutilisation des données autorisée selon la licence CC BY 4.0.» → CC-BY-4.0
3. «Creative Commons Attribution - Pas d'utilisation commerciale 4.0» → CC-BY-NC (respinta)
4. «Tous droits réservés. Toute reproduction des contenus est interdite.» → riservata (respinta)
5. «Données ouvertes de la commune : licence CC0.» → CC0

Anche i riconoscimenti «Namensnennung»/«Attribution» con varianti NC/ND/SA (inglesi incluse) respingono la licenza; un trattino non riconosciuto dopo «Attribution» non vale mai CC-BY semplice.

## Geocoding

Dry-run con budget a 0: **762 richieste di indirizzo da fare**. Centri dei comuni già in cache (calcolati durante l'attivazione). Con il budget di 3.000 richieste a giro il primo import completo di tutte e 7 le regioni richiede **1 giro (al massimo 2)**, circa 25-30 minuti con l'intervallo di 2 s del workflow. Il messaggio "762 giorni" del dry-run è un artefatto del budget a 0.

## Quote a regime

Ipotesi: eventi all'orizzonte 60 giorni, ricambio ~7% al giorno (nuovi o modificati), dopo il primo import.

- **Manifest**: letture quotidiane per regione = 1 (`importState`) + n. eventi manuali (min. 1) + nuovi eventi (get_all). Riconciliazione completa (manifest assente o > 7 giorni, o `--reconcile`) = tutti gli eventi della regione.
- **Prima ondata + seconda ondata oggi** (~3.800 eventi, 11 regioni): letture ~0,5-1k/giorno, scritture ~0,4k/giorno.
- **Italia a regime, scenario realistico** (tasso di attivazione 12-20% come finora: ~1.600 comuni, ~8.700 eventi): letture ~1k/giorno (importer) + ~1,2k/giorno di riconciliazione media, picco ~10k se tutte le regioni si riconciliassero lo stesso giorno; scritture ~0,7k/giorno; cancellazioni ~0,6k/giorno.
- **Scenario estremo** (tutti i 7.900 comuni con ~4 eventi: ~31.600 eventi): letture ~3,3k/giorno, riconciliazione fino a ~35k in un solo giorno se non scaglionata; scritture ~2,3k/giorno; cancellazioni ~2,3k/giorno.
- **Senza manifest** (come prima): ~8,7k letture/giorno nello scenario realistico, ~31,6k nell'estremo, solo per l'importer.
- **Margini rispetto a Spark** (50.000 letture, 20.000 scritture, 20.000 cancellazioni): scritture e cancellazioni hanno margine ampio in entrambi gli scenari (≥ 85%). Le letture, scenario realistico: ~38-47k disponibili per gli utenti, cioè ~5.400-6.700 aperture della home non in cache al giorno (7 letture) oppure ~12-15k pagine città (3 letture), molte di più grazie alla cache all'edge (`s-maxage`).
- **Rischio**: il budget per job della matrice è 40.000/n. regioni; con ~20 regioni sono 2.000 letture per job, sufficiente nello scenario realistico, ma nell'estremo una regione grande farebbe scattare `QuotaExceeded` (fallimento sicuro, nessuna scrittura). Da scaglionare le riconciliazioni quando si passa a tutta l'Italia.

Primo import della seconda ondata: ~900 scritture (881 eventi, 7 coverage, 14 `importState`) e ~900 letture (riconciliazione).
