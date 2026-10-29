# Sviluppo, test e deploy

## Avvio in locale

### Requisiti

- **Node.js 24.22.1 o superiore (`.nvmrc`: 24)** (`engines` in `web/package.json`).
- **JDK 21** per gli emulatori Firebase. La CI usa Temurin 21.
- **Python 3.12** per l'importer (la CI usa 3.12).

Su Windows, se il JDK non è nel PATH, si può impostare `JAVA_HOME` nella sessione PowerShell. Il percorso è un esempio: adattalo alla tua installazione JDK 21.

```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.x.y-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
```

### Installazione

```bash
cd web
npm install

cd ../firebase
npm install
```

`web/` richiama gli emulatori da `../firebase/node_modules`, quindi serve anche l'installazione in `firebase/`.

### Variabili locali

- Per lo sviluppo con `npm run dev`: copia `web/.env.example` in `web/.env`.
- Per `npm run preview` (wrangler): copia `web/.dev.vars.example` in `web/.dev.vars`.

Entrambi i file puntano agli emulatori (`PUBLIC_USE_EMULATORS=true`, `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080`). I file `.env` e `.dev.vars` sono esclusi da git.

### Comandi

Da `web/`:

```bash
# 1. Emulatori Auth (9099), Firestore (8080), UI (4000).
#    Resta in primo piano: per lo sviluppo manuale, chiudilo con Ctrl+C.
npm run emulators

# 2. In un altro terminale: dati di prova nell'emulatore (con gli emulatori attivi).
npm run seed

# 3. Sviluppo con hot reload (vite dev, legge .env).
npm run dev

# 4. Build e anteprima come su Cloudflare (wrangler pages dev, porta 8788, legge .dev.vars).
npm run preview
```

Note:

- `npm run emulators` è un processo che resta aperto. Non usarlo per i test: vedi [Test e verifiche](#test-e-verifiche).
- Su Windows alcune porte (ad esempio 4173) sono riservate dal sistema. Playwright usa la porta 4300 (vedi `web/playwright.config.ts`).

---

## Test e verifiche

### Comandi

| Dove | Comando | Cosa fa |
|---|---|---|
| `web/` | `npm run check` | `svelte-kit sync` e `svelte-check` con il tsconfig del progetto. |
| `web/` | `npm run lint` | ESLint (`eslint .`). |
| `web/` | `npm test` | Test unitari Vitest (`src/**/*.test.ts`). Non usa gli emulatori. |
| `web/` | `npm run build` | Build SvelteKit per Cloudflare (`.svelte-kit/cloudflare`). |
| `web/` | `npm run test:e2e` | Avvia gli emulatori Auth e Firestore con `firebase emulators:exec`, poi Playwright. Il `globalSetup` pulisce gli emulatori e carica i dati di prova. Playwright fa `npm run build` e `vite preview` sulla porta 4300. Profili: mobile (Pixel 7) e desktop (Chrome). |
| `firebase/` | `npm test` | `firebase emulators:exec --only firestore` poi `vitest run`: test delle regole in `test/rules.test.js`. |
| `tools/importer/` | `python -m pytest -q tests` | Test del mapping e del geocoding con fixture salvate. |

Per i test con gli emulatori usa sempre `firebase emulators:exec` (già incluso in `npm test` di `firebase/` e in `npm run test:e2e` di `web/`). Non lasciare aperto `emulators:start` durante i test: le porte restano occupate e i dati di prova si mescolano.

I browser di Playwright devono essere installati sulla macchina. Il repository non contiene il comando di installazione: verificalo con la documentazione di Playwright.

### CI

`.github/workflows/ci.yml`, su ogni pull request e su push a `main`:

- **job `web`** (Ubuntu, Node 24, `npm ci` in `web/`): `npm run check`, `npm run lint`, `npm test`, `npm run build`.
- **job `rules`** (Ubuntu, Node 24, Temurin JDK 21, `npm ci` in `firebase/`): `npm test` (test delle regole con emulatore).

La CI non esegue i test E2E Playwright. Il test dell'importer gira nel workflow `import-events.yml`, prima dell'import.

---

## Deploy su Cloudflare Pages

Il sito è pubblicato su https://eventi-vicini.pages.dev. Questi sono i passi per ricrearlo da zero.

Prima della webapp, pubblica indici e regole Firestore (vedi [Firebase Console](architettura.md#firebase-console)): la query per raggio usa l'indice `(endTime, geohash)`, che senza indice fa fallire la ricerca.

1. Dashboard Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**. Scegli il repository GitHub.
2. Impostazioni del build:
   - **Root directory**: `web`
   - **Build command**: `npm run build`
   - **Build output directory**: `.svelte-kit/cloudflare`
3. Versione di Node: imposta la variabile di build `NODE_VERSION` = `24` (Settings → Variables and Secrets → Build, sia Production sia Preview); in alternativa Cloudflare legge `.nvmrc` alla radice del repository.
4. **Settings → Variables**: aggiungi le variabili `PUBLIC_*`, `CONTACT_EMAIL` e `CONTROLLER_NAME` con i valori di produzione (vedi [variabili d'ambiente](architettura.md#variabili-dambiente)). `PUBLIC_USE_EMULATORS` deve essere `"false"`; `FIRESTORE_EMULATOR_HOST` non va impostata in produzione.
5. Imposta la **compatibility date** del progetto a `2026-10-01`, come in `wrangler.toml`.
6. Salva e avvia il primo deploy. Il progetto si chiama `eventi-vicini` (come in `wrangler.toml`), quindi l'URL atteso è `https://eventi-vicini.pages.dev`, uguale a `PUBLIC_SITE_URL`. Verificalo dopo il deploy.
7. Dopo ogni deploy la cache delle pagine HTML dura al massimo 5 minuti (vedi [quote-firestore.md](quote-firestore.md)). Per azzerarla subito usa **Purge cache** (il percorso nell'interfaccia Cloudflare può cambiare).
