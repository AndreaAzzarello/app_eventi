# appEventi (Eventi Vicini)

Agenda gratuita di eventi pubblici locali (partita da Modena). Dettagli completi in `README.md`; stato e ondate in `FINAL_REPORT.md`.

## Stack
- `web/`: SvelteKit + `adapter-cloudflare`, deploy su Cloudflare Pages. Lettura Firestore via REST nel Worker (niente Admin SDK).
- `firebase/`: regole e indici Firestore, test delle regole. Progetto `appeventi-1e860`.
- `tools/importer/`: importer Python (Plone, WordPress DCI, Design Comuni HTML) lanciato da GitHub Actions.

## Vincoli
- **Tutto gratis**: Firebase piano Spark (solo Auth + Firestore; niente Storage, Functions, Hosting). Quote al giorno: 50.000 letture, 20.000 scritture, 20.000 cancellazioni. Nessuna carta.
- Scrivere su Firestore solo i documenti cambiati (`contentHash`); l'importer si ferma oltre `--max-writes` (15.000) / `--max-reads` (40.000).
- Import reali a tappe, una regione alla volta (`--regione`); prima sempre `--dry-run`. Mai import reali senza mia conferma.
- Cron di GitHub Actions sempre in **UTC** (`17 5 * * *`, senza chiave `timezone`).
- Cloudflare: flusso **Pages**, non Workers. Root `web`, build `npm run build`, output `.svelte-kit/cloudflare`, `NODE_VERSION=24`.
- robots.txt e licenze dei siti comunali: rispettarli sempre; attivare una fonte solo con licenza sui contenuti (CC0/CC-BY).
- OpenStreetMap/Nominatim: User-Agent identificativo, max 1 richiesta/s.
- Design: rispettare il design system (README §6b, `web/src/lib/styles/tokens.css`, controllo automatico in `design.test.ts`). Non esiste un DESIGN.md.

## Comandi (da `web/` salvo diversa indicazione)
- Dev: `npm run dev` (legge `.env`); anteprima Cloudflare: `npm run preview` (porta 8788).
- Controlli: `npm run check`, `npm run lint`, `npm test`, `npm run build`.
- E2E: `npm run test:e2e` (usa `emulators:exec`, chiude da solo). Regole: `npm test` in `firebase/`.
- Importer (`tools/importer/`): `python -m pytest -q tests`, `python run.py --dry-run [--regione X]`.
- Deploy regole/indici (prima della webapp): `npm run deploy:rules` in `firebase/`, solo su mia conferma.

## Cartelle importanti
`web/src/lib/server/firestore.ts` (letture REST, limite per cella), `web/src/lib/styles/`, `firebase/firestore.rules`, `tools/importer/sources/*.csv` (registro fonti), `.github/workflows/`.

## Da non fare
- Non usare `emulators:start` nei test: solo `emulators:exec`.
- Non committare `.env`, `.dev.vars`, chiavi service account (`FIREBASE_SERVICE_ACCOUNT` è un segreto).
- Non modificare a mano `reports/` o `sources/*.csv` senza passare dagli script (`activate.py`, `licenses.py`).
- Non usare tile OSM pubbliche per traffico intenso; non aggiungere analytics o cookie di profilazione.
