# Terza ondata: copertura, licenze, geocoding e quote (Italia intera)

Dry-run completo del 28/10/2026 sulle sole 9 regioni nuove (nessuna scrittura su Firestore). Le 11 regioni già attive non sono state rielaborate. Registro costruito da ISTAT/IndicePA: 2.929 comuni, conteggi uguali a quelli ISTAT per ogni regione.

## Copertura per regione

| regione | comuni | attivi | da verificare | esclusi | eventi (dry-run) | esclusi dal filtro |
|---|---|---|---|---|---|---|
| Lazio | 378 | 19 | 290 | 69 | 57 | 7 |
| Abruzzo | 305 | 10 | 219 | 76 | 14 | 0 |
| Molise | 136 | 2 | 66 | 68 | 2 | 0 |
| Campania | 550 | 13 | 349 | 188 | 30 | 3 |
| Puglia | 257 | 9 | 203 | 45 | 14 | 1 |
| Basilicata | 131 | 6 | 105 | 20 | 8 | 0 |
| Calabria | 404 | 10 | 329 | 65 | 30 | 2 |
| Sicilia | 391 | 19 | 292 | 80 | 42 | 9 |
| Sardegna | 377 | 27 | 334 | 16 | 63 | 8 |
| **Totale** | **2.929** | **115** | **2.187** | **627** | **260** | **30** |

Comuni attivi a zero eventi nel dry-run (9): Arzachena, Bacoli, Catania, Comiso, Corato, Frazzanò, Godrano, Greccio, Monserrato. Nessun comune con errori di rete.

### Motivi principali dei "da verificare" (2.187)

| motivo | comuni |
|---|---|
| nessun evento futuro valido (fuori stagione o sito che non pubblica) | 1.586 |
| nessun adapter: CMS "altro" o sito irraggiungibile | 344 |
| pagina eventi non trovata | 97 |
| clausola restrittiva sui contenuti (diritti riservati non riferiti solo a loghi) | 81 |
| licenza dei contenuti non verificata o non aperta | 61 |
| coordinate fuori provincia o non trovate | 10 |
| fonte non raggiungibile / errore imprevisto | 8 |

I 1.586 senza eventi sono quasi tutti in licenza CC-BY e con adapter: li riprende il ricontrollo settimanale della domenica sera (`recheck-sources.yml`) quando compaiono eventi. Il tasso di attivazione (3,9%) è più basso delle ondate precedenti: fine ottobre, bassa stagione e molti siti del Sud pubblicano pochi eventi.

### Esclusi dal filtro (30)

Pagine riassuntive (12), sedute di consiglio (7), edizioni passate (7, nuova regola: titolo con un anno precedente a quello dell'evento, es. "Natale 2023"), avvisi (4).

## Correzioni emerse dal dry-run

- **Sitemap relativa nel robots.txt** (`Sitemap: /SiteMap.aspx`): risolta sull'host, 34 comuni lucani non finiscono più in errore (poi tutti "nessun evento futuro").
- **Date inesistenti nel testo libero** ("0 gennaio", "31 aprile"): prima facevano cadere la fonte (Cefalù), ora si saltano.
- **Province sarde**: ISTAT e IndicePA usano sigle diverse dopo la riforma; 155 comuni su 377 risultavano senza sito. Ora la provincia non entra nella chiave per la Sardegna e il registro ha 377/377 siti.
- **`build_registry`** non cancella più un `comune_alt` inserito a mano.
- Resta un errore: Supersano (risposta non JSON dall'API WordPress), lasciato "da verificare".

## Frasi di licenza (5 comuni attivi, regioni diverse)

1. **Anzio (Lazio)**, https://www.comune.anzio.roma.it/note-legali: «…ai sensi dell'articolo 52 del decreto legislativo 7 marzo 2005, n. 82 (CAD) e salvo dove diversamente specificato (compresi i contenuti incorporati di terzi), i dati, i documenti e le informazioni pubblicati sul sito sono rilasciati con https://creativecommons.org/licenses/by/4.0/legalcode.it licenza CC-BY 4.0.»
2. **Ostuni (Puglia)**, https://www.comune.ostuni.br.it/note-legali/: «In applicazione del principio open by default ai sensi dell'articolo 52 del decreto legislativo 7 marzo 2005, n. 82 (CAD)… i dati, i documenti e le informazioni pubblicati sul sito sono rilasciati con licenza CC-BY 4.0.»
3. **Villafranca Tirrena (Sicilia)**, https://www.comune.villafrancatirrena.me.it/note-legali/: stessa formula CAD, «…rilasciati con https://creativecommons.org/licenses/by/4.0/legalcode.it licenza CC-BY 4.0.»
4. **Oristano (Sardegna)**, https://comune.oristano.it/it/service/note-legali/: stessa formula CAD, «…rilasciati con …/by/4.0/legalcode.it licenza CC-BY 4.0.»
5. **Sellia Marina (Calabria)**, https://comune.selliamarina.cz.it/note-legali: «…i dati, i documenti e le informazioni pubblicati sul sito sono rilasciati con https://creativecommons.org/licenses/by/4.0/legalcode.it licenza CC-BY 4.0.»

Sono quasi identiche perché derivano dal modello nazionale Design Comuni Italia. Le prime parole di alcune frasi sono tagliate dall'estrazione automatica del contesto (la frase attesta comunque CC-BY 4.0 sui contenuti).

## Sardegna: nomi bilingui

Nessun nome alternativo è stato inserito. La ricerca non ha trovato un atto ufficiale (statuto, delibera, decreto) letto nel testo per nessun comune: Alghero ha un indizio nello statuto del 1991 (art. 9, tutela del catalano) ma non il testo con "L'Alguer"; Carloforte e Calasetta (tabarchino) e Sassari (Tàtari) risultano solo d'uso. Il sistema è pronto: basta scrivere il nome in `comune_alt` nella riga del comune in `sources/sardegna.csv` (city resta in italiano, l'alias va in `cityAlt`, ricerca e 301 funzionano come per Bolzano/Bozen) e ora `build_registry` non lo cancella. Servono le fonti ufficiali: statuto di Alghero (PDF su comune.alghero.ss.it) e delibere dei comuni tabarchini.

## Geocoding

288 richieste di indirizzo da fare (centri dei comuni già in cache). Con il budget di 3.000 a giro il primo import completo richiede **1 giro**, circa 20 minuti con l'intervallo di 4 s per job (4 job in parallelo = 1 richiesta al secondo in tutto). Anche a regime (×4 eventi) ne basterebbe 1. Il messaggio "288 giorni" del dry-run è un artefatto del budget a 0.

## Scaglionamento e simulazione delle quote (Italia intera, 20 regioni)

Ogni regione si riconcilia con Firestore in un giorno fisso (`ci_report.reconcile_days`, bilanciato per fonti attive); il budget di letture per job è proporzionale al peso, ×7 nel giorno di riconciliazione. Ipotesi: ricambio 7% al giorno, pulizia ~eventi/60 al giorno, eventi per regione dal dry-run (nuove) e dall'ultimo import (4 regioni della prima ondata) e dal dry-run della seconda; Trentino-Alto Adige stimato a 2.495 eventi per tornare ai ~5.400 totali (Open Data Hub, valore da verificare). Quote Spark: 50.000 / 20.000 / 20.000.

**A – oggi (20 regioni, ~5.660 eventi)**

| giorno | letture | scritture | cancellazioni | quota peggiore | riconciliano |
|---|---|---|---|---|---|
| lunedì | 1.922 | 458 | 94 | 4% | lombardia |
| martedì | 861 | 458 | 94 | 2% | veneto |
| mercoledì | 861 | 458 | 94 | 2% | piemonte |
| giovedì | 3.044 | 458 | 94 | 6% | abruzzo, molise, trentino-alto-adige |
| venerdì | 1.070 | 458 | 94 | 2% | emilia-romagna, friuli-venezia-giulia, liguria, puglia |
| sabato | 819 | 458 | 94 | 2% | calabria, sicilia, toscana, valle-d-aosta |
| domenica | 814 | 458 | 94 | 2% | basilicata, campania, lazio, marche, sardegna, umbria |

**B – a regime (nuove ×3 fonti ×4 eventi, ~6.440 eventi)**: letture 929–3.244, scritture 513, cancellazioni 107 al giorno; quota peggiore 6% (giovedì).

**C – estremo (tutti i 7.900 comuni attivi, ~31.600 eventi)**: letture 6.703–8.791 (giorno peggiore lunedì, 18% della quota), scritture 2.273, cancellazioni 527 al giorno; ~42.000 letture sempre libere per gli utenti. Nessun giorno supera l'80% di una quota in nessuno scenario.

Durata: modello 3 min + 0,15 min per fonte (calibrato su Lombardia: 255 fonti, ~40 min). Scenario A: tutti i job entro ~50 min con 4 in parallelo; scenario C: Lombardia sola ~230 min, workflow intero ~5 ore (timeout per job alzato a 330 min, limite GitHub 360).

## Limiti GitHub Actions con 20 job

- Repository pubblico: minuti dei runner standard gratuiti; 20 job concorrenti sul piano Free (usiamo `max-parallel: 4`); 256 job massimi per matrice (ne servono 20); 6 ore per job.
- Cache: oggi 14 voci, 0–10 MB per regione e ~0,6 GB in tutto (le voci `importer-<regione>-<run>` pesano poco perché si salvano solo risposte con ETag). Anche con 20 regioni e 7 giorni di storia restano ben sotto i 10 GB; GitHub elimina da sé le voci non usate da 7 giorni e le più vecchie oltre il limite. Le chiavi sono già per regione, nessuna pulizia manuale necessaria.
