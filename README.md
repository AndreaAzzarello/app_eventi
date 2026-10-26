# Eventi Vicini

L'agenda degli eventi locali dell'area di Modena: concerti, sagre, mostre, mercatini e attività per bambini, in lista e su mappa.
Un'unica codebase Flutter per **web (PWA)**, **Android** e **iOS**.

## Funzionalità

- **Lista** e **Mappa** (OpenStreetMap con `flutter_map`), marker colorati per categoria; tap sul marker apre il dettaglio.
- Su schermi larghi (≥ 900 px, desktop/tablet/web) lista e mappa sono affiancate; su smartphone sono in tab separati.
- Filtri: **Oggi**, **Weekend**, **Gratis**, **Bambini**, categoria, ricerca testuale e raggio in km.
- Dettaglio con data e ora in italiano, indirizzo, **Apri in Maps**, **Biglietti**, preferito e **Aggiungi al calendario**
  (calendario di sistema su mobile, download di un file `.ics` sul web).
- **Preferiti** salvati sul dispositivo (`shared_preferences`).
- Posizione con `geolocator`; se il permesso è negato si usa Modena centro (44.6471, 10.9252).
- Tema Material 3 chiaro e scuro.
- **Area admin** su `/admin` (login Google) per creare, modificare ed eliminare eventi.
- **Import automatico** giornaliero dagli eventi pubblici dei comuni (GitHub Actions + `tools/importer`).

## Requisiti

- Flutter 3.35+ (Dart 3.7+): `flutter --version`
- Chrome per il web; Android Studio / SDK Android per Android; Xcode (solo macOS) per iOS
- Node.js + Firebase CLI per il deploy: `npm install -g firebase-tools`
- Un progetto Firebase con Cloud Firestore attivo (quello attuale è `appeventi-1e860`), **piano Spark gratuito**
- Python 3.12+ per l'importer

## Setup

```bash
git clone https://github.com/AndreaAzzarello/app_eventi.git
cd app_eventi
flutter pub get
```

### Configurare Firebase

`lib/firebase_options.dart` è già presente ma contiene solo la configurazione **Android**.
Per web e iOS va rigenerato con FlutterFire CLI:

```bash
firebase login
dart pub global activate flutterfire_cli
flutterfire configure --project=appeventi-1e860 --platforms=android,ios,web
```

Il comando registra le app mancanti nel progetto Firebase e riscrive `lib/firebase_options.dart`
(e `android/app/google-services.json`). Se `flutterfire` non viene trovato, aggiungi al `PATH`
la cartella `%LOCALAPPDATA%\Pub\Cache\bin` (Windows) o `~/.pub-cache/bin` (macOS/Linux).

Se Firebase non è configurato per la piattaforma corrente l'app si avvia lo stesso
e mostra "Impossibile caricare gli eventi".

### Regole Firestore

`firestore.rules`: lettura pubblica di `events`; scrittura solo all'admin
(`request.auth.token.email == 'azzatubo@gmail.com'` con `email_verified == true`) e con i campi
minimi (`title`, `startTime`, `endTime`, `lat`, `lng`) del tipo giusto. Tutto il resto è chiuso.
L'importer usa l'Admin SDK, che non passa dalle regole.

```bash
firebase deploy --only firestore:rules
```

Per cambiare admin modifica l'email **sia** in `firestore.rules` **sia** in `lib/features/auth/auth.dart`
(la seconda serve solo a mostrare la UI giusta: il controllo vero sono le regole).

L'app legge solo gli eventi non ancora finiti (`endTime >= ora`, ordinati per `endTime`, max 500):
basta l'indice a campo singolo che Firestore crea da solo, quindi non serve `firestore.indexes.json`.
Si filtra su `endTime` e non su `startTime` per non perdere mostre e rassegne già iniziate.

Schema di un documento `events`:

| campo | tipo | note |
|---|---|---|
| `title`, `shortDescription`, `venueName`, `address` | string | |
| `category` | string | `music`, `food`, `culture`, `sport`, `kids`, `market`, `other` |
| `priceType` | string | `free`, `low`, `premium` |
| `startTime`, `endTime` | number (ms) o timestamp | |
| `lat`, `lng` | number | |
| `imageUrl`, `ticketUrl` | string | possono essere vuoti |
| `tags` | array di string | `kids` o `family` attivano il filtro Bambini |
| `source` | string | `manual` (admin) o `scraper` (importer); assente = `manual` |
| `sourceUrl` | string | pagina originale; nell'app diventa il link "Fonte" |
| `createdAt`, `updatedAt` | number (ms) | |

## Admin

L'area admin è su **`/admin`** (es. `https://appeventi-1e860.web.app/admin`): non compare nella
navigazione, ci si arriva solo dall'URL. Gli URL sono "veri" (senza `#`) grazie a `usePathUrlStrategy()`
e alla rewrite di `firebase.json`.

- Login con Google; se l'account non è quello admin compare "Account non autorizzato".
- Lista di tutti gli eventi, anche passati, con ricerca; tap per modificare, cestino per eliminare (con conferma).
- Form con validazione: titolo, descrizione breve, categoria, prezzo, inizio/fine, luogo, indirizzo,
  URL immagine e biglietti (solo `http(s)`), tag, flag bambini (tag `kids`).
- **Trova coordinate** geocodifica l'indirizzo con Nominatim (solo Italia, max 1 richiesta al secondo);
  il pin si sposta toccando la mini-mappa.
- Le immagini sono solo URL (nessun upload, niente Cloud Storage).
- Un evento importato e modificato a mano diventa `manual`: l'importer non lo sovrascrive più.

### Abilitare il login Google (Console Firebase, gratuito)

1. [Console Firebase](https://console.firebase.google.com/project/appeventi-1e860/authentication) →
   **Authentication** → **Inizia** (se è la prima volta).
2. Scheda **Metodo di accesso** → **Aggiungi nuovo provider** → **Google** → **Attiva**,
   scegli l'email di assistenza → **Salva**.
3. Scheda **Impostazioni** → **Domini autorizzati**: devono esserci `localhost`,
   `appeventi-1e860.web.app` e `appeventi-1e860.firebaseapp.com` (di solito già presenti).
4. **Android**: Impostazioni progetto → app Android → **Aggiungi impronta digitale** con lo SHA-1
   (e SHA-256) della chiave di debug e di quella di release. Lo SHA-1 di debug si ottiene con
   `cd android && ./gradlew signingReport`. Poi riscarica `google-services.json` (o rilancia `flutterfire configure`).
5. **iOS**: in `ios/Runner/Info.plist` è già registrato lo schema URL con l'Encoded App ID
   (`app-1-398100140878-ios-aabd7a6ffdf7862c6f441f`). Se il login non torna all'app, aggiungi anche
   il `REVERSED_CLIENT_ID` presente in `GoogleService-Info.plist`.

## Importer

`tools/importer` è uno script Python che legge gli eventi pubblici dei comuni e li scrive in `events`.

**Fonti** (tutte siti design-comuni-plone con API REST pubblica `++api++/@search`, niente scraping HTML):

| fonte | robots.txt | termini |
|---|---|---|
| Comune di Modena | tutto consentito | riuso senza fini di lucro citando la fonte; art. 7 D.Lgs. 33/2013 |
| Comune di Formigine | tutto consentito | come Modena |
| Comune di Sassuolo | tutto consentito | note legali non leggibili in automatico: da verificare a mano |
| Comune di Mirandola | tutto consentito | riuso citando la fonte |

L'app cita la fonte con il link "Fonte" nel dettaglio. Il riuso è consentito **senza fini di lucro**:
se l'app diventa commerciale, chiedi l'autorizzazione ai comuni.

**Pipeline**: estrazione paginata (1 richiesta/s) → normalizzazione nel modello Event (categoria da
`tipologia_evento` o dal titolo, prezzo dal testo, fuso `Europe/Rome`, prossima occorrenza per gli eventi
ricorrenti, orario reale dal campo `orari` quando quello inserito è fittizio) → coordinate dal luogo,
altrimenti Nominatim con cache in `geocache.json` → id deterministico (hash di `sourceUrl`) e deduplica
per titolo + giorno + luogo → upsert → eliminazione degli eventi `scraper` finiti da oltre 7 giorni.
Si importano gli eventi in corso o che iniziano entro 60 giorni (`--horizon-days`).

```bash
cd tools/importer
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q tests          # test del mapping con fixture reali
python run.py --dry-run            # stampa senza scrivere (non servono credenziali)
python run.py --dry-run --source formigine
```

Per scrivere su Firestore serve una chiave di service account, passata **solo** da variabile d'ambiente
(mai committarla: `.gitignore` esclude `*serviceAccount*.json`, `*-firebase-adminsdk-*.json`, `.env`):

```powershell
# Windows PowerShell: chiave salvata FUORI dal repo
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\<utente>\keys\appeventi-importer.json"
python run.py
python seed_demo.py            # carica 10 eventi demo (id fissi demo-01..10)
python seed_demo.py --delete   # li rimuove
```

In alternativa `FIREBASE_SERVICE_ACCOUNT` può contenere direttamente il JSON della chiave (è quello che usa GitHub Actions).

### Generare e revocare la chiave del service account

1. Console Firebase → ⚙️ **Impostazioni progetto** → **Account di servizio**.
2. **Firebase Admin SDK** → **Genera nuova chiave privata** → **Genera chiave**: si scarica un file JSON.
   Spostalo fuori dal repository. È gratuito e non richiede il piano Blaze.
3. **Revoca**: dalla stessa pagina apri **Gestisci le autorizzazioni dell'account di servizio**
   (Google Cloud Console → IAM → Account di servizio) → account `firebase-adminsdk-…` → scheda **Chiavi**
   → elimina la chiave. Chi la usa smette subito di funzionare; generane una nuova e aggiorna il secret.

## GitHub Actions

`.github/workflows/import-events.yml` esegue l'importer **ogni giorno alle 06:17 ora italiana**
(`timezone: Europe/Rome`) e si può avviare a mano da **Actions → Import eventi → Run workflow**,
con l'opzione *dry_run*. Prima dell'import gira `pytest`; la cache del geocoding è salvata con `actions/cache`.

Configurare il secret:

1. Genera la chiave come sopra e apri il file JSON con un editor.
2. GitHub → repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
3. Nome `FIREBASE_SERVICE_ACCOUNT`, valore: **tutto** il contenuto del JSON → **Add secret**.
4. Cancella il file locale se non ti serve più.
5. Per revocare: elimina la chiave in Google Cloud (vedi sopra) e poi il secret su GitHub.

Sui repository pubblici GitHub Actions è gratuito; i workflow schedulati vengono sospesi dopo 60 giorni
senza attività sul repository (basta riattivarli dalla scheda Actions).

## Avvio

```bash
flutter run -d chrome     # web
flutter run -d android    # dispositivo/emulatore Android (oppure l'id da `flutter devices`)
flutter run -d ios        # solo su macOS
```

## Test e qualità

```bash
flutter analyze
flutter test
cd tools/importer && python -m pytest -q tests
```

## Deploy su Firebase Hosting

```bash
flutter build web --release
firebase deploy --only hosting,firestore:rules
```

`firebase.json` pubblica `build/web` e reindirizza ogni percorso a `index.html`.
L'app sarà su `https://appeventi-1e860.web.app`.

## Struttura

```
lib/
  app/theme.dart                  tema, colori e icone delle categorie
  common/utils/                   distanza (haversine) e formattazione date/prezzi
  features/events/                modello Event, filtri, EventService (Firestore), provider Riverpod
  features/auth/                  login Google e stato admin
  features/admin/                 scritture admin, validatori del form, geocoding Nominatim
  features/favorites/             FavoritesStore (shared_preferences)
  features/location/              posizione utente con fallback
  features/calendar/              add_2_calendar (mobile) e file .ics (web)
  pages/                          home (lista/mappa/preferiti) e dettaglio
  pages/admin/                    area admin: accesso, lista eventi, form
tools/importer/                   importer Python, seed_demo.py, test pytest
.github/workflows/                import giornaliero
  widgets/                        card, barra filtri, mappa, stati vuoto/errore
```

## Mappe

Le tile sono quelle pubbliche di OpenStreetMap, con attribuzione "© OpenStreetMap contributors".
La [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) non consente traffico intenso:
in produzione con molti utenti passa a un provider dedicato (es. MapTiler, Stadia, Thunderforest)
cambiando `urlTemplate` in `lib/widgets/events_map.dart`.
