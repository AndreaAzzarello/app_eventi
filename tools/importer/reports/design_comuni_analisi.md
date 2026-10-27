# Analisi del modello "Design Comuni Italia" e piano dell'adapter HTML

Fixture: `tests/fixtures/html/<comune>/{lista,dettaglio-1,dettaglio-2}.html` (9 comuni, 18 pagine di dettaglio, `INDEX.md`
con gli URL). Raccolte con `fetch.Fetcher` (robots.txt, 1 richiesta/s per host, UA del progetto).

| fornitore / piattaforma | comuni in fixture |
|---|---|
| WordPress, tema design-comuni-wordpress-theme (AgID) | Bagno di Romagna, Mercato Saraceno, Montiano, Sarsina, Verghereto, Casina, Pavullo nel Frignano |
| ComWeb (epublic.it), Bootstrap Italia | Granarolo dell'Emilia |
| ASP.NET WebForms (fornitore non identificato), Bootstrap Italia | Medicina |

Non salvati: Masi Torello e Voghiera (la lista non mostra link a eventi futuri), Cadeo, Collecchio, Soragna, Polinago,
Longiano, Fiumalbo (nessun link o uno solo) e Alfonsine (eZ/OpenPA: i link sono categorie). **Drupal, Joomla, Halley e
Maggioli non sono rappresentati**: i campioni provati non avevano eventi leggibili. È il limite principale di questa fase.

## Quanto sono diffusi i marcatori (18 pagine di dettaglio)

| marcatore | pagine |
|---|---|
| classi `cmp-*` / `it-page-section`, breadcrumb | 18 / 18 |
| link "Aggiungi al calendario" (Google Calendar con `dates=AAAAMMGGTHHMMSS/…`) | 12 |
| elenco puntato `.point-list` (giorno, mese abbreviato, orari) in "Date e orari" | 15 |
| sezione `#costi` | 13 |
| sezione `#luogo` | 10 |
| JSON-LD `schema.org/Event` | **2** (solo Granarolo, con `startDate` senza ora) |
| microdata/RDFa `Event` | **0** (c'è solo `BreadcrumbList`) |
| feed iCal (`.ics`, `text/calendar`) | **0** |
| feed RSS | solo quello generico di WordPress (articoli, non eventi) |

Conclusione: l'ordine di priorità richiesto (JSON-LD, microdata, iCal/RSS) viene quasi sempre a vuoto; il lavoro vero lo fanno
il link Google Calendar (date e ore esatte) e i selettori del modello.

## Selettori stabili (tema WordPress DCI e cloni Bootstrap Italia)

- Titolo: `h1`. URL canonico: `link[rel=canonical]`.
- Date: `small` "Dal:" / "Al:" seguiti da `h5`; `#date-e-orari` (o `#dataora`) con `.point-list` → `.point-date`, `.point-month`
  e orari in `.point-list-content`.
- Luogo: `#luogo` → `.card-title` (nome) e `.card-text` (indirizzo, spesso "via X, 1 - Comune (FC), 47027").
- Costi: `#costi` (testi come "Gratuito", "Ingresso libero", "Quota di partecipazione € 5,00").
- Tipo evento: `<strong>Tipo di evento</strong>: Convegno`, oppure `.category` nelle card.
- Immagine: `og:image` è spesso la favicon del tema (Sarsina): meglio il primo link a immagine in `.it-page-sections-container`.
- Lista: `.cmp-list-card-img` (WordPress) o `.card-wrapper` (ComWeb); data nella card in `.data_num` ("Dal 24/10/26 al 24/10/26").

## Varianti per fornitore

- **WordPress DCI**: sezioni con `id` (`cos-e`, `luogo`, `date-e-orari`, `costi`). La lista mostra solo le prime 3 card e il
  resto arriva con "Carica altri risultati" (POST a `admin-ajax.php`): **non lo usiamo**; si legge la sitemap dichiarata in
  `robots.txt` (`/sitemap.xml`, elenco piatto con `lastmod`) e si prendono gli URL sotto `/vivere-il-comune/eventi/`.
  Alcuni eventi non hanno `#luogo` (Montiano) o `#costi`.
- **ComWeb (Granarolo)**: URL relativi, card senza `.data_num`, JSON-LD con la sola data (evento "tutto il giorno"), i link
  `…/eventi/storico` e `…/eventi-principali` sono schede della lista e non eventi.
- **ASP.NET (Medicina)**: stesse classi Bootstrap Italia ma `id="dataora"` e `<section>` al posto di `<article>`; orari in
  `.point-list` come sopra.

## Piano dell'adapter (implementato in `adapters/design_comuni_html.py`)

1. Scoperta: `url_eventi` del registro, poi `/vivere-il-comune/eventi/`, `/novita/eventi/`, `/eventi/`, `/evento/`; card della lista con
   salto di quelle già finite; paginazione con `rel=next` (al massimo 5 pagine); sitemap come integrazione.
2. Dettaglio, nell'ordine: (a) JSON-LD Event, (b) microdata, (c) link Google Calendar, (d) `.point-list` (prossima data) poi Dal/Al,
   (e) testo libero ("dal 3 al 5 novembre 2026", "tutti i sabati", "ore 21:00").
3. Normalizzazione con `mapping.py` (prezzo, categoria da titolo e tipo, kids, indirizzo per il geocoding vincolato alla provincia).
4. Fuso Europe/Rome, scarto degli eventi finiti, oltre l'orizzonte o più lunghi di 45 giorni.
5. Cortesia: robots.txt, 1 richiesta/s per host, retry con backoff, cache ETag/Last-Modified, al massimo 40 dettagli per comune.

Limiti noti: nessuna fixture Drupal/Joomla/Halley/Maggioli; il microdata è implementato ma non provato su pagine reali; il parsing dei feed `.ics` linkati
**non è implementato** (nessuna pagina ne espone: il link Google Calendar porta le stesse informazioni); i siti che caricano la lista solo in AJAX senza sitemap restituiscono 0 eventi.
