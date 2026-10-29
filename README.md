# Eventi Vicini

Agenda gratuita di eventi pubblici locali. La prima area coperta è quella di Modena (fonti: i siti dei comuni di Modena, Formigine, Mirandola e Sassuolo). Il sito è una webapp SvelteKit con lista, mappa, filtri, pagine per città e preferiti. Il repository non contiene più l'app Flutter precedente.

Il repository è un monorepo con quattro parti:

- `web/`: webapp SvelteKit, deploy su Cloudflare Pages.
- `firebase/`: regole e indici Firestore, test delle regole.
- `tools/importer/`: importer Python che raccoglie gli eventi dai siti dei comuni.
- `.github/workflows/`: CI e import giornaliero.

---

## 1. Cos'è e vincoli

Il progetto è pensato per non costare nulla e per non richiedere una carta di credito.

- **Firebase, piano Spark**: si usano solo Authentication (login Google o link via email) e Cloud Firestore. Non si usano Storage, Cloud Functions né Firebase Hosting. Il piano Spark ha quote gratuite: per Firestore, 50.000 letture al giorno (dato di progetto, da verificare nella console).
- **Cloudflare Pages, piano gratuito**: ospita la webapp (SvelteKit con `adapter-cloudflare`, quindi un Worker che serve SSR e API).
- **OpenStreetMap**: mappe (tile pubblici) e geocoding (Nominatim). Il progetto rispetta le policy: User-Agent identificativo, massimo 1 richiesta al secondo, cache, risultati solo per l'Italia. Per traffico intenso le tile pubbliche non sono ammesse (vedi sezione 12).
- **Nessun Admin SDK nel Worker**: il server legge Firestore con la API REST pubblica. Funziona perché la collezione `events` è a lettura pubblica (vedi sezione 8).

---

## 2. Architettura

```
 Browser (PWA)
   |  HTML SSR, JSON /api/*        |  Firebase JS SDK, caricato solo quando serve
   |                               |  (login, preferiti, proposte, admin)
   v                               v
 Cloudflare Pages                 Firebase
 (Worker SvelteKit)               - Authentication
   - SSR: lib/server/firestore.ts - Cloud Firestore <------------+
     fetch REST, senza Admin SDK                                  |
   - /api/events  -> query per geohash, cache                     |
   - /api/geocode -> proxy verso Nominatim (OSM)                  |
          |                                                       |
          v                                                       |
 Nominatim (OSM)                                                  |
                                                                  |
 Importer Python (GitHub Actions, ogni giorno)  -- Admin SDK ----+
   - legge i siti dei comuni (API Plone)
   - geocoding Nominatim con cache

 Browser -> tile OpenStreetMap (Leaflet, mappa)
```

Punti chiave:

- **Lista e pagine pubbliche**: SSR sul Worker. La home carica gli eventi della zona predefinita (Modena, 25 km). I filtri si applicano nel browser.
- **Posizione**: se l'utente la concede, la webapp chiama `/api/events` con coordinate arrotondate a una griglia di circa 5 km. La posizione resta nel localStorage del dispositivo.
- **Query per raggio**: ogni raggio diventa un insieme di intervalli di geohash (`geofire-common`). Una query Firestore per intervallo, mai l'intera collezione.
- **Firebase lato client**: `web/src/lib/firebase/client.ts` importa `firebase/app`, `firebase/auth` e `firebase/firestore/lite` in modo dinamico. Chi naviga senza account non scarica l'SDK.
- **Cache**: in memoria per isolate (5 minuti), `Cache-Control` sulle risposte HTML e JSON (vedi sezione 10).

---

## 3. Struttura delle cartelle

```
web/
  src/
    routes/            pagine e API: /, /eventi/[slug], /citta/[slug], /proponi,
                       /preferiti, /account, /accedi, /admin, /privacy, /termini,
                       /api/events, /api/geocode, sitemap.xml, robots.txt, /offline,
                       /admin/statistiche, /admin/stile
    lib/
      server/          firestore.ts (lettura REST), cache.ts (header di cache), legal.ts
      firebase/        caricamento lazy dell'SDK Firebase lato browser
      components/      componenti Svelte
      event.ts         modello Event, validazione, limiti dei campi
      geo.ts           raggi, geohash, griglia della cache, distanza
      geocode.ts       ricerca comuni e indirizzi via /api/geocode
      images.ts        srcset delle immagini di terze parti (scale Plone)
      styles/          tokens.css (design system) e design.test.ts (controllo automatico)
      *.test.ts        test unitari (Vitest)
    service-worker.ts  PWA: app shell e pagina offline
  e2e/                 test Playwright (desktop e mobile)
  scripts/seed-emulator.mjs   dati di prova per l'emulatore Firestore
  wrangler.toml        configurazione Cloudflare Pages e variabili pubbliche
  .env.example         variabili per `npm run dev` (emulatori)
  .dev.vars.example    variabili per `npm run preview` (wrangler, emulatori)

firebase/
  firebase.json        regole, indici, porte degli emulatori
  firestore.rules      regole di sicurezza (vedi "Regole Firestore")
  firestore.indexes.json
  test/rules.test.js   test delle regole sull'emulatore
  .firebaserc          progetto di default: appeventi-1e860

tools/importer/
  run.py               importer: raccolta, geocoding, deduplica, scrittura dei soli cambiamenti
  cleanup.py           pulizia giornaliera del database (eventi e proposte scaduti)
  activate.py          attivazione automatica delle fonti (regola approvata)
  ci_report.py         matrice per regione e riepilogo unico del workflow
  migrate.py           migrazione una tantum degli eventi esistenti
  adapters/            fonti: base.py (interfaccia), plone.py, wordpress.py, __init__.py (registro)
  sources/<regione>.csv   registro delle fonti, un file per regione (comuni, CMS, licenza, stato)
  provinces.json       riquadri delle province (generato da build_provinces.py)
  build_registry.py    genera il registro da ISTAT e IndicePA
  build_provinces.py   genera provinces.json da ISTAT e OpenStreetMap
  detect_cms.py        riconosce CMS, pagina eventi e licenza dei comuni
  geo.py, geocode.py, licenses.py, mapping.py, registry.py, db.py
  seed_demo.py         10 eventi demo (solo emulatore Firestore: vedi sezione 9)
  tests/               test pytest con fixture

.github/workflows/
  ci.yml               controlli della webapp e test delle regole
  import-events.yml    import giornaliero dell'importer
```

---

## 4. Avvio in locale

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

- `npm run emulators` è un processo che resta aperto. Non usarlo per i test: vedi la sezione 6.
- Su Windows alcune porte (ad esempio 4173) sono riservate dal sistema. Playwright usa la porta 4300 (vedi `web/playwright.config.ts`).

---

## 5. Variabili d'ambiente

I nomi con prefisso `PUBLIC_` sono esposti al browser da SvelteKit. Non sono segreti: la configurazione web di Firebase è pubblica per costruzione, e la sicurezza dei dati sta nelle regole Firestore e nelle regole di Authentication.

| Nome | Dove va | Valore / esempio | Note |
|---|---|---|---|
| `PUBLIC_SITE_URL` | `wrangler.toml` `[vars]`; `.env`; `.dev.vars` | `https://eventi-vicini.pages.dev`; in locale `http://localhost:5173` (`.env`) o `http://localhost:8788` (`.dev.vars`) | URL del sito, usato per canonical, Open Graph, sitemap e per il Referer verso Nominatim. |
| `PUBLIC_FIREBASE_API_KEY` | `wrangler.toml`; `.env` (`demo-key`) | chiave web del progetto `appeventi-1e860` (il valore è in `wrangler.toml`) | Pubblica. Non è una chiave segreta: non limita l'accesso ai dati. |
| `PUBLIC_FIREBASE_AUTH_DOMAIN` | `wrangler.toml`; `.env` (`localhost`) | `appeventi-1e860.firebaseapp.com` | Dominio dell'auth. |
| `PUBLIC_FIREBASE_PROJECT_ID` | `wrangler.toml`; `.env` / `.dev.vars` (`demo-eventi`) | `appeventi-1e860` | Anche per le letture REST del server. |
| `PUBLIC_FIREBASE_APP_ID` | `wrangler.toml`; `.env` / `.dev.vars` (`demo-app`) | `1:398100140878:web:...` | ID dell'app web Firebase. |
| `PUBLIC_USE_EMULATORS` | `wrangler.toml` (`"false"`); `.env` e `.dev.vars` (`"true"`) | `true` attiva gli emulatori Auth (127.0.0.1:9099) e Firestore (127.0.0.1:8080) nel browser | Il valore deve essere la stringa `true` per attivarli. |
| `FIRESTORE_EMULATOR_HOST` | `.env`; `.dev.vars` | `127.0.0.1:8080` | Solo lato server: le letture REST vanno all'emulatore e non usano la API key. Non è in `wrangler.toml`. |
| `CONTACT_EMAIL` | `wrangler.toml` (`azzatubo@gmail.com`); `.env.example` (`privacy@example.org`) | indirizzo di contatto | Mostrato in `/privacy` e `/termini` (`web/src/lib/server/legal.ts`). Lato server. |
| `CONTROLLER_NAME` | `wrangler.toml` (`Andrea Azzarello`); `.env.example` (`Mario Rossi (esempio)`) | nome del titolare | Mostrato in `/privacy` e `/termini`. Lato server. |
| `FIREBASE_SERVICE_ACCOUNT` | GitHub: Settings → Secrets → Actions; locale: variabile d'ambiente | contenuto JSON della chiave del service account | **Segreto.** Usato dall'importer. Non committarlo. |
| `GOOGLE_APPLICATION_CREDENTIALS` | variabile d'ambiente sul PC | percorso di un file JSON fuori dal repository | Alternativa locale a `FIREBASE_SERVICE_ACCOUNT`, per l'importer. **Segreto**: il file non va in git. |

Note:

- `wrangler.toml` contiene le stesse variabili pubbliche di produzione. Per il deploy su Cloudflare impostale nella dashboard (vedi sezione 7). Non dare per scontato che il build collegato a git le legga da `wrangler.toml`: va verificato al primo deploy.
- `CONTACT_EMAIL` e `CONTROLLER_NAME` hanno valori di esempio in `.env.example` e `.dev.vars.example`. In produzione devono essere quelli reali.

---

## 6. Test e verifiche

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

## 6b. Design system

Regole, token e controlli automatici sono in [`DESIGN.md`](DESIGN.md).

## 7. Deploy su Cloudflare Pages

Nessun deploy è stato ancora fatto. Questi sono i passi da eseguire.

Prima della webapp, pubblica indici e regole Firestore (sezione 8): la query per raggio usa l'indice `(endTime, geohash)`, che senza indice fa fallire la ricerca.

1. Dashboard Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**. Scegli il repository GitHub.
2. Impostazioni del build:
   - **Root directory**: `web`
   - **Build command**: `npm run build`
   - **Build output directory**: `.svelte-kit/cloudflare`
3. Versione di Node: imposta la variabile di build `NODE_VERSION` = `24` (Settings → Variables and Secrets → Build, sia Production sia Preview); in alternativa Cloudflare legge `.nvmrc` alla radice del repository.
4. **Settings → Variables**: aggiungi le variabili `PUBLIC_*`, `CONTACT_EMAIL` e `CONTROLLER_NAME` con i valori di produzione (vedi sezione 5). `PUBLIC_USE_EMULATORS` deve essere `"false"`; `FIRESTORE_EMULATOR_HOST` non va impostata in produzione.
5. Imposta la **compatibility date** del progetto a `2026-10-01`, come in `wrangler.toml`.
6. Salva e avvia il primo deploy. Il progetto si chiama `eventi-vicini` (come in `wrangler.toml`), quindi l'URL atteso è `https://eventi-vicini.pages.dev`, uguale a `PUBLIC_SITE_URL`. Verificalo dopo il deploy.
7. Dopo ogni deploy la cache delle pagine HTML dura al massimo 5 minuti (vedi sezione 10). Per azzerarla subito usa **Purge cache** (il percorso nell'interfaccia Cloudflare può cambiare).

---

## 8. Firebase Console

### Authentication

Console Firebase → progetto `appeventi-1e860` → **Authentication**:

1. **Metodo di accesso**: abilita **Google** e **Link via email** (accesso con link all'email).
2. **Impostazioni → Domini autorizzati**: aggiungi il dominio `pages.dev` del progetto (`eventi-vicini.pages.dev`) e il dominio proprio, se c'è.

### Regole e indici

Le regole e gli indici sono in `firebase/firestore.rules` e `firebase/firestore.indexes.json`. Il deploy avviene con:

```bash
cd firebase
npm run deploy:rules
```

Lo script esegue `firebase deploy --only firestore:rules,firestore:indexes --project appeventi-1e860`. Serve essere autenticati con Firebase CLI: il repository non contiene il comando di login.

### Admin

L'admin è **azzatubo@gmail.com**, con email verificata (`email_verified == true`). Il controllo vero è in `isAdmin()` nelle regole. La stessa email è in `web/src/lib/config.ts` (`ADMIN_EMAIL`) per mostrare l'interfaccia giusta. Per cambiare admin vanno modificate entrambe.

### Regole Firestore

Il modello dati e le motivazioni stanno in `firebase/firestore.rules`. Riassunto:

- **`events`**: lettura pubblica. Scrittura (creazione, modifica, eliminazione) solo per l'admin. L'importer scrive con Admin SDK, che non passa dalle regole, quindi per gli eventi `scraper` il controllo è nel codice dell'importer.
- Ogni evento deve avere i campi previsti, con tipi e limiti di lunghezza (coincidono con `LIMITS` in `web/src/lib/event.ts`). Le URL (immagine, biglietti, fonte) devono essere vuote o `http(s)`, per escludere `javascript:` e `data:`.
- **`submissions`** (proposte degli utenti): creazione da utente autenticato con `status: 'pending'`. Il contatore `pendingCount` dell'autore cambia nello stesso batch della proposta; massimo 5 proposte in attesa. Solo l'admin cambia lo stato, una volta sola (approvata con `eventId`, rifiutata con motivo). L'autore vede le proprie proposte e può ritirarle.
- **`users/{uid}`**: lettura e modifica solo del proprietario, su pochi campi (nome, città, contatore). Il profilo non si cancella con proposte in attesa. Sotto `favorites/{eventId}` ci sono i preferiti dell'utente.
- **`coverage/{regione}`** e **`stats/{regione}_{AAAA-MM}`**: lettura pubblica, scrittura negata a tutti i client (le scrive l'importer con l'Admin SDK).
- Tutto il resto è chiuso (`allow read, write: if false`).

Indici composti: `events` per `geohash` + `endTime`, per `endTime` + `geohash` e per `citySlug` + `endTime`; `submissions` per `ownerId` + `createdAt` e per `status` + `createdAt`.

**Ordine di pubblicazione.** L'indice `endTime` + `geohash` va pubblicato con `npm run deploy:rules` **prima** del deploy della webapp: la webapp lo usa per il limite per cella (`web/src/lib/server/firestore.ts`).

---

## 9. Importer

Il codice è in `tools/importer/`. Legge gli eventi pubblici dei comuni e li scrive nella collezione `events`.

### Come funziona

1. **Adapter per fonte**: ogni fonte attiva ha un adapter per il suo CMS. Plone (`adapters/plone.py`) legge la API paginata (`++api++/@search`), con una richiesta al secondo. WordPress "Design Comuni Italia" (`adapters/wordpress.py`, CMS `wordpress-dci`) legge `/wp-json/wp/v2/eventi` con una sola richiesta; se l'endpoint manca cerca la route eventi nell'indice `/wp-json/`. Cesena, Ravenna e Serramazzoni non espongono eventi via REST: zero eventi e un avviso. Design Comuni Italia senza API (CMS `design_comuni_html`) legge l'HTML: vedi la sezione seguente.
2. **Normalizzazione** (`mapping.py`): categoria dalla tipologia o dal titolo (parole chiave italiane: kids, food, sport, music, market, culture), prezzo dal testo, fuso `Europe/Rome`, prossima occorrenza per gli eventi ricorrenti, orario reale dal campo `orari` quando quello inserito è fittizio. Si importano gli eventi in corso o che iniziano entro 60 giorni (`--horizon-days`).
3. **Coordinate**: dal campo geolocalizzato della fonte. Se la fonte è fuori dalla provincia del comune, quelle coordinate vengono scartate. Altrimenti Nominatim sugli indirizzi, con comune e provincia nella query (es. "via X, Modena") e il riquadro della provincia come filtro. Se nessun indirizzo si trova, si usa il centro del comune con `approxLocation=true`: la webapp lo mostra come "Luogo da confermare". Cache in `geocache.json`, anche per i "non trovato".
4. **Località su ogni evento**: `enrich()` in `geo.py` scrive `geohash` (precisione 10, stesso algoritmo di `geofire-common`), `city`, `citySlug`, `province` e `region`. Il reverse geocoding è cachato a circa 100 metri. Se Nominatim non risponde, vale la località della fonte.
5. **Id e deduplica**: l'id è l'hash SHA-1 di `sourceUrl` (20 caratteri), quindi lo stesso evento aggiorna lo stesso documento. Due siti che pubblicano lo stesso evento si uniscono con la chiave titolo normalizzato (minuscole, senza accenti né punteggiatura) + giorno + comune.
6. **Scrittura dei soli cambiamenti**: ogni evento ha `contentHash` (sha256 dei campi normalizzati, senza `updatedAt` e campi di servizio) e `importRegion` (regione del registro). All'inizio dell'import una sola query di proiezione (`select`) legge id, `contentHash`, `removedAt`, `missingRuns` e pochi altri campi degli eventi `scraper` delle regioni in elaborazione. Si scrivono, in batch da 400, solo i documenti nuovi o con hash diverso (e quelli da ripristinare dopo un `removedAt`). `createdAt` si conserva. Gli eventi con `source: "manual"` (modificati a mano dall'admin) non vengono mai sovrascritti. A fine import il log riporta letture, scritti, invariati, nascosti. **Se le scritture stimate superano `--max-writes` (15.000) o le letture `--max-reads` (40.000) l'import si ferma prima di scrivere** (codice di uscita 2).

   **Manifest locale**: per non rileggere ogni giorno tutti gli eventi, il confronto parte da `tools/importer/manifests/<regione>.json` (id → campi della proiezione), salvato nella cache di GitHub Actions insieme a `geocache.json`. La lettura di proiezione da Firestore (riconciliazione) avviene solo se il manifest manca, ha più di 8 giorni, non coincide col `token` del documento `importState/<regione>` (scritto prima e dopo ogni import: un run interrotto o una cache persa lasciano un segnaposto) oppure con `--reconcile` (input `reconcile` del workflow). **Scaglionamento**: ogni regione si riconcilia in un giorno fisso della settimana (`ci_report.reconcile_days`, assegnazione deterministica bilanciata per fonti attive) e il budget di letture del job è proporzionale al peso della regione, ×7 nel suo giorno; `python ci_report.py simulate` stampa le quote per giorno (report in `tools/importer/reports/copertura_ondata3.md`). Nel confronto da manifest si rileggono solo gli eventi `manual` e gli id non presenti (nuovi). Se un documento è sparito (`NotFound`), l'import rifà il giro con la riconciliazione completa. Le scritture sono idempotenti, quindi il fallback non crea duplicati né cancellazioni. Il riepilogo indica per regione la fonte del confronto (`manifest` o `firestore`) e le letture effettive.
7. **Scadenza e pulizia**: vedi "Pulizia automatica" qui sotto.
8. **Eventi spariti dalla fonte**: un evento `scraper` che non compare più nella lista di una fonte letta con successo (e inizia entro l'orizzonte) riceve `missingRuns`. Al 2° import consecutivo senza l'evento riceve `removedAt`: la webapp lo nasconde (`web/src/lib/server/firestore.ts`), non lo cancella. Se la fonte non risponde, il conteggio non cambia.

Le fonti sono scaricate in parallelo (4 worker, `WORKERS` in `run.py`); geocoding e scrittura restano in sequenza.

### Statistiche mensili: `stats/{regione}_{AAAA-MM}`

Ogni import scrive, per ogni regione elaborata, un documento del mese corrente (ora di Roma) con `events` (eventi attivi nel mese), `comuni` (comuni con almeno un evento), `cities` (le prime 10 città per eventi) e `name`. L'import vede solo eventi in corso o futuri, quindi il documento conserva anche gli id già contati nei giorni precedenti (campo `ids`, per comune) e li unisce a quelli del giorno: un evento finito a metà mese resta nel totale. Costo: 1 lettura e 1 scrittura per regione al giorno, contate in `reads`/`writes` delle statistiche dell'import. Non si scrivono con `--dry-run` né con `--source`.

La webapp li legge con una `batchGet` a maschera (esclude `ids`) per `/regione/[slug]` (mese corrente e precedente, 2 letture, cache 5 minuti) e con una query client-side per `/admin/statistiche`. Se il mese corrente non ha dati non si mostra nulla; se manca il precedente si mostra solo il numero del mese. Il confronto è perciò disponibile dal secondo mese di raccolta.

### Adapter HTML `design_comuni_html`

Per i siti Design Comuni Italia senza API degli eventi (`adapters/design_comuni_html.py`). Analisi e fixture: `reports/design_comuni_analisi.md`, `tests/fixtures/html/`.

- **Lista**: `url_eventi` del registro, poi `/vivere-il-comune/eventi/`, `/novita/eventi/`, `/eventi/`, `/evento/`; paginazione `rel=next` (al massimo 5 pagine). Le liste caricate via AJAX ("Carica altri risultati") non si seguono: la sitemap dichiarata in `robots.txt` integra la lista quando mancano eventi.
- **Dettaglio**, in ordine di priorità: JSON-LD `schema.org/Event`, microdata, link "Aggiungi al calendario" (Google Calendar), `.point-list` e Dal/Al, testo libero.
- **Limite**: al massimo 40 dettagli per comune a ogni import (`MAX_DETAILS`).
- **Cortesia**: `robots.txt` prima di ogni richiesta, 1 richiesta al secondo per host, retry con backoff, cache ETag/Last-Modified in `tools/importer/.httpcache` (risposta 304 senza riscaricare).
- **Limiti**: i feed `.ics` non sono letti. Drupal, Joomla, Halley e Maggioli non sono nei campioni analizzati.

### Comandi

```powershell
cd tools\importer
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q tests

python run.py --dry-run                 # stampa, non scrive, non servono credenziali
python run.py --dry-run --source modena # una sola fonte (nome = slug del comune)
python run.py --dry-run --regione lombardia --dump lombardia.json   # una regione, eventi in un file JSON
python run.py --regione veneto          # scrive su Firestore solo gli eventi cambiati di una regione
python run.py --stats-out stats.json    # statistiche dell'import (letture, scritture, invariati)
python run.py --max-geocode 1500        # richieste nuove a Nominatim per giro (default 3000)
python run.py --horizon-days 30         # orizzonte diverso (default 60)
python cleanup.py --dry-run             # conta cosa verrebbe eliminato
python cleanup.py                       # elimina eventi e proposte scaduti (al massimo 15.000 al giorno)
python geocode.py --clean               # ripulisce geocache.json, senza chiamare Nominatim
python copertura.py                     # reports/copertura_er.md: stima su campione (1 pagina, sitemap, max 10 dettagli per comune), senza geocoding e senza scrivere
python copertura.py --no-estimate       # solo i conteggi del registro
```

Le credenziali per la scrittura arrivano solo da variabili d'ambiente (vedi sezione 5). Con `GOOGLE_APPLICATION_CREDENTIALS` il file sta fuori dal repository. `.gitignore` esclude i file `*serviceAccount*.json` e `*-firebase-adminsdk-*.json`.

**Migrazione degli eventi esistenti.** `migrate.py` è una tantum: aggiunge `geohash`, `city`, `citySlug`, `province` e `region` agli eventi che non li hanno. Legge l'intera collezione una volta sola e fa il reverse geocoding con la cache. Gli eventi senza coordinate valide vengono elencati: vanno sistemati a mano in `/admin`.

```powershell
python migrate.py --dry-run    # mostra cosa cambierebbe, non scrive
python migrate.py              # scrive
```

**`geocode.py --clean`** toglie da `geocache.json` i "non trovato" (si riprovano alla prossima esecuzione) e i risultati fuori dal riquadro della provincia nominata nella query. Serve dopo aver corretto un riquadro o una query.

**`seed_demo.py`** carica 10 eventi demo con id `demo-01`…`demo-10`; con `--delete` li rimuove. Funziona **solo con l'emulatore Firestore**: `FIRESTORE_EMULATOR_HOST` deve essere impostato su `127.0.0.1`, `localhost` o `[::1]`, altrimenti lo script si ferma con un errore. Usa il progetto `demo-eventi` e non legge le credenziali, quindi non può scrivere sul progetto reale. Con l'emulatore avviato (`npm run emulators`, da `web/`):

```powershell
$env:FIRESTORE_EMULATOR_HOST = "127.0.0.1:8080"
python seed_demo.py
```

### GitHub Action

`.github/workflows/import-events.yml`:

- Esecuzione ogni giorno alle **08:17 UTC**, cioè 09:17 in Italia con l'ora solare e 10:17 con l'ora legale (`cron: "17 8 * * *"`, senza `timezone`). Va dopo il reset della quota Firestore (mezzanotte del Pacifico = 07:00 o 08:00 UTC, 08:00/09:00 in Italia): così l'import non intacca le letture del giorno prima.
- Avvio manuale: **Actions → Import eventi → Run workflow**, con le opzioni `dry_run` e `regione` (slug, per esempio `lombardia`).
- Job `plan`: gira `pytest` e `ci_report.py matrix`, che elenca le regioni con almeno una fonte attiva e divide le soglie di quota tra i job.
- Job `import`: **una matrice per regione**, 4 in parallelo (`max-parallel: 4`), timeout 330 minuti (limite GitHub 360). Ogni job ha `NOMINATIM_INTERVAL=4`, cioè 0,25 richieste al secondo: quattro job insieme restano a 1 richiesta al secondo in tutto, come chiede la policy di Nominatim. `geocache.json` e `.httpcache` sono salvati con `actions/cache` **per regione** (chiave `importer-<regione>-<run>`).
- Job `cleanup`: gira dopo gli import, anche se una regione è fallita, ed esegue `cleanup.py`.
- Un solo riepilogo in `GITHUB_STEP_SUMMARY` (job `cleanup`): eventi per regione, letture, scritture, invariati, richieste di geocoding, e le quote Spark usate.
- Durata: i repository pubblici hanno minuti gratuiti sui runner standard; il limite di GitHub per job è 6 ore. Il tempo dominante sono le richieste ai siti dei comuni (1 al secondo per host) e il geocoding (vedi sezione 10).
- Concorrenza: gruppo `import-events`, senza annullare l'esecuzione in corso.
- Secret richiesto: **`FIREBASE_SERVICE_ACCOUNT`** (Settings → Secrets and variables → Actions). Il valore è l'intero JSON della chiave del service account.

Per generare la chiave: Console Firebase → Impostazioni progetto → Account di servizio → Firebase Admin SDK → Genera nuova chiave privata. Il file va spostato fuori dal repository. Per revocarla: Google Cloud Console → IAM → Account di servizio → scheda Chiavi → elimina la chiave, poi aggiorna il secret.

### Pulizia automatica

`cleanup.py` gira ogni giorno dopo l'import. Le query usano solo indici a campo singolo, con proiezione dei campi.

| cosa | quando si elimina |
|---|---|
| eventi `scraper` | finiti da più di 7 giorni |
| eventi con `removedAt` | da più di 30 giorni |
| eventi `manual` e `user` | finiti da più di 30 giorni |
| proposte rifiutate | `reviewedAt` da più di 90 giorni |
| proposte approvate | `reviewedAt` da più di 30 giorni |

Le cancellazioni sono a lotti da 400 e non superano `--max-deletes` (15.000 al giorno, la quota Spark è 20.000): il resto passa al giorno dopo. Le proposte `pending` non si toccano mai.

### Registro delle fonti: `sources/<regione>.csv`

Un file per regione (`emilia-romagna.csv`, `lombardia.csv`, …). `registry.read_rows()` li legge tutti; `write_rows()` li riscrive divisi per regione. Il file è in UTF-8 con BOM, separatore `;`, si apre in Excel. Colonne:

`regione;provincia;comune;codice_istat;sito;url_eventi;cms;fornitore;stato;licenza;robots_ok;note`

`fornitore` è la piattaforma riconosciuta da `detect_cms.py` (WordPress, Drupal, ComWeb, ASP.NET, ecc.), vuota se non si capisce. Compare nel riepilogo `--report` e in `copertura.py`.

Stati (colonna `stato`):

| stato | significato |
|---|---|
| `da_verificare` | riga nuova o dubbia. Gli script la analizzano, ma non è attiva. |
| `candidato` | CMS supportato, robots.txt consente l'accesso e la licenza è aperta. Serve la tua conferma. |
| `escluso` | robots.txt vieta l'accesso, oppure la licenza è restrittiva (NC/ND, riservata). |
| `attivo` | l'importer legge questa fonte. Lo imposta `activate.py` con la regola automatica (vedi sotto) o tu a mano. |
| `manuale` | gestita a mano. Gli script automatici non la toccano mai. |

Stato al momento della stesura (da `comuni.csv`, 330 comuni): 4 `attivo` (Formigine, Mirandola, Modena, Sassuolo, tutti Plone), 23 `candidato`, 274 `da_verificare`, 29 `escluso`. Per CMS: 52 `plone`, 21 `wordpress-dci`, 237 `altro`, 20 `irraggiungibile`.

**`build_registry.py`** genera o aggiorna il registro dagli open data:

- comuni da ISTAT, "Elenco dei comuni italiani" (CC-BY 3.0 IT);
- siti istituzionali da IndicePA, "Amministrazioni" (CC-BY 4.0).

Si indica `--regione <nome>` (ripetibile) oppure `--tutte`; senza argomenti dà errore. Le righe `attivo` e `manuale` non vengono toccate. Le altre aggiornano regione, provincia, comune e sito. I comuni nuovi entrano come `da_verificare`. Se il sito cambia, il rilevamento precedente viene azzerato.

**`detect_cms.py`** visita i siti del registro:

- Rispetta `robots.txt` prima di ogni richiesta. Se il robots.txt non è raggiungibile (errore 5xx o rete), non visita nulla.
- Al massimo 1 richiesta al secondo per sito. User-Agent identificativo (`EventiVicini-importer/1.0`).
- Riconosce il CMS: `plone` (design-comuni-plone), `wordpress-dci` (design-comuni-italia o design-comuni-wordpress), `design_comuni_html` (modello Design Comuni dai marcatori dell'HTML, senza API) oppure `altro`.
- Cerca la pagina eventi e la pagina delle note legali, e ricava la licenza dal loro testo (o dal piè di pagina, come ripiego).
- Non tocca mai le righe `attivo` o `manuale`. Non attiva nessuna fonte: al massimo propone `candidato`.

```powershell
cd tools\importer
python detect_cms.py                  # righe non ancora analizzate
python detect_cms.py --comune Modena  # una riga (ripetibile)
python detect_cms.py --force          # rianalizza anche le righe già fatte
python detect_cms.py --report         # solo il riepilogo, senza visitare nulla
python detect_cms.py --regione lombardia --regione veneto   # solo queste regioni
```

Usa la cache HTTP (`.httpcache`, risposte 304) e, a fine giro, riprova una volta i siti `irraggiungibili`.

Solo fonti con licenza che consente il riuso (CC0, CC-BY, CC-BY-SA, IODL). Mai testate giornalistiche o siti commerciali.

### Licenze: `licenses.py`

`python licenses.py` verifica la licenza dei contenuti dei siti candidati (più Modena, Formigine, Sassuolo e Mirandola). Cerca le pagine di note legali e privacy, estrae la frase sulla licenza e scrive `reports/licenze_er.md`. Legge il `robots.txt` con `protego`, con 1 richiesta al secondo per sito. Aggiorna le colonne `licenza` e `note` dei CSV, mai `stato`; `--no-csv` non tocca i CSV. `--regione` limita a una regione. La nota comincia con `licenza[attivare|da|escludere]` (la raccomandazione) e, se il sito contiene "esclusiva proprietà" o "tutti i diritti riservati", con `conflitto`: `activate.py` legge questi marcatori. Le etichette `CC-BY-NC` e `CC-BY-ND` sono distinte. Le licenze "non chiara" o "non trovata" vanno lette a mano. Per tutti i comuni con un CMS: `python licenses.py --cms design_comuni_html --out reports/licenze_design_comuni.md` (non solo i candidati).

### Attivazione automatica: `activate.py`

Regola approvata, applicata a tutte le righe `da_verificare` e `candidato` (mai a `manuale`, `escluso` e `attivo`). Una riga diventa `attivo` **solo se**:

- a) esiste un adapter per il suo CMS (`plone`, `wordpress-dci`, `design_comuni_html`);
- b) `licenses.py` ha trovato la licenza dei **contenuti** (formula AGID sulle note legali): CC0 o CC-BY, senza NC, ND, SA, "esclusiva proprietà" o "tutti i diritti riservati";
- c) il `robots.txt` permette i percorsi usati (colonna `robots_ok` e controllo di `licenses.py`);
- d) il dry-run del comune produce almeno 1 evento futuro valido: titolo, date e coordinate dentro la provincia (se la fonte non dà le coordinate vale il centro del comune, una richiesta a Nominatim per comune).

Le altre restano `da_verificare` con il motivo all'inizio della colonna `note` (`attivazione: …`). Ordine dei comandi per una regione nuova:

```powershell
python build_registry.py --regione Lombardia
python detect_cms.py --regione lombardia
python licenses.py --regione lombardia --out reports/licenze_lombardia.md
python activate.py --regione lombardia --dry-run   # tabella senza scrivere
python activate.py --regione lombardia
```

### Ricontrollo settimanale: `recheck-sources.yml`

Molti comuni sono respinti con "nessun evento futuro valido" solo perché in quel momento non avevano eventi (fuori stagione). Ogni **domenica alle 23:00 ora italiana** il workflow riesegue `activate.py --tutte --only-reason "nessun evento futuro valido"`: rivaluta solo le righe `da_verificare` respinte per quel motivo e attiva quelle che ora rispettano **tutte** le condizioni a–d (le condizioni a–c sono quelle già registrate nel CSV, non vengono ricontrollate sui siti; il dry-run sì).

- Riepilogo in `GITHUB_STEP_SUMMARY`: per regione, comuni rivalutati, attivati (con i nomi) e ancora respinti.
- Se qualcosa cambia, il workflow fa il commit di `tools/importer/sources/*.csv` ("Ricontrollo settimanale: attivate N fonti…") e lo manda a `main` con `GITHUB_TOKEN` (permesso `contents: write`). L'import del lunedì mattina (08:17 UTC) trova le nuove fonti già attive. Se `main` ha una regola di protezione che vieta il push al bot, il passaggio di commit fallisce: consenti al bot o apri una PR a mano.
- Avvio manuale: Actions → Ricontrollo fonti → Run workflow (con `dry_run` non modifica nulla). Stessa cosa in locale: `python activate.py --tutte --only-reason "nessun evento futuro valido" --dry-run`.
- Durata stimata 1-2 ore con circa 1.000 comuni (12 in parallelo, 1 richiesta al secondo per sito); timeout 240 minuti. Il commit del bot non rilancia altri workflow.

### Attivare una fonte a mano

1. Verifica a mano la pagina eventi, le note legali (licenza, obbligo di citare la fonte, uso non commerciale se previsto) e il `robots.txt`.
2. Controlla che il CMS sia `plone`, `wordpress-dci` o `design_comuni_html`. L'importer legge solo i CMS con un adapter: una riga con un altro CMS viene saltata con un avviso.
3. Nel CSV imposta `stato` a `attivo` e compila le note con la verifica fatta.
4. Prova con `python run.py --dry-run --source <slug>`. Lo slug è il nome del comune in minuscolo con trattini (es. `modena`).

### Aggiungere un adapter per un nuovo CMS

L'interfaccia è in `adapters/base.py`, un `Protocol` con gli attributi `name`, `city`, `province`, `region`, `viewbox` e il metodo `events(client, now, horizon_days)`. Il metodo restituisce dict nel modello dell'app, con almeno: `id`, `title`, `shortDescription`, `category`, `priceType`, `startTime`, `endTime` (ms), `venueName`, `address`, `lat`, `lng` (`None` se da geocodificare), `imageUrl`, `ticketUrl`, `tags`, `source` (`"scraper"`), `sourceUrl` e `_geocode` (indirizzi da provare con Nominatim, in ordine).

Passi:

1. Crea `adapters/<cms>.py` con una classe che implementa l'interfaccia. Imposta `id` (ad esempio `mapping.event_id(sourceUrl)`): `run.py` lo richiede. La docstring di `base.py` dice "senza id", ma `write()` usa `ev["id"]`.
2. In `adapters/__init__.py`, in `load_sources()`, aggiungi un ramo per il valore `cms` del CSV, oltre a quello di `plone`, e il nome in `CMS_ADAPTERS` (lo legge anche `activate.py`).
3. Scrivi un test con una fixture salvata, in `tests/`.

`mapping.to_event()` è specifico per il formato Plone. Un nuovo adapter non lo riusa: produce il suo dict. Geocoding, località, geohash, deduplica e scrittura restano in `run.py`.

**Stato attuale:** adapter per Plone (`plone`), WordPress Design Comuni Italia (`wordpress-dci`) e Design Comuni HTML senza API (`design_comuni_html`). Gli altri CMS non sono importabili.

---

## 10. Stima delle letture Firestore

Quote del piano Spark al giorno: 50.000 letture, 20.000 scritture, 20.000 cancellazioni, 1 GB.

### Misure sull'emulatore (`npm run test:reads`, dati di seed)

A freddo (cache vuota). «Reali» = massimo con dati veri (somma dei `limit` delle query). Il test fallisce se una rotta supera il suo budget.

| rotta | letture (seed) | richieste | reali, al massimo |
|---|---|---|---|
| `/` senza luogo | 4 | 1 | 4 |
| `/?luogo=modena` (25 km) | 11 | 5 | 504 |
| `/?luogo=bologna&r=100` | 20 | 13 | 1.504 |
| `/?luogo=sconosciuto` (prima 13 / 624: caricava anche Modena) | 6 | 3 | 124 |
| `/api/events` (stessa chiave della home) | 7 | 4 | 500 |
| `/api/places` | 4 | 1 | 4 |
| `/citta/modena` | 4 | 3 | 201 |
| `/regione/emilia-romagna` | 3 | 2 | 3 |
| `/eventi/[slug]` | 1 | 1 | 1 |
| `/sitemap.xml` (prima fino a 2.004) | 14 | 2 | 504 |
| ripetizione, o stessa cella ~5 km | 0 | 0 | 0 |

**Cache a due livelli** (`lib/server/firestore.ts`): memoria dell'isolate e Cache API di Cloudflare (per data center, vale anche tra isolate e deploy). Liste 6 ore, evento/copertura 1 ora, sitemap 12 ore. Scaduta la freschezza si rilegge; se Firestore risponde 429 (quota esaurita) o è giù si serve l'ultima copia (fino a 2 giorni) e per 10 minuti non lo si richiama. Home e `/api/events` interrogano lo stesso punto della griglia di ~5 km, quindi condividono la chiave. Le pagine HTML restano a 5 minuti all'edge (vedi il punto 7 del deploy): costano zero letture perché i dati sono già in cache.

Limite noto: una lista non in cache costa un documento per evento (non 1-2); per scendere ancora servirebbero liste precalcolate dall'importer (un documento per città o regione) o Cloudflare KV.

### Import a regime (dry-run di Emilia-Romagna, Lombardia, Veneto, Toscana)

| regione | comuni attivi | eventi | 1° import: letture / scritture | 2° giorno: letture / scritture |
|---|---|---|---|---|
| Emilia-Romagna | 66 | 505 | 506 / 506 | 506 / 1 |
| Lombardia | 255 | 1.405 | 1.406 / 1.406 | 1.407 / 1 |
| Veneto | 157 | 738 | 739 / 739 | 739 / 1 |
| Toscana | 54 | 220 | 221 / 221 | 221 / 1 |
| **Totale** | **532** | **2.868** | **2.872 / 2.872** | **2.873 / 4** |

Le scritture del secondo giorno sono il documento `coverage/{regione}` (una per regione); in pratica si aggiungono gli eventi nuovi o modificati del giorno (qualche punto percento). Le letture dell'import sono gli eventi scraper della regione già presenti, compresi quelli finiti da meno di 7 giorni (circa +30%). Con la pulizia (alcune centinaia di letture e cancellazioni) siamo sotto il 10% della quota di letture e sotto il 5% di quella di scritture e cancellazioni. Il primo import di una regione grande va fatto a tappe (vedi `FINAL_REPORT.md`).

### Stima dalle formule (traffico)

Stima ricavata dal codice (`web/src/lib/server/firestore.ts`, `cache.ts`, `geo.ts`, `api/events`).

**Come si legge una ricerca per raggio.** `eventsNear(centro, km)` chiama `radiusBounds`, che usa `geohashQueryBounds` di `geofire-common`. Questa funzione genera 9 punti (centro, quattro lati, quattro angoli) e li trasforma in intervalli di geohash, poi rimuove i duplicati. Quindi una ricerca fa da 1 a 9 query, ciascuna con `where geohash in [inizio, fine]` e `endTime >= ora`, limitata a `PER_CELL_LIMIT = 150` documenti.

**Formula per una cache miss:**

```
letture_miss(eventsNear) = somma su Q query di max(1, documenti_restituiti)
                         ~= eventi futuri nei riquadri di geohash  (+ 1 per ogni query vuota)
```

Dove `Q` è il numero di intervalli dopo deduplica (da 1 a 9). Il `max(1, …)` segue l'ipotesi del codice: una query vuota costa comunque una lettura.

**Cache.** Più livelli, tutti per isolate (il Worker può avere più isolate, non condivisi):

- **Memoria del Worker**: TTL di 5 minuti. Chiavi: `near:lat,lng,km` (home e `/api/events`), `city:slug`, `upcoming:n`, `event:id`. Il limite di 300 voci è gestito per eliminazione della più vecchia.
- **Cache HTTP delle pagine**: `public, max-age=60, s-maxage=300, stale-while-revalidate=60` (`HTML_CACHE`) su home, città ed evento.
- **Cache HTTP di `/api/events`**: `s-maxage=1800` con `stale-while-revalidate=86400`. Le coordinate sono arrotondate a 0,05° (circa 5 km), quindi molti utenti condividono la stessa chiave.

**Visita con cache hit: 0 letture.** Una visita alla home nella stessa finestra di 5 minuti di un isolate già caldo non legge Firestore. Lo stesso vale per la cache HTTP dell'edge, se Cloudflare la applica alle risposte SSR (da verificare in produzione).

**Visita con cache miss.** Costa `letture_miss` per la chiave di quell'isolate. Per il dettaglio di un evento, una lettura per id (`getEvent`), con il tetto di 1 lettura per miss. Per una città, fino a 100 letture (`limit` di `eventsInCity`).

**Ordine di grandezza.** Dipende da due numeri che non si conoscono (eventi futuri nell'area, traffico per finestra):

- Per la home si ha, al massimo, una miss per finestra di 5 minuti per isolate attivo: fino a 288 miss al giorno per isolate. Con 60 eventi nei riquadri, un isolate sempre caldo costa circa 17.000 letture al giorno (288 × 60). Due isolate sempre caldi superano la metà della quota.
- Il caso realistico è molto più basso: una finestra costa letture solo se arriva almeno una richiesta. Con traffico modesto, il costo scala con il numero di finestre con traffico, non con il numero di visite.
- Quindi il limite sostenibile non sono le visite in sé: con cache calda, decine di migliaia di visite al giorno costano relativamente poco. I limiti più probabili sono le quote Cloudflare (richieste e CPU del piano gratuito, da verificare nella documentazione) e il numero di isolate.

**Incertezze:**

- Il numero di eventi nei riquadri non è misurato: dipende dai dati importati.
- Il numero di intervalli dopo deduplica (da 1 a 9) non è misurato.
- Non è verificato se Firestore addebita una lettura per query vuota (il codice lo assume).
- Non è verificato il comportamento della cache HTTP dell'edge di Cloudflare per le risposte SSR.
- Il ciclo di vita degli isolate (quanto restano caldi) è deciso da Cloudflare.
- Per misurare davvero: usare la console Firebase (uso delle letture) o aggiungere un log di `readCount` (oggi non esiste).

---

## 11. Privacy

- Nessun analytics, nessun pixel, nessun banner dei cookie. Non ci sono cookie di profilazione.
- Archiviazione locale (localStorage) per preferiti, posizione e tema. Con l'account, i preferiti vengono anche salvati in Firestore sotto `users/{uid}/favorites`.
- Firebase Authentication: la sessione di accesso è gestita dall'SDK di Firebase, in IndexedDB e localStorage.
- Account facoltativo: serve per sincronizzare preferiti e proporre eventi. Età minima **14 anni** (art. 2-quinquies del Codice privacy).
- `/privacy` e `/termini` riportano titolare e contatto da `CONTROLLER_NAME` e `CONTACT_EMAIL`.
- L'indirizzo di aggiornamento (`updated`) in `web/src/lib/server/legal.ts` è scritto a mano: va cambiato quando cambiano le pagine.
- L'API `/api/geocode` non salva nulla e non passa l'IP dell'utente a Nominatim.

---

## 12. Problemi noti e prossimi passi

### Limiti noti

- **Cache HTML di 5 minuti**: dopo un deploy, una pagina vecchia può restare fino a 5 minuti e puntare a file JS non più esistenti. Usa "Purge cache" su Cloudflare.
- **Limite per cella**: `PER_CELL_LIMIT = 150` per intervallo di geohash, ordinato per fine evento e poi per geohash (non per distanza dal centro). In una zona con più di 150 eventi futuri, vengono scartati quelli che finiscono più tardi. A parità di fine evento vale il geohash.
- **Cache e rate limit per isolate**: la cache in memoria e il limite di 1 richiesta al secondo verso Nominatim valgono per ogni isolate, non globalmente. Con molto traffico servono un geocoder self-hosted (Photon o Nominatim) o una cache condivisa (KV).
- **Tile OpenStreetMap**: le tile pubbliche non sono ammesse per traffico intenso. Il progetto le usa direttamente dal browser. Con molto traffico va cambiato provider di tile.
- **Importer WordPress: solo REST**. Cesena, Ravenna e Serramazzoni non espongono eventi via REST e non c'è un fallback iCal o RSS.
- **Importer: nessun controllo robots.txt a ogni esecuzione**. Il controllo è fatto da `detect_cms.py` quando la riga viene analizzata. gli adapter non lo ripetono.
- **Importer scrive con Admin SDK**: le regole Firestore non validano i dati scritti dall'importer.
- **Geocoding in Lombardia**: il primo giro ha circa 1.440 richieste nuove a Nominatim; con il budget di 3.000 per giro entrano tutte, ma con `NOMINATIM_INTERVAL=2` (due job in parallelo) servono circa 50 minuti. Se il budget finisce, gli eventi senza geocoding restano col centro del comune (`approxLocation`) e si sistemano nei giorni dopo.
- **Cache di Actions**: la cache HTTP pesa circa 1 MB per comune attivo; con 500 comuni sono centinaia di MB per giro e GitHub tiene al massimo 10 GB per repository (le più vecchie vengono eliminate).
- **Nessun adapter per Drupal, Joomla, Halley, Maggioli**: restano `da_verificare`.
- **Date legali**: la data di aggiornamento di `/privacy` e `/termini` è scritta a mano.

### Prossimi passi

- Eseguire il primo deploy su Cloudflare Pages e verificare le variabili di produzione.
- Configurare Authentication (Google e link via email) e i domini autorizzati, poi `npm run deploy:rules`.
- Verificare le letture reali su Firebase per una settimana e rivedere la sezione 10.
- Controllare a campione le fonti attivate in automatico (`activate.py`) e rivedere i motivi di rifiuto nelle note, soprattutto "nessun evento futuro valido" (1.019 comuni nella prima ondata: molti sono fuori stagione, alcuni hanno liste che l'adapter non legge).
- Prossime ondate di regioni: vedi `FINAL_REPORT.md`.
- Impacchettare la webapp con **Capacitor** per Android e iOS (da valutare: il login Google e l'auth nativa richiedono una configurazione dedicata, e la policy delle tile OSM va rispettata anche nell'app).
