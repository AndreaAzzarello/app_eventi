# Changelog

Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it/). Le versioni sono ricostruite dalla cronologia dei commit.

## [1.0.0] - 2026-10-29

Prima versione pubblica, su tutta Italia.

### Aggiunto
- **Bundle delle liste**: l'importer scrive liste precalcolate per cella geohash e per città (`bundles/*`), la webapp legge una sola volta per cella invece di una query per visita; regole in sola lettura pubblica.
- Cache a due livelli nel Worker (memoria e Cache API di Cloudflare), con copia vecchia se la quota Firestore è esaurita.
- Import giornaliero alle 08:17 UTC, dopo il reset della quota Firestore.
- File di progetto: README rifatto, licenza MIT, SECURITY, CONTRIBUTING, brand kit e documentazione tecnica in `docs/`.

### Modificato
- Repository rinominato in `EventiVicini`; User-Agent dell'importer e del geocoder aggiornati.

## [0.5.0] - 2026-10-28 · Redesign sobrio e statistiche

### Aggiunto
- Design system ([`DESIGN.md`](DESIGN.md)): carta calda e notte calda, accento terracotta, titoli in Fraunces, card a biglietto, lista per sezioni di tempo, mappa con pin per categoria e cluster, icone Lucide, controllo automatico dei token.
- Statistiche mensili per regione (`stats/*`) e confronto mensile nelle pagine regione.
- Ricerca unificata di eventi e luoghi con luogo nell'URL; comuni bilingui.

## [0.4.0] - 2026-10-27 / 28 · Tutta Italia

### Aggiunto
- Registro delle fonti per regione (ISTAT e IndicePA) per le 20 regioni, rilevamento del CMS e delle licenze, attivazione automatica con regola (adapter, licenza CC0/CC-BY, robots.txt, evento valido) e ricontrollo settimanale.
- Seconda e terza ondata: Piemonte, Valle d'Aosta, Liguria, Friuli-Venezia Giulia, Trentino-Alto Adige, Marche, Umbria, poi Lazio, Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna. Adapter Open Data Hub Alto Adige.
- Import a matrice per regione su GitHub Actions, manifest locale degli hash, riconciliazioni scaglionate, geocoding con budget, filtro anti-avvisi.
- Scelta di regione e comune al primo accesso; copertura per regione.

## [0.3.0] - 2026-10-27 · Prima ondata e scritture minime

### Aggiunto
- Scrittura dei soli cambiamenti (`contentHash`), tetti di quota (`--max-writes`, `--max-reads`), pulizia automatica del database, eventi spariti dalla fonte nascosti.
- Adapter WordPress e HTML Design Comuni Italia; prima ondata Lombardia, Veneto, Toscana.

## [0.2.0] - 2026-10-26 / 27 · Webapp SvelteKit

### Cambiato
- Migrazione da Flutter a **SvelteKit su Cloudflare Pages**; l'app Flutter è archiviata nel tag `flutter-legacy`.

### Aggiunto
- Lista, mappa e filtri con SSR, pagine per città, PWA installabile con pagina offline.
- Account facoltativo (Google o link email), preferiti, proposte di eventi, area admin.
- Regole Firestore riscritte e testate; importer Python per i comuni di Modena, Formigine, Sassuolo e Mirandola (API Plone) con geocoding Nominatim.

## [0.1.0] - 2025-08 / 2026-10-26 · App Flutter

- Prima app Flutter (Firebase, mappa, calendario), poi archiviata.
