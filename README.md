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
                       /api/events, /api/geocode, sitemap.xml, robots.txt, /offline
    lib/
      server/          firestore.ts (lettura REST), cache.ts (header di cache), legal.ts
      firebase/        caricamento lazy dell'SDK Firebase lato browser
      components/      componenti Svelte
      event.ts         modello Event, validazione, limiti dei campi
      geo.ts           raggi, geohash, griglia della cache, distanza
      geocode.ts       ricerca comuni e indirizzi via /api/geocode
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
  run.py               importer: raccolta, geocoding, deduplica, scrittura
  migrate.py           migrazione una tantum degli eventi esistenti
  adapters/            fonti: base.py (interfaccia), plone.py, __init__.py (registro)
  sources/comuni.csv   registro delle fonti (comuni, CMS, licenza, stato)
  build_registry.py    genera il registro da ISTAT e IndicePA
  detect_cms.py        riconosce CMS, pagina eventi e licenza dei comuni
  geo.py, geocode.py, mapping.py, registry.py, db.py
  seed_demo.py         10 eventi demo (scrive sul progetto reale: vedi sezione 9)
  tests/               test pytest con fixture

.github/workflows/
  ci.yml               controlli della webapp e test delle regole
  import-events.yml    import giornaliero dell'importer
```

---

## 4. Avvio in locale

### Requisiti

- **Node.js 22 o superiore** (`engines` in `web/package.json`).
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

- **job `web`** (Ubuntu, Node 22, `npm ci` in `web/`): `npm run check`, `npm run lint`, `npm test`, `npm run build`.
- **job `rules`** (Ubuntu, Node 22, Temurin JDK 21, `npm ci` in `firebase/`): `npm test` (test delle regole con emulatore).

La CI non esegue i test E2E Playwright. Il test dell'importer gira nel workflow `import-events.yml`, prima dell'import.

---

## 7. Deploy su Cloudflare Pages

Nessun deploy è stato ancora fatto. Questi sono i passi da eseguire.

1. Dashboard Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**. Scegli il repository GitHub.
2. Impostazioni del build:
   - **Root directory**: `web`
   - **Build command**: `npm run build`
   - **Build output directory**: `.svelte-kit/cloudflare`
3. Versione di Node: il progetto richiede Node 22 o superiore (`engines`). Il repository non fissa la versione del build su Cloudflare: impostala tu nelle variabili di build, se necessario.
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
- Tutto il resto è chiuso (`allow read, write: if false`).

Indici composti: `events` per `geohash` + `endTime` e per `citySlug` + `endTime`; `submissions` per `ownerId` + `createdAt` e per `status` + `createdAt`.

---

## 9. Importer

Il codice è in `tools/importer/`. Legge gli eventi pubblici dei comuni e li scrive nella collezione `events`.

### Come funziona

1. **Adapter per fonte**: ogni fonte attiva ha un adapter (oggi solo Plone, in `adapters/plone.py`). Legge la API paginata (`++api++/@search`), con una richiesta al secondo.
2. **Normalizzazione** (`mapping.py`): categoria dalla tipologia o dal titolo, prezzo dal testo, fuso `Europe/Rome`, prossima occorrenza per gli eventi ricorrenti, orario reale dal campo `orari` quando quello inserito è fittizio. Si importano gli eventi in corso o che iniziano entro 60 giorni (`--horizon-days`).
3. **Coordinate**: dal campo geolocalizzato; altrimenti Nominatim sugli indirizzi (con `viewbox` per la provincia di Modena), con cache in `geocache.json`.
4. **Località su ogni evento**: `enrich()` in `geo.py` scrive `geohash` (precisione 10, stesso algoritmo di `geofire-common`), `city`, `citySlug`, `province` e `region`. Il reverse geocoding è cachato a circa 100 metri. Se Nominatim non risponde, vale la località della fonte.
5. **Id e deduplica**: l'id è l'hash SHA-1 di `sourceUrl` (20 caratteri), quindi lo stesso evento aggiorna lo stesso documento. Due comuni che pubblicano lo stesso evento si uniscono con la chiave titolo + giorno + luogo.
6. **Scrittura**: upsert in batch da 400. `createdAt` si conserva. Gli eventi con `source: "manual"` (modificati a mano dall'admin) non vengono mai sovrascritti.
7. **Scadenza**: gli eventi `scraper` finiti da più di 7 giorni vengono eliminati. Gli eventi manuali restano.

### Comandi

```powershell
cd tools\importer
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q tests

python run.py --dry-run                 # stampa, non scrive, non servono credenziali
python run.py --dry-run --source modena # una sola fonte (nome = slug del comune)
python run.py                           # scrive su Firestore
python run.py --horizon-days 30         # orizzonte diverso (default 60)
```

Le credenziali per la scrittura arrivano solo da variabili d'ambiente (vedi sezione 5). Con `GOOGLE_APPLICATION_CREDENTIALS` il file sta fuori dal repository. `.gitignore` esclude i file `*serviceAccount*.json` e `*-firebase-adminsdk-*.json`.

**Migrazione degli eventi esistenti.** `migrate.py` è una tantum: aggiunge `geohash`, `city`, `citySlug`, `province` e `region` agli eventi che non li hanno. Legge l'intera collezione una volta sola e fa il reverse geocoding con la cache. Gli eventi senza coordinate valide vengono elencati: vanno sistemati a mano in `/admin`.

```powershell
python migrate.py --dry-run    # mostra cosa cambierebbe, non scrive
python migrate.py              # scrive
```

**Attenzione: `seed_demo.py`** carica 10 eventi demo con id `demo-01`…`demo-10` e con `--delete` li rimuove. Usa `db.py`, che punta sempre al progetto reale `appeventi-1e860`: non esiste una modalità emulatore. Non eseguirlo se non vuoi scrivere sul database di produzione.

### GitHub Action

`.github/workflows/import-events.yml`:

- Esecuzione ogni giorno alle **06:17 ora italiana** (`cron` con `timezone: Europe/Rome`).
- Avvio manuale: **Actions → Import eventi → Run workflow**, con l'opzione `dry_run`.
- Prima dell'import gira `pytest`. La cache di `geocache.json` è salvata con `actions/cache`.
- Concorrenza: gruppo `import-events`, senza annullare l'esecuzione in corso.
- Secret richiesto: **`FIREBASE_SERVICE_ACCOUNT`** (Settings → Secrets and variables → Actions). Il valore è l'intero JSON della chiave del service account.

Per generare la chiave: Console Firebase → Impostazioni progetto → Account di servizio → Firebase Admin SDK → Genera nuova chiave privata. Il file va spostato fuori dal repository. Per revocarla: Google Cloud Console → IAM → Account di servizio → scheda Chiavi → elimina la chiave, poi aggiorna il secret.

### Registro delle fonti: `sources/comuni.csv`

Il file è in UTF-8 con BOM, separatore `;`, si apre in Excel. Colonne:

`regione;provincia;comune;codice_istat;sito;url_eventi;cms;stato;licenza;robots_ok;note`

Stati (colonna `stato`):

| stato | significato |
|---|---|
| `da_verificare` | riga nuova o dubbia. Gli script la analizzano, ma non è attiva. |
| `candidato` | CMS supportato, robots.txt consente l'accesso e la licenza è aperta. Serve la tua conferma. |
| `escluso` | robots.txt vieta l'accesso, oppure la licenza è restrittiva (NC/ND, riservata). |
| `attivo` | l'importer legge questa fonte. Lo imposti tu a mano. |
| `manuale` | gestita a mano. Gli script automatici non la toccano mai. |

Stato al momento della stesura (da `comuni.csv`, 330 comuni): 4 `attivo` (Formigine, Mirandola, Modena, Sassuolo, tutti Plone), 15 `candidato`, 310 `da_verificare`, 1 `escluso`. Per 226 righe il CMS non è ancora stato rilevato.

**`build_registry.py`** genera o aggiorna il registro dagli open data:

- comuni da ISTAT, "Elenco dei comuni italiani" (CC-BY 3.0 IT);
- siti istituzionali da IndicePA, "Amministrazioni" (CC-BY 4.0).

Di default prende l'Emilia-Romagna (`--regione` è ripetibile per altre regioni). Le righe `attivo` e `manuale` non vengono toccate. Le altre aggiornano regione, provincia, comune e sito. I comuni nuovi entrano come `da_verificare`. Se il sito cambia, il rilevamento precedente viene azzerato.

**`detect_cms.py`** visita i siti del registro:

- Rispetta `robots.txt` prima di ogni richiesta. Se il robots.txt non è raggiungibile (errore 5xx o rete), non visita nulla.
- Al massimo 1 richiesta al secondo per sito. User-Agent identificativo (`EventiVicini-importer/1.0`).
- Riconosce il CMS: `plone` (design-comuni-plone), `wordpress-dci` (design-comuni-italia o design-comuni-wordpress) oppure `altro`.
- Cerca la pagina eventi e la pagina delle note legali, e ricava la licenza dal loro testo (o dal piè di pagina, come ripiego).
- Non tocca mai le righe `attivo` o `manuale`. Non attiva nessuna fonte: al massimo propone `candidato`.

```powershell
cd tools\importer
python detect_cms.py                  # righe non ancora analizzate
python detect_cms.py --comune Modena  # una riga (ripetibile)
python detect_cms.py --force          # rianalizza anche le righe già fatte
python detect_cms.py --report         # solo il riepilogo, senza visitare nulla
```

Solo fonti con licenza che consente il riuso (CC0, CC-BY, CC-BY-SA, IODL). Mai testate giornalistiche o siti commerciali.

### Attivare una fonte

1. Verifica a mano la pagina eventi, le note legali (licenza, obbligo di citare la fonte, uso non commerciale se previsto) e il `robots.txt`.
2. Controlla che il CMS sia `plone`. L'importer oggi legge solo quello: una riga con un altro CMS viene saltata con un avviso.
3. Nel CSV imposta `stato` a `attivo` e compila le note con la verifica fatta.
4. Prova con `python run.py --dry-run --source <slug>`. Lo slug è il nome del comune in minuscolo con trattini (es. `modena`).

### Aggiungere un adapter per un nuovo CMS

L'interfaccia è in `adapters/base.py`, un `Protocol` con gli attributi `name`, `city`, `province`, `region`, `viewbox` e il metodo `events(client, now, horizon_days)`. Il metodo restituisce dict nel modello dell'app, con almeno: `id`, `title`, `shortDescription`, `category`, `priceType`, `startTime`, `endTime` (ms), `venueName`, `address`, `lat`, `lng` (`None` se da geocodificare), `imageUrl`, `ticketUrl`, `tags`, `source` (`"scraper"`), `sourceUrl` e `_geocode` (indirizzi da provare con Nominatim, in ordine).

Passi:

1. Crea `adapters/<cms>.py` con una classe che implementa l'interfaccia. Imposta `id` (ad esempio `mapping.event_id(sourceUrl)`): `run.py` lo richiede. La docstring di `base.py` dice "senza id", ma `write()` usa `ev["id"]`.
2. In `adapters/__init__.py`, in `load_sources()`, aggiungi un ramo per il valore `cms` del CSV, oltre a quello di `plone`.
3. Scrivi un test con una fixture salvata, in `tests/`.

`mapping.to_event()` è specifico per il formato Plone. Un nuovo adapter non lo riusa: produce il suo dict. Geocoding, località, geohash, deduplica e scrittura restano in `run.py`.

**Stato attuale:** gli adapter esistenti sono solo per Plone. I comuni con WordPress (`wordpress-dci`) sono candidati nel registro, ma non sono ancora importabili.

---

## 10. Stima delle letture Firestore

Quota del piano Spark: 50.000 letture al giorno. Stima ricavata dal codice (`web/src/lib/server/firestore.ts`, `cache.ts`, `geo.ts`, `api/events`). Nessuna misura reale: `readCount` esiste nel codice ma non viene scritto in nessun log.

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
- **Limite per geohash**: `PER_CELL_LIMIT = 150` è applicato in ordine di geohash, non di data o di distanza. In una zona con più di 150 eventi futuri, alcuni vengono scartati senza criterio di priorità.
- **Cache e rate limit per isolate**: la cache in memoria e il limite di 1 richiesta al secondo verso Nominatim valgono per ogni isolate, non globalmente. Con molto traffico servono un geocoder self-hosted (Photon o Nominatim) o una cache condivisa (KV).
- **Tile OpenStreetMap**: le tile pubbliche non sono ammesse per traffico intenso. Il progetto le usa direttamente dal browser. Con molto traffico va cambiato provider di tile.
- **Importer: solo Plone**. I comuni WordPress non sono ancora importabili.
- **Importer: nessun controllo robots.txt a ogni esecuzione**. Il controllo è fatto da `detect_cms.py` quando la riga viene analizzata. `plone.py` non lo ripete.
- **Importer scrive con Admin SDK**: le regole Firestore non validano i dati scritti dall'importer.
- **`seed_demo.py` scrive sul progetto reale** (vedi sezione 9).
- **Date legali**: la data di aggiornamento di `/privacy` e `/termini` è scritta a mano.
- **Modifiche non committate**: all'analisi, `tools/importer/` aveva modifiche e file nuovi non ancora in git (`build_registry.py`, `detect_cms.py`, `registry.py`, `sources/`).

### Prossimi passi

- Eseguire il primo deploy su Cloudflare Pages e verificare le variabili di produzione.
- Configurare Authentication (Google e link via email) e i domini autorizzati, poi `npm run deploy:rules`.
- Verificare le letture reali su Firebase per una settimana e rivedere la sezione 10.
- Verificare le fonti in `comuni.csv` a mano e attivarne altre, dopo la verifica.
- Adapter WordPress (`wordpress-dci`) per i candidati già nel registro.
- Impacchettare la webapp con **Capacitor** per Android e iOS (da valutare: il login Google e l'auth nativa richiedono una configurazione dedicata, e la policy delle tile OSM va rispettata anche nell'app).
