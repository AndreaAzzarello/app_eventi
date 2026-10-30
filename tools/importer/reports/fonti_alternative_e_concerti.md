# Fonti alternative per i comuni bloccati da robots.txt e concerti con link d'acquisto

Data: 2026-10-30. Fase di sola ricerca: nessuna fonte attivata, nessun import, nessuna iscrizione.
Metodo: ricerca web e lettura di termini/robots (agenti Haiku), un dry-run leggero (Sonnet), valutazione mia.
Tutto ciò che non è stato letto alla fonte è marcato **non verificato**.

## Parte A – Comuni esclusi per robots.txt

Esclusi con `robots_ok=no` nei registri: Lombardia 413 (~405 con `server: HGATE`), Campania 184, Abruzzo 73, Sicilia 72, Liguria 69, Lazio 68, Molise 68, Calabria 51, Marche 38, Umbria 38, Piemonte 34, Puglia 34, Emilia-Romagna 24, Toscana 23, Basilicata 19, Sardegna 7, Veneto 3, Trentino-AA 1.

### A1. Fornitore dietro "HGATE"
**Non identificato.** Circa 10 ricerche: nessuna fonte collega "HGATE" a un fornitore o a un prodotto. Il robots.txt di comune.arzago.bg.it (letto) contiene solo `Disallow: /`, una whitelist di bot con `Crawl-delay: 600` e il commento "allow only important bots": nessun nome né contatto. Nessun indirizzo trovato, quindi nessuno inventato.
Azione consigliata: scrivere al **titolare del sito** (Comune, ufficio CED/URP), che sa chi gestisce l'hosting; la mail è in `docs/contatti/email_comune_robots.md`. Il robots.txt è probabilmente una regola di hosting/WAF uguale per tutti i clienti, quindi la risposta di un solo Comune può sbloccare l'intero gruppo.

### A2. Fonti aperte alternative

| Fonte | Formato | Licenza (verificata?) | Robots | Aggiornamento | Copertura | Eventi futuri | Esito |
|---|---|---|---|---|---|---|---|
| Umbria ODN "Eventi e manifestazioni" (odn.regione.umbria.it/dataset/eventi-e-manifestazioni) | CSV/JSON, no API | CC-BY, versione non indicata (verificata sulla pagina) | `Crawl-Delay: 10`, download consentito | Ultimo evento 2023-03-04, dataset fermo al 2023-02-02 | 199 stringhe-comune, 32 comuni esclusi coperti (Assisi, Norcia, Cascia, Bevagna…) | **0** (1 record anomalo al 2029) | **Scartata**: dati stantii, nessuna immagine/prezzo/url, CSV non UTF-8, comune senza ISTAT |
| Lombardia dati.lombardia.it (36 dataset "eventi") | Socrata API/CSV | CC0 per la maggior parte (metadati); Villa Monastero CC-BY 4.0; uno senza licenza | `Crawl-delay: 1` | Letti 2 dataset su 36: dati 2017-2018 | Un dataset per singolo comune/unione, non regionale | **0** nei 2 letti | **Scartata** come agenda; schema ricco solo in alcuni (campo `istat`, prezzo, coordinate) |
| Lombardia "In Lombardia" eventi.regione.lombardia.it | non verificato (API/feed?) | **non verificata** | `Allow: /` (letto) | non verificato | Regionale (potenzialmente tutti i 413) | non verificato | **Da indagare**: unica pista regionale lombarda |
| Lazio dati.lazio.it | CKAN | solo un catalogo buone pratiche (CC-BY 4.0 da snippet) | `Crawl-Delay: 10`, `/api/` vietata | – | – | – | Nessun dataset eventi |
| Campania dati.campania.it | – | – | dominio non raggiungibile | – | – | – | Non verificato; contatto citato da fonti, non confermato |
| Sicilia, Liguria | – | – | – | – | – | – | Nessuna fonte aperta machine-readable trovata |
| Abruzzo opendata.regione.abruzzo.it | – | CC-BY-NC secondo fonte del 2016 (non riverificata) | – | – | – | – | Scartata se NC è ancora valida |
| Milano CAM (DS1689), Rimini | CSV | CC-BY 4.0 (snippet) | – | Rimini 2017 | Comuni non esclusi | – | Non rilevanti per i bloccati |
| Pro Loco / UNPLI iCal | iCal | nessuna licenza esplicita | – | – | – | – | Non utilizzabili senza permesso scritto |

Dry-run: script in `scratchpad/f.py` e `scratchpad/an_um.py` (1 richiesta CSV Umbria, 1 query catalogo Socrata, 2 dataset Lombardia); nessuna scrittura.

**Conclusione A**: gli open data regionali esistenti **non** colmano i 1.340 comuni. Le strade reali sono (1) sbloccare il robots.txt via titolari/fornitore, (2) indagare il portale regionale "In Lombardia", (3) per le altre regioni, richieste dirette agli enti (Regione Campania: open data; enti turistici).

## Parte B – Concerti e grandi eventi con link d'acquisto

### B1. Canali ufficiali

| Canale | Gratis | P.IVA/carta | Approvazione | Italia | Campi | Obblighi / divieti | Commissioni | Esito |
|---|---|---|---|---|---|---|---|---|
| **Ticketmaster Discovery API** | Sì: 5.000 chiamate/giorno, 5 req/s | non citate (non verificato) | Chiave immediata | IT nel Discovery Feed | **non verificati** (titolo, data, venue, immagini, url attesi) | Cache solo "for reasonable periods"; rimozione entro 24 h su richiesta; vietato "derive revenues from the use of the API"; terzi possono servire contenuti (informare in privacy) | Affiliazione separata via Impact | **Candidato principale** |
| TicketOne via Awin (ui.awin.com/merchant-profile/9567) | non verificato | non trovato | "valutate caso per caso" | Sì | Catalogo giornaliero, non API | Pagina ufficiale TicketOne non caricata (timeout): termini **non verificati** | 1,10 € a vendita, cookie 15 giorni | Da verificare (richiede iscrizione: non fatta) |
| CTS Eventim | DE/UK su Awin | non trovato | non trovato | IT non trovato | nessuna API pubblica | DE: vietati PPC e banner | dati in conflitto | Scartato |
| Vivaticket, Mailticket/Boxol, Live Nation IT | non trovato | – | contatto diretto | IT | – | – | – | Non verificati |
| Eventbrite | – | – | – | – | ricerca pubblica chiusa nel 2019 | – | – | Scartato |
| Songkick, Bandsintown, Dice, Viagogo | – | – | non self-serve / a pagamento / widget con script di terzi / aggregatore sanzionato | – | – | – | – | Scartati |

### B2. Impatto su Eventi Vicini
- **Modello Event**: `source` oggi vale `scraper`: aggiungere un valore `ticketmaster` (o `ticket`), `category: "music"`, `ticketUrl` (già nel modello, oggi vuoto), `priceType` + eventuale `priceMin/priceMax` se la API li dà; `sourceUrl` = pagina evento del venditore. Adapter nuovo sul modello di `adapters/opendatahub.py` (API JSON, 1 richiesta/s, licenza per record).
- **Deduplica**: concerti grandi raramente coincidono con eventi comunali; dove capita (stesso giorno, luogo entro ~300 m, titolo simile) vince l'evento comunale e gli si aggiunge solo il `ticketUrl`.
- **UI**: bottone "Acquista su Ticketmaster" (etichetta del venditore), `rel="noopener noreferrer"`; con link affiliato `rel="sponsored noopener"` e nota "link di affiliazione: se acquisti, Eventi Vicini può ricevere una commissione". Nessuno script di terzi nel nostro sito: i cookie nascono solo sul sito del venditore dopo il clic.
- **PRODUCT.md** ("senza pubblicità né tracciamento"): un link d'acquisto semplice non è pubblicità; un link **affiliato** è monetizzazione e sta in zona grigia. Decisione di prodotto tua. Se resti senza affiliazione, PRODUCT.md non cambia (basta aggiungere "con link ufficiali d'acquisto, senza commissioni"). Se attivi l'affiliazione va riscritto.
- **Privacy/Termini**: aggiungere che i link portano a siti terzi che possono impostare cookie dopo il clic, e (per Ticketmaster) la presenza di contenuti di terzi; Termini: dati dei concerti forniti dal venditore, rimozione entro 24 h.
- **Conflitto da chiarire**: i termini vietano di "derive revenues" dall'uso dell'API; l'affiliazione lo è. **Senza affiliazione il conflitto non c'è.** Resta incerto se salvare gli eventi su Firestore sia "cache for reasonable periods": chiedere conferma a Ticketmaster o tenere i dati con scadenza breve (cancellare gli eventi non più futuri/non più restituiti ad ogni giro).

### B3. Quote Firestore e bundle (stime, **non verificate**: numero reale di eventi IT non misurato)
- Ipotesi: 2.000-5.000 eventi musicali/grandi eventi futuri in Italia a 60-90 giorni. Prima scrittura: 2.000-5.000 scritture (10-25 % del limite giornaliero di 20.000, da fare in più giorni per regione). Poi solo i cambiati (`contentHash`): ~50-300 scritture/giorno.
- Chiamate API: ~25 pagine da 200 per giro, ben sotto 5.000/giorno.
- Bundle: ~1 KB per evento, +2-5 MB complessivi sui bundle `bundles/*`; da misurare con un dry-run quando si ha la chiave. Letture degli utenti invariate (stessi bundle).
- Cancellazioni: gli eventi passati rientrano nella pulizia esistente (`cleanup.py`).

## Raccomandazione (in ordine)

1. **Subito, a costo zero**: scrivere ai Comuni/titolari per il robots.txt (mail `email_comune_robots.md`, ai Comuni lombardi con più eventi o a un Comune che ti risponde con il nome del fornitore). Poi usare `email_fornitore_robots.md` col destinatario corretto. È l'unica leva su ~405 comuni.
2. **Indagare "In Lombardia"** (eventi.regione.lombardia.it): cercare una pagina "open data"/licenza e scrivere alla Regione per sapere se esiste un feed riutilizzabile (mail in `email_regione_lombardia_eventi.md`). Se esiste con CC-BY, è il candidato A con più copertura.
3. **Ticketmaster Discovery API, senza affiliazione**, come primo canale concerti: gratis, chiave immediata, IT coperta. Prima di scrivere codice: registrare la chiave (azione tua), leggere i campi reali e fare un dry-run per stimare eventi e bundle. Rimandare l'affiliazione finché non decidi su "senza pubblicità".
4. **TicketOne/Awin**: solo se vorrai monetizzare; richiede iscrizione e verifica dei termini che non ho potuto leggere. Non prima del punto 3.
5. **Non attivare**: Umbria ODN (stantia), dataset comunali di dati.lombardia.it (vecchi), Pro Loco senza licenza, widget Dice/Eventbrite.

### Cosa devi fare tu
- Inviare le mail (testi in `docs/contatti/`), completando firma e contatto.
- Registrarti gratuitamente a developer.ticketmaster.com (solo quando decidi di procedere; leggi i campi di una risposta di prova).
- Decidere se un link affiliato è compatibile con "senza pubblicità".

### Non verificato
Fornitore HGATE; licenza e API di eventi.regione.lombardia.it; campi reali e copertura IT della Discovery API; requisiti P.IVA di Ticketmaster/Impact e Awin; termini TicketOne; Vivaticket/Eventim IT/Live Nation IT; 34 dataset Lombardia su 36; versione CC dell'Umbria; numero eventi futuri per i canali concerti.
