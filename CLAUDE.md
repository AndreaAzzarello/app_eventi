# appEventi (Eventi Vicini)

Agenda gratuita di eventi pubblici locali (partita da Modena). Dettagli completi in `README.md`; stato e ondate in `FINAL_REPORT.md`.

## Stack
- `web/`: SvelteKit + `adapter-cloudflare`, deploy su Cloudflare Pages. Lettura Firestore via REST nel Worker (niente Admin SDK).
- `firebase/`: regole e indici Firestore, test delle regole. Progetto `appeventi-1e860`.
- `tools/importer/`: importer Python (Plone, WordPress DCI, Design Comuni HTML) lanciato da GitHub Actions.

## Vincoli
- Firebase resta sul piano Spark (solo Auth + Firestore; niente Storage, Functions, Hosting). Quote al giorno: 50.000 letture, 20.000 scritture, 20.000 cancellazioni.
- Scrivi su Firestore solo i documenti cambiati (`contentHash`); l'importer si ferma oltre `--max-writes` (15.000) / `--max-reads` (40.000).
- Gli import reali vanno a tappe, una regione alla volta (`--regione`), dopo un `--dry-run`.
- I cron di GitHub funzionano solo in UTC e la chiave `timezone` si è rivelata inaffidabile: scrivili in UTC, dopo il reset della quota Firestore, senza `timezone`. Avvio puntuale 08:17 dal Worker `scheduler/` (Cloudflare Cron Trigger → `workflow_dispatch` con `auto=true`); il cron di GitHub (10:17) è riserva; il job `guard` evita il doppio import.
- Cloudflare: flusso Pages, non Workers. Root `web`, build `npm run build`, output `.svelte-kit/cloudflare`, `NODE_VERSION=24`.
- Rispetta robots.txt e licenze dei siti comunali; attiva una fonte solo con licenza sui contenuti (CC0/CC-BY).
- OpenStreetMap/Nominatim: User-Agent identificativo, max 1 richiesta/s.
- Design: le regole sono in `DESIGN.md`, i valori in `web/src/lib/styles/tokens.css`, il controllo automatico in `design.test.ts`.

## Comandi (da `web/` salvo diversa indicazione)
- Dev: `npm run dev` (legge `.env`); anteprima Cloudflare: `npm run preview` (porta 8788).
- Controlli: `npm run check`, `npm run lint`, `npm test`, `npm run build`.
- E2E: `npm run test:e2e` (usa `emulators:exec`, chiude da solo). Regole: `npm test` in `firebase/`.
- Importer (`tools/importer/`): `python -m pytest -q tests`, `python run.py --dry-run [--regione X]`.
- Deploy regole/indici (prima della webapp): `npm run deploy:rules` in `firebase/`.

## Finito quando
- In `web/` passano `npm run check`, `npm run lint`, `npm test` e `npm run build`. Se tocchi le regole passa anche `npm test` in `firebase/`; se tocchi l'importer, `python -m pytest -q tests`.
- Per il frontend controlla a 360 px (vedi `DESIGN.md`).
- Dichiara se non hai eseguito `test:e2e`, il `--dry-run` dell'importer o il controllo visivo. Un import reale lo esegui solo con la mia conferma.

## Cartelle importanti
`web/src/lib/server/firestore.ts` (letture REST; legge i bundle `bundles/*` scritti da `tools/importer/bundles.py`, ripiega sulle query per cella), `web/src/lib/styles/`, `firebase/firestore.rules`, `tools/importer/sources/*.csv` (registro fonti), `.github/workflows/`.

## Da non fare
- Nei test usa `emulators:exec` (chiude da solo), non `emulators:start`.
- Tieni fuori dai commit `.env`, `.dev.vars` e le chiavi service account: `FIREBASE_SERVICE_ACCOUNT` è un segreto.
- Modifica `reports/` e `sources/*.csv` solo tramite gli script (`activate.py`, `licenses.py`), non a mano.
- Le tile OSM pubbliche non sono adatte a traffico intenso; niente analytics né cookie di profilazione.
