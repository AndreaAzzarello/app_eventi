# Prossimi passi di sicurezza

Dall'audit di sicurezza del 30 ottobre 2026 (run-1). Le correzioni a basso costo sono già fatte (limiti nel Worker, regole, intestazioni e CSP, privacy, `safeNext`, `submittedBy`). Restano questi punti.

## A2 — Chiudere la lettura diretta di Firestore (alta)
**Problema.** Le regole hanno `allow read: if true` su `events`, `bundles`, `coverage` e `stats`, e la chiave web Firebase è pubblica (`web/wrangler.toml`). Chiunque può interrogare Firestore via REST senza passare dal Worker, quindi i limiti e le cache del Worker non servono contro un abuso intenzionale: bastano poche richieste per esaurire le 50.000 letture giornaliere del piano Spark. Sito e importer (budget 40.000 letture) si fermano fino al reset; nessun dato va perso.

**Opzioni, dalla più forte alla più debole**
1. **Account di servizio in sola lettura per il Worker.** Il Worker firma un token OAuth con WebCrypto (chiave in un segreto Cloudflare) e legge con quello; le regole passano a lettura solo admin per `events`, `bundles`, `coverage`, `stats`. Chiude davvero la porta. Costo: 1-2 giorni, un nuovo segreto, il token va rinnovato (scade in un'ora, si tiene in cache). Prima di toccare le regole il Worker deve essere già in produzione con il token, altrimenti il sito smette di leggere. Attenzione: la webapp legge `stats` e `events` dal browser anche nell'area admin (già coperta da `isAdmin()`).
2. **App Check (reCAPTCHA gratuito)** sulle chiamate del browser, con applicazione obbligatoria su Firestore. Da solo non protegge le letture REST fatte dal Worker (non ha un token App Check), quindi va abbinato all'opzione 1 oppure il Worker deve presentare un token App Check generato con l'Admin SDK. Utile soprattutto per limitare le scritture degli utenti (preferiti, proposte).
3. **Restringere la chiave API** nella console Google (referrer HTTP e API ammesse). Meno forte: il Worker non invia un referrer e un attaccante può falsificarlo; da usare solo come difesa aggiuntiva.

**Ordine consigliato.** 1) implementare e pubblicare il Worker con l'account di servizio, 2) verificare le letture in produzione, 3) pubblicare le regole con lettura chiusa (`npm run deploy:rules` in `firebase/`), 4) attivare App Check per le scritture degli utenti. Aggiornare `README.md`/`docs/architettura.md` (oggi dicono che la lettura è pubblica) e i test delle regole.

**Vincoli.** Tutto gratis, nessuna carta: account di servizio e reCAPTCHA sono gratuiti. Non mettere la chiave dell'account di servizio nel repository (solo variabili Cloudflare).

## Altri punti aperti
- Console Firebase/Google: provider attivi (solo Google e link email), domini autorizzati, restrizioni della chiave API (da lì dipende la sicurezza dell'admin, basata sull'email verificata).
- Token GitHub del Worker `scheduler/`: fine-grained, un solo repository, solo Actions: write.
- Rate limiting su `/api/*` e `/eventi/*`: richiede un dominio proprio sulla zona Cloudflare (non c'è su `pages.dev`).
- Importer: allowlist degli host di biglietteria, limite di dimensione delle risposte, `persist-credentials: false` nei checkout senza push, action GitHub fissate per commit, Dependabot.
- `/citta/<slug>`: costa una lettura per ogni slug nuovo (cache 6 ore); non validabile sulla copertura perché le città con eventi ma fuori da `coverage` devono restare raggiungibili.
- Dipendenze: dev di `web/` con 6 vulnerabilità basse risolvibili solo con aggiornamenti major; `pytest` 8.4.2 (PYSEC-2026-1845, solo test). Da rivedere al prossimo aggiornamento maggiore.
