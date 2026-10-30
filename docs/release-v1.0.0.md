# Eventi Vicini v1.0.0

Prima versione pubblica: un'agenda gratuita degli eventi pubblici di **tutta Italia**, raccolti ogni giorno dai siti dei comuni e dagli open data che ne consentono il riuso (CC-BY/CC0). Niente pubblicità, niente tracciamento, sempre il link alla fonte originale.

**Sito:** https://eventi-vicini.pages.dev

![Home desktop](https://raw.githubusercontent.com/AndreaAzzarello/EventiVicini/v1.0.0/docs/screenshots/home-desktop-chiaro.png)

## Novità

- **Bundle delle liste**: l'importer scrive liste precalcolate per cella geohash e per città (`bundles/*`); la webapp legge una sola volta per cella invece di una query per visita.
- **Cache a due livelli** nel Worker (memoria e Cache API di Cloudflare), con copia vecchia se la quota Firestore è esaurita.
- **Import giornaliero** alle 08:17 UTC, dopo il reset della quota Firestore.
- **Documentazione**: README rifatto con screenshot reali, licenza MIT, SECURITY, CONTRIBUTING, brand kit e documentazione tecnica in `docs/`.
- Repository rinominato in `EventiVicini`.

Storico completo delle versioni precedenti (0.1–0.5: webapp SvelteKit, tutta Italia, redesign e statistiche) in [CHANGELOG.md](https://github.com/AndreaAzzarello/EventiVicini/blob/main/CHANGELOG.md).

## Copertura

Stato al 29 ottobre 2026: 20 regioni, circa 7.900 comuni censiti, **921 con una fonte attiva**, circa 4.000 eventi su un orizzonte di 45-60 giorni.

## Limiti noti

- Le liste si aggiornano una volta al giorno: un evento approvato appare entro 24 ore.
- Le tile pubbliche di OpenStreetMap non reggono traffico intenso.
- Nessun adapter per Drupal, Joomla, Halley, Maggioli.
- La ricerca testuale non guarda la descrizione degli eventi.

## Licenza

Codice sotto [MIT](https://github.com/AndreaAzzarello/EventiVicini/blob/main/LICENSE); i dati degli eventi restano sotto la licenza di ciascuna fonte.
