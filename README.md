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
- In debug, il pulsante ✨ carica 10 eventi demo (`seedSampleEvents`).

## Requisiti

- Flutter 3.35+ (Dart 3.7+): `flutter --version`
- Chrome per il web; Android Studio / SDK Android per Android; Xcode (solo macOS) per iOS
- Node.js + Firebase CLI per il deploy: `npm install -g firebase-tools`
- Un progetto Firebase con Cloud Firestore attivo (quello attuale è `appeventi-1e860`)

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

`firestore.rules` permette la sola lettura della collezione `events`; le scritture dai client sono negate.

```bash
firebase deploy --only firestore:rules
```

Gli eventi si inseriscono dalla console Firebase o con l'Admin SDK. Il pulsante demo funziona
solo contro l'emulatore Firestore o allentando temporaneamente le regole.

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
```

## Deploy su Firebase Hosting

```bash
flutter build web --release
firebase deploy --only hosting
```

`firebase.json` pubblica `build/web` e reindirizza ogni percorso a `index.html`.
L'app sarà su `https://appeventi-1e860.web.app`.

## Struttura

```
lib/
  app/theme.dart                  tema, colori e icone delle categorie
  common/utils/                   distanza (haversine) e formattazione date/prezzi
  features/events/                modello Event, filtri, EventService (Firestore), provider Riverpod
  features/favorites/             FavoritesStore (shared_preferences)
  features/location/              posizione utente con fallback
  features/calendar/              add_2_calendar (mobile) e file .ics (web)
  pages/                          home (lista/mappa/preferiti) e dettaglio
  widgets/                        card, barra filtri, mappa, stati vuoto/errore
```

## Mappe

Le tile sono quelle pubbliche di OpenStreetMap, con attribuzione "© OpenStreetMap contributors".
La [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) non consente traffico intenso:
in produzione con molti utenti passa a un provider dedicato (es. MapTiler, Stadia, Thunderforest)
cambiando `urlTemplate` in `lib/widgets/events_map.dart`.
